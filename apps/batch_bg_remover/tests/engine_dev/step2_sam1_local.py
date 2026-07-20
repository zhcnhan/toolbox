#!/usr/bin/env python3
"""
engine_dev/step2_sam1_local.py

完整端到端管线：Qwen3-VL Box 定位 + 本地 SAM 1（ViT-L）分割 + 合成透明 PNG。

运行：
  cd apps/batch_bg_remover
  $env:SILICONFLOW_API_KEY="你的Key"
  python tests/engine_dev/step2_sam1_local.py

环境变量：
  SILICONFLOW_API_KEY  (必填，硅基流动 API Key)
"""

import base64
import io
import json
import os
import re
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from segment_anything import sam_model_registry, SamPredictor

try:
    from scipy import ndimage

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def keep_large_components(mask: np.ndarray, min_area: int = 0) -> np.ndarray:
    """
    保留二值 mask 中面积 >= min_area 的连通区域。
    min_area=0 表示不做清理。
    """
    if not HAS_SCIPY or min_area <= 0:
        return mask
    labeled, num_features = ndimage.label(mask)
    if num_features <= 1:
        return mask
    sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
    keep = np.where(sizes >= min_area)[0] + 1
    if len(keep) == 0:
        return mask
    return np.isin(labeled, keep)


# ── UI 图标抠图（颜色距离法）───────────────────────────────────────


def remove_bg_by_color(img: np.ndarray, border_ratio: float = 0.06) -> np.ndarray:
    """
    通过采样边缘检测背景颜色，按像素颜色距离生成 alpha 通道。
    适用于纯色/渐变背景的 UI 图标（头像框、按钮等）。
    返回 RGBA numpy array (h, w, 4)。
    """
    h, w = img.shape[:2]

    # 采样四条边获取背景色
    bw = max(int(min(h, w) * border_ratio), 2)
    top = img[:bw, :].reshape(-1, 3)
    bottom = img[-bw:, :].reshape(-1, 3)
    left = img[bw:-bw, :bw].reshape(-1, 3)
    right = img[bw:-bw, -bw:].reshape(-1, 3)
    border_pixels = np.vstack([top, bottom, left, right]).astype(np.float32)
    bg_color = np.median(border_pixels, axis=0)

    # 每像素到背景色的欧几里得距离
    diff = img.astype(np.float32) - bg_color
    dist = np.sqrt(np.sum(diff ** 2, axis=2))
    dist_norm = dist / np.sqrt(3 * 255 ** 2)  # [0, 1]

    # smoothstep 映射：接近背景 → 透明，远离背景 → 不透明
    lo, hi = 0.02, 0.12
    alpha = np.clip((dist_norm - lo) / (hi - lo), 0.0, 1.0)

    # 轻微高斯模糊平滑边缘
    if HAS_SCIPY:
        alpha = ndimage.gaussian_filter(alpha, sigma=0.8)

    # 只保留面积 >= 0.3% 图面积的连通分量
    min_area = int(h * w * 0.003)
    alpha_bin = (alpha > 0.1).astype(np.uint8)
    alpha_bin = keep_large_components(alpha_bin, min_area)
    alpha = alpha * alpha_bin.astype(np.float32)

    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, :3] = img
    result[:, :, 3] = (alpha * 255).astype(np.uint8)
    return result


# ── 路径配置 ──────────────────────────────────────────────────────
_MODEL_DIR = Path(__file__).parent
_SAM_CHECKPOINT = _MODEL_DIR / "sam_vit_l_0b3195.pth"
_TEST_DIR = _MODEL_DIR.parent  # tests/

# ── 测试用例 ──────────────────────────────────────────────────────
# method="sam"  = SAM 分割（自然照片）
# method="icon" = 颜色距离抠图（UI 图标，纯色/渐变背景）
TEST_CASES = [
    (_TEST_DIR / "test_frame_gold.jpg", "金色圆形头像框", "icon"),
    (_TEST_DIR / "test_frame_dark.jpg", "深色圆形头像框", "icon"),
    (_TEST_DIR / "test_button_newstory.jpg", "New Story 游戏按钮", "icon"),
]

# ── Step 1: Box 定位（复用 step1 的逻辑）───────────────────────────
MODEL = "Qwen/Qwen3-VL-32B-Instruct"
API_BASE = "https://api.siliconflow.cn/v1/chat/completions"
_MAX_IMG_SIZE = 800

PROMPT = """你是一个精准的视觉定位助手。给定一张图片和一段描述，找出描述所指的物体，并返回其 bounding box。

请使用 Qwen3-VL 的标准格式：
<box>[[x_min, y_min, x_max, y_max]]</box>

坐标规则：
- x_min, y_min, x_max, y_max 都是归一化到 0-1000 的整数
- (x_min, y_min) 是 box 左上角，(x_max, y_max) 是 box 右下角
- 四边必须紧贴物体最外侧像素，包括该物体穿戴/携带的任何附属物（帽子、衣服、围巾等）
- 框必须紧密包裹，不要把大面积无关背景包进去。不要让框覆盖整张图片
- 如果图中没有该物体，返回空 box：<box>[]</box>

返回格式示例：
<box>[[120, 200, 400, 800]]</box>

只输出 <box> 标签，不要输出其他文字。

要定位的物体："""


def detect_box(api_key: str, image_path: Path, object_prompt: str) -> dict:
    """调用 Qwen3-VL 返回 {box_2d: [ymin, xmin, ymax, xmax], label: ...}，坐标 0-1000。"""
    img = Image.open(image_path).convert("RGB")
    orig_w, orig_h = img.size
    if max(orig_w, orig_h) > _MAX_IMG_SIZE:
        ratio = _MAX_IMG_SIZE / max(orig_w, orig_h)
        img = img.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT + object_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ]
        }],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    resp = requests.post(API_BASE, json=payload, headers=headers, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"API 失败: HTTP {resp.status_code} - {resp.text[:400]}")

    data = resp.json()
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not content:
        raise RuntimeError("模型未返回文本")

    match = re.search(r"<box>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]</box>", content)
    if not match:
        if "<box>[]</box>" in content or "<box> </box>" in content:
            return {"box_2d": [], "label": "not found"}
        raise RuntimeError(f"未能提取 box: {content[:300]}")

    x_min, y_min, x_max, y_max = map(int, match.groups())
    return {
        "box_2d": [y_min, x_min, y_max, x_max],
        "label": object_prompt,
    }


def box_to_pixels(box_2d: list, img_w: int, img_h: int, margin: float = 0.12) -> tuple:
    """
    box_2d: [ymin, xmin, ymax, xmax] 0-1000 归一化
    返回像素坐标 (x1, y1, x2, y2)，并 clamp 到图片边界内。

    自适应策略：
    - 普通框：外扩 margin 12%
    - 超大框（原始面积 > 80%）：不再外扩，而是内缩 5% 左右/底部，
      顶部保留，避免把背景篱笆和猫头顶的配饰裁掉。
    """
    ymin, xmin, ymax, xmax = box_2d
    x1 = int(xmin / 1000 * img_w)
    y1 = int(ymin / 1000 * img_h)
    x2 = int(xmax / 1000 * img_w)
    y2 = int(ymax / 1000 * img_h)

    bw, bh = x2 - x1, y2 - y1
    box_area = bw * bh
    img_area = img_w * img_h

    if box_area / img_area > 0.8:
        # 超大框 → 非对称内缩，顶部保留帽子
        shrink_x = int(bw * 0.05)
        shrink_y_bottom = int(bh * 0.05)
        x1 = min(x1 + shrink_x, x2 - 1)
        x2 = max(x2 - shrink_x, x1 + 1)
        y2 = max(y2 - shrink_y_bottom, y1 + 1)
        print(f"  [Box] 原始框已占 {box_area / img_area:.0%}，内缩为 ({x1},{y1})-({x2},{y2})")
    else:
        x1 = max(0, int(x1 - bw * margin))
        y1 = max(0, int(y1 - bh * margin))
        x2 = min(img_w, int(x2 + bw * margin))
        y2 = min(img_h, int(y2 + bh * margin))
    return x1, y1, x2, y2


# ── Step 2: SAM 1 本地分割 ────────────────────────────────────────

# 全局加载一次
_sam_predictor = None


def get_predictor() -> SamPredictor:
    global _sam_predictor
    if _sam_predictor is None:
        if not _SAM_CHECKPOINT.exists():
            raise FileNotFoundError(
                f"SAM 模型文件不存在: {_SAM_CHECKPOINT}\n"
                f"请下载: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth"
            )
        print(f"  [SAM] 加载模型: {_SAM_CHECKPOINT.name} ({_SAM_CHECKPOINT.stat().st_size / 1e6:.0f}MB)...")
        sam = sam_model_registry["vit_l"](checkpoint=str(_SAM_CHECKPOINT))
        _sam_predictor = SamPredictor(sam)
        print("  [SAM] 模型就绪")
    return _sam_predictor


def segment_with_box(image_np: np.ndarray, box_px: tuple) -> np.ndarray:
    """
    image_np: RGB numpy (H, W, 3)
    box_px: (x1, y1, x2, y2) 像素坐标
    返回 bool mask (H, W)，True = 前景。

    策略：
    1. Box-only：小/中框，SAM 最稳定。
    2. 大框（>60%面积）：如果框是纵向（高明显大于宽）且主体居中，
       用 1 个中心正样本 + 4 个角点负样本引导 SAM。否则 box-only。
    3. 中等框（40-60%）：加 4 角负样本作为轻量背景提示。
    4. 结果可疑 → multimask 兜底。
    5. 前景主要落在框外 → 自动翻转。
    6. 只去除面积 < 1% 图片的孤立小碎片。
    """
    x1, y1, x2, y2 = box_px
    predictor = get_predictor()
    predictor.set_image(image_np)

    h, w = image_np.shape[:2]
    box_mask = np.zeros((h, w), dtype=bool)
    box_mask[y1:y2, x1:x2] = True
    box_area = int(np.sum(box_mask))
    box_area_ratio = box_area / (w * h)

    input_box = np.array([x1, y1, x2, y2])

    bw, bh = x2 - x1, y2 - y1
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    img_cx, img_cy = w / 2, h / 2
    is_centered = abs(cx - img_cx) / w < 0.12 and abs(cy - img_cy) / h < 0.12
    is_portrait = bh > bw * 1.05

    # 构建提示点
    if box_area_ratio > 0.6 and is_portrait and is_centered:
        # 纵向居中主体（如猫）：1 中心正 + 4 角负
        pos_points = np.array([[cx, cy]], dtype=np.float32)
        pos_labels = np.array([1], dtype=np.int32)

        margin_px = min(30, bw // 15, bh // 15)
        neg_points = np.array([
            [x1 + margin_px, y1 + margin_px],
            [x2 - margin_px, y1 + margin_px],
            [x1 + margin_px, y2 - margin_px],
            [x2 - margin_px, y2 - margin_px],
        ], dtype=np.float32)
        neg_labels = np.array([0, 0, 0, 0], dtype=np.int32)

        point_coords = np.vstack([pos_points, neg_points])
        point_labels = np.hstack([pos_labels, neg_labels])
        print(f"  [SAM] 纵向居中主体（{box_area_ratio:.0%}），启用 1 正 + 4 负提示点")
    elif box_area_ratio > 0.4:
        # 中等大框或靠边主体 → 仅 4 角负样本
        margin_px = min(20, bh // 10, bw // 10)
        point_coords = np.array([
            [x1 + margin_px, y1 + margin_px],
            [x2 - margin_px, y1 + margin_px],
            [x1 + margin_px, y2 - margin_px],
            [x2 - margin_px, y2 - margin_px],
        ], dtype=np.float32)
        point_labels = np.array([0, 0, 0, 0], dtype=np.int32)
    else:
        point_coords = None
        point_labels = None

    # Step 1: 单 mask 尝试
    masks, scores, _ = predictor.predict(
        point_coords=point_coords,
        point_labels=point_labels,
        box=input_box[None, :],
        multimask_output=False,
    )
    mask = masks[0].astype(bool)
    score = float(scores[0]) if len(scores) > 0 else 0.0
    fg_inside = int(np.sum(mask & box_mask))
    fg_outside = int(np.sum(mask & ~box_mask))
    fg_ratio_in_box = fg_inside / box_area if box_area > 0 else 0.0

    # Step 2: 可疑检测 → 多候选兜底
    need_fallback = (box_area_ratio > 0.6 and score < 0.75) or (
        box_area_ratio > 0.4 and (fg_ratio_in_box < 0.20 or score < 0.75)
    )
    if need_fallback:
        print(f"  [SAM] 单 mask 可疑 (框占 {box_area_ratio:.0%}, 前景占框 {fg_ratio_in_box:.0%}, 得分={score:.3f})，启用多候选...")
        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            box=input_box[None, :],
            multimask_output=True,
        )
        # 把单 mask 也纳入候选
        all_masks = list(masks) + [mask]
        all_scores = list(scores) + [score]

        best_idx = 0
        best_candidate_score = -1.0
        for i, m in enumerate(all_masks):
            m_bool = m.astype(bool)
            c_fg_inside = int(np.sum(m_bool & box_mask))
            c_fg_outside = int(np.sum(m_bool & ~box_mask))
            total_fg = c_fg_inside + c_fg_outside
            inside_ratio = c_fg_inside / total_fg if total_fg > 0 else 0.0
            candidate_score = inside_ratio * float(all_scores[i])
            if candidate_score > best_candidate_score:
                best_candidate_score = candidate_score
                best_idx = i
        mask = all_masks[best_idx].astype(bool)
        score = float(all_scores[best_idx]) if len(all_scores) > best_idx else 0.0
        fg_inside = int(np.sum(mask & box_mask))
        fg_outside = int(np.sum(mask & ~box_mask))

    # Step 3: 如果最佳 mask 仍主要落在框外，翻转
    if fg_outside > fg_inside:
        print(f"  [SAM] 检测到 mask 反转 (框内={fg_inside}px, 框外={fg_outside}px)，自动翻转")
        mask = ~mask
        fg_inside, fg_outside = fg_outside, fg_inside

    # Step 4: 只去除面积 < 1% 图片的孤立小碎片
    original_fg = int(mask.sum())
    mask = keep_large_components(mask, min_area=int(w * h * 0.01))
    removed = original_fg - int(mask.sum())
    if removed:
        print(f"  [SAM] 后处理：去除 {removed} 个孤立前景像素（<1% 图面积）")
        fg_inside = int(np.sum(mask & box_mask))
        fg_outside = int(np.sum(mask & ~box_mask))

    fg_ratio = mask.sum() / (w * h) * 100
    print(
        f"  [SAM] mask 得分: {score:.4f}, 前景: {fg_ratio:.0f}% "
        f"(框内={fg_inside}px 框外={fg_outside}px)"
    )
    return mask



# ── Step 3: 合成透明 PNG ──────────────────────────────────────────


def composite_transparent(image_np: np.ndarray, mask: np.ndarray) -> Image.Image:
    """将 RGB 图像 + bool mask 合成为 RGBA 透明 PNG。"""
    rgba = np.zeros((image_np.shape[0], image_np.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = image_np
    rgba[:, :, 3] = mask.astype(np.uint8) * 255
    return Image.fromarray(rgba, mode="RGBA")


def make_comparison(
    original: Image.Image,
    box_px: tuple,
    mask: np.ndarray,
    result: Image.Image,
    output_path: Path,
    object_prompt: str,
    elapsed_s: float,
) -> None:
    """生成 2×2 对比图并保存。"""
    w, h = original.size
    thumb_w = min(w, 600)
    thumb_h = int(h * thumb_w / w)

    # 左上：原图 + 红框
    vis_box = original.convert("RGBA").resize((thumb_w, thumb_h), Image.LANCZOS)
    scale = thumb_w / w
    draw = ImageDraw.Draw(vis_box)
    x1, y1, x2, y2 = box_px
    draw.rectangle(
        [int(x1 * scale), int(y1 * scale), int(x2 * scale), int(y2 * scale)],
        outline=(255, 0, 0),
        width=3,
    )

    # 右上：mask（灰底）
    mask_img = Image.fromarray((mask.astype(np.uint8) * 255), mode="L").resize(
        (thumb_w, thumb_h), Image.LANCZOS
    )
    mask_rgba = Image.new("RGBA", (thumb_w, thumb_h), (128, 128, 128, 255))
    mask_alpha = mask_img.convert("L")
    mask_colored = Image.new("RGBA", (thumb_w, thumb_h), (102, 204, 255, 255))
    mask_rgba.paste(mask_colored, (0, 0), mask_alpha)

    # 左下：透明结果（棋盘格背景）
    result_thumb = result.resize((thumb_w, thumb_h), Image.LANCZOS)
    checker = Image.new("RGBA", (thumb_w, thumb_h))
    cs = 12
    for cy in range(0, thumb_h, cs):
        for cx in range(0, thumb_w, cs):
            color = (180, 180, 180, 255) if ((cx // cs) + (cy // cs)) % 2 == 0 else (220, 220, 220, 255)
            ImageDraw.Draw(checker).rectangle([cx, cy, cx + cs - 1, cy + cs - 1], fill=color)
    checker.paste(result_thumb, (0, 0), result_thumb)

    # 组装 2×2
    canvas = Image.new("RGBA", (thumb_w * 2, thumb_h * 2 + 30), (30, 30, 30, 255))
    canvas.paste(vis_box, (0, 0))
    canvas.paste(mask_rgba, (thumb_w, 0))
    canvas.paste(checker, (0, thumb_h))
    # 右下：信息
    info = Image.new("RGBA", (thumb_w, thumb_h), (30, 30, 30, 255))
    font = None
    for fp in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simsun.ttc", "arial.ttf"]:
        try:
            font = ImageFont.truetype(fp, size=16)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    info_text = (
        f"提示词: {object_prompt}\n"
        f"Box: ({x1},{y1})-({x2},{y2})\n"
        f"原图: {w}x{h}\n"
        f"耗时: {elapsed_s:.1f}s\n"
        f"SAM 1 ViT-L (CPU)"
    )
    draw_info = ImageDraw.Draw(info)
    draw_info.text((10, 10), info_text, fill=(200, 200, 200, 255), font=font)
    canvas.paste(info, (thumb_w, thumb_h))

    canvas.convert("RGB").save(output_path, quality=92)
    print(f"  对比图: {output_path}")


# ── 主流程 ────────────────────────────────────────────────────────


def run(api_key: str, image_path: Path, object_prompt: str, output_dir: Path,
        method: str = "sam") -> None:
    safe_name = re.sub(r"[^\w\-]", "_", f"{image_path.stem}_{object_prompt}")
    t_start = time.time()

    print(f"\n{'=' * 60}")
    print(f"图片: {image_path.name}  |  方法: {method}")
    print(f"标签: {object_prompt}")

    img = Image.open(image_path).convert("RGB")
    img_w, img_h = img.size
    image_np = np.array(img)

    # ── icon 模式：颜色距离抠图 ──
    if method == "icon":
        print(f"[1/1] 颜色距离抠图...")
        result_img_rgba = remove_bg_by_color(image_np)
        png_path = output_dir / f"step2_sam1_{safe_name}.png"
        Image.fromarray(result_img_rgba).save(png_path)
        elapsed = time.time() - t_start
        print(f"  透明PNG: {png_path}")
        print(f"  总耗时: {elapsed:.1f}s")
        return

    # ── sam 模式 ──
    # [1] Box 定位
    print(f"[1/3] Qwen3-VL 定位...")
    result = detect_box(api_key, image_path, object_prompt)
    box = result["box_2d"]
    if not box or len(box) != 4:
        raise RuntimeError("未检测到目标物体")
    print(f"  归一化坐标: {box}")

    # [2] SAM 1 分割
    print(f"[2/3] SAM 1 ViT-L 分割...")
    x1, y1, x2, y2 = box_to_pixels(box, img_w, img_h, margin=0.12)
    print(f"  Box (像素): ({x1},{y1}) -> ({x2},{y2}), 尺寸: {x2 - x1}x{y2 - y1}")

    mask = segment_with_box(image_np, (x1, y1, x2, y2))
    fg_pixels = mask.sum()
    print(f"  前景像素: {fg_pixels} / {img_w * img_h} ({fg_pixels / (img_w * img_h) * 100:.1f}%)")

    # [3] 合成
    print(f"[3/3] 合成透明 PNG...")
    result_img = composite_transparent(image_np, mask)
    png_path = output_dir / f"step2_sam1_{safe_name}.png"
    result_img.save(png_path)
    print(f"  透明PNG: {png_path}")

    elapsed = time.time() - t_start
    comp_path = output_dir / f"step2_sam1_{safe_name}_comparison.jpg"
    make_comparison(img, (x1, y1, x2, y2), mask, result_img, comp_path, object_prompt, elapsed)
    print(f"  总耗时: {elapsed:.1f}s")


def main():
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        raise RuntimeError("请设置环境变量 SILICONFLOW_API_KEY")

    output_dir = _MODEL_DIR

    for image_path, prompt, method in TEST_CASES:
        if not image_path.exists():
            print(f"跳过（文件不存在）: {image_path}")
            continue
        try:
            run(api_key, image_path, prompt, output_dir, method=method)
        except Exception as e:
            print(f"  [FAIL] {e}")

    print(f"\n{'=' * 60}")
    print("全部测试完成，查看 tests/engine_dev/step2_sam1_*.jpg")


if __name__ == "__main__":
    main()

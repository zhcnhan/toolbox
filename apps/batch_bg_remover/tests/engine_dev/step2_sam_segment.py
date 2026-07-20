#!/usr/bin/env python3
"""
engine_dev/step2_sam_segment.py

Step 2: SAM 2 分割测试。
模式 A：全图 + Box Prompt → SAM 2 在框内分割 → 返回全图 Mask → 合成透明 PNG

流程：
  1. 读取图片 + 提示词
  2. 调用 Qwen3-VL 获取 Box（复用 Step 1 逻辑）
  3. Box 外扩 margin，转为像素坐标
  4. 全图 + Box → SAM 2 API
  5. Mask 合成 → 透明 PNG
  6. 保存 4 格对比图

运行：
  $env:SILICONFLOW_API_KEY="..."
  $env:REPLICATE_API_TOKEN="..."
  python tests/engine_dev/step2_sam_segment.py

首次运行先安装 replicate SDK：
  pip install replicate
"""

import base64
import io
import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont

# ── 配置 ─────────────────────────────────────────────────────────
BOX_MODEL = "Qwen/Qwen3-VL-32B-Instruct"
BOX_API_BASE = "https://api.siliconflow.cn/v1/chat/completions"

SAM_MODEL = "meta/sam-2"

_MARGIN_PERCENT = 0.12  # Box 外扩比例
_MAX_IMG_SIZE = 800     # 传给 Qwen 的压缩尺寸
_POLL_INTERVAL = 3      # Replicate 轮询间隔（秒）
_MAX_WAIT = 120         # 最大等待时间（秒）

BOX_PROMPT = """你是一个精准的视觉定位助手。给定一张图片和一段描述，找出描述所指的物体，并返回其 bounding box。

请使用 Qwen3-VL 的标准格式：
<box>[[x_min, y_min, x_max, y_max]]</box>

坐标规则：
- x_min, y_min, x_max, y_max 都是归一化到 0-1000 的整数
- (x_min, y_min) 是 box 左上角，(x_max, y_max) 是 box 右下角
- 四边必须贴合物体的最外侧像素
- 如果图中没有该物体，返回空 box：<box>[]</box>

返回格式示例：
<box>[[120, 200, 400, 800]]</box>

只输出 <box> 标签，不要输出其他文字。

要定位的物体："""

# ── 测试配置 ─────────────────────────────────────────────────────
_BASE_DIR = Path(__file__).parent.parent  # tests/
IMAGE_PATH = _BASE_DIR / "test_bird.jpg"
OBJECT_PROMPT = "左边那只鸟"
OUTPUT_DIR = Path(__file__).parent  # engine_dev/

# 添加新测试直接改这里
TEST_IMAGE_PATH = _BASE_DIR / "test_bird.jpg"
TEST_OBJECT = "左边那只鸟"


# ═════════════════════════════════════════════════════════════════
#  Step 1 复用 — Box 检测
# ═════════════════════════════════════════════════════════════════

def _encode_for_box_api(image_path: Path) -> tuple[str, tuple[int, int]]:
    """压缩图片到最长边 _MAX_IMG_SIZE 并返回 base64 + 原始尺寸"""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    if img.width > _MAX_IMG_SIZE or img.height > _MAX_IMG_SIZE:
        ratio = _MAX_IMG_SIZE / max(img.width, img.height)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8"), (w, h)


def detect_box(api_key: str, image_b64: str, object_prompt: str) -> list:
    """调用硅基流动 Qwen3-VL 返回归一化 box [ymin, xmin, ymax, xmax]"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": BOX_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": BOX_PROMPT + object_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ]
        }],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    resp = requests.post(BOX_API_BASE, json=payload, headers=headers, timeout=120)
    if resp.status_code == 429:
        raise RuntimeError("硅基流动额度已用完")
    if resp.status_code != 200:
        raise RuntimeError(f"Box API 失败: HTTP {resp.status_code} - {resp.text[:400]}")

    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("模型未返回文本")

    match = re.search(r"<box>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]</box>", content)
    if not match:
        if "<box>[]</box>" in content:
            raise RuntimeError(f"模型报告未找到物体: \"{object_prompt}\"")
        raise RuntimeError(f"未能提取 box: {content[:300]}")

    x_min, y_min, x_max, y_max = map(int, match.groups())
    return [y_min, x_min, y_max, x_max]  # [ymin, xmin, ymax, xmax]


def box_to_pixels(box_norm: list, img_w: int, img_h: int, margin: float = _MARGIN_PERCENT) -> tuple[int, int, int, int]:
    """
    归一化 box → 像素坐标（x1, y1, x2, y2），带 margin 外扩。
    box_norm: [ymin, xmin, ymax, xmax]  (0-1000)
    返回: (x1, y1, x2, y2) 像素坐标，已 clamp
    """
    ymin, xmin, ymax, xmax = box_norm
    x1 = int(xmin / 1000 * img_w)
    y1 = int(ymin / 1000 * img_h)
    x2 = int(xmax / 1000 * img_w)
    y2 = int(ymax / 1000 * img_h)

    # 外扩 margin
    bw, bh = x2 - x1, y2 - y1
    mx = int(bw * margin)
    my = int(bh * margin)
    x1, y1 = max(0, x1 - mx), max(0, y1 - my)
    x2, y2 = min(img_w, x2 + mx), min(img_h, y2 + my)

    return x1, y1, x2, y2


# ═════════════════════════════════════════════════════════════════
#  Step 2 — SAM 2 API
# ═════════════════════════════════════════════════════════════════

def _upload_to_replicate_data_uri(image_path: Path) -> str:
    """将图片转为 data URI"""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def call_sam2_sdk(api_token: str, image_data_uri: str, box_px: tuple) -> Image.Image:
    """通过 replicate Python SDK 调用 SAM 2（需要 pip install replicate）"""
    try:
        import replicate  # type: ignore
    except ImportError:
        raise RuntimeError("请先安装 replicate: pip install replicate")

    client = replicate.Client(api_token=api_token)

    x1, y1, x2, y2 = box_px
    input_data: dict = {
        "image": image_data_uri,
        "box": [x1, y1, x2, y2],
    }

    print(f"  调用 Replicate SAM2... (box=[{x1},{y1},{x2},{y2}])")
    t0 = time.time()

    # 尝试运行
    prediction = client.predictions.create(
        model=SAM_MODEL,
        input=input_data,
    )

    # 轮询
    while prediction.status not in ("succeeded", "failed", "canceled"):
        time.sleep(_POLL_INTERVAL)
        prediction.reload()
        elapsed = time.time() - t0
        print(f"  ... {prediction.status} ({elapsed:.0f}s)")

    elapsed = time.time() - t0
    if prediction.status != "succeeded":
        raise RuntimeError(f"SAM2 失败: {prediction.status} - {prediction.error}")

    output = prediction.output
    print(f"  SAM2 完成 ({elapsed:.0f}s)")

    return _parse_sam2_output(output)


def call_sam2_rest(api_token: str, image_data_uri: str, box_px: tuple) -> Image.Image:
    """通过 Replicate REST API（无需安装 SDK）调用 SAM 2"""
    x1, y1, x2, y2 = box_px
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json",
    }

    # 创建预测
    create_resp = requests.post(
        "https://api.replicate.com/v1/predictions",
        json={
            "model": SAM_MODEL,
            "input": {
                "image": image_data_uri,
                "box": [x1, y1, x2, y2],
            },
        },
        headers=headers,
        timeout=30,
    )
    if create_resp.status_code != 201:
        raise RuntimeError(f"Replicate 创建预测失败: HTTP {create_resp.status_code} - {create_resp.text[:400]}")

    pred = create_resp.json()
    prediction_url = pred.get("urls", {}).get("get", "")
    if not prediction_url:
        raise RuntimeError("Replicate 未返回轮询 URL")

    print(f"  调用 Replicate SAM2... (box=[{x1},{y1},{x2},{y2}])")
    t0 = time.time()

    # 轮询
    status = "starting"
    while status not in ("succeeded", "failed", "canceled"):
        time.sleep(_POLL_INTERVAL)
        poll_resp = requests.get(prediction_url, headers=headers, timeout=10)
        if poll_resp.status_code != 200:
            raise RuntimeError(f"Replicate 轮询失败: HTTP {poll_resp.status_code}")
        pred = poll_resp.json()
        status = pred.get("status", "failed")
        elapsed = time.time() - t0
        print(f"  ... {status} ({elapsed:.0f}s)")
        if elapsed > _MAX_WAIT:
            raise RuntimeError(f"SAM2 超时 ({_MAX_WAIT}s)")

    elapsed = time.time() - t0
    if status != "succeeded":
        raise RuntimeError(f"SAM2 失败: {pred.get('error', 'unknown')}")

    output = pred.get("output")
    print(f"  SAM2 完成 ({elapsed:.0f}s)")

    return _parse_sam2_output(output)


def _parse_sam2_output(output) -> Image.Image:
    """解析 SAM2 返回，统一转为 PIL Image (mode='L')"""
    # 可能是 URL 字符串
    if isinstance(output, str):
        resp = requests.get(output, timeout=30)
        if resp.status_code == 200:
            return Image.open(io.BytesIO(resp.content)).convert("L")
        raise RuntimeError(f"下载 mask 失败: HTTP {resp.status_code}")

    # 可能是包含多个 mask 的列表
    if isinstance(output, list):
        if not output:
            raise RuntimeError("SAM2 返回空结果")
        item = output[0]
        if isinstance(item, dict) and "mask" in item:
            output = item["mask"]
        elif isinstance(item, str):
            output = item
        else:
            raise RuntimeError(f"无法解析 SAM2 输出: {type(item)}")
        if isinstance(output, str):
            resp = requests.get(output, timeout=30)
            return Image.open(io.BytesIO(resp.content)).convert("L")

    # 可能是 dict
    if isinstance(output, dict):
        mask_url = output.get("mask") or output.get("image") or output.get("url")
        if mask_url:
            resp = requests.get(mask_url, timeout=30)
            return Image.open(io.BytesIO(resp.content)).convert("L")
        raise RuntimeError(f"SAM2 输出字典中未找到 mask URL: {list(output.keys())[:5]}")

    raise RuntimeError(f"无法解析 SAM2 输出类型: {type(output)}")


def call_sam2(api_token: str, image_path: Path, box_px: tuple) -> Image.Image:
    """
    调用 SAM 2 API，统一入口。
    优先尝试 SDK，回退到 REST API。
    """
    data_uri = _upload_to_replicate_data_uri(image_path)

    try:
        return call_sam2_sdk(api_token, data_uri, box_px)
    except (ImportError, RuntimeError) as e:
        if isinstance(e, ImportError):
            print("  [INFO] replicate SDK 未安装，改用 REST API")
        return call_sam2_rest(api_token, data_uri, box_px)


# ═════════════════════════════════════════════════════════════════
#  合成 & 可视化
# ═════════════════════════════════════════════════════════════════

def composite_transparent(original_path: Path, mask: Image.Image) -> Image.Image:
    """将 mask 应用到原图，生成 RGBA 透明 PNG"""
    original = Image.open(original_path).convert("RGBA")
    if mask.size != original.size:
        mask = mask.resize(original.size, Image.LANCZOS)
    # mask 中 0 = 背景（透明），非 0 = 前景（保留）
    r, g, b, _ = original.split()
    return Image.merge("RGBA", (r, g, b, mask))


def _load_font() -> ImageFont.FreeTypeFont:
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "arial.ttf",
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size=18)
        except Exception:
            continue
    return ImageFont.load_default()


def save_comparison(
    original_path: Path,
    box_norm: list,
    box_px: tuple,
    mask: Image.Image,
    composite: Image.Image,
    output_path: Path,
) -> None:
    """保存 4 格对比图：原图+框 | mask | 透明结果"""
    original = Image.open(original_path).convert("RGBA")
    w, h = original.size
    font = _load_font()

    # 1) 原图 + Box 标注
    img_box = original.copy()
    draw = ImageDraw.Draw(img_box)
    x1, y1, x2, y2 = box_px
    draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=3)
    draw.text((x1, max(0, y1 - 22)), f"box: {box_norm}", fill=(255, 0, 0), font=font)

    # 2) Mask（灰底显示）
    img_mask = Image.new("RGBA", (w, h), (128, 128, 128, 255))
    mask_rgba = mask.convert("RGBA")
    if mask_rgba.size != (w, h):
        mask_rgba = mask_rgba.resize((w, h), Image.LANCZOS)
    img_mask = Image.alpha_composite(img_mask, mask_rgba)

    # 3) 透明结果
    img_result = composite.convert("RGBA")

    # 拼成 2x2
    canvas = Image.new("RGBA", (w * 2, h * 2), (255, 255, 255, 255))
    canvas.paste(img_box, (0, 0))
    canvas.paste(img_mask, (w, 0))
    # 左下：Checkerboard 背景 + 透明结果
    checker = _checkerboard((w, h), tile=20)
    checker.paste(img_result, (0, 0), img_result)
    canvas.paste(checker, (0, h))
    # 右下：文字信息
    info = Image.new("RGBA", (w, h), (245, 245, 245, 255))
    info_draw = ImageDraw.Draw(info)
    lines = [
        f"原始尺寸: {original.size[0]}x{original.size[1]}",
        f"Box (0-1000): {box_norm}",
        f"Box (像素): {box_px}",
        f"掩膜写入: {output_path.name}",
    ]
    for i, line in enumerate(lines):
        info_draw.text((20, 20 + i * 28), line, fill=(60, 60, 60), font=font)
    canvas.paste(info, (w, h))

    canvas.convert("RGB").save(output_path, quality=92)
    print(f"  对比图 -> {output_path}")


def _checkerboard(size: tuple[int, int], tile: int = 20) -> Image.Image:
    """生成透明棋盘格背景"""
    w, h = size
    img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            if (x // tile + y // tile) % 2 == 0:
                continue
            for dy in range(tile):
                for dx in range(tile):
                    px, py = x + dx, y + dy
                    if px < w and py < h:
                        img.putpixel((px, py), (220, 220, 220, 255))
    return img


# ═════════════════════════════════════════════════════════════════
#  主流程
# ═════════════════════════════════════════════════════════════════

class Step2Runner:
    """Step 2 完整管线"""

    def __init__(self, box_api_key: str, sam2_api_token: str):
        self.box_key = box_api_key
        self.sam2_token = sam2_api_token

    def run(self, image_path: Path, object_prompt: str) -> tuple[Path, Path]:
        """
        运行完整管线，返回 (comparison_image_path, transparent_png_path)
        """
        print(f"\n{'='*60}")
        print(f"Step 2: {image_path.name}  \"{object_prompt}\"")
        print(f"{'='*60}")

        # ── Step 2.1: Box 检测 ──
        print("\n[2.1] Box 检测")
        image_b64, (w, h) = _encode_for_box_api(image_path)
        print(f"  图片: {w}x{h}")
        box_norm = detect_box(self.box_key, image_b64, object_prompt)
        print(f"  Box (0-1000): {box_norm}")

        box_px = box_to_pixels(box_norm, w, h)
        print(f"  Box (像素):  {box_px}")

        # ── Step 2.2: SAM 2 分割 ──
        print("\n[2.2] SAM 2 分割")
        mask = call_sam2(self.sam2_token, image_path, box_px)
        print(f"  Mask 尺寸: {mask.size}")

        # ── Step 2.3: 合成透明 PNG ──
        print("\n[2.3] 合成透明 PNG")
        transparent = composite_transparent(image_path, mask)

        # ── Step 2.4: 保存结果 ──
        safe_name = re.sub(r"[^\w\-]", "_", f"{image_path.stem}_{object_prompt}")
        comparison_path = OUTPUT_DIR / f"step2_{safe_name}_comparison.jpg"
        png_path = OUTPUT_DIR / f"step2_{safe_name}.png"

        transparent.save(png_path, "PNG")
        print(f"  透明 PNG -> {png_path}")

        save_comparison(image_path, box_norm, box_px, mask, transparent, comparison_path)

        return comparison_path, png_path


def main():
    box_key = os.environ.get("SILICONFLOW_API_KEY")
    sam2_token = os.environ.get("REPLICATE_API_TOKEN")

    if not box_key:
        raise RuntimeError("请设置 SILICONFLOW_API_KEY")
    if not sam2_token:
        raise RuntimeError("请设置 REPLICATE_API_TOKEN")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    runner = Step2Runner(box_key, sam2_token)

    # ── 测试用例 ──
    test_cases = [
        (_BASE_DIR / "test_bird.jpg", "左边那只鸟"),
        (_BASE_DIR / "test_bird.jpg", "右边那只鸟"),
    ]

    for img_path, prompt in test_cases:
        if not img_path.exists():
            print(f"\n[SKIP] 图片不存在: {img_path}")
            continue
        try:
            runner.run(img_path, prompt)
        except Exception as e:
            print(f"\n[ERROR] {img_path.name} \"{prompt}\": {e}")

    print(f"\n完成。输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

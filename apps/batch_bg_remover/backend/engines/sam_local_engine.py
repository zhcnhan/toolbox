"""
engines/sam_local_engine.py — 本地 SAM 1 ViT-L 引擎

管线：Qwen3-VL Box 定位（云端）→ 本地 SAM 1 ViT-L 分割 → 合成透明 PNG。
支持自动抠图（默认"画面中的主体"）和文本提示词两种模式。
"""

import base64
import io
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image

from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine

try:
    from segment_anything import sam_model_registry, SamPredictor
    HAS_SAM = True
except ImportError:
    HAS_SAM = False

try:
    from scipy import ndimage
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

logger = logging.getLogger(__name__)

# ── 配置 ──────────────────────────────────────────────────────────
_VL_MODEL = "Qwen/Qwen3-VL-32B-Instruct"
_VL_API = "https://api.siliconflow.cn/v1/chat/completions"
_MAX_IMG_SIZE = 800

_SAM_DIR = Path(os.environ.get("SAM_MODEL_DIR", os.path.expanduser("~/.cache/sam")))
_SAM_CHECKPOINT = _SAM_DIR / "sam_vit_l_0b3195.pth"
_SAM_DOWNLOAD_URL = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth"
# 镜像列表（国内加速）
_SAM_MIRRORS = [
    "https://ghproxy.net/{}",
    "https://gh-proxy.com/{}",
    "https://mirror.ghproxy.com/{}",
    "https://github.moeyy.xyz/{}",
    "{}",  # 直连（最后试）
]

# ── 模型下载任务（全局状态） ────────────────────────────────────
_SAM_DOWNLOAD_TASK: dict = {
    "running": False,
    "progress": 0,
    "error": "",
    "stage": "",
    "downloaded_bytes": 0,
    "total_bytes": 0,
}


def get_sam_status() -> dict:
    """返回 SAM 模型状态，供 API 和前端查询"""
    exists = _SAM_CHECKPOINT.exists()
    size = _SAM_CHECKPOINT.stat().st_size if exists else 0
    return {
        "engine_id": "sam_local",
        "model_exists": exists,
        "model_size_mb": round(size / 1e6, 1) if exists else 0,
        "model_path": str(_SAM_CHECKPOINT),
        "download_url": _SAM_DOWNLOAD_URL,
        **_SAM_DOWNLOAD_TASK,
    }


def _update_progress(progress: int, stage: str = "", downloaded: int = 0, total: int = 0):
    _SAM_DOWNLOAD_TASK["progress"] = progress
    if stage:
        _SAM_DOWNLOAD_TASK["stage"] = stage
    if downloaded:
        _SAM_DOWNLOAD_TASK["downloaded_bytes"] = downloaded
    if total:
        _SAM_DOWNLOAD_TASK["total_bytes"] = total


def _download_sam_model_background():
    """后台线程：下载 SAM 模型到 _SAM_DIR，多镜像轮询"""
    _SAM_DOWNLOAD_TASK["running"] = True
    _SAM_DOWNLOAD_TASK["error"] = ""
    _SAM_DOWNLOAD_TASK["progress"] = 0
    _SAM_DOWNLOAD_TASK["stage"] = "准备下载..."
    _SAM_DOWNLOAD_TASK["downloaded_bytes"] = 0
    _SAM_DOWNLOAD_TASK["total_bytes"] = 0

    try:
        _SAM_DIR.mkdir(parents=True, exist_ok=True)

        # 遍历镜像
        for mirror_template in _SAM_MIRRORS:
            url = mirror_template.format(_SAM_DOWNLOAD_URL)
            host = url.split("/")[2]
            _update_progress(0, f"正在连接 {host}...")

            try:
                resp = requests.get(url, stream=True, timeout=(15, 180))
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                _SAM_DOWNLOAD_TASK["total_bytes"] = total

                # 校验：模型至少 1GB
                if total > 0 and total < 1_000_000_000:
                    logger.warning("镜像 %s 返回文件过小 (%d bytes)，跳过", host, total)
                    continue

                temp_path = _SAM_DIR / ".sam_download.tmp"
                downloaded = 0
                last_pct = -1
                chunk_size = 1024 * 1024  # 1MB
                with open(temp_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            pct = min(int(downloaded / total * 100), 99) if total else 0
                            if pct != last_pct:
                                _update_progress(
                                    pct, f"下载中... ({downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB)",
                                    downloaded, total,
                                )
                                last_pct = pct

                # 下载完成，移到最终路径
                import shutil
                shutil.move(str(temp_path), str(_SAM_CHECKPOINT))
                final_size = _SAM_CHECKPOINT.stat().st_size

                if final_size > 1_000_000_000:
                    _update_progress(100, "下载完成", final_size, final_size)
                    logger.info("SAM 模型下载完成: %s (%.1fMB)", _SAM_CHECKPOINT, final_size / 1e6)
                    _SAM_DOWNLOAD_TASK["running"] = False
                    return
                else:
                    # 文件太小，删除重试
                    _SAM_CHECKPOINT.unlink(missing_ok=True)
                    logger.warning("镜像 %s 下载文件大小异常 (%d bytes)，换下一个", host, final_size)

            except requests.RequestException as e:
                logger.warning("镜像 %s 下载失败: %s", host, str(e)[:100])
                continue

        # 全部镜像都失败
        _SAM_DOWNLOAD_TASK["error"] = "所有镜像下载失败，请手动下载"
        _SAM_DOWNLOAD_TASK["stage"] = "下载失败"

    except Exception as e:
        _SAM_DOWNLOAD_TASK["error"] = str(e)
        _SAM_DOWNLOAD_TASK["stage"] = "下载异常"
        logger.error("SAM 模型下载异常: %s", e)
    finally:
        _SAM_DOWNLOAD_TASK["running"] = False


def trigger_sam_download() -> dict:
    """触发 SAM 模型下载（如果尚未下载且不在运行中）"""
    if _SAM_CHECKPOINT.exists():
        return {"status": "already_cached", "progress": 100}
    if _SAM_DOWNLOAD_TASK["running"]:
        return {"status": "downloading", "progress": _SAM_DOWNLOAD_TASK["progress"]}

    thread = threading.Thread(target=_download_sam_model_background, daemon=True)
    thread.start()
    return {"status": "started", "progress": 0, "stage": "准备下载..."}

_BOX_PROMPT = """你是一个精准的视觉定位助手。给定一张图片和一段描述，找出描述所指的物体，并返回其 bounding box。

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

# ── 全局 SAM 单例 ─────────────────────────────────────────────────
_sam_predictor = None


def _get_predictor() -> "SamPredictor":
    """懒加载 SAM 模型单例"""
    global _sam_predictor
    if _sam_predictor is not None:
        return _sam_predictor

    if not HAS_SAM:
        raise RuntimeError(
            "segment-anything 未安装。请运行: pip install segment-anything"
        )

    if not _SAM_CHECKPOINT.exists():
        _SAM_DIR.mkdir(parents=True, exist_ok=True)
        raise RuntimeError(
            f"SAM 模型文件不存在，请在网页上点击「开始下载」自动下载，"
            f"或手动下载并放置到 {_SAM_CHECKPOINT}\n  {_SAM_DOWNLOAD_URL}"
        )

    logger.info(
        "加载 SAM 模型: %s (%.0fMB)...",
        _SAM_CHECKPOINT.name, _SAM_CHECKPOINT.stat().st_size / 1e6,
    )
    sam = sam_model_registry["vit_l"](checkpoint=str(_SAM_CHECKPOINT))
    _sam_predictor = SamPredictor(sam)
    logger.info("SAM 模型就绪")
    return _sam_predictor


# ── 工具函数 ─────────────────────────────────────────────────────


def _resize_for_api(img: Image.Image) -> Image.Image:
    """将图片缩放到 API 允许的最大尺寸"""
    w, h = img.size
    if max(w, h) > _MAX_IMG_SIZE:
        ratio = _MAX_IMG_SIZE / max(w, h)
        return img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    return img


def _build_retry_session() -> requests.Session:
    """构建带重试机制的 requests Session"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=2.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _detect_box(api_key: str, image_bytes: bytes, prompt: str,
                max_retries: int = 3, timeout: int = 300) -> list:
    """调用 Qwen3-VL 返回 box_2d [xmin, ymin, xmax, ymax] 0-1000 归一化"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = _resize_for_api(img)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    payload = {
        "model": _VL_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": _BOX_PROMPT + prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}"
                }},
            ],
        }],
        "temperature": 0.1,
        "max_tokens": 512,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    session = _build_retry_session()
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = session.post(
                _VL_API, json=payload, headers=headers, timeout=timeout,
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"硅基流动 API 失败: HTTP {resp.status_code} - {resp.text[:300]}"
                )
            content = (
                resp.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if not content:
                raise RuntimeError("Qwen3-VL 未返回文本")

            match = re.search(
                r"<box>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]</box>", content,
            )
            if not match:
                if "<box>[]</box>" in content or "<box> </box>" in content:
                    raise RuntimeError(f"在图中未找到「{prompt}」")
                raise RuntimeError(f"未能提取 box: {content[:200]}")
            return [int(x) for x in match.groups()]

        except requests.Timeout as e:
            last_error = e
            wait = 5 * (attempt + 1)
            logger.warning(
                "VL API 超时 (尝试 %d/%d), %ds 后重试...",
                attempt + 1, max_retries, wait,
            )
            if attempt < max_retries - 1:
                time.sleep(wait)
        except requests.ConnectionError as e:
            last_error = e
            wait = 3 * (attempt + 1)
            logger.warning(
                "VL API 连接失败 (尝试 %d/%d), %ds 后重试...",
                attempt + 1, max_retries, wait,
            )
            if attempt < max_retries - 1:
                time.sleep(wait)

    raise RuntimeError(
        f"硅基流动 API 请求失败（已重试 {max_retries} 次）: {last_error}"
    )


def _box_to_pixels(box_xy: list, img_w: int, img_h: int,
                   margin: float = 0.12) -> tuple:
    """
    box_xy: [xmin, ymin, xmax, ymax] 0-1000
    返回 (x1, y1, x2, y2) 像素坐标

    自适应策略：
    - 普通框：外扩 margin
    - 超大框（>80% 面积）：非对称内缩（顶部保留，左右底部各缩 5%）
    """
    xmin, ymin, xmax, ymax = box_xy
    x1 = int(xmin / 1000 * img_w)
    y1 = int(ymin / 1000 * img_h)
    x2 = int(xmax / 1000 * img_w)
    y2 = int(ymax / 1000 * img_h)

    bw, bh = x2 - x1, y2 - y1
    box_area = bw * bh
    img_area = img_w * img_h

    if box_area / img_area > 0.8:
        # 超大框 → 非对称内缩，顶部保留（帽子等）
        shrink_x = int(bw * 0.05)
        shrink_y_bottom = int(bh * 0.05)
        x1 = min(x1 + shrink_x, x2 - 1)
        x2 = max(x2 - shrink_x, x1 + 1)
        y2 = max(y2 - shrink_y_bottom, y1 + 1)
    else:
        x1 = max(0, int(x1 - bw * margin))
        y1 = max(0, int(y1 - bh * margin))
        x2 = min(img_w, int(x2 + bw * margin))
        y2 = min(img_h, int(y2 + bh * margin))
    return x1, y1, x2, y2


def _keep_large_components(mask: np.ndarray, min_area: int = 0) -> np.ndarray:
    """保留 mask 中面积 >= min_area 的连通区域"""
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


def _segment_with_box(image_np: np.ndarray, box_px: tuple) -> np.ndarray:
    """
    SAM 分割：给定图像和像素框，返回 bool mask
    image_np: (H, W, 3) RGB
    box_px: (x1, y1, x2, y2)
    """
    x1, y1, x2, y2 = box_px
    h, w = image_np.shape[:2]
    predictor = _get_predictor()
    predictor.set_image(image_np)

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
        margin_px = min(30, bw // 15, bh // 15)
        point_coords = np.array([
            [cx, cy],
            [x1 + margin_px, y1 + margin_px],
            [x2 - margin_px, y1 + margin_px],
            [x1 + margin_px, y2 - margin_px],
            [x2 - margin_px, y2 - margin_px],
        ], dtype=np.float32)
        point_labels = np.array([1, 0, 0, 0, 0], dtype=np.int32)
    elif box_area_ratio > 0.4:
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

    # Step 1: 单 mask
    masks, scores, _ = predictor.predict(
        point_coords=point_coords,
        point_labels=point_labels,
        box=input_box[None, :],
        multimask_output=False,
    )
    mask = masks[0].astype(bool)
    score = float(scores[0]) if len(scores) > 0 else 0.0
    fg_inside = int(np.sum(mask & box_mask))
    fg_ratio_in_box = fg_inside / box_area if box_area > 0 else 0.0

    # Step 2: 可疑 → 多候选兜底
    need_fallback = (box_area_ratio > 0.6 and score < 0.75) or (
        box_area_ratio > 0.4 and (fg_ratio_in_box < 0.20 or score < 0.75)
    )
    if need_fallback:
        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            box=input_box[None, :],
            multimask_output=True,
        )
        all_masks = list(masks) + [mask]
        all_scores = list(scores) + [score]
        best_idx, best_score = 0, -1.0
        for i, m in enumerate(all_masks):
            m_bool = m.astype(bool)
            c_fg_inside = int(np.sum(m_bool & box_mask))
            total_fg = int(np.sum(m_bool))
            inside_ratio = c_fg_inside / total_fg if total_fg > 0 else 0.0
            cs = inside_ratio * float(all_scores[i])
            if cs > best_score:
                best_score, best_idx = cs, i
        mask = all_masks[best_idx].astype(bool)
        fg_inside = int(np.sum(mask & box_mask))

    # Step 3: 如果最佳 mask 仍主要落在框外，翻转
    fg_outside = int(np.sum(mask & ~box_mask))
    if fg_outside > fg_inside:
        mask = ~mask

    # Step 4: 去除面积 < 1% 的孤立碎片
    original_fg = int(mask.sum())
    mask = _keep_large_components(mask, min_area=int(w * h * 0.01))
    removed = original_fg - int(mask.sum())
    if removed:
        logger.debug("后处理：去除 %d 个孤立前景像素", removed)

    fg_ratio = mask.sum() / (w * h) * 100
    logger.info(
        "SAM 结果 — 得分: %.4f, 前景: %.1f%%, "
        "框内=%dpx 框外=%dpx", score, fg_ratio, fg_inside, fg_outside,
    )
    return mask


def _composite_transparent(image_np: np.ndarray, mask: np.ndarray) -> bytes:
    """RGB + bool mask → RGBA PNG bytes"""
    rgba = np.zeros((image_np.shape[0], image_np.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = image_np
    rgba[:, :, 3] = mask.astype(np.uint8) * 255
    buf = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG")
    return buf.getvalue()


# ── 引擎实现 ─────────────────────────────────────────────────────


@register_engine("sam_local")
class SamLocalEngine(BaseEngine):
    """本地 SAM 1 ViT-L 引擎"""

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="sam_local",
            name="SAM 1 ViT-L (本地)",
            description=(
                "Qwen3-VL 智能定位 + 本地 SAM ViT-L 分割，"
                "精度高，支持文本提示选取特定物体"
            ),
            type="local",
            supports_auto=False,  # 自动模式也要调 Qwen3-VL 花钱，只开放提示词模式
            supports_prompt=True,
            needs_api_key=True,
            api_key_label="硅基流动 API Key",
            api_key_help_url="https://cloud.siliconflow.cn/account/ak",
            icon="🎯",
        )

    async def remove_bg(self, image_bytes: bytes,
                        api_key: Optional[str] = None) -> bytes:
        """自动抠图：以"画面中的主体"为目标"""
        return await self.remove_bg_with_prompt(
            image_bytes, "画面中的主体", api_key=api_key,
        )

    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str,
        api_key: Optional[str] = None,
    ) -> bytes:
        if not api_key:
            raise ValueError(
                "SAM 本地引擎需要硅基流动 API Key 进行目标定位，"
                "请在设置中填写"
            )

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_w, img_h = img.size
        image_np = np.array(img)

        # [1] Box 定位
        t0 = time.time()
        box = _detect_box(api_key, image_bytes, prompt)
        x1, y1, x2, y2 = _box_to_pixels(box, img_w, img_h, margin=0.12)
        logger.info(
            "Box 定位: (%.0f%%,%.0f%%)→(%.0f%%,%.0f%%) | "
            "像素: (%d,%d)→(%d,%d) | 耗时 %.1fs",
            box[0] / 10, box[1] / 10, box[2] / 10, box[3] / 10,
            x1, y1, x2, y2, time.time() - t0,
        )

        # [2] SAM 分割
        mask = _segment_with_box(image_np, (x1, y1, x2, y2))

        # [3] 合成
        result = _composite_transparent(image_np, mask)
        logger.info("总耗时 %.1fs", time.time() - t0)
        return result

"""
engines/icon_bg_engine.py — UI 图标背景去除引擎

通过采样图像边缘检测背景颜色，按像素颜色距离生成 alpha 通道。
适用于纯色/渐变背景的 UI 图标（头像框、按钮、徽章等）。

算法简介：
  1. 采样图片四条边的像素，取中位数作为背景色
  2. 计算每个像素到背景色的欧几里得距离（RGB 空间）
  3. 用 smoothstep 将距离映射为 alpha（接近背景→透明，远离→不透明）
  4. 高斯模糊平滑边缘，去除 <0.3% 面积的噪点
"""

import io
import logging
from typing import Optional

import numpy as np
from PIL import Image

from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine

try:
    from scipy import ndimage
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

logger = logging.getLogger(__name__)

# 连通分量保留最小面积（图面积占比）
_MIN_COMPONENT_RATIO = 0.003


def _remove_bg_by_color(
    img: np.ndarray,
    border_ratio: float = 0.06,
    lo: float = 0.02,
    hi: float = 0.12,
    sigma: float = 0.8,
) -> np.ndarray:
    """
    颜色距离法去背景。

    参数:
        img: (H, W, 3) RGB numpy array
        border_ratio: 采样边缘占图的比例
        lo, hi: smoothstep 阈值（[0,1]，归一化颜色距离）
            lo 以下 → alpha=0（透明），hi 以上 → alpha=1（不透明）
        sigma: 高斯模糊 sigma

    返回:
        (H, W, 4) RGBA numpy array
    """
    h, w = img.shape[:2]

    # 1. 采样四条边获取背景色（中位数比均值更抗干扰）
    bw = max(int(min(h, w) * border_ratio), 2)
    top = img[:bw, :].reshape(-1, 3)
    bottom = img[-bw:, :].reshape(-1, 3)
    left = img[bw:-bw, :bw].reshape(-1, 3)
    right = img[bw:-bw, -bw:].reshape(-1, 3)
    border_pixels = np.vstack([top, bottom, left, right]).astype(np.float32)
    bg_color = np.median(border_pixels, axis=0)

    # 2. 每像素到背景色的欧几里得距离 → [0,1]
    diff = img.astype(np.float32) - bg_color
    dist = np.sqrt(np.sum(diff ** 2, axis=2))
    dist_norm = dist / np.sqrt(3 * 255 ** 2)

    # 3. smoothstep 映射
    alpha = np.clip((dist_norm - lo) / (hi - lo), 0.0, 1.0)

    # 4. 高斯模糊平滑边缘
    if HAS_SCIPY:
        alpha = ndimage.gaussian_filter(alpha, sigma=sigma)

    # 5. 去除面积 < 0.3% 的零星噪点
    min_area = int(h * w * _MIN_COMPONENT_RATIO)
    if HAS_SCIPY and min_area > 0:
        alpha_bin = (alpha > 0.1).astype(np.uint8)
        labeled, num_features = ndimage.label(alpha_bin)
        if num_features > 1:
            sizes = ndimage.sum(alpha_bin, labeled, range(1, num_features + 1))
            keep = np.where(sizes >= min_area)[0] + 1
            if len(keep) > 0:
                alpha = alpha * np.isin(labeled, keep).astype(np.float32)

    # 6. 组装 RGBA
    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, :3] = img
    result[:, :, 3] = (alpha * 255).astype(np.uint8)
    return result


@register_engine("icon_bg")
class IconBgEngine(BaseEngine):
    """UI 图标背景去除引擎（颜色距离法）"""

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="icon_bg",
            name="图标抠图 (本地)",
            description=(
                "颜色距离法，自动检测背景色并去除。"
                "适用于纯色/渐变背景的 UI 图标、头像框、按钮等"
            ),
            type="local",
            supports_auto=True,
            supports_prompt=False,
            needs_api_key=False,
            icon="🖼️",
        )

    async def remove_bg(self, image_bytes: bytes,
                        api_key: Optional[str] = None) -> bytes:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(img)

        result_rgba = _remove_bg_by_color(image_np)

        buf = io.BytesIO()
        Image.fromarray(result_rgba, mode="RGBA").save(buf, format="PNG")
        logger.info("图标抠图完成 (%dx%d)", img.width, img.height)
        return buf.getvalue()

    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str,
        api_key: Optional[str] = None,
    ) -> bytes:
        raise NotImplementedError(
            "图标抠图引擎无需提示词，请直接使用自动抠图模式"
        )

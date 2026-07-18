"""
engines/clipseg_local_engine.py — 本地文本提示词分割引擎

基于 CLIPSeg (https://github.com/timojl/clipseg)
支持通过文本提示词（如"猫"、"红色汽车"、"左边的人"）指定要分割的主体

安装依赖：pip install transformers torch pillow

注意：首次运行会自动下载模型（~1.5GB），之后缓存复用。
此引擎为可选引擎，未安装 transformers/torch 时不会加载（不影响其他引擎）。
"""

import io
import json
from pathlib import Path

import numpy as np
from PIL import Image
from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine

# 本地模型路径（可通过 snapshot_download 预下载，避免联网）
_LOCAL_MODEL_DIR = Path("/app/clipseg-model")

# 默认 processor 配置（当 HuggingFace 下载不完整时自动补全）
_DEFAULT_PROCESSOR_CONFIG = {
    "image_processor_type": "CLIPSegProcessor",
    "do_resize": True,
    "size": {"height": 352, "width": 352},
    "do_normalize": True,
    "image_mean": [0.485, 0.456, 0.406],
    "image_std": [0.229, 0.224, 0.225],
}


def _ensure_model_dir(model_dir: Path):
    """确保模型目录完整，缺失的配置文件自动补全"""
    if not model_dir.exists():
        return False

    # 补全缺失的 processor_config.json
    proc_file = model_dir / "processor_config.json"
    if not proc_file.exists():
        proc_file.write_text(json.dumps(_DEFAULT_PROCESSOR_CONFIG, indent=2), encoding="utf-8")

    # 补全缺失的 preprocessor_config.json（部分 transformers 版本需要）
    preproc_file = model_dir / "preprocessor_config.json"
    if not preproc_file.exists() and proc_file.exists():
        preproc_file.write_text(proc_file.read_text(encoding="utf-8"), encoding="utf-8")

    return True


@register_engine("clipseg_local")
class CLIPSegLocalEngine(BaseEngine):
    """本地 CLIPSeg 文本提示词分割引擎"""

    _processor = None
    _model = None

    def _load_model(self):
        if self._model is None:
            from transformers import CLIPSegProcessor, CLIPSegForImageSegmentation
            import torch

            # 优先从本地路径加载（离线部署场景）
            if _ensure_model_dir(_LOCAL_MODEL_DIR):
                model_id = str(_LOCAL_MODEL_DIR)
            else:
                model_id = "CIDAS/clipseg-rd64-refined"

            self._processor = CLIPSegProcessor.from_pretrained(model_id)
            self._model = CLIPSegForImageSegmentation.from_pretrained(model_id)
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model.to(self._device)

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="clipseg_local",
            name="CLIPSeg (本地)",
            description="通过文本提示词指定要抠的主体（如「猫」「红色汽车」），首次使用需下载模型 ~1.5GB。CPU 可运行但较慢，建议 GPU。需安装 transformers + torch。",
            type="local",
            supports_auto=False,
            supports_prompt=True,
            needs_api_key=False,
            icon="clipseg",
        )

    async def remove_bg(self, image_bytes: bytes, api_key: str | None = None) -> bytes:
        raise NotImplementedError("CLIPSeg 不支持自动抠图，请使用提示词模式或 rembg")

    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str, api_key: str | None = None,
        sensitivity: float = 0.5
    ) -> bytes:
        """
        根据文本提示词分割主体并返回透明 PNG。

        sensitivity: 0.0~1.0, 控制 mask 灵敏度。
          值越低越容易出图（但可能包含无关区域），
          值越高要求越精确匹配（但可能漏掉主体）。
        """
        import torch
        import torch.nn.functional as F

        # 将 sensitivity 映射到百分位参数
        # sensitivity=0.0 → 用 95% 分位做白, 10% 以下透明 (宽松)
        # sensitivity=0.5 → 用 85% 分位做白, 50% 以下透明 (默认)
        # sensitivity=1.0 → 用 70% 分位做白, 70% 以下透明 (严格)
        white_pct = 95 - sensitivity * 25  # 95→70
        black_pct = 10 + sensitivity * 60  # 10→70

        self._load_model()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        orig_size = image.size

        inputs = self._processor(
            text=[prompt],
            images=[image],
            padding="max_length",
            return_tensors="pt",
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            preds = outputs.logits.unsqueeze(1)

        # 上采样到原图大小
        mask = F.interpolate(preds, size=(orig_size[1], orig_size[0]), mode="bilinear", align_corners=False)
        mask = torch.sigmoid(mask[0, 0]).cpu().numpy()

        # 自动拉伸 mask 对比度
        lo, hi = mask.min(), mask.max()
        if hi - lo > 0.05:
            mask = (mask - lo) / (hi - lo)
        # 用可调节的百分比拉伸
        p_white = np.percentile(mask, white_pct)
        p_black = np.percentile(mask, black_pct)
        if p_white <= p_black:
            p_white = p_black + 0.01
        mask = np.clip((mask - p_black) / (p_white - p_black + 1e-8), 0, 1)
        # 作为 alpha 通道
        mask_uint8 = (mask * 255).astype(np.uint8)

        # 合成 RGBA 图片
        rgba = np.array(image.convert("RGBA"))
        rgba[:, :, 3] = mask_uint8

        result = Image.fromarray(rgba, "RGBA")
        output = io.BytesIO()
        result.save(output, format="PNG")
        return output.getvalue()

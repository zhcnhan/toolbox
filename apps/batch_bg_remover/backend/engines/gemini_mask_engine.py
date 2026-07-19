"""
engines/gemini_mask_engine.py — Gemini 智能目标定位引擎

支持两种输出模式，用户可自由切换：

  polygon 模式（默认，更省 Token）
    Gemini 返回物体轮廓坐标（JSON）→ 本地画多边形掩膜 → 抠图
    ★ 适用于对精度要求不高、但需要省钱的场景

  mask 模式（更精确）
    Gemini 返回黑白 PNG 掩膜图片 → 本地贴回原图 → 抠图
    ★ 适用于需要精确边缘的场景
"""

import base64
import io
import json
import logging
import re
from typing import Optional

import requests
from PIL import Image, ImageDraw

from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine
from proxy import get_proxies_for_requests
from rate_limiter import track_request

logger = logging.getLogger(__name__)

# ── 模型配置 ──────────────────────────────────────────────────
# polygon 模式：用文本模型，出 JSON 坐标（便宜）
_POLYGON_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
]

# mask 模式：用 image 模型，出 PNG 掩膜（精确）
_MASK_MODELS = [
    "gemini-3.1-flash-lite-image",   # 优先（便宜）
    "gemini-3.1-flash-image",         # 次选
]

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_REQUEST_TIMEOUT = 90


# ── Polygon 模式提示词 ───────────────────────────────────────
_POLYGON_PROMPT = """You are a precise image segmentation assistant. Given an image and a text description, locate the described object precisely and return its outline as polygon coordinates.

The user will describe an object using ANY combination of cues: position (left/right/center/top/bottom - from the viewer's perspective), color, size, shape, texture, spatial relationships, or category. Use ALL available cues to identify the correct object. If there are multiple objects, compare them against all cues in the description.

Return ONLY valid JSON with this exact structure:
{
  "box_2d": [ymin, xmin, ymax, xmax],
  "polygon": [[x1,y1], [x2,y2], ...],
  "label": "short description of what you found"
}

RULES:
- ALL coordinates are normalized to 0-1000 range relative to image dimensions
- The polygon must trace the object's OUTLINE accurately (at least 8 points)
- More complex shapes need MORE points (up to 40)
- Points should follow the outline in clockwise order
- Include the FULL object all the way around
- If the object is NOT visible: return {"box_2d": [], "polygon": [], "label": "not found"}
- Do NOT include any text outside the JSON object

Object to find: """


# ── Mask 模式提示词 ───────────────────────────────────────────
_MASK_PROMPT = """Generate a precise segmentation mask for the described object.

Return BOTH a bounding box in text and a mask image:

TEXT: write the bounding box as exactly: BOX=[ymin,xmin,ymax,xmax]
      (coordinates normalized 0-1000)

IMAGE: output a PNG mask image where:
  - The described object is WHITE (pixel value 255)
  - Everything else is BLACK (pixel value 0)
  - The mask should cover the FULL image at the same aspect ratio

Object to find: """


@register_engine("gemini_mask")
class GeminiMaskEngine(BaseEngine):
    """Gemini 智能目标定位引擎"""

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="gemini_mask",
            name="Gemini Mask (本地切割)",
            description="利用 Gemini 识别物体轮廓 → 本地精确切割，保留原图分辨率，Token 成本极低",
            type="cloud",
            supports_auto=False,
            supports_prompt=True,
            needs_api_key=True,
            api_key_label="Gemini API Key",
            api_key_help_url="https://aistudio.google.com/apikey",
            icon="🧠",
        )

    async def remove_bg(self, image_bytes: bytes, api_key: Optional[str] = None) -> bytes:
        raise NotImplementedError("Gemini Mask 需要输入文字提示词指定要抠的目标物体")

    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str,
        api_key: Optional[str] = None, mask_mode: str = "polygon"
    ) -> bytes:
        if not api_key:
            raise ValueError("Gemini API Key 未提供，请在设置中填写")

        if mask_mode == "polygon":
            mask_data = self._get_polygon_segmentation(api_key, prompt, image_bytes)
            if not mask_data or not mask_data.get("polygon"):
                raise ValueError(f"Gemini 未能识别出「{prompt}」，请换个描述试试")
            return self._apply_polygon_mask(image_bytes, mask_data)

        elif mask_mode == "mask":
            mask_data = self._get_mask_segmentation(api_key, prompt, image_bytes)
            return self._apply_image_mask(image_bytes, mask_data)

        else:
            raise ValueError(f"未知的 mask_mode: {mask_mode}，可选值为 polygon / mask")

    # ============================================================
    #  通用请求发送
    # ============================================================

    def _send_request(self, api_key: str, model_name: str, url: str, payload: dict) -> requests.Response:
        tracker = track_request(api_key)
        tracker.wait()
        resp = requests.post(url, json=payload, timeout=_REQUEST_TIMEOUT, proxies=get_proxies_for_requests())
        if resp.status_code == 429:
            tracker.record_429()
            logger.warning("429 %s: RPM→%d/min", model_name, tracker.get_info()["rpm_current"])
        else:
            tracker.record_success()
        return resp

    # ============================================================
    #  Polygon 模式：Gemini → JSON 坐标 → 本地画 mask
    # ============================================================

    def _get_polygon_segmentation(self, api_key: str, prompt: str, image_bytes: bytes) -> dict:
        img_b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "contents": [{"parts": [
                {"text": _POLYGON_PROMPT + prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]}],
            "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
        }
        for model in _POLYGON_MODELS:
            url = f"{_API_BASE}/{model}:generateContent?key={api_key}"
            try:
                resp = self._send_request(api_key, model, url, payload)
                if resp.status_code != 200:
                    last_error = self._friendly_error(resp.text, resp.status_code) if resp.status_code < 500 else f"{model} 服务不可用"
                    continue
                data = resp.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                if not text:
                    last_error = f"{model} 未返回文字"
                    continue
                result = json.loads(text.strip())
                if result.get("label") == "not found" or not result.get("polygon"):
                    last_error = f"Gemini 在图中未找到「{prompt}」"
                    continue
                if len(result["polygon"]) < 3:
                    last_error = f"轮廓点太少（{len(result['polygon'])}），无法形成有效多边形"
                    continue
                return result
            except json.JSONDecodeError:
                last_error = f"{model} 返回了非 JSON 格式"
                continue
            except Exception as e:
                last_error = str(e)[:200]
                continue
        raise RuntimeError(f"Gemini Mask 调用失败：{last_error}")

    def _apply_polygon_mask(self, image_bytes: bytes, mask_data: dict) -> bytes:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        w, h = img.size
        polygon = mask_data.get("polygon", [])
        if len(polygon) < 3:
            raise ValueError("轮廓点不足 3 个")

        scaled = [
            (max(0, min(w - 1, int(pt[0] / 1000 * w))),
             max(0, min(h - 1, int(pt[1] / 1000 * h))))
            for pt in polygon
        ]
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).polygon(scaled, fill=255)
        result = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        result.paste(img, (0, 0), mask)
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()

    # ============================================================
    #  Mask 模式：Gemini → PNG 掩膜图 → 本地贴回原图
    # ============================================================

    def _get_mask_segmentation(self, api_key: str, prompt: str, image_bytes: bytes) -> dict:
        img_b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "contents": [{"parts": [
                {"text": _MASK_PROMPT + prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]}],
            "generationConfig": {"temperature": 0.1, "responseModalities": ["IMAGE", "TEXT"]}
        }
        for model in _MASK_MODELS:
            url = f"{_API_BASE}/{model}:generateContent?key={api_key}"
            try:
                resp = self._send_request(api_key, model, url, payload)
                if resp.status_code != 200:
                    last_error = self._friendly_error(resp.text, resp.status_code)
                    continue
                data = resp.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])

                # 提取文本（bounding box）
                text = "".join(p.get("text", "") for p in parts if "text" in p)
                # 提取图片（mask PNG）
                mask_b64 = None
                for p in parts:
                    if "inlineData" in p:
                        idata = p["inlineData"]
                        if idata.get("mimeType", "").startswith("image/"):
                            mask_b64 = idata["data"]
                            break

                if not mask_b64:
                    last_error = f"{model} 未返回掩膜图片"
                    continue

                # 解析 bounding box
                box = None
                m = re.search(r"BOX\s*=\s*\[([\d,\s]+)\]", text, re.IGNORECASE)
                if m:
                    nums = [int(x.strip()) for x in m.group(1).split(",")]
                    if len(nums) == 4:
                        box = nums

                return {
                    "box_2d": box,
                    "mask_b64": mask_b64,
                }
            except Exception as e:
                last_error = str(e)[:200]
                continue
        raise RuntimeError(
            f"掩膜模式调用失败：{last_error}。\n"
            "建议切换到「多边形坐标」模式（当前免费 Key 的图片模型配额有限，"
            "绑卡后可启用掩膜模式）。请在设置页切换输出模式。"
        )

    def _apply_image_mask(self, image_bytes: bytes, mask_data: dict) -> bytes:
        """将 Gemini 返回的 PNG 掩膜贴回原图"""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        w, h = img.size

        # 解析掩膜 PNG
        mask_bytes = base64.b64decode(mask_data["mask_b64"])
        mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L")

        # 如果掩膜尺寸和原图不同，缩放到原图尺寸
        if mask_img.size != (w, h):
            logger.info("Mask resize: %s → (%d,%d)", mask_img.size, w, h)
            mask_img = mask_img.resize((w, h), Image.NEAREST)

        result = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        result.paste(img, (0, 0), mask_img)
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()

    # ============================================================
    #  错误提示
    # ============================================================

    @staticmethod
    def _friendly_error(body: str, status: int) -> str:
        if status == 400:
            if "API_KEY_INVALID" in body or "API key not valid" in body:
                return "Gemini API Key 无效，请检查设置中的 Key 是否正确"
            if "INVALID_ARGUMENT" in body:
                return "Gemini 请求参数有误，可能是图片格式或大小问题"
            return "Gemini 无法处理这张图片，请换一张试试"
        if status == 403:
            return "Gemini API 权限不足，请确认 Key 已开通或已绑定支付方式"
        if status == 429:
            return "Gemini 请求过频或当日额度已用完。查看实时配额：https://aistudio.google.com/rate-limit"
        if status >= 500:
            return "Gemini 服务暂时不可用，请稍后重试"
        return f"Gemini 调用失败（HTTP {status}），请稍后重试"

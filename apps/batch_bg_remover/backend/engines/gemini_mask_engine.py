"""
engines/gemini_mask_engine.py — Gemini 智能目标定位引擎

核心思路：
  利用 Gemini 的视觉理解能力，只提取物体的「多边形轮廓坐标」，
  在本地进行精确分割和透明化处理。

与传统的 Gemini 引擎区别：
  - 传统引擎：让 Gemini 直接生成透明背景图（图生图，Token 高，分辨率受限）
  - 本引擎：  让 Gemini 返回物体轮廓坐标 → 本地在原图上裁剪（保留原图分辨率，Token 极低）

模型（按优先级）：
  1. gemini-3.1-flash-lite  — 优先使用，速度快，支持 JSON 结构化输出
     （gemini-2.5-flash 已对新用户不可用，故替换为此模型）

速率限制（Gemini 2.5 Flash，2026.07 参考值）：
  https://ai.google.dev/gemini-api/docs/rate-limits
  https://aistudio.google.com/rate-limit （查看你账号的实时配额）

  ┌──────────┬──────┬──────────┬───────┐
  │ Tier     │ RPM  │ TPM      │ RPD   │
  ├──────────┼──────┼──────────┼───────┤
  │ Free     │  10  │ 250,000  │   250 │  （无需绑卡）
  │ Tier 1   │ 300  │ 2,000,000│ 1,500 │  （绑卡）
  │ Tier 2   │2000  │ 4,000,000│10,000 │  （累计消费 >$250）
  │ Tier 3   │ 4000+│ 8,000,000+│ 自定义│  （累计消费 >$1,000）
  └──────────┴──────┴──────────┴───────┘

  遇到 429（RESOURCE_EXHAUSTED）时采用指数退避 + 随机抖动重试。

用户需要在 https://aistudio.google.com/apikey 获取 API Key。
"""

import base64
import io
import json
import logging
import random
import time
from typing import Optional

import requests
from PIL import Image, ImageDraw

from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine
from proxy import get_proxies_for_requests
from rate_limiter import gemini_limiter

logger = logging.getLogger(__name__)

# ── 模型配置 ──────────────────────────────────────────────────
# 优先使用 gemini-2.5-flash，失败后尝试 pro 兜底
_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
]

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# ── 速率限制重试配置 ──────────────────────────────────────────
_MAX_RETRIES = 3            # 429 后最多重试次数
_BASE_DELAY = 1.0           # 初始等待秒数
_MAX_DELAY = 15.0           # 最大等待秒数

# ── 分割提示词 ─────────────────────────────────────────────────
_SEGMENT_PROMPT = """You are a precise image segmentation assistant.

Given an image and a description of an object, you MUST:
1. Locate the described object precisely
2. Return its outline as polygon coordinates

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
- If the object is NOT visible: return {"box_2d": [], "polygon": [], "label": "not found"}
- Do NOT include any text outside the JSON object

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
        self, image_bytes: bytes, prompt: str, api_key: Optional[str] = None
    ) -> bytes:
        if not api_key:
            raise ValueError("Gemini API Key 未提供，请在设置中填写")

        # Step 1: 调用 Gemini 获取多边形坐标
        mask_data = self._get_segmentation(api_key, prompt, image_bytes)

        if not mask_data or not mask_data.get("polygon") or not mask_data.get("box_2d"):
            raise ValueError(f"Gemini 未能识别出「{prompt}」，请换个更具体的描述试试")

        # Step 2: 本地根据坐标创建掩膜并抠图
        return self._apply_mask(image_bytes, mask_data)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _call_with_retry(self, url: str, payload: dict) -> requests.Response:
        """带指数退避 + 随机抖动重试的 HTTP 请求

        官方文档推荐策略：
        https://ai.google.dev/gemini-api/docs/rate-limits#handling-rate-limits
        """
        # RPM 节流 + RPD 计数
        gemini_limiter.wait_and_count()

        for attempt in range(_MAX_RETRIES + 1):
            resp = requests.post(
                url, json=payload, timeout=90,
                proxies=get_proxies_for_requests()
            )

            if resp.status_code != 429:
                return resp  # 非限流错误，直接返回

            # 429：触发指数退避，公式：base * 2^attempt + random(0, base * 2^(attempt-1))
            if attempt < _MAX_RETRIES:
                delay = min(_BASE_DELAY * (2 ** attempt), _MAX_DELAY)
                jitter = random.uniform(0, delay * 0.5)
                sleep_time = delay + jitter
                logger.warning(
                    f"Gemini 429 限流 (attempt {attempt+1}/{_MAX_RETRIES})，"
                    f"等待 {sleep_time:.1f}s 后重试..."
                )
                time.sleep(sleep_time)

        return resp  # 重试用完，返回最后一次的 429 响应

    def _get_segmentation(self, api_key: str, prompt: str, image_bytes: bytes) -> dict:
        """调用 Gemini API，获取物体轮廓坐标（JSON）"""
        # 先检查配额，不够就直接拒绝
        quota = gemini_limiter.get_quota()
        if quota["rpd_remaining"] <= 0:
            raise RuntimeError(
                f"Gemini 今日配额已用完（{quota['rpd_limit']} 次/日）。"
                f"绑卡升级可提升至 1,500 次/日。实时配额：https://aistudio.google.com/rate-limit"
            )

        img_b64 = base64.b64encode(image_bytes).decode()
        full_prompt = _SEGMENT_PROMPT + prompt

        payload = {
            "contents": [{
                "parts": [
                    {"text": full_prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            }
        }

        last_error = ""
        for model in _MODELS:
            url = f"{_API_BASE}/{model}:generateContent?key={api_key}"
            try:
                resp = self._call_with_retry(url, payload)

                if resp.status_code == 429:
                    last_error = (
                        f"{model} 请求过频或免费额度已用完。"
                        f"免费层每日限制 250 次请求（RPD），查看实时配额："
                        f"https://aistudio.google.com/rate-limit"
                    )
                    continue
                if resp.status_code == 403:
                    last_error = f"{model} API Key 无权限或已过期，请检查"
                    continue
                if resp.status_code == 404:
                    last_error = f"{model} 模型不存在，尝试下一个"
                    continue
                if not resp.ok:
                    last_error = self._friendly_error(resp.text, resp.status_code)
                    continue

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    last_error = f"{model} 未返回任何结果"
                    continue

                # 提取 JSON 文本
                parts = candidates[0].get("content", {}).get("parts", [])
                text = ""
                for part in parts:
                    if "text" in part:
                        text += part["text"]

                if not text:
                    last_error = f"{model} 返回了结果但不含有效 JSON"
                    continue

                # 解析 JSON
                try:
                    result = json.loads(text.strip())
                    if result.get("label") == "not found" or not result.get("polygon"):
                        last_error = f"Gemini 在图中未找到「{prompt}」"
                        continue
                    return result
                except json.JSONDecodeError:
                    last_error = f"{model} 返回了非 JSON 格式的结果"
                    continue

            except requests.exceptions.Timeout:
                last_error = f"{model} 请求超时（可能是图片太大或网络慢）"
                continue
            except Exception as e:
                last_error = str(e)[:200]
                continue

        raise RuntimeError(f"Gemini Mask 调用失败：{last_error}")

    def _apply_mask(self, image_bytes: bytes, mask_data: dict) -> bytes:
        """根据多边形坐标在原图上创建掩膜并返回透明 PNG"""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        w, h = img.size

        # 解析边界框
        box = mask_data.get("box_2d", [])
        polygon = mask_data.get("polygon", [])

        if not box or len(box) != 4:
            raise ValueError("未获取到有效的边界框")
        if not polygon or len(polygon) < 3:
            raise ValueError("未获取到有效的轮廓点（至少需要 3 个点）")

        # 将归一化坐标 (0-1000) 缩放到实际像素
        def scale_x(val):
            return max(0, min(w - 1, int(val / 1000 * w)))

        def scale_y(val):
            return max(0, min(h - 1, int(val / 1000 * h)))

        scaled_polygon = [(scale_x(pt[0]), scale_y(pt[1])) for pt in polygon]

        # 创建二值掩膜 (L 模式: 0=透明, 255=保留)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).polygon(scaled_polygon, fill=255)

        # 用掩膜作为 alpha 通道，合成透明背景图
        result = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        result.paste(img, (0, 0), mask)

        # 输出为 PNG bytes
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()

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
            return (
                "Gemini 请求过频或当日额度已用完。"
                "免费层每日限制 250 次请求，可在以下链接查看实时配额："
                "https://aistudio.google.com/rate-limit"
            )
        if status >= 500:
            return "Gemini 服务暂时不可用，请稍后重试"
        return f"Gemini 调用失败（HTTP {status}），请稍后重试"

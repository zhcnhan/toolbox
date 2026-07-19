"""
engines/gemini_engine.py — Google Gemini 云端引擎

使用 Gemini API 进行抠图和文本提示词分割。
模型（按优先级）：
  1. gemini-2.5-flash  — 优先使用，速度快，成本低

速率限制：
  https://ai.dev/gemini-api/docs/rate-limits
  https://aistudio.google.com/rate-limit （查看实时配额）
  遇到 429 时采用指数退避 + 随机抖动重试。

用户需要在 https://aistudio.google.com/apikey 获取 API Key。
"""

import base64
import logging
import random
import time

import requests
from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine
from proxy import get_proxies_for_requests
from rate_limiter import gemini_limiter

logger = logging.getLogger(__name__)

# 模型优先级
_IMAGE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# 速率限制重试配置
_MAX_RETRIES = 3
_BASE_DELAY = 1.0
_MAX_DELAY = 15.0


@register_engine("gemini")
class GeminiEngine(BaseEngine):
    """Google Gemini 云端抠图引擎"""

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="gemini",
            name="Gemini (云端)",
            description="Google Gemini 图像生成模型，支持自动抠图和文本提示词分割。有免费额度，效果好速度快。",
            type="cloud",
            supports_auto=True,
            supports_prompt=True,
            needs_api_key=True,
            api_key_label="Gemini API Key",
            api_key_help_url="https://aistudio.google.com/apikey",
            icon="cloud",
        )

    def _call_with_retry(self, url: str, payload: dict) -> requests.Response:
        """带指数退避 + 随机抖动 + RPM 节流的 HTTP 请求"""
        # RPM 节流 + RPD 计数
        gemini_limiter.wait_and_count()

        for attempt in range(_MAX_RETRIES + 1):
            resp = requests.post(
                url, json=payload, timeout=90,
                proxies=get_proxies_for_requests()
            )
            if resp.status_code != 429:
                return resp
            if attempt < _MAX_RETRIES:
                delay = min(_BASE_DELAY * (2 ** attempt), _MAX_DELAY)
                jitter = random.uniform(0, delay * 0.5)
                sleep_time = delay + jitter
                logger.warning(
                    f"Gemini 429 限流 (attempt {attempt+1}/{_MAX_RETRIES})，"
                    f"等待 {sleep_time:.1f}s 后重试..."
                )
                time.sleep(sleep_time)
        return resp

    def _call_gemini(self, api_key: str, prompt: str, image_bytes: bytes) -> bytes:
        """调用 Gemini API，尝试多个图像生成模型，返回图片 bytes"""
        # 先检查配额
        quota = gemini_limiter.get_quota()
        if quota["rpd_remaining"] <= 0:
            raise RuntimeError(
                f"Gemini 今日配额已用完（{quota['rpd_limit']} 次/日）。"
                f"绑卡升级可提升至 1,500 次/日。实时配额：https://aistudio.google.com/rate-limit"
            )

        img_b64 = base64.b64encode(image_bytes).decode()

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"]
            }
        }

        last_error = ""
        for model in _IMAGE_MODELS:
            url = f"{_API_BASE}/{model}:generateContent?key={api_key}"
            try:
                resp = self._call_with_retry(url, payload)
                if resp.status_code == 429:
                    last_error = (
                        f"{model} 请求过频或免费额度已用完。"
                        f"查看实时配额：https://aistudio.google.com/rate-limit"
                    )
                    continue
                if resp.status_code == 404:
                    last_error = f"{model} 模型不存在"
                    continue
                if not resp.ok:
                    last_error = self._friendly_error(resp.text, resp.status_code)
                    continue

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    last_error = "Gemini 未返回任何结果"
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        return base64.b64decode(inline["data"])

                last_error = "Gemini 返回了结果但不含图片"
                continue

            except requests.exceptions.Timeout:
                last_error = f"{model} 请求超时，可能是网络慢或图片太大"
                continue
            except Exception as e:
                last_error = str(e)[:200]
                continue

        raise RuntimeError(f"Gemini 全部模型都调用失败，最后错误：{last_error}")

    @staticmethod
    def _friendly_error(body: str, status: int) -> str:
        if status == 400:
            if "API_KEY_INVALID" in body or "API key not valid" in body:
                return "Gemini API Key 无效，请检查设置中的 Key 是否正确"
            if "INVALID_ARGUMENT" in body:
                return "Gemini 请求参数有误，可能是图片格式或大小问题"
            return "Gemini 无法处理这张图片，请换一张试试"
        if status == 403:
            return "Gemini API 权限不足，请确认 Key 已开通图像生成权限"
        if status == 429:
            return (
                "Gemini 请求过频或当日额度已用完。"
                "免费层每日限制 250 次请求，可在以下链接查看实时配额："
                "https://aistudio.google.com/rate-limit"
            )
        if status == 404:
            return "Gemini 模型不存在或已下线，请换其他引擎"
        if status >= 500:
            return "Gemini 服务暂时不可用，请稍后重试"
        return f"Gemini 调用失败（HTTP {status}），请稍后重试"

    async def remove_bg(self, image_bytes: bytes, api_key: str | None = None) -> bytes:
        if not api_key:
            raise ValueError("Gemini API Key 未提供，请在设置中填写")

        prompt = (
            "Remove the background from this image. "
            "Return ONLY the subject with a completely transparent background. "
            "The output must be a PNG image with alpha channel. "
            "Keep the original subject quality, colors, and details unchanged."
        )
        return self._call_gemini(api_key, prompt, image_bytes)

    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str, api_key: str | None = None
    ) -> bytes:
        if not api_key:
            raise ValueError("Gemini API Key 未提供，请在设置中填写")

        full_prompt = (
            f'From this image, extract ONLY the subject described as: "{prompt}". '
            f"Remove everything else including the background. "
            f"The output must be a PNG image with transparent background (alpha channel). "
            f"If the described subject is not found, return the most prominent subject instead."
        )
        return self._call_gemini(api_key, full_prompt, image_bytes)

"""
engines/custom_engine.py — 自定义云端引擎

允许用户填写任意 OpenAI 兼容的图像生成 API：
  - base_url: API 端点地址
  - model_name: 模型名称
  - api_key: API Key

支持两种 API 格式：
  1. Gemini 风格：{base_url}/models/{model}:generateContent?key={api_key}
  2. OpenAI 风格：{base_url}/chat/completions（images）
"""

import base64
import requests
from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine
from proxy import get_proxies_for_requests


@register_engine("custom")
class CustomEngine(BaseEngine):
    """自定义云端抠图引擎，用户自己填 URL / 模型名 / Key"""

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="custom",
            name="自定义引擎",
            description="填入你自己的 API 地址、模型名和 Key。支持 Gemini 风格和 OpenAI 兼容接口。",
            type="cloud",
            supports_auto=True,
            supports_prompt=True,
            needs_api_key=True,
            api_key_label="API Key",
            api_key_help_url="",
            icon="custom",
        )

    def _call_gemini_style(self, base_url: str, model: str, api_key: str, prompt: str, image_bytes: bytes) -> bytes:
        """Gemini 风格 API 调用"""
        img_b64 = base64.b64encode(image_bytes).decode()
        # 规范化 base_url：去掉末尾斜杠
        base_url = base_url.rstrip("/")
        url = f"{base_url}/models/{model}:generateContent?key={api_key}"

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

        resp = requests.post(url, json=payload, timeout=120, proxies=get_proxies_for_requests())
        if resp.status_code == 400:
            if "API_KEY_INVALID" in resp.text or "API key not valid" in resp.text:
                raise RuntimeError("API Key 无效，请检查设置中的 Key 是否正确")
            raise RuntimeError(f"请求参数有误：{resp.text[:200]}")
        if resp.status_code == 403:
            raise RuntimeError("API 权限不足，请确认 Key 是否有图像生成权限")
        if resp.status_code == 429:
            raise RuntimeError("API 额度已用完或调用太频繁，请稍后重试")
        if resp.status_code == 404:
            raise RuntimeError(f"模型不存在：{model}。请检查模型名是否正确")
        if not resp.ok:
            raise RuntimeError(f"API 服务暂时不可用（HTTP {resp.status_code}），请稍后重试")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("API 未返回结果，请检查模型名和 API 地址是否正确")

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])

        raise RuntimeError("API 返回了结果但不含图片，该模型可能不支持图像输出功能")

    def _call_openai_style(self, base_url: str, model: str, api_key: str, prompt: str, image_bytes: bytes) -> bytes:
        """OpenAI 兼容风格 API 调用（chat completions + image input/output）"""
        img_b64 = base64.b64encode(image_bytes).decode()
        base_url = base_url.rstrip("/")
        url = f"{base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ]
            }],
            "modalities": ["image", "text"],
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=120, proxies=get_proxies_for_requests())
        if resp.status_code == 401:
            raise RuntimeError("API Key 无效，请检查设置中的 Key 是否正确")
        if resp.status_code == 429:
            raise RuntimeError("API 额度已用完或调用太频繁，请稍后重试")
        if resp.status_code == 404:
            raise RuntimeError(f"模型不存在：{model}。请检查模型名是否正确")
        if resp.status_code == 400:
            raise RuntimeError(f"请求参数有误：{resp.text[:200]}")
        if not resp.ok:
            raise RuntimeError(f"API 服务暂时不可用（HTTP {resp.status_code}），请稍后重试")

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("API 未返回结果，该模型可能不支持图像生成")

        message = choices[0].get("message", {})
        content = message.get("content", [])

        # content 可能是 list 或 str
        if isinstance(content, list):
            for part in content:
                # 图片输出格式
                if isinstance(part, dict):
                    if part.get("type") == "image_url":
                        url_data = part.get("image_url", {}).get("url", "")
                        if url_data.startswith("data:image"):
                            b64_data = url_data.split(",", 1)[-1]
                            return base64.b64decode(b64_data)
                    # 内联图片数据
                    inline = part.get("inline_data") or part.get("inlineData")
                    if inline and inline.get("data"):
                        return base64.b64decode(inline["data"])
                    # b64_json 格式
                    if part.get("b64_json"):
                        return base64.b64decode(part["b64_json"])

        raise RuntimeError("API 返回了结果但不含图片，该模型可能不支持图像输出功能")

    def _call_siliconflow_style(self, base_url: str, model: str, api_key: str, prompt: str, image_bytes: bytes) -> bytes:
        """
        硅基流动风格 API 调用：POST /v1/images/generations
        支持 Qwen/Qwen-Image-Edit 等图像编辑模型
        请求格式：{model, prompt, image(base64)}
        响应格式：{images: [{url: "..."}]}
        """
        import io
        img_b64 = base64.b64encode(image_bytes).decode()
        base_url = base_url.rstrip("/")
        url = f"{base_url}/images/generations"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "image": f"data:image/jpeg;base64,{img_b64}",
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=120, proxies=get_proxies_for_requests())
        if resp.status_code == 401:
            raise RuntimeError("API Key 无效，请检查设置中的 Key 是否正确")
        if resp.status_code == 429:
            raise RuntimeError("API 调用太频繁或额度已用完，请稍后重试")
        if resp.status_code == 404:
            raise RuntimeError(f"模型不存在：{model}。请检查模型名是否正确，注意区分大小写")
        if resp.status_code == 400:
            try:
                err = resp.json()
                raw_msg = err.get("message") or str(err)[:200]
            except Exception:
                raw_msg = resp.text[:200]
            raise RuntimeError(f"请求参数有误：{raw_msg}")
        if not resp.ok:
            raise RuntimeError(f"API 服务暂时不可用（HTTP {resp.status_code}），请稍后重试")

        data = resp.json()
        images = data.get("images", [])
        if not images:
            raise RuntimeError("API 未返回图片，可能是模型不支持图像输出")

        # 结果是 URL，需要下载
        img_url = images[0].get("url", "")
        if not img_url:
            raise RuntimeError("API 返回结果中无图片地址，可能是模型不支持图像输出")

        # 如果是 data URI
        if img_url.startswith("data:image"):
            b64_data = img_url.split(",", 1)[-1]
            return base64.b64decode(b64_data)

        # 下载图片
        img_resp = requests.get(img_url, timeout=60, proxies=get_proxies_for_requests())
        if not img_resp.ok:
            raise RuntimeError("下载结果图片失败，请稍后重试")
        return img_resp.content

    def _detect_api_style(self, base_url: str, model: str) -> str:
        """自动判断 API 风格"""
        url_lower = base_url.lower()
        model_lower = model.lower()
        # Gemini 官方
        if "generativelanguage.googleapis.com" in url_lower or "gemini" in url_lower:
            return "gemini"
        # 硅基流动 / SiliconFlow
        if "siliconflow" in url_lower or "qwen" in model_lower:
            return "siliconflow"
        # 默认 OpenAI 兼容
        return "openai"

    async def remove_bg(
        self,
        image_bytes: bytes,
        api_key: str | None = None,
        base_url: str = "",
        model_name: str = "",
    ) -> bytes:
        if not api_key:
            raise ValueError("请填写 API Key")
        if not base_url:
            raise ValueError("请填写 API 地址")
        if not model_name:
            raise ValueError("请填写模型名称")

        prompt = (
            "Remove the background from this image completely. "
            "Keep ONLY the main subject with a completely transparent background. "
            "The output must be a PNG image with alpha channel showing only the subject. "
            "Preserve all details of the subject: edges, fine features (hair, fur), "
            "and original colors unchanged. Do NOT crop or resize the image."
        )

        # 自动判断 API 风格
        style = self._detect_api_style(base_url, model_name)
        if style == "gemini":
            return self._call_gemini_style(base_url, model_name, api_key, prompt, image_bytes)
        elif style == "siliconflow":
            return self._call_siliconflow_style(base_url, model_name, api_key, prompt, image_bytes)
        else:
            return self._call_openai_style(base_url, model_name, api_key, prompt, image_bytes)

    async def remove_bg_with_prompt(
        self,
        image_bytes: bytes,
        prompt: str,
        api_key: str | None = None,
        base_url: str = "",
        model_name: str = "",
    ) -> bytes:
        if not api_key:
            raise ValueError("请填写 API Key")
        if not base_url:
            raise ValueError("请填写 API 地址")
        if not model_name:
            raise ValueError("请填写模型名称")

        full_prompt = (
            f'From this image, extract ONLY the subject matching: "{prompt}". '
            f"Remove everything else — background, other objects, and debris. "
            f"The output must be a PNG image with transparent background showing only the extracted subject. "
            f"Preserve the subject's edges and details precisely. "
            f"Pay special attention to thin parts, fine edges, and concave areas. "
            f"If the described subject is not found, return the most visually prominent subject instead."
        )

        style = self._detect_api_style(base_url, model_name)
        if style == "gemini":
            return self._call_gemini_style(base_url, model_name, api_key, full_prompt, image_bytes)
        elif style == "siliconflow":
            return self._call_siliconflow_style(base_url, model_name, api_key, full_prompt, image_bytes)
        else:
            return self._call_openai_style(base_url, model_name, api_key, full_prompt, image_bytes)

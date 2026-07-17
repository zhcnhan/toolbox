"""
engines/removebg_engine.py — remove.bg 云端抠图引擎

专业抠图 API，专为背景移除设计，效果最好。
API 文档：https://www.remove.bg/api
免费额度：50 张/月，之后 $0.09/张

调用方式：
  POST https://api.remove.bg/v1.0/removebg
  headers: X-Api-Key
  files: image_file (图片二进制)
  data: size=auto
  返回：透明背景 PNG 二进制

注意：remove.bg 不支持文本提示词选取主体，
它是全自动抠图（自动检测前景主体）。
"""

import requests
from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine

_API_URL = "https://api.remove.bg/v1.0/removebg"


@register_engine("removebg")
class RemoveBgEngine(BaseEngine):
    """remove.bg 专业抠图引擎"""

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="removebg",
            name="remove.bg (推荐)",
            description="专业抠图 API，效果最好，发丝级精度。免费 50 张/月，之后 $0.09/张。全自动抠图，不支持提示词。",
            type="cloud",
            supports_auto=True,
            supports_prompt=False,
            needs_api_key=True,
            api_key_label="remove.bg API Key",
            api_key_help_url="https://www.remove.bg/api",
            icon="removebg",
        )

    def _call_removebg(self, api_key: str, image_bytes: bytes) -> bytes:
        """调用 remove.bg API"""
        headers = {"X-Api-Key": api_key}
        files = {"image_file": image_bytes}
        data = {"size": "auto"}

        resp = requests.post(_API_URL, headers=headers, files=files, data=data, timeout=120)

        if resp.status_code == 429:
            raise RuntimeError("remove.bg 免费额度已用完（每月 50 张），请下月重置或充值")
        if resp.status_code == 403:
            raise RuntimeError("remove.bg API Key 无效，请检查设置中的 Key 是否正确")
        if resp.status_code == 402:
            raise RuntimeError("remove.bg 账户余额不足，请充值或购买套餐")
        if resp.status_code == 400:
            # 解析错误详情，转成用户能看懂的提示
            try:
                err = resp.json()
                raw_msg = err.get("errors", [{}])[0].get("title", "")
            except Exception:
                raw_msg = resp.text[:200]
            # 常见错误的友好翻译
            if "Could not identify foreground" in raw_msg:
                raise RuntimeError(
                    "remove.bg 无法识别这张图片里的主体。\n"
                    "可能原因：图片主体不清晰、主体和背景颜色太接近、图片太小或模糊。\n"
                    "建议：换一张主体明确的图，或用本地 rembg 引擎试试。"
                )
            if "Image file size" in raw_msg or "too large" in raw_msg.lower():
                raise RuntimeError("图片太大了，请压缩到 25MB 以下再试")
            if "Image file format" in raw_msg or "not supported" in raw_msg.lower():
                raise RuntimeError("图片格式不支持，请用 JPG/PNG 格式")
            raise RuntimeError(f"remove.bg 处理失败：{raw_msg}")
        if not resp.ok:
            raise RuntimeError(f"remove.bg 服务暂时不可用（HTTP {resp.status_code}），请稍后重试")

        # 返回的是透明 PNG 二进制
        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type:
            raise RuntimeError(f"remove.bg 返回了非图片内容: {content_type}")

        return resp.content

    async def remove_bg(self, image_bytes: bytes, api_key: str | None = None) -> bytes:
        if not api_key:
            raise ValueError("请填写 remove.bg API Key")

        return self._call_removebg(api_key, image_bytes)

    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str, api_key: str | None = None
    ) -> bytes:
        """remove.bg 不支持提示词分割"""
        raise NotImplementedError("remove.bg 不支持提示词选取主体，它是全自动抠图。请用 Gemini/自定义引擎做提示词分割")

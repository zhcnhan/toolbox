"""
engines/replicate_engine.py — Replicate 云端引擎

通过 Replicate 平台运行开源模型（BiRefNet、SAM3 等）。
用户需要在 https://replicate.com/account/api-tokens 获取 API Token。
按使用时长计费（~$0.001/秒），适合高精度需求。

安装依赖：pip install replicate
"""

from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine
from proxy import apply_proxy_env, get_proxy_url


@register_engine("replicate")
class ReplicateEngine(BaseEngine):
    """Replicate 云端抠图引擎"""

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="replicate",
            name="Replicate (云端)",
            description="在云端运行 BiRefNet / SAM3 等开源模型，精度高。按使用时长计费，适合专业需求。",
            type="cloud",
            supports_auto=True,
            supports_prompt=True,
            needs_api_key=True,
            api_key_label="Replicate API Token",
            api_key_help_url="https://replicate.com/account/api-tokens",
            icon="🔬",
        )

    def _get_client(self, api_key: str):
        import replicate
        client = replicate.Client(api_token=api_key)
        return client

    async def remove_bg(self, image_bytes: bytes, api_key: str | None = None) -> bytes:
        """使用 Replicate + BiRefNet 自动抠图"""
        if not api_key:
            raise ValueError("Replicate API Token 未提供，请在设置中填写")

        import replicate
        import base64

        apply_proxy_env()
        client = replicate.Client(api_token=api_key)

        # 将图片转为 data URI
        data_uri = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"

        output = client.run(
            "lucataco/birefnet:fd8e47e1f1a9efc2a5f2e8c2e7b1a3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9",
            input={"image": data_uri},
        )

        # Replicate 返回的是 URL
        if isinstance(output, str):
            import httpx
            resp = httpx.get(output, timeout=60, proxy=get_proxy_url())
            resp.raise_for_status()
            return resp.content

        raise RuntimeError("Replicate 返回了非预期格式的结果，模型可能已更新，请联系开发者")

    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str, api_key: str | None = None
    ) -> bytes:
        """使用 Replicate + SAM3 根据提示词分割"""
        if not api_key:
            raise ValueError("Replicate API Token 未提供，请在设置中填写")

        import replicate
        import base64

        apply_proxy_env()
        client = replicate.Client(api_token=api_key)

        data_uri = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"

        output = client.run(
            "meta/sam-3:latest",
            input={
                "image": data_uri,
                "prompt": prompt,
            },
        )

        if isinstance(output, str):
            import httpx
            resp = httpx.get(output, timeout=60, proxy=get_proxy_url())
            resp.raise_for_status()
            return resp.content

        raise RuntimeError("Replicate 返回了非预期格式的结果，模型可能已更新，请联系开发者")

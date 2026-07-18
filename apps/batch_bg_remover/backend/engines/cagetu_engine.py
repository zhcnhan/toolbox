"""
engines/cagetu_engine.py — 擦个图 (cagetu.com) 云端抠图引擎

国内抠图 API，专为背景移除设计，效果专业。
API 文档：https://cagetu.com
计费：0.1 元/次（成功才扣费），需充值
返回：PNG 透明背景图片 URL（有效期 3 小时）

调用方式：
  POST https://cagetu.com/api/koutu/remove
  headers: Authorization: Bearer sk-xxx
  files: image (图片文件)
  响应 JSON: {code: 0, msg: "抠图成功", data: {image_url: "https://..."}}

注意：擦个图是全自动抠图，不支持文本提示词选取主体。
"""

import requests
from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine
from proxy import get_proxies_for_requests

_API_URL = "https://cagetu.com/api/koutu/remove"


def _detect_image_ext(data: bytes) -> str:
    """根据文件头判断图片格式，返回扩展名（如 .jpg）"""
    if len(data) < 12:
        return ".jpg"
    if data[:2] == b'\xff\xd8':
        return ".jpg"
    if data[:4] == b'\x89PNG':
        return ".png"
    if data[:4] in (b'GIF8', b'GIF7'):
        return ".gif"
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return ".webp"
    if data[:2] == b'BM':
        return ".bmp"
    return ".jpg"


@register_engine("cagetu")
class CagetuEngine(BaseEngine):
    """擦个图 (cagetu.com) 专业抠图引擎"""

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="cagetu",
            name="擦个图 (国内推荐)",
            description="国内专业抠图 API，效果专业，PNG 透明背景输出。0.1 元/次（成功才扣费）。全自动抠图，不支持提示词。",
            type="cloud",
            supports_auto=True,
            supports_prompt=False,
            needs_api_key=True,
            api_key_label="擦个图 API Key (sk-xxx)",
            api_key_help_url="https://cagetu.com",
            icon="cagetu",
        )

    def _call_cagetu(self, api_key: str, image_bytes: bytes) -> bytes:
        """调用擦个图 API"""
        headers = {"Authorization": f"Bearer {api_key}"}
        # 根据文件头判断真实格式，给 API 传正确的文件名后缀
        ext = _detect_image_ext(image_bytes)
        files = {"image": (f"image{ext}", image_bytes, f"image/{ext.lstrip('.')}")}

        resp = requests.post(_API_URL, headers=headers, files=files, timeout=120, proxies=get_proxies_for_requests())

        # HTTP 状态码错误
        if resp.status_code == 401:
            raise RuntimeError("擦个图 API Key 无效，请检查设置中的 Key 是否正确")
        if resp.status_code == 402:
            raise RuntimeError("擦个图账户余额不足，请登录 cagetu.com 充值")
        if resp.status_code == 403:
            raise RuntimeError("擦个图账号已被禁用，请联系客服")
        if not resp.ok:
            raise RuntimeError(f"擦个图服务暂时不可用（HTTP {resp.status_code}），请稍后重试")

        # 解析 JSON 响应
        try:
            data = resp.json()
        except Exception:
            raise RuntimeError("擦个图返回了非 JSON 数据，服务可能异常，请稍后重试")

        code = data.get("code", -1)
        msg = data.get("msg", "")

        if code != 0:
            # 常见错误的友好提示
            if "超出" in msg or "过大" in msg or "6000" in msg:
                raise RuntimeError(f"图片太大，擦个图要求宽高均不超过 6000px 且 20MB 以内")
            if "格式" in msg or "format" in msg.lower():
                raise RuntimeError(f"图片格式不支持，请用 JPG/PNG/GIF/WEBP 格式")
            raise RuntimeError(f"擦个图处理失败：{msg}")

        result = data.get("data", {})
        image_url = result.get("image_url", "")
        if not image_url:
            raise RuntimeError("擦个图返回成功但无图片地址，请稍后重试")

        # 下载结果图片（URL 有效期 3 小时）
        img_resp = requests.get(image_url, timeout=60, proxies=get_proxies_for_requests())
        if not img_resp.ok:
            raise RuntimeError("下载擦个图结果图片失败，请稍后重试")

        return img_resp.content

    async def remove_bg(self, image_bytes: bytes, api_key: str | None = None) -> bytes:
        if not api_key:
            raise ValueError("请填写擦个图 API Key")

        return self._call_cagetu(api_key, image_bytes)

    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str, api_key: str | None = None
    ) -> bytes:
        """擦个图不支持提示词分割"""
        raise NotImplementedError("擦个图不支持提示词选取主体，它是全自动抠图。请用 Gemini/自定义引擎做提示词分割")

"""
engines/kimi_engine.py — 月之暗面 Kimi 引擎（通过硅基流动 API）

利用 Kimi 系列模型的结构化输出能力，返回物体多边形坐标。
实验结果：Kimi-K2.6 (Pro) 在 polygon 输出上表现最佳。

API 兼容 OpenAI 格式，通过 https://api.siliconflow.cn/v1 访问。
Configurable `num_points` parameter: 30 (cheap) ~ 80 (precise).

用户需要去 https://cloud.siliconflow.cn 注册获取 API Key。
"""

import base64
import io
import json
import logging
from typing import Optional

import requests
from PIL import Image, ImageDraw

from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine

logger = logging.getLogger(__name__)

_API_BASE = "https://api.siliconflow.cn/v1"
_DEFAULT_MODEL = "Pro/moonshotai/Kimi-K2.6"
_FALLBACK_MODEL = "moonshotai/Kimi-K2.7-Code"

_POLYGON_PROMPT = """You are a precise image segmentation assistant. Given an image and a description of an object, locate the described object precisely and return its outline as polygon coordinates.

Return ONLY a valid JSON object with this exact structure:
{"polygon": [[x1,y1], [x2,y2], ...]}

RULES:
- ALL coordinates are normalized to 0-1000 range relative to image dimensions
- The polygon must trace the object's OUTLINE accurately
- Use exactly {num_points} points
- Points should follow the outline in clockwise order
- If the object is NOT visible, return {{"polygon": []}}

Object to find: {prompt}"""


@register_engine("kimi")
class KimiEngine(BaseEngine):
    """Kimi 多边形坐标引擎（通过硅基流动）"""

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="kimi",
            name="Kimi (多边形坐标)",
            description="通过硅基流动调用 Kimi 模型，返回物体轮廓坐标 → 本地精确切割。Kimi-K2.6 效果最佳",
            type="cloud",
            supports_auto=False,
            supports_prompt=True,
            needs_api_key=True,
            api_key_label="硅基流动 API Key",
            api_key_help_url="https://cloud.siliconflow.cn",
            icon="kimi",
        )

    async def remove_bg(self, image_bytes: bytes, api_key: Optional[str] = None) -> bytes:
        raise NotImplementedError("Kimi 引擎需要输入文字提示词指定要抠的目标物体")

    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str,
        api_key: Optional[str] = None,
        num_points: int = 35,
    ) -> bytes:
        if not api_key:
            raise ValueError("硅基流动 API Key 未提供，请在设置中填写")

        polygon = self._get_polygon(api_key, prompt, image_bytes, num_points)
        if not polygon or len(polygon) < 3:
            raise ValueError(f"Kimi 未能识别出「{prompt}」，请换个描述试试")

        return self._apply_mask(image_bytes, polygon)

    # ============================================================
    #  Kimi API 调用
    # ============================================================

    def _get_polygon(self, api_key: str, prompt: str, image_bytes: bytes, num_points: int) -> list:
        """调用 Kimi API，获取多边形坐标"""
        img_b64 = base64.b64encode(image_bytes).decode()
        user_prompt = _POLYGON_PROMPT.format(prompt=prompt, num_points=min(max(num_points, 15), 100))

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        payload = {
            "model": _DEFAULT_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ]
            }],
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        last_error = ""
        for model in [_DEFAULT_MODEL, _FALLBACK_MODEL]:
            payload["model"] = model
            url = f"{_API_BASE}/chat/completions"
            try:
                # 硅基流动在国内可直接访问，不走代理
                import sys
                logger.info("Kimi sending to %s | img=%d chars | key_len=%d", model, len(img_b64), len(api_key))
                resp = requests.post(url, json=payload, headers=headers, timeout=90)
                logger.info("Kimi %s status: %s | len=%d", model, resp.status_code, len(resp.content))
                if resp.status_code == 429:
                    last_error = f"{model} 免费额度已用完"
                    continue
                if not resp.ok:
                    last_error = f"{model} HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning("Kimi %s error body: %s", model, resp.text[:300])
                    continue

                data = resp.json()
                logger.info("Kimi %s choices: %d", model, len(data.get("choices", [])))
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                logger.info("Kimi %s response: %s", model, content[:400] if content else "(empty)")
                if not content:
                    last_error = f"{model} 未返回有效内容"
                    continue

                # 提取 JSON（Kimi 可能输出 markdown 包裹或其他文字）
                content = content.strip()
                if "```" in content:
                    for block in content.split("```"):
                        block = block.strip()
                        if block.startswith("json"):
                            block = block[4:].strip()
                        if block.startswith("{"):
                            content = block
                            break

                # 找第一个 { 到最后一个 } 之间的内容
                start = content.find("{")
                end = content.rfind("}")
                if start >= 0 and end > start:
                    content = content[start:end+1]
                else:
                    raise ValueError("未找到 JSON")

                result = json.loads(content)
                polygon = result.get("polygon") or result.get("points") or result.get("coordinates") or result.get("polygons") or []
                if isinstance(polygon, list) and len(polygon) >= 3:
                    return polygon
                last_error = f"{model} 未识别出目标物体"

            except Exception as e:
                last_error = f"{model}: {str(e)[:150]}"
                continue

        raise RuntimeError(f"Kimi 调用失败：{last_error}")

    # ============================================================
    #  本地掩膜处理
    # ============================================================

    def _apply_mask(self, image_bytes: bytes, polygon: list) -> bytes:
        """根据多边形坐标在原图上创建掩膜并返回透明 PNG"""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        w, h = img.size

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

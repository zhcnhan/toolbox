"""
engines/kimi_engine.py — 月之暗面 Kimi 引擎（通过硅基流动 API）

利用 Kimi 系列模型的结构化输出能力，返回物体多边形坐标。
实验结果：Kimi-K2.6 (Pro) 在 polygon 输出上表现最佳。

API 兼容 OpenAI 格式，通过 https://api.siliconflow.cn/v1 访问。

工作流：
  1. 用固定 ~50 点调 API（快、不超时）
  2. matting.py: 离群点剔除 → Centripetal Catmull-Rom 插值
     → 超分抗锯齿掩膜 → 羽化 → RGBA 输出

用户需要去 https://cloud.siliconflow.cn 注册获取 API Key。
"""

import base64
import io
import json
import logging
from typing import Optional

import requests
from PIL import Image

from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine
from matting import matting_cut

logger = logging.getLogger(__name__)

_API_BASE = "https://api.siliconflow.cn/v1"
_KIMI_MODEL = "Pro/moonshotai/Kimi-K2.6"
_API_POLYGON_POINTS = 50  # 固定：API 每次请求约 50 个点，后端再插值

_POLYGON_PROMPT = """You are an expert image segmentation specialist that produces pixel-tight polygon outlines.

# Task
Given the image, locate the object described below and trace its **complete silhouette** as a polygon.

# Object identification
The user may describe the object with ANY cues: position (left/right/center/top/bottom — from the viewer's perspective), color, size, shape, texture, spatial relationships ("next to", "behind", "on top of"), or a category name. Use ALL cues to identify the correct object. When multiple objects exist, compare against all cues.

# Critical: outline precision
The polygon must **tightly hug the object's actual boundary** — every point must sit ON the edge between the object and the background, not in empty space, not inside the object.

Special attention to:
- Thin / extending parts — these are the most important and the easiest to miss
- Concave areas — the polygon should follow INWARD into these areas
- Sharp corners and small protrusions — do not "smooth over" them with straight lines
- Translucent / semi-transparent regions — include the full shape

# Output format
Return ONLY a valid JSON object (no other text):
{{"polygon": [[x1,y1], [x2,y2], ...]}}

# Rules
- ALL coordinates are normalized to 0-1000 range relative to image dimensions
- Use approximately {num_points} points total
- Place MORE points on high-curvature parts and fewer on long straight edges
- Points must be in clockwise order
- The polygon must form a closed loop
- If the described object is not in the image, return {{"polygon": []}}

# Object to find
{prompt}"""


@register_engine("kimi")
class KimiEngine(BaseEngine):
    """Kimi 多边形坐标引擎（通过硅基流动）"""

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="kimi",
            name="Kimi (多边形坐标)",
            description="通过硅基流动调用 Kimi 模型，返回物体轮廓坐标 → 本地平滑切割。Kimi-K2.6 效果最佳",
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
        num_points: Optional[int] = None,
    ) -> bytes:
        if not api_key:
            raise ValueError("硅基流动 API Key 未提供，请在设置中填写")

        # 1. 调用 API 获取粗轮廓（固定 ~50 点）
        polygon = self._get_polygon(api_key, prompt, image_bytes)
        if not polygon or len(polygon) < 3:
            raise ValueError(f"Kimi 未能识别出「{prompt}」，请换个描述试试")

        # 2. Kimi 返回 [0,1000] 坐标 → 转为 [0,1]
        contour_01 = [(x / 1000.0, y / 1000.0) for x, y in polygon]

        # 3. matting.py 全流程：预处理 → 插值 → 掩膜 → 合成
        img = Image.open(io.BytesIO(image_bytes))
        _, result = matting_cut(
            image=img,
            contour_points=contour_01,
            target_points=num_points if num_points and num_points > 0 else None,
            blur_radius=1.5,
        )

        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()

    # ============================================================
    #  Kimi API 调用（固定 ~50 点）
    # ============================================================

    def _get_polygon(self, api_key: str, prompt: str, image_bytes: bytes) -> list:
        """调用 Kimi API，获取多边形坐标（固定 ~50 点），自动重试"""
        # 压缩图片到最长边 800px，加快 API 响应
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode == "RGBA":
            img = img.convert("RGB")
        max_size = 800
        if img.width > max_size or img.height > max_size:
            ratio = max_size / max(img.width, img.height)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        user_prompt = _POLYGON_PROMPT.format(
            prompt=prompt, num_points=_API_POLYGON_POINTS
        )

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        url = f"{_API_BASE}/chat/completions"
        last_error = ""

        # 自动重试 3 次（Kimi-K2.6 偶发返回空 content 或无效 JSON，重试通常能解决）
        for attempt in range(3):
            payload = {
                "model": _KIMI_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    ]
                }],
                "temperature": 0.01,
                "max_tokens": 2048,
                "enable_thinking": False,
            }

            logger.info("Kimi sending [attempt %d/3] | img=%d chars", attempt + 1, len(img_b64))
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            logger.info("Kimi status: %s | len=%d", resp.status_code, len(resp.content))

            if resp.status_code == 429:
                raise RuntimeError("Kimi 免费额度已用完")
            if not resp.ok:
                last_error = f"Kimi HTTP {resp.status_code}: {resp.text[:200]}"
                continue

            data = resp.json()
            message = data.get("choices", [{}])[0].get("message", {})
            # Kimi 有时把结果放在 reasoning_content 而非 content 中
            content = message.get("content", "") or message.get("reasoning_content", "")
            logger.info("Kimi response [attempt %d/3]: %s", attempt + 1, content[:300] if content else "(empty)")

            if not content:
                last_error = "Kimi 未返回有效内容"
                continue

            # 提取 JSON 对象（兼容各种格式：纯 JSON、markdown 包裹、前后有多余文字）
            json_str = self._extract_json(content)
            if not json_str:
                last_error = "Kimi 未返回有效 JSON"
                continue

            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                last_error = "Kimi 返回了格式错误的 JSON"
                continue

            polygon = result.get("polygon") or result.get("points") or result.get("coordinates") or []
            if isinstance(polygon, list) and len(polygon) >= 3:
                return polygon

            last_error = "Kimi 未能识别出目标物体"
            # 如果识别结果为空的 polygon 列表，不再重试（模型明确表示没找到）
            if isinstance(polygon, list) and len(polygon) == 0:
                break

        raise RuntimeError(last_error)

    @staticmethod
    def _extract_json(text: str) -> str:
        """
        从模型返回文本中提取 JSON 对象字符串。

        兼容：
        - 纯 JSON：{"polygon": [[...]]}
        - Markdown 包裹：```json ... ``` 或 ``` ... ```
        - 前后有多余文字：如 "Here is the result: {...}"
        - 多个花括号嵌套：取最外层匹配的一对 {}
        """
        text = text.strip()

        # 去掉 markdown 代码块标记
        if "```" in text:
            for block in text.split("```"):
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if block.startswith("{") or block.startswith("["):
                    text = block
                    break

        # 找最外层的一对 {}（处理嵌套花括号）
        start = -1
        depth = 0
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start >= 0:
                    return text[start:i + 1]

        # 如果没找到 {}，试试找最外层的 []
        start = -1
        depth = 0
        for i, ch in enumerate(text):
            if ch == "[":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0 and start >= 0:
                    return text[start:i + 1]

        return ""

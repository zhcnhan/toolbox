"""
engines/kimi_engine.py — 月之暗面 Kimi 引擎（通过硅基流动 API）

利用 Kimi 系列模型的结构化输出能力，返回物体多边形坐标。
实验结果：Kimi-K2.6 (Pro) 在 polygon 输出上表现最佳。

API 兼容 OpenAI 格式，通过 https://api.siliconflow.cn/v1 访问。

工作流：
  1. 用固定 ~50 点调 API（快、不超时）
  2. 后端用 Catmull-Rom 样条插值到前端要求的精度（平滑、本地计算无成本）

用户需要去 https://cloud.siliconflow.cn 注册获取 API Key。
"""

import base64
import io
import json
import logging
import sys
from typing import Optional

import requests
from PIL import Image, ImageDraw

from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine

logger = logging.getLogger(__name__)

_API_BASE = "https://api.siliconflow.cn/v1"
_KIMI_MODEL = "Pro/moonshotai/Kimi-K2.6"
_API_POLYGON_POINTS = 50  # 固定：API 每次请求约 50 个点，后端再插值

_POLYGON_PROMPT = """You are an expert image segmentation specialist that produces pixel-tight polygon outlines.

# Task
Given the image, locate the object described below and trace its **complete silhouette** as a polygon.

# Description
The user may describe the object with ANY cues: position (left/right/center/top/bottom — from the viewer's perspective), color, size, shape, texture, spatial relationships ("next to", "behind", "on top of"), or category ("the person", "the car", "the bird"). Use ALL cues to identify the correct object. Compare against multiple candidates if present.

# Critical: outline precision
The polygon must **tightly hug the object's actual boundary** — every point must sit ON the edge between the object and the background, not in empty space, not inside the object, not in the surrounding background. Treat this as a tracing exercise: imagine you are placing dots directly on the silhouette.

Special attention to:
- Thin / extending parts: wings, tails, beaks, ears, fingers, hair strands, leaves, branches — these are often the most important and the easiest to miss
- Concave areas: between limbs, around joints, between fingers — the polygon should follow INWARD into these areas
- Sharp corners and small protrusions — do not "smooth over" them with straight lines
- Translucent / semi-transparent regions: include the full shape

# Output format
Return ONLY a valid JSON object (no other text):
{{"polygon": [[x1,y1], [x2,y2], ...]}}

# Rules
- ALL coordinates are normalized to 0-1000 range relative to image dimensions
- Use approximately {num_points} points, distributed so they densely sample curves and corners
- Place MORE points on high-curvature parts (head, beak, wing tips, tail) and fewer on long straight edges
- Points should follow the outline in clockwise order, starting from the top of the head
- The polygon must be CLOSED (traces all the way around)
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
        num_points: int = 100,
    ) -> bytes:
        if not api_key:
            raise ValueError("硅基流动 API Key 未提供，请在设置中填写")

        # 1. 调用 API 获取粗轮廓（固定点数，速度快）
        polygon = self._get_polygon(api_key, prompt, image_bytes)
        if not polygon or len(polygon) < 3:
            raise ValueError(f"Kimi 未能识别出「{prompt}」，请换个描述试试")

        # 2. Catmull-Rom 样条插值：粗轮廓 → 精细轮廓
        smooth_polygon = self._catmull_rom_spline(polygon, num_output=max(num_points, 10))

        # 3. 用插值后的精细轮廓生成掩膜
        return self._apply_mask(image_bytes, smooth_polygon)

    # ============================================================
    #  Catmull-Rom 样条插值
    # ============================================================

    @staticmethod
    def _catmull_rom_spline(polygon: list, num_output: int = 200) -> list:
        """
        Catmull-Rom 样条插值，对封闭多边形做平滑。

        将粗轮廓（e.g. 50 点）平滑插值到 num_output 个点，
        让轮廓更精细顺滑，且完全本地计算、无额外 API 成本。

        Args:
            polygon: [[x1,y1], [x2,y2], ...] — 原始多边形（已归一化到 0-1000）
            num_output: 输出的目标点数

        Returns:
            平滑后的多边形坐标列表
        """
        n = len(polygon)
        if n < 4:
            return polygon  # 点太少，无法插值

        # 对于封闭曲线，前后各扩展 3 个点以处理边缘
        # 顺序: P0, P1, ..., Pn-1, P0, P1, P2
        extended = polygon + polygon[:3]

        result = []
        for i in range(num_output):
            # 均分到所有线段上
            t_float = (i / num_output) * n
            seg = int(t_float) % n          # 当前线段索引
            t = t_float - int(t_float)       # 段内参数 [0, 1)

            # Catmull-Rom 需要 4 个控制点
            p0 = extended[seg]
            p1 = extended[(seg + 1) % n]
            p2 = extended[(seg + 2) % n]
            p3 = extended[(seg + 3) % n]

            t2 = t * t
            t3 = t2 * t

            x = 0.5 * (
                2 * p1[0] +
                (-p0[0] + p2[0]) * t +
                (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                2 * p1[1] +
                (-p0[1] + p2[1]) * t +
                (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            result.append([round(x), round(y)])

        return result

    # ============================================================
    #  Kimi API 调用（固定 ~50 点，不做超时限制）
    # ============================================================

    def _get_polygon(self, api_key: str, prompt: str, image_bytes: bytes) -> list:
        """调用 Kimi API，获取多边形坐标（固定 ~50 点）"""
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

        payload = {
            "model": _KIMI_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ]
            }],
            "temperature": 0.1,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
            "enable_thinking": False,
        }

        url = f"{_API_BASE}/chat/completions"
        logger.info("Kimi sending to %s | img=%d chars", _KIMI_MODEL, len(img_b64))
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        logger.info("Kimi status: %s | len=%d", resp.status_code, len(resp.content))

        if resp.status_code == 429:
            raise RuntimeError("Kimi 免费额度已用完")
        if not resp.ok:
            raise RuntimeError(f"Kimi HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info("Kimi response: %s", content[:400] if content else "(empty)")
        if not content:
            raise RuntimeError("Kimi 未返回有效内容")

        # 提取 JSON（兜底兼容 markdown 包裹）
        content = content.strip()
        if "```" in content:
            for block in content.split("```"):
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if block.startswith("{"):
                    content = block
                    break

        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            content = content[start:end + 1]
        else:
            raise RuntimeError("Kimi 未返回有效 JSON")

        result = json.loads(content)
        polygon = result.get("polygon") or result.get("points") or result.get("coordinates") or []
        if isinstance(polygon, list) and len(polygon) >= 3:
            return polygon

        raise RuntimeError("Kimi 未能识别出目标物体")

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

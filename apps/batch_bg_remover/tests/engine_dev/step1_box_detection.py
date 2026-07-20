#!/usr/bin/env python3
"""
engine_dev/step1_box_detection.py

轻量定位 + 局部 SAM 2 引擎 —— 第一步测试脚本：
  用国产视觉模型（Qwen2.5-VL-7B，硅基流动）根据文本提示词提取主体 Bounding Box，
  并将框绘制在图片上保存为 debug_box.jpg，用于验证粗定位效果。

运行：
  cd apps/batch_bg_remover
  $env:SILICONFLOW_API_KEY="你的Key"
  python tests/engine_dev/step1_box_detection.py

环境变量：
  SILICONFLOW_API_KEY  (必填)
"""

import base64
import io
import json
import os
import re
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

# ── 配置 ─────────────────────────────────────────────────────────
# Qwen3-VL-32B：国产多模态，32B 参数，视觉定位精准
MODEL = "Qwen/Qwen3-VL-32B-Instruct"
API_BASE = "https://api.siliconflow.cn/v1/chat/completions"

# 最大图片边长，避免超时
_MAX_IMG_SIZE = 800

PROMPT = """你是一个精准的视觉定位助手。给定一张图片和一段描述，找出描述所指的物体，并返回其 bounding box。

请使用 Qwen3-VL 的标准格式：
<box>[[x_min, y_min, x_max, y_max]]</box>

坐标规则：
- x_min, y_min, x_max, y_max 都是归一化到 0-1000 的整数
- (x_min, y_min) 是 box 左上角，(x_max, y_max) 是 box 右下角
- 四边必须贴合物体的最外侧像素
- "左边" 指图片中 x 坐标较小的物体，"右边" 指 x 坐标较大的物体
- 如果图中没有该物体，返回空 box：<box>[]</box>

返回格式示例：
<box>[[120, 200, 400, 800]]</box>

只输出 <box> 标签，不要输出其他文字。

要定位的物体："""

# 图片和提示词（测试时修改这两个）
IMAGE_PATH = Path(__file__).parent.parent / "test_bird.jpg"
OBJECT_PROMPT = "左边那只鸟"
OUTPUT_PATH = Path(__file__).parent / "debug_box.jpg"


def encode_image(image_path: Path) -> tuple[str, tuple[int, int]]:
    """将图片压缩到最长边 800px 转为 JPEG base64。"""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    if img.width > _MAX_IMG_SIZE or img.height > _MAX_IMG_SIZE:
        ratio = _MAX_IMG_SIZE / max(img.width, img.height)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return b64, (w, h)  # 返回原始尺寸


def call_vision_api(api_key: str, image_b64: str, prompt: str) -> dict:
    """调用硅基流动 Vision API，返回 JSON 中的 box_2d 和 label。"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT + prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ]
        }],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    resp = requests.post(API_BASE, json=payload, headers=headers, timeout=60)

    if resp.status_code == 429:
        raise RuntimeError("硅基流动免费额度已用完，请稍后再试或切换 API Key")
    if resp.status_code != 200:
        raise RuntimeError(f"API 失败: HTTP {resp.status_code} - {resp.text[:400]}")

    data = resp.json()
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not content:
        raise RuntimeError("模型未返回文本")

    # 提取 Qwen3-VL 的 <box>[[x_min, y_min, x_max, y_max]]</box> 格式
    match = re.search(r"<box>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]</box>", content)
    if not match:
        # 兼容空 box
        if "<box>[]</box>" in content or "<box> </box>" in content:
            return {"box_2d": [], "label": "not found"}
        raise RuntimeError(f"未能从响应中提取 box 标签: {content[:300]}")

    x_min, y_min, x_max, y_max = map(int, match.groups())

    # 内部统一使用 [ymin, xmin, ymax, xmax] 的 0-1000 格式
    return {
        "box_2d": [y_min, x_min, y_max, x_max],
        "label": prompt,
    }


def draw_box(image_path: Path, box: list, output_path: Path) -> None:
    """
    box: [ymin, xmin, ymax, xmax] 归一化到 0-1000
    在图片上绘制红色半透明框，并保存。
    """
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    # 转换到像素坐标
    ymin, xmin, ymax, xmax = box
    x1 = int(xmin / 1000 * w)
    y1 = int(ymin / 1000 * h)
    x2 = int(xmax / 1000 * w)
    y2 = int(ymax / 1000 * h)

    # 绘制半透明红色框
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0, 255), width=4)

    # 填充淡红色半透明背景
    box_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    box_draw = ImageDraw.Draw(box_layer)
    box_draw.rectangle([x1, y1, x2, y2], fill=(255, 0, 0, 40))

    # 尝试加载中文字体，避免 Windows 默认字体显示方块
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "arial.ttf",
    ]
    font = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, size=20)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    label = f"{OBJECT_PROMPT} | box: {box}"
    text_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text((x1, max(0, y1 - 30)), label, fill=(255, 0, 0, 255), font=font)

    composite = Image.alpha_composite(img, box_layer)
    composite = Image.alpha_composite(composite, overlay)
    composite = Image.alpha_composite(composite, text_layer)
    composite.convert("RGB").save(output_path, quality=95)
    print(f"  已保存可视化结果: {output_path}")


def main():
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        raise RuntimeError("请设置环境变量 SILICONFLOW_API_KEY")

    print(f"[1/3] 读取图片: {IMAGE_PATH}")
    image_b64, (w, h) = encode_image(IMAGE_PATH)
    print(f"  原始尺寸: {w}x{h}")

    print(f"""[2/3] 调用 {MODEL} 检测: "{OBJECT_PROMPT}" """)
    result = call_vision_api(api_key, image_b64, OBJECT_PROMPT)
    print(f"  原始响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

    box = result.get("box_2d")
    if not box or len(box) != 4:
        raise RuntimeError("未检测到有效 Bounding Box")
    print(f"  [OK] 箱体坐标: {box}")

    print(f"[3/3] 绘制 BBox 到图片")
    draw_box(IMAGE_PATH, box, OUTPUT_PATH)
    print(f"  完成。请查看 tests/engine_dev/debug_box.jpg")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
engine_dev/step1_batch.py

批量测试 Box 定位效果，支持一张图 + 多个提示词。
每轮生成独立的 debug 图，方便横向对比。

运行：
  cd apps/batch_bg_remover
  $env:SILICONFLOW_API_KEY="你的Key"
  python tests/engine_dev/step1_batch.py

环境变量：
  SILICONFLOW_API_KEY  (必填)

如需加更多测试用例，直接编辑 TEST_CASES 列表即可：
  (image_path, prompt, output_suffix)
"""

import base64
import io
import json
import os
import re
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont

# ── 配置 ─────────────────────────────────────────────────────────
MODEL = "Qwen/Qwen3-VL-32B-Instruct"
API_BASE = "https://api.siliconflow.cn/v1/chat/completions"
_MAX_IMG_SIZE = 800

PROMPT_TEMPLATE = """你是一个精准的视觉定位助手。给定一张图片和一段描述，找出描述所指的物体，并返回其 bounding box。

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

# ── 测试用例 ─────────────────────────────────────────────────────
# 格式: (图片路径, 提示词, 输出文件名后缀)
# 添加新用例只需要加一行

_BASE_DIR = Path(__file__).parent.parent  # tests/

TEST_CASES = [
    (_BASE_DIR / "test_bird.jpg", "左边那只鸟", "bird_left"),
    (_BASE_DIR / "test_bird.jpg", "右边那只鸟", "bird_right"),
    (_BASE_DIR / "test_bird.jpg", "两只鸟", "bird_both"),
    (_BASE_DIR / "test_cat.jpg", "猫的绿色帽子", "cat_hat"),
    (_BASE_DIR / "test_cat.jpg", "整只猫", "cat_body"),
    (_BASE_DIR / "test_person_pc.jpg", "人", "person"),
    (_BASE_DIR / "test_person_pc.jpg", "电脑", "pc"),
]

OUTPUT_DIR = Path(__file__).parent  # engine_dev/


# ── 核心函数 ─────────────────────────────────────────────────────

def encode_image(image_path: Path) -> tuple[str, tuple[int, int]]:
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    if img.width > _MAX_IMG_SIZE or img.height > _MAX_IMG_SIZE:
        ratio = _MAX_IMG_SIZE / max(img.width, img.height)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8"), (w, h)


def call_vision_api(api_key: str, image_b64: str, prompt: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT_TEMPLATE + prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ]
        }],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    resp = requests.post(API_BASE, json=payload, headers=headers, timeout=120)

    if resp.status_code == 429:
        raise RuntimeError("硅基流动额度已用完，请稍后再试或切换 API Key")
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

    match = re.search(r"<box>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]</box>", content)
    if not match:
        if "<box>[]</box>" in content or "<box> </box>" in content:
            return {"box_2d": [], "label": "not found"}
        raise RuntimeError(f"未能从响应中提取 box 标签: {content[:300]}")

    x_min, y_min, x_max, y_max = map(int, match.groups())
    return {"box_2d": [y_min, x_min, y_max, x_max], "label": prompt}


def _load_font() -> Optional[ImageFont.FreeTypeFont]:
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "arial.ttf",
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size=20)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_box(image_path: Path, box: list, label: str, output_path: Path) -> None:
    """
    box: [ymin, xmin, ymax, xmax]  归一化到 0-1000
    """
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    ymin, xmin, ymax, xmax = box
    x1 = int(xmin / 1000 * w)
    y1 = int(ymin / 1000 * h)
    x2 = int(xmax / 1000 * w)
    y2 = int(ymax / 1000 * h)

    font = _load_font()

    # 红色边框
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0, 255), width=4)

    # 红色半透明填充
    box_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    box_draw = ImageDraw.Draw(box_layer)
    box_draw.rectangle([x1, y1, x2, y2], fill=(255, 0, 0, 40))

    # 文字标签
    text_str = f"{label} | box: {box}"
    text_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text((x1, max(0, y1 - 30)), text_str, fill=(255, 0, 0, 255), font=font)

    composite = Image.alpha_composite(img, box_layer)
    composite = Image.alpha_composite(composite, overlay)
    composite = Image.alpha_composite(composite, text_layer)
    composite.convert("RGB").save(output_path, quality=95)


def run_one(image_path: Path, object_prompt: str, output_suffix: str, api_key: str) -> None:
    """运行单条测试用例"""
    output_path = OUTPUT_DIR / f"debug_box_{output_suffix}.jpg"

    image_b64, (w, h) = encode_image(image_path)
    print(f"  图片: {image_path.name}  ({w}x{h})")
    print(f"  提示: \"{object_prompt}\"")

    result = call_vision_api(api_key, image_b64, object_prompt)
    box = result.get("box_2d")
    if not box or len(box) != 4:
        print(f"  [FAIL] 未检测到有效 BBox -> {json.dumps(result, ensure_ascii=False)}")
        return

    print(f"  [OK] box: {box}")
    draw_box(image_path, box, object_prompt, output_path)
    print(f"  -> {output_path.name}\n")


def main():
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        raise RuntimeError("请设置环境变量 SILICONFLOW_API_KEY")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"模型: {MODEL}")
    print(f"共 {len(TEST_CASES)} 条测试用例\n")

    success = 0
    for i, (img_path, prompt, suffix) in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}]", end=" ")
        try:
            run_one(img_path, prompt, suffix, api_key)
            success += 1
        except Exception as e:
            print(f"  [ERROR] {e}\n")

    print(f"完成: {success}/{len(TEST_CASES)} 条通过")
    print(f"输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

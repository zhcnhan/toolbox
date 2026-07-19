"""
测试工具：在鸟图上画出多边形轮廓并保存。
用法：
    python tests/test_draw_polygon.py <模型名> "<多边形坐标JSON>"

示例：
    python tests/test_draw_polygon.py gemini-3.1-flash-lite "[{\"x\": 462, \"y\": 431}, ...]"
"""

import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
IMAGE_PATH = BASE / "test_bird.jpg"
OUTPUT_DIR = BASE / "polygon_results"

def main():
    if len(sys.argv) < 3:
        print("用法: python test_draw_polygon.py <模型名> \"<坐标JSON>\"")
        print("坐标格式: [[x1,y1],[x2,y2],...]")
        sys.exit(1)

    model_name = sys.argv[1].replace(" ", "_").replace("/", "-")
    coords_str = sys.argv[2]

    # 解析坐标
    try:
        points = json.loads(coords_str)
    except json.JSONDecodeError:
        print("❌ 坐标 JSON 格式错误")
        sys.exit(1)

    # 如果是 {"polygon": [...]} 格式，提取 polygon
    if isinstance(points, dict) and "polygon" in points:
        points = points["polygon"]

    if not isinstance(points, list) or len(points) < 3:
        print("❌ 至少需要 3 个点")
        sys.exit(1)

    # 读图
    img = Image.open(IMAGE_PATH).convert("RGB")
    W, H = img.size

    # 坐标可能是 0-1000 归一化，也可能是像素坐标，自动判断
    max_val = max(max(p[0], p[1]) for p in points)
    if max_val > 10:  # 不是归一化就是像素
        # 判断是否为 0-1000 归一化
        if max_val > 100:
            # 像素坐标，直接使用
            scaled = [(int(p[0]), int(p[1])) for p in points]
        else:
            # 0-1000 归一化
            scaled = [(int(p[0] / 1000 * W), int(p[1] / 1000 * H)) for p in points]
    else:
        # 0-1 归一化
        scaled = [(int(p[0] * W), int(p[1] * H)) for p in points]

    # 画轮廓
    draw = ImageDraw.Draw(img)
    draw.polygon(scaled, outline=(255, 0, 0), width=3)

    # 保存
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{model_name}.png"
    img.save(out_path)
    print(f"✅ {out_path}")

if __name__ == "__main__":
    main()

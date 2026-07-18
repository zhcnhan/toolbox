#!/usr/bin/env python3
"""
run.py — 一键启动 Batch Background Remover

生产模式（默认）：
  - 前端已构建为静态文件，由 FastAPI 直接服务
  - 单进程，访问 http://127.0.0.1:8001

开发模式（--dev）：
  - 前端用 Vite 开发服务器（热更新）
  - 后端用 uvicorn --reload
  - 前端 http://127.0.0.1:5174，后端 http://127.0.0.1:8001

用法：
  python run.py           # 生产模式
  python run.py --dev     # 开发模式
  python run.py --build   # 仅构建前端
  python run.py --port 9000  # 自定义端口
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = BACKEND_DIR / "static"


def build_frontend():
    """构建前端静态文件到 backend/static/"""
    print("[Build] 构建前端静态文件...")
    # 优先用 node 直接调 vite，避免 npm 的开销
    vite_bin = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
    if vite_bin.exists():
        cmd = ["node", str(vite_bin), "build"]
        result = subprocess.run(cmd, cwd=FRONTEND_DIR)
    else:
        # Windows 上 npm 是 .cmd 文件，需要 shell=True
        result = subprocess.run("npm run build", cwd=FRONTEND_DIR, shell=True)
    if result.returncode != 0:
        print("[Build] 构建失败！")
        sys.exit(1)
    print(f"[Build] 构建完成，输出到 {STATIC_DIR}")


def check_clipseg_deps():
    """
    检测 CLIPSeg 依赖（torch + transformers）是否已安装。
    未安装时提示用户是否要安装（体积大，可选）。
    """
    try:
        import torch  # type: ignore  # noqa: F401
        import transformers  # type: ignore  # noqa: F401
        return True  # 已安装
    except ImportError:
        pass

    print()
    print("=" * 60)
    print("  CLIPSeg 提示词分割引擎 — 依赖未安装")
    print("=" * 60)
    print()
    print("  CLIPSeg 引擎可以让用户通过文本提示词（如「猫」「红色汽车」）")
    print("  精确选取图片中的主体进行抠图。")
    print()
    print("  ⚠️  警告：安装体积较大")
    print("     · torch (CPU 版)      ~200 MB")
    print("     · transformers         ~500 MB")
    print("     · 首次使用还需下载模型  ~1.5 GB")
    print("     合计约 2.2 GB 磁盘空间")
    print()
    print("  不安装也能正常使用其他功能：")
    print("     · rembg 本地自动抠图    ✅")
    print("     · remove.bg 云端抠图    ✅")
    print("     · 擦个图云端抠图        ✅")
    print("     · Gemini 云端抠图       ✅")
    print("     · 自定义引擎            ✅")
    print("     · CLIPSeg 提示词分割    ❌（需要此依赖）")
    print()

    try:
        choice = input("  是否现在安装 CLIPSeg 依赖？[y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        choice = "n"

    if choice != "y":
        print()
        print("  跳过安装。CLIPSeg 引擎将不可用，其他功能不受影响。")
        print("  之后可手动安装: pip install transformers torch")
        print()
        return False

    print()
    print("  正在安装 torch (CPU 版) + transformers ...")
    print("  这可能需要几分钟，请耐心等待...")
    print()

    # 先装 CPU 版 torch（从官方源，体积更小）
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install",
         "torch", "--index-url", "https://download.pytorch.org/whl/cpu"],
        cwd=BACKEND_DIR,
    )
    if result.returncode != 0:
        print("  torch 安装失败！CLIPSeg 将不可用。")
        print("  可稍后手动安装: pip install transformers torch")
        return False

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "transformers"],
        cwd=BACKEND_DIR,
    )
    if result.returncode != 0:
        print("  transformers 安装失败！CLIPSeg 将不可用。")
        return False

    print()
    print("  CLIPSeg 依赖安装成功！首次使用时会自动下载模型 (~1.5GB)。")
    print()
    return True


def run_production(port):
    """生产模式：单进程"""
    if not STATIC_DIR.exists():
        print("[Prod] 前端未构建，先执行构建...")
        build_frontend()

    print(f"[Prod] 启动服务: http://0.0.0.0:{port}")
    print(f"[Prod] API 文档: http://127.0.0.1:{port}/docs")
    print("[Prod] 按 Ctrl+C 停止")

    cmd = [sys.executable, "main.py"]
    env = os.environ.copy()
    env["PORT"] = str(port)
    subprocess.run(cmd, cwd=BACKEND_DIR, env=env)


def run_dev(port):
    """开发模式：前后端分离，热更新"""
    print(f"[Dev] 启动后端: http://127.0.0.1:{port}")
    print(f"[Dev] 启动前端: http://127.0.0.1:5174")

    # 后端
    backend = subprocess.Popen(
        [sys.executable, "main.py", "--reload"],
        cwd=BACKEND_DIR,
    )

    # 前端
    vite_bin = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
    frontend = subprocess.Popen(
        ["node", str(vite_bin), "--host", "0.0.0.0", "--port", "5174"],
        cwd=FRONTEND_DIR,
    )

    print("[Dev] 按 Ctrl+C 停止所有服务")
    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\n[Dev] 正在停止...")
        backend.terminate()
        frontend.terminate()
        backend.wait()
        frontend.wait()


def main():
    parser = argparse.ArgumentParser(description="Batch Background Remover 启动器")
    parser.add_argument("--dev", action="store_true", help="开发模式（热更新）")
    parser.add_argument("--build", action="store_true", help="仅构建前端")
    parser.add_argument("--port", type=int, default=8001, help="端口号（默认 8001）")
    args = parser.parse_args()

    if args.build:
        build_frontend()
        return

    # 检测 CLIPSeg 依赖（可选，体积大，提示用户）
    check_clipseg_deps()

    if args.dev:
        run_dev(args.port)
    else:
        run_production(args.port)


if __name__ == "__main__":
    main()

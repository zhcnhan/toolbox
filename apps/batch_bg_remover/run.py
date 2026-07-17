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
    npm = os.environ.get("npm_execpath", "npm")
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

    if args.dev:
        run_dev(args.port)
    else:
        run_production(args.port)


if __name__ == "__main__":
    main()

"""
main.py — FastAPI 主入口

提供：
  GET  /api/engines              — 列出所有可用引擎
  POST /api/upload               — 批量上传图片
  POST /api/remove-bg            — 自动抠图
  POST /api/remove-bg-prompt     — 提示词抠图
  GET  /api/download/{file_id}   — 下载单张结果
  GET  /api/download-zip/{task_id} — 打包下载所有结果
  GET  /api/health               — 健康检查
"""

import io
import os
import json
import uuid
import zipfile
import shutil
import asyncio
import threading
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 自动发现并注册所有引擎（扫描 engines/ 目录，无需手动 import）
from engine_registry import auto_discover_engines, get_engine, list_engines
auto_discover_engines()

# Gemini 速率限制查询
from rate_limiter import gemini_limiter

# 代理配置管理
from proxy import get_proxy_config, set_proxy_config

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per image

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Batch Background Remover",
    description="批量抠图服务：支持本地引擎（rembg/CLIPSeg）和云端引擎（Gemini/Replicate）",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 线程池，用于执行同步的本地模型推理
_executor = ThreadPoolExecutor(max_workers=2)


def _run_sync(coro_func, *args):
    """
    将 async 协程函数包装成同步可调用对象，供 run_in_executor 使用。
    本地引擎的 remove_bg 是 async 但内部是同步逻辑，
    用 asyncio.run 在子线程中创建新事件循环来执行。
    """
    import asyncio
    def _wrapper():
        return asyncio.run(coro_func(*args))
    return _wrapper

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
class EngineInfoResponse(BaseModel):
    engines: list

class RemoveBgRequest(BaseModel):
    engine_id: str
    api_key: Optional[str] = None

class RemoveBgPromptRequest(BaseModel):
    engine_id: str
    prompt: str
    api_key: Optional[str] = None

# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "batch-bg-remover"}


@app.get("/api/proxy")
async def get_proxy():
    """获取代理配置"""
    return get_proxy_config()


@app.put("/api/proxy")
async def update_proxy(
    enabled: bool = Form(False),
    url: str = Form(""),
    auth_type: str = Form("none"),
    username: str = Form(""),
    password: str = Form(""),
):
    """更新代理配置"""
    validated_url = url.strip()
    # 基本校验：如果启用代理，URL 必须以 http:// 或 https:// 开头
    if enabled and validated_url:
        if not validated_url.startswith(("http://", "https://")):
            raise HTTPException(400, "代理地址必须以 http:// 或 https:// 开头")
    config = set_proxy_config(enabled, validated_url, auth_type, username, password)
    # 返回时隐藏密码
    safe_config = dict(config)
    if safe_config.get("password"):
        safe_config["password"] = "******"
    return {"success": True, "config": safe_config}


@app.get("/api/engines")
async def get_engines():
    """列出所有可用引擎"""
    engines = list_engines()
    return {
        "engines": [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "type": e.type,
                "supports_auto": e.supports_auto,
                "supports_prompt": e.supports_prompt,
                "needs_api_key": e.needs_api_key,
                "api_key_label": e.api_key_label,
                "api_key_help_url": e.api_key_help_url,
                "icon": e.icon,
            }
            for e in engines
        ]
    }


@app.get("/api/engine/gemini/quota")
async def gemini_quota():
    """查询 Gemini API 配额状态（RPM / RPD）"""
    return gemini_limiter.get_quota()


# ============================================================
_CLIPSEG_MODEL_ID = "CIDAS/clipseg-rd64-refined"
_CLIPSEG_DOWNLOAD_TASK: dict = {"running": False, "progress": 0, "error": ""}


def _get_clipseg_cache_path() -> Path | None:
    """检查 CLIPSeg 模型是否已缓存，返回缓存目录或 None"""
    # HuggingFace 缓存路径
    hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    hub_dir = hf_home / "hub"
    if not hub_dir.exists():
        return None
    # 查找模型缓存目录
    for d in hub_dir.iterdir():
        if d.is_dir() and "clipseg-rd64-refined" in d.name:
            # 检查关键文件
            snapshots = d / "snapshots"
            if snapshots.exists():
                for s in snapshots.iterdir():
                    if (s / "pytorch_model.bin").exists():
                        return s
    return None


@app.get("/api/engine/clipseg_local/status")
async def clipseg_status():
    """检查 CLIPSeg 模型下载状态"""
    cached = _get_clipseg_cache_path() is not None
    return {
        "engine_id": "clipseg_local",
        "cached": cached,
        "downloading": _CLIPSEG_DOWNLOAD_TASK["running"],
        "progress": _CLIPSEG_DOWNLOAD_TASK["progress"],
        "error": _CLIPSEG_DOWNLOAD_TASK["error"],
    }


def _download_clipseg_background():
    """后台线程：下载 CLIPSeg 模型并更新进度"""
    try:
        from huggingface_hub import snapshot_download
        _CLIPSEG_DOWNLOAD_TASK["running"] = True
        _CLIPSEG_DOWNLOAD_TASK["progress"] = 0
        _CLIPSEG_DOWNLOAD_TASK["error"] = ""
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

        # 检查是否已缓存
        if _get_clipseg_cache_path() is not None:
            _CLIPSEG_DOWNLOAD_TASK["progress"] = 100
            _CLIPSEG_DOWNLOAD_TASK["running"] = False
            return

        # 带进度的下载
        def on_progress(current, total):
            if total > 0:
                _CLIPSEG_DOWNLOAD_TASK["progress"] = int(current / total * 100)

        snapshot_download(
            _CLIPSEG_MODEL_ID,
            local_files_only=False,
            callback=on_progress,
        )
        _CLIPSEG_DOWNLOAD_TASK["progress"] = 100
    except Exception as e:
        _CLIPSEG_DOWNLOAD_TASK["error"] = str(e)
    finally:
        _CLIPSEG_DOWNLOAD_TASK["running"] = False


@app.post("/api/engine/clipseg_local/download")
async def clipseg_download():
    """触发 CLIPSeg 模型下载"""
    if _CLIPSEG_DOWNLOAD_TASK["running"]:
        return {
            "status": "already_downloading",
            "progress": _CLIPSEG_DOWNLOAD_TASK["progress"],
        }
    if _get_clipseg_cache_path() is not None:
        return {"status": "already_cached", "progress": 100}

    thread = threading.Thread(target=_download_clipseg_background, daemon=True)
    thread.start()
    return {"status": "started", "progress": 0}


@app.get("/api/engine/clipseg_local/download/progress")
async def clipseg_download_progress():
    """获取 CLIPSeg 模型下载进度"""
    return dict(_CLIPSEG_DOWNLOAD_TASK)


# ============================================================
# CLIPSeg 依赖（torch + transformers）自动安装
# ============================================================

_CLIPSEG_DEPS_TASK: dict = {"running": False, "progress": 0, "error": "", "stage": ""}


def _check_clipseg_deps_installed() -> bool:
    """检查 CLIPSeg 依赖（torch + transformers）是否已安装"""
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _install_clipseg_deps_background():
    """后台线程：安装 torch + transformers"""
    import subprocess
    import sys

    _CLIPSEG_DEPS_TASK["running"] = True
    _CLIPSEG_DEPS_TASK["progress"] = 0
    _CLIPSEG_DEPS_TASK["error"] = ""
    _CLIPSEG_DEPS_TASK["stage"] = "installing"

    try:
        # step 1: torch
        _CLIPSEG_DEPS_TASK["stage"] = "正在安装 PyTorch（约 800MB）..."
        _CLIPSEG_DEPS_TASK["progress"] = 10
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "torch",
             "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
             "--no-cache-dir"],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            _CLIPSEG_DEPS_TASK["error"] = f"PyTorch 安装失败: {result.stderr[-200:]}"
            return

        _CLIPSEG_DEPS_TASK["progress"] = 55

        # step 2: transformers
        _CLIPSEG_DEPS_TASK["stage"] = "正在安装 transformers..."
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "transformers",
             "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
             "--no-cache-dir"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            _CLIPSEG_DEPS_TASK["error"] = f"transformers 安装失败: {result.stderr[-200:]}"
            return

        _CLIPSEG_DEPS_TASK["progress"] = 85
        _CLIPSEG_DEPS_TASK["stage"] = "验证安装..."
        import torch  # noqa: F401
        import transformers  # noqa: F401
        _CLIPSEG_DEPS_TASK["progress"] = 100
        _CLIPSEG_DEPS_TASK["stage"] = "安装完成"

    except ImportError:
        _CLIPSEG_DEPS_TASK["error"] = "验证失败，请尝试手动安装"
    except subprocess.TimeoutExpired:
        _CLIPSEG_DEPS_TASK["error"] = "安装超时，请检查网络后重试"
    except Exception as e:
        _CLIPSEG_DEPS_TASK["error"] = str(e)
    finally:
        _CLIPSEG_DEPS_TASK["running"] = False


@app.get("/api/engine/clipseg_local/deps-status")
async def clipseg_deps_status():
    """检查 CLIPSeg 依赖安装状态"""
    installed = _check_clipseg_deps_installed()
    return {
        "engine_id": "clipseg_local",
        "installed": installed,
        **dict(_CLIPSEG_DEPS_TASK),
    }


@app.post("/api/engine/clipseg_local/install-deps")
async def clipseg_install_deps():
    """触发 CLIPSeg 依赖安装（torch + transformers）"""
    if _check_clipseg_deps_installed():
        return {"status": "already_installed", "progress": 100}
    if _CLIPSEG_DEPS_TASK["running"]:
        return {"status": "installing", "progress": _CLIPSEG_DEPS_TASK["progress"]}

    thread = threading.Thread(target=_install_clipseg_deps_background, daemon=True)
    thread.start()
    return {"status": "started", "progress": 0, "stage": "正在安装 PyTorch（约 800MB）..."}


@app.post("/api/upload")
async def upload_images(files: list[UploadFile] = File(...)):
    """批量上传图片，返回文件 ID 列表"""
    if not files:
        raise HTTPException(400, "请至少上传一张图片")

    result = []
    for f in files:
        if f.size and f.size > MAX_FILE_SIZE:
            raise HTTPException(400, f"文件 {f.filename} 超过 50MB 限制")

        file_id = uuid.uuid4().hex
        content = await f.read()

        # 保存原始文件
        file_path = UPLOAD_DIR / f"{file_id}_{f.filename}"
        file_path.write_bytes(content)

        result.append({
            "file_id": file_id,
            "filename": f.filename,
            "size": len(content),
        })

    return {"files": result}


@app.post("/api/remove-bg")
async def remove_background(
    file_id: str = Form(...),
    engine_id: str = Form("rembg_local"),
    api_key: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
):
    """
    对指定图片执行自动抠图
    前端对每张图独立调用此接口
    """
    engine = get_engine(engine_id)
    if engine is None:
        raise HTTPException(400, f"未知引擎: {engine_id}")

    # 查找上传的文件
    files = list(UPLOAD_DIR.glob(f"{file_id}_*"))
    if not files:
        raise HTTPException(404, "文件未找到，请重新上传")
    file_path = files[0]

    image_bytes = file_path.read_bytes()

    try:
        engine_info = engine.__class__.info()
        if engine_info.type == "local":
            loop = asyncio.get_event_loop()
            result_bytes = await loop.run_in_executor(
                _executor, _run_sync(engine.remove_bg, image_bytes, api_key)
            )
        elif engine_id == "custom":
            # 自定义引擎需要额外参数
            result_bytes = await engine.remove_bg(
                image_bytes, api_key, base_url=base_url or "", model_name=model_name or ""
            )
        else:
            result_bytes = await engine.remove_bg(image_bytes, api_key)

        # 保存结果
        result_id = uuid.uuid4().hex
        result_path = OUTPUT_DIR / f"{result_id}.png"
        result_path.write_bytes(result_bytes)

        return {
            "success": True,
            "result_id": result_id,
            "size": len(result_bytes),
        }

    except NotImplementedError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"抠图失败: {str(e)}")


@app.post("/api/remove-bg-prompt")
async def remove_background_with_prompt(
    file_id: str = Form(...),
    engine_id: str = Form(...),
    prompt: str = Form(...),
    api_key: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    sensitivity: Optional[float] = Form(None),
):
    """
    根据文本提示词选取主体并抠图
    """
    engine = get_engine(engine_id)
    if engine is None:
        raise HTTPException(400, f"未知引擎: {engine_id}")

    if not prompt or not prompt.strip():
        raise HTTPException(400, "请输入提示词")

    files = list(UPLOAD_DIR.glob(f"{file_id}_*"))
    if not files:
        raise HTTPException(404, "文件未找到，请重新上传")
    file_path = files[0]

    image_bytes = file_path.read_bytes()

    # 为 CLIPSeg 准备 sensitivity 参数
    clip_sens = max(0.0, min(1.0, sensitivity)) if engine_id == "clipseg_local" and sensitivity is not None else None

    try:
        engine_info = engine.__class__.info()
        if engine_info.type == "local":
            loop = asyncio.get_event_loop()
            if clip_sens is not None:
                result_bytes = await loop.run_in_executor(
                    _executor, _run_sync(engine.remove_bg_with_prompt, image_bytes, prompt, api_key, clip_sens)
                )
            else:
                result_bytes = await loop.run_in_executor(
                    _executor, _run_sync(engine.remove_bg_with_prompt, image_bytes, prompt, api_key)
                )
        elif engine_id == "custom":
            result_bytes = await engine.remove_bg_with_prompt(
                image_bytes, prompt, api_key, base_url=base_url or "", model_name=model_name or ""
            )
        else:
            result_bytes = await engine.remove_bg_with_prompt(image_bytes, prompt, api_key)

        result_id = uuid.uuid4().hex
        result_path = OUTPUT_DIR / f"{result_id}.png"
        result_path.write_bytes(result_bytes)

        return {
            "success": True,
            "result_id": result_id,
            "size": len(result_bytes),
        }

    except NotImplementedError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"抠图失败: {str(e)}")


@app.get("/api/download/{result_id}")
async def download_result(result_id: str):
    """下载单张抠图结果"""
    result_path = OUTPUT_DIR / f"{result_id}.png"
    if not result_path.exists():
        raise HTTPException(404, "结果未找到")

    return FileResponse(
        result_path,
        media_type="image/png",
        filename=f"removed_bg_{result_id[:8]}.png",
    )


@app.get("/api/download-zip")
async def download_zip(result_ids: str = Query(..., description="逗号分隔的 result_id 列表")):
    """打包下载多个结果"""
    ids = [rid.strip() for rid in result_ids.split(",") if rid.strip()]
    if not ids:
        raise HTTPException(400, "请指定要下载的结果")

    zip_path = OUTPUT_DIR / f"batch_{uuid.uuid4().hex[:8]}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, rid in enumerate(ids):
            png_path = OUTPUT_DIR / f"{rid}.png"
            if png_path.exists():
                zf.write(png_path, f"result_{i+1}_{rid[:8]}.png")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="batch_bg_removed.zip",
    )


# ---------------------------------------------------------------------------
# 静态文件服务（前端 SPA）
# 前端构建后输出到 backend/static/，由 FastAPI 直接服务
# 所有非 /api 路径都返回 index.html（SPA 路由）
# ---------------------------------------------------------------------------
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    from fastapi.staticfiles import StaticFiles

    # 挂载静态资源（JS/CSS/图片等）
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # SPA fallback：所有非 /api 路径返回 index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 先尝试匹配 static 目录下的实际文件（如 favicon.ico）
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        # 否则返回 index.html（React Router 接管）
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(404, "前端未构建，请先运行 npm run build")


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    import sys

    # 生产模式：单进程，无 reload
    # 开发模式加 --reload 参数
    reload = "--reload" in sys.argv
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)

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
import time
from datetime import datetime
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

# Gemini 速率限制查询（按 API Key 追踪）
from rate_limiter import track_request, list_all_keys

# 代理配置管理
from proxy import get_proxy_config, set_proxy_config, test_proxy_connectivity

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
    description="批量抠图服务：支持本地引擎（rembg/SAM）和云端引擎（Gemini/Kimi/硅基流动/自定义）",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 线程池，用于执行同步的模型推理（本地引擎 CPU 计算 + 云端引擎 HTTP 请求）
_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="bg_remover")

# 全局任务超时（秒），防止卡死的任务永久占用线程
_TASK_TIMEOUT = 600

# ---------------------------------------------------------------------------
# 文件清理
# ---------------------------------------------------------------------------
_CLEANUP_INTERVAL = 3600  # 1 小时清理一次
_OUTPUT_MAX_AGE = 7200    # 输出文件保留 2 小时
_UPLOAD_MAX_AGE = 7200    # 上传文件保留 2 小时

# ---------------------------------------------------------------------------
# 使用监控（临时，用于客户试用期跟踪）
# ---------------------------------------------------------------------------
USAGE_LOG = BASE_DIR / "data" / "usage.jsonl"
USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)


def _log_usage(entry: dict):
    """记录一条使用日志到 usage.jsonl（无锁写入，文件 append 是原子的）"""
    entry["_time"] = datetime.now().isoformat()
    try:
        with open(USAGE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 日志不能影响主流程


def _get_usage_stats() -> dict:
    """汇总使用统计"""
    stats = {
        "total_requests": 0,
        "total_images": 0,
        "by_engine": {},
        "errors": [],
        "first_request": None,
        "last_request": None,
        "log_file": str(USAGE_LOG),
    }
    if not USAGE_LOG.exists():
        return stats
    try:
        with open(USAGE_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                stats["total_requests"] += 1
                stats["total_images"] += entry.get("image_count", 1)
                eid = entry.get("engine", "unknown")
                if eid not in stats["by_engine"]:
                    stats["by_engine"][eid] = {"count": 0, "success": 0, "fail": 0}
                stats["by_engine"][eid]["count"] += 1
                if entry.get("success"):
                    stats["by_engine"][eid]["success"] += 1
                else:
                    stats["by_engine"][eid]["fail"] += 1
                    stats["errors"].append({
                        "time": entry.get("_time"),
                        "engine": eid,
                        "error": entry.get("error", "")[:120],
                    })
                if stats["first_request"] is None:
                    stats["first_request"] = entry.get("_time")
                stats["last_request"] = entry.get("_time")
        # 只保留最近 20 条错误
        stats["errors"] = stats["errors"][-20:]
    except Exception:
        pass
    return stats


@app.get("/api/stats")
async def usage_stats():
    """查看使用统计（临时监控用）"""
    return _get_usage_stats()


@app.post("/api/stats/clear")
async def clear_stats():
    """清空使用日志"""
    try:
        USAGE_LOG.unlink(missing_ok=True)
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(500, str(e))


def _run_sync(coro_func, *args):
    """
    将 async 协程函数包装成同步可调用对象，供 run_in_executor 使用。
    所有引擎（本地 + 云端）都通过此方式运行，避免阻塞事件循环。
    """
    import asyncio
    def _wrapper():
        try:
            return asyncio.run(coro_func(*args))
        except asyncio.CancelledError:
            return None  # 任务被取消，静默退出
    return _wrapper


# ---------------------------------------------------------------------------
# 后台任务：定期清理过期文件
# ---------------------------------------------------------------------------
async def _cleanup_old_files():
    """每小时清理超过 2 小时的 uploads 和 outputs 文件"""
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL)
        now = time.time()
        for directory, max_age in [(UPLOAD_DIR, _UPLOAD_MAX_AGE), (OUTPUT_DIR, _OUTPUT_MAX_AGE)]:
            if not directory.exists():
                continue
            deleted = 0
            for f in directory.iterdir():
                if f.is_file() and (now - f.stat().st_mtime) > max_age:
                    try:
                        f.unlink()
                        deleted += 1
                    except Exception:
                        pass
            if deleted:
                print(f"[清理] {directory.name}: 删除了 {deleted} 个过期文件")


# ---------------------------------------------------------------------------
# 健康检查（含线程池状态）
# ---------------------------------------------------------------------------

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
@app.on_event("startup")
async def _startup():
    """启动后台任务：文件清理"""
    asyncio.create_task(_cleanup_old_files())


@app.get("/api/health")
async def health():
    """健康检查（含线程池状态）"""
    pool = _executor
    return {
        "status": "ok",
        "service": "batch-bg-remover",
        "thread_pool": {
            "max_workers": pool._max_workers,
            "alive": sum(1 for t in pool._threads if t.is_alive()) if hasattr(pool, "_threads") else -1,
        },
    }


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


@app.post("/api/proxy/test")
async def test_proxy(
    url: str = Form(""),
    auth_type: str = Form("none"),
    username: str = Form(""),
    password: str = Form(""),
):
    """测试代理连通性"""
    # 构建测试用的代理 URL 字符串
    test_url = None
    if url:
        from proxy import _build_proxy_url
        test_config = {"enabled": True, "url": url, "auth_type": auth_type, "username": username, "password": password}
        test_url = _build_proxy_url(test_config) or url

    result = test_proxy_connectivity(proxy_url=test_url)
    return result


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


@app.post("/api/engine/gemini/usage")
async def gemini_usage(api_key: str = Form("")):
    """查询 API Key 的今日用量（POST，Key 不暴露在 URL 中）"""
    if not api_key:
        return {"keys": list_all_keys()}
    tracker = track_request(api_key)
    return {"usage": tracker.get_info()}


# ---------------------------------------------------------------------------
# SAM 本地引擎 — 模型下载管理
# ---------------------------------------------------------------------------
try:
    from engines.sam_local_engine import get_sam_status, trigger_sam_download
    _HAS_SAM_ENGINE = True
except Exception:
    _HAS_SAM_ENGINE = False
    logger.warning("SAM 引擎加载失败，/api/engine/sam_local/* 路由不可用")


if _HAS_SAM_ENGINE:
    @app.get("/api/engine/sam_local/status")
    async def sam_status():
        """检查 SAM 模型缓存状态"""
        return get_sam_status()


    @app.post("/api/engine/sam_local/download")
    async def sam_download():
        """触发 SAM 模型下载"""
        result = trigger_sam_download()
        return result


@app.get("/api/engine/sam_local/download/progress")
async def sam_download_progress():
    """获取 SAM 模型下载进度"""
    status = get_sam_status()
    return {
        "running": status["running"],
        "progress": status["progress"],
        "error": status["error"],
        "stage": status["stage"],
        "downloaded_bytes": status["downloaded_bytes"],
        "total_bytes": status["total_bytes"],
    }


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


@app.delete("/api/upload/{file_id}")
async def delete_upload(file_id: str):
    """删除已上传的图片及对应的抠图结果"""
    # 删除上传的原图
    deleted_files = 0
    for f in UPLOAD_DIR.glob(f"{file_id}_*"):
        f.unlink()
        deleted_files += 1

    # 删除该文件对应的抠图结果（通过查找 results 中匹配的 file_id）
    # 前端会同步清理状态，后端只清理文件
    return {
        "status": "deleted" if deleted_files > 0 else "not_found",
        "deleted_files": deleted_files,
    }


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
    filename = file_path.name

    image_bytes = file_path.read_bytes()
    t0 = time.time()

    try:
        # 所有引擎统一走线程池，避免阻塞事件循环
        loop = asyncio.get_event_loop()
        if engine_id == "custom":
            future = loop.run_in_executor(
                _executor, _run_sync(engine.remove_bg, image_bytes, api_key,
                                     base_url=base_url or "", model_name=model_name or "")
            )
        else:
            future = loop.run_in_executor(
                _executor, _run_sync(engine.remove_bg, image_bytes, api_key)
            )
        result_bytes = await asyncio.wait_for(future, timeout=_TASK_TIMEOUT)

        if result_bytes is None:
            raise HTTPException(500, "任务被取消，请重试")

        elapsed = time.time() - t0
        result_id = uuid.uuid4().hex
        result_path = OUTPUT_DIR / f"{result_id}.png"
        result_path.write_bytes(result_bytes)

        _log_usage({
            "action": "remove_bg",
            "engine": engine_id,
            "filename": filename,
            "image_count": 1,
            "success": True,
            "elapsed_s": round(elapsed, 2),
            "result_size": len(result_bytes),
        })

        return {
            "success": True,
            "result_id": result_id,
            "size": len(result_bytes),
        }

    except NotImplementedError as e:
        _log_usage({"action": "remove_bg", "engine": engine_id, "filename": filename, "success": False, "error": str(e)[:120], "elapsed_s": round(time.time() - t0, 2)})
        raise HTTPException(400, str(e))
    except ValueError as e:
        _log_usage({"action": "remove_bg", "engine": engine_id, "filename": filename, "success": False, "error": str(e)[:120], "elapsed_s": round(time.time() - t0, 2)})
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        _log_usage({"action": "remove_bg", "engine": engine_id, "filename": filename, "success": False, "error": str(e)[:120], "elapsed_s": round(time.time() - t0, 2)})
        raise HTTPException(400, str(e))
    except Exception as e:
        _log_usage({"action": "remove_bg", "engine": engine_id, "filename": filename, "success": False, "error": str(e)[:120], "elapsed_s": round(time.time() - t0, 2)})
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
    mask_mode: Optional[str] = Form("polygon"),
    num_points: Optional[int] = Form(35),
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
    filename = file_path.name

    image_bytes = file_path.read_bytes()
    t0 = time.time()

    try:
        # 所有引擎统一走线程池，避免阻塞事件循环
        loop = asyncio.get_event_loop()
        if engine_id == "custom":
            future = loop.run_in_executor(
                _executor, _run_sync(engine.remove_bg_with_prompt, image_bytes, prompt, api_key,
                                     base_url=base_url or "", model_name=model_name or "")
            )
        elif engine_id == "gemini_mask":
            mode = mask_mode if mask_mode in ("polygon", "mask") else "mask"
            n_pts = num_points if num_points and 15 <= num_points <= 500 else None
            future = loop.run_in_executor(
                _executor, _run_sync(engine.remove_bg_with_prompt, image_bytes, prompt, api_key,
                                     mask_mode=mode, num_points=n_pts)
            )
        elif engine_id == "kimi":
            n_pts = num_points if num_points and 15 <= num_points <= 500 else 100
            future = loop.run_in_executor(
                _executor, _run_sync(engine.remove_bg_with_prompt, image_bytes, prompt, api_key,
                                     num_points=n_pts)
            )
        else:
            future = loop.run_in_executor(
                _executor, _run_sync(engine.remove_bg_with_prompt, image_bytes, prompt, api_key)
            )
        result_bytes = await asyncio.wait_for(future, timeout=_TASK_TIMEOUT)

        if result_bytes is None:
            raise HTTPException(500, "任务被取消，请重试")

        elapsed = time.time() - t0
        result_id = uuid.uuid4().hex
        result_path = OUTPUT_DIR / f"{result_id}.png"
        result_path.write_bytes(result_bytes)

        _log_usage({
            "action": "remove_bg_prompt",
            "engine": engine_id,
            "filename": filename,
            "prompt": prompt[:80],
            "image_count": 1,
            "success": True,
            "elapsed_s": round(elapsed, 2),
            "result_size": len(result_bytes),
        })

        return {
            "success": True,
            "result_id": result_id,
            "size": len(result_bytes),
        }

    except NotImplementedError as e:
        _log_usage({"action": "remove_bg_prompt", "engine": engine_id, "filename": filename, "prompt": prompt[:80], "success": False, "error": str(e)[:120], "elapsed_s": round(time.time() - t0, 2)})
        raise HTTPException(400, str(e))
    except ValueError as e:
        _log_usage({"action": "remove_bg_prompt", "engine": engine_id, "filename": filename, "prompt": prompt[:80], "success": False, "error": str(e)[:120], "elapsed_s": round(time.time() - t0, 2)})
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        _log_usage({"action": "remove_bg_prompt", "engine": engine_id, "filename": filename, "prompt": prompt[:80], "success": False, "error": str(e)[:120], "elapsed_s": round(time.time() - t0, 2)})
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


@app.get("/api/original/{file_id}")
async def get_original(file_id: str):
    """获取上传的原图预览"""
    files = list(UPLOAD_DIR.glob(f"{file_id}_*"))
    if not files:
        raise HTTPException(404, "原图未找到")
    file_path = files[0]
    # 根据扩展名判断 media_type
    ext = file_path.suffix.lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }.get(ext, "application/octet-stream")
    return FileResponse(file_path, media_type=media_type)


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

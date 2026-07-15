"""
Format Converter — FastAPI 服务端

提供格式转换 REST API，支持:
  - 数据格式 (JSON, YAML, CSV, XML, TOML)
  - 音频格式 (MP3, WAV, FLAC, OGG, AAC 等)
  - 视频格式 (MP4, AVI, MKV, MOV, WEBM 等)
  - 图片格式 (JPG, PNG, WEBP, BMP, GIF 等)
  - 文档格式 (PDF, DOCX, TXT, MD, HTML 等)

启动:  uvicorn format_converter.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .converters import convert_file, get_supported_conversions
from .utils import (
    FORMAT_CATEGORIES, CATEGORY_LABELS, CATEGORY_ICONS,
    INPUT_FORMATS, OUTPUT_FORMATS,
    detect_format, detect_category,
    make_output_path,
)

# ============================================================
#  日志
# ============================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("format_converter")

# ============================================================
#  FastAPI 应用
# ============================================================
app = FastAPI(
    title="Format Converter API",
    description="通用格式转换服务 — 支持数据、图片、音频、视频、文档等多种格式互转",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — 开发时允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
#  任务管理（内存中）
# ============================================================
_tasks: dict[str, dict] = {}
_tasks_lock = threading.Lock()

TASK_STATUS_PENDING = "pending"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_DONE = "done"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_CANCELLED = "cancelled"

# 上传临时目录
UPLOAD_DIR = Path(tempfile.gettempdir()) / "format_converter_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 输出目录
OUTPUT_BASE = Path(tempfile.gettempdir()) / "format_converter_outputs"
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)


# ============================================================
#  数据模型
# ============================================================
class FormatInfo(BaseModel):
    name: str
    extension: str
    category: str
    category_label: str
    category_icon: str


class ConversionRequest(BaseModel):
    files: list[str]  # 已上传文件的临时路径列表
    source_fmt: str
    target_fmt: str
    original_names: list[str] | None = None  # 原始文件名


class TaskStatus(BaseModel):
    task_id: str
    status: str
    total: int
    completed: int
    failed: int
    overall_progress: float
    current_file: str | None
    results: list[dict]
    logs: list[str]
    output_dir: str | None


class TaskListItem(BaseModel):
    task_id: str
    status: str
    total: int
    completed: int
    created_at: float


# ============================================================
#  API 路由
# ============================================================

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/api/formats")
async def list_formats():
    """获取所有可用格式和转换路径。"""
    return {
        "categories": {
            cat: {
                "label": CATEGORY_LABELS.get(cat, cat),
                "icon": CATEGORY_ICONS.get(cat, "file"),
                "input_formats": INPUT_FORMATS.get(cat, []),
                "output_formats": OUTPUT_FORMATS.get(cat, []),
            }
            for cat in FORMAT_CATEGORIES
        },
        "conversions": get_supported_conversions(),
    }


@app.get("/api/formats/{category}")
async def list_category_formats(category: str):
    """获取某个类别下的输入/输出格式。"""
    if category not in FORMAT_CATEGORIES:
        raise HTTPException(status_code=404, detail=f"未知类别: {category}")
    return {
        "category": category,
        "label": CATEGORY_LABELS.get(category, category),
        "icon": CATEGORY_ICONS.get(category, "file"),
        "input_formats": INPUT_FORMATS.get(category, []),
        "output_formats": OUTPUT_FORMATS.get(category, []),
    }


@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """上传文件并返回临时路径列表。"""
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    results: list[dict] = []
    for f in files:
        safe_name = f"{uuid.uuid4().hex}_{f.filename or 'unnamed'}"
        dest = UPLOAD_DIR / safe_name
        total_written = 0
        with open(dest, "wb") as buffer:
            while True:
                chunk = await f.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total_written += len(chunk)
                if total_written > MAX_FILE_SIZE:
                    buffer.close()
                    os.unlink(dest)
                    raise HTTPException(status_code=413, detail=f"文件 {f.filename} 超过 500MB 大小限制")
                buffer.write(chunk)
        fmt = detect_format(str(dest))
        category = detect_category(fmt) if fmt else None
        results.append({
            "temp_path": str(dest),
            "original_name": f.filename,
            "detected_format": fmt,
            "category": category,
            "size": os.path.getsize(dest),
        })
    return {"files": results}


@app.post("/api/convert")
async def start_conversion(req: ConversionRequest):
    """启动批量转换任务。"""
    _cleanup_old_tasks()  # Clean up old tasks before creating new one
    task_id = uuid.uuid4().hex[:12]

    # 验证格式
    category = detect_category(req.source_fmt)
    if not category:
        raise HTTPException(status_code=400, detail=f"不支持的源格式: {req.source_fmt}")
    if req.target_fmt not in OUTPUT_FORMATS.get(category, []):
        raise HTTPException(
            status_code=400,
            detail=f"{CATEGORY_LABELS.get(category, category)}不支持输出为 {req.target_fmt}",
        )

    output_dir = OUTPUT_BASE / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    with _tasks_lock:
        _tasks[task_id] = {
            "task_id": task_id,
            "status": TASK_STATUS_PENDING,
            "total": len(req.files),
            "completed": 0,
            "failed": 0,
            "overall_progress": 0.0,
            "current_file": None,
            "results": [],
            "logs": [],
            "output_dir": str(output_dir),
            "created_at": time.time(),
            "cancel_flag": False,
        }

    # 后台线程执行转换
    thread = threading.Thread(
        target=_run_conversion,
        args=(task_id, req.files, req.original_names or [], req.source_fmt, req.target_fmt, str(output_dir)),
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id, "status": TASK_STATUS_PENDING}


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """轮询任务状态。"""
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskStatus(**{
        k: v for k, v in task.items()
        if k in TaskStatus.model_fields
    })


@app.delete("/api/task/{task_id}")
async def cancel_task(task_id: str):
    """取消任务。"""
    with _tasks_lock:
        task = _tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        if task["status"] in (TASK_STATUS_DONE, TASK_STATUS_FAILED, TASK_STATUS_CANCELLED):
            return {"task_id": task_id, "status": task["status"]}
        task["cancel_flag"] = True
        task["status"] = TASK_STATUS_CANCELLED
    return {"task_id": task_id, "status": TASK_STATUS_CANCELLED}


@app.get("/api/tasks")
async def list_tasks():
    """列出所有任务。"""
    with _tasks_lock:
        tasks = [
            TaskListItem(
                task_id=t["task_id"],
                status=t["status"],
                total=t["total"],
                completed=t["completed"],
                created_at=t["created_at"],
            )
            for t in sorted(_tasks.values(), key=lambda x: x["created_at"], reverse=True)
        ]
    return {"tasks": tasks}


@app.get("/api/download/{task_id}/{filename:path}")
async def download_file(task_id: str, filename: str):
    """下载转换完成的文件。"""
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    # Prevent path traversal — resolve and verify path stays within output_dir
    out_dir = Path(task["output_dir"]).resolve()
    filepath = (out_dir / filename).resolve()
    if not str(filepath).startswith(str(out_dir)):
        raise HTTPException(status_code=403, detail="非法路径")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        path=str(filepath),
        filename=filepath.name,
        media_type="application/octet-stream",
    )


@app.get("/api/download-zip/{task_id}")
async def download_zip(task_id: str):
    """打包下载所有转换结果。"""
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["status"] not in (TASK_STATUS_DONE, TASK_STATUS_FAILED):
        raise HTTPException(status_code=400, detail="任务尚未完成")

    out_dir = Path(task["output_dir"])
    zip_path = out_dir.parent / f"{task_id}_results.zip"

    if not zip_path.exists():
        import zipfile
        # Write to temp file first, then rename for atomicity
        tmp_zip = zip_path.with_suffix(".tmp")
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in out_dir.iterdir():
                if f.is_file():
                    zf.write(f, f.name)
        tmp_zip.rename(zip_path)

    return FileResponse(
        path=str(zip_path),
        filename=f"converted_{task_id}.zip",
        media_type="application/zip",
    )


# ============================================================
#  后台转换执行器
# ============================================================

def _run_conversion(
    task_id: str,
    file_paths: list[str],
    original_names: list[str],
    source_fmt: str,
    target_fmt: str,
    output_dir: str,
) -> None:
    """在后台线程中顺序执行批量转换。"""
    with _tasks_lock:
        task = _tasks.get(task_id)
        if not task:
            return
        task["status"] = TASK_STATUS_RUNNING

    total = len(file_paths)

    for idx, file_path in enumerate(file_paths):
        # 检查取消
        with _tasks_lock:
            if task["cancel_flag"]:
                break

        original = original_names[idx] if idx < len(original_names) else os.path.basename(file_path)

        # 验证文件格式
        detected = detect_format(file_path)
        if detected != source_fmt:
            # 宽松匹配：同类别即可
            cat_detected = detect_category(detected) if detected else None
            cat_expected = detect_category(source_fmt)
            if cat_detected != cat_expected:
                with _tasks_lock:
                    _add_result(task, original, None, False, f"文件格式不匹配: 期望 {source_fmt}, 检测到 {detected}")
                    _add_log(task, f"  ✗ 跳过: {original} (格式不匹配)")
                continue

        # 生成输出路径
        output_path = make_output_path(original, target_fmt, output_dir)

        # 更新当前文件
        with _tasks_lock:
            task["current_file"] = original
            _add_log(task, f"[{idx + 1}/{total}] 转换中: {original} ({source_fmt} → {target_fmt})")

        # Progress callback — updates overall_progress in real-time
        def _progress_cb(file_progress, _idx=idx, _total=total):
            with _tasks_lock:
                task["overall_progress"] = (_idx + min(file_progress, 0.99)) / _total

        # 执行转换（传入 progress_callback 实现实时进度更新）
        result = convert_file(file_path, source_fmt, target_fmt, output_path, _progress_cb)

        with _tasks_lock:
            task["completed"] += 1
            if result["success"]:
                _add_result(task, original, os.path.basename(output_path), True, None)
                _add_log(task, f"  ✓ 完成: {os.path.basename(output_path)}")
            else:
                task["failed"] += 1
                _add_result(task, original, None, False, result.get("error"))
                _add_log(task, f"  ✗ 失败: {result.get('error')}")
            task["overall_progress"] = task["completed"] / total

    # 标记完成
    with _tasks_lock:
        if not task["cancel_flag"]:
            task["status"] = TASK_STATUS_DONE
            task["overall_progress"] = 1.0
            _add_log(task, f"转换完成！成功 {total - task['failed']}/{total} 个文件")

    # 清理上传的临时文件
    for fp in file_paths:
        try:
            os.unlink(fp)
        except Exception:
            pass


def _add_result(task: dict, original: str, output: str | None, success: bool, error: str | None) -> None:
    task["results"].append({
        "original": original,
        "output": output,
        "success": success,
        "error": error,
    })


def _add_log(task: dict, message: str) -> None:
    task["logs"].append(message)
    # 限制日志条数
    if len(task["logs"]) > 500:
        task["logs"] = task["logs"][-500:]


def _cleanup_old_tasks(max_age_seconds: int = 3600) -> None:
    """Remove completed/failed/cancelled tasks older than max_age_seconds.
    Also deletes their output directories and zip files."""
    now = time.time()
    with _tasks_lock:
        to_remove = [
            tid for tid, t in _tasks.items()
            if t["status"] in (TASK_STATUS_DONE, TASK_STATUS_FAILED, TASK_STATUS_CANCELLED)
            and now - t.get("created_at", 0) > max_age_seconds
        ]
        for tid in to_remove:
            task = _tasks.pop(tid, None)
            if task:
                out_dir = Path(task.get("output_dir", ""))
                if out_dir.exists():
                    shutil.rmtree(out_dir, ignore_errors=True)
                zip_path = out_dir.parent / f"{tid}_results.zip"
                if zip_path.exists():
                    try:
                        zip_path.unlink()
                    except Exception:
                        pass


@app.on_event("startup")
async def _startup_cleanup():
    """Clean up stale temp files and old tasks on startup."""
    # Remove old upload files (older than 1 hour)
    now = time.time()
    for f in UPLOAD_DIR.iterdir():
        try:
            if f.is_file() and now - f.stat().st_mtime > 3600:
                f.unlink()
        except Exception:
            pass
    # Remove old output directories
    for d in OUTPUT_BASE.iterdir():
        try:
            if d.is_dir() and now - d.stat().st_mtime > 3600:
                shutil.rmtree(d, ignore_errors=True)
            elif d.is_file() and now - d.stat().st_mtime > 3600:
                d.unlink()
        except Exception:
            pass
    _cleanup_old_tasks(0)  # Clean all old tasks on startup


# ============================================================
#  生产模式：挂载前端静态文件
# ============================================================
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ============================================================
#  启动入口
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "format_converter.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )

"""Flask REST API 后端。

提供格式信息查询、文件转换任务管理、进度追踪。
作为本地服务运行在 QWebEngineView 加载的页面背后。
"""

import os
import sys
import threading
import uuid
import json
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from format_converter.utils.file_utils import (
    INPUT_FORMATS, OUTPUT_FORMATS, FORMAT_CATEGORIES,
    detect_format, detect_category, make_output_path,
    CATEGORY_FILTERS,
)
from format_converter.utils.worker import ConvertWorker

# ── 静态文件目录 ───────────────────────────────────────────
# 从 server.py 位置推算 web/ 目录
_SRC_DIR = Path(__file__).resolve().parent
_WEB_DIR = _SRC_DIR / "web"

app = Flask(__name__, static_folder=str(_WEB_DIR), static_url_path="")

# ── 任务状态管理 ───────────────────────────────────────────

_tasks: dict[str, dict] = {}          # task_id → task_info
_task_lock = threading.Lock()


def _create_task(files: list[str], source_fmt: str | None,
                 target_fmt: str, output_dir: str | None) -> str:
    """创建转换任务，返回 task_id。"""
    task_id = str(uuid.uuid4())[:8]

    task = {
        "id": task_id,
        "files": files,
        "source_fmt": source_fmt,
        "target_fmt": target_fmt,
        "output_dir": output_dir,
        "status": "pending",          # pending | running | completed | cancelled | error
        "total": len(files),
        "completed": 0,
        "overall_progress": 0,
        "file_progress": 0,
        "current_file": "",
        "results": [],                # (ok, path-or-error)
        "logs": [],
        "cancelled": False,
        "workers": [],
    }
    with _task_lock:
        _tasks[task_id] = task
    return task_id


def _run_conversion(task_id: str):
    """在后台线程中执行转换。"""
    with _task_lock:
        task = _tasks.get(task_id)
        if not task:
            return

    # 预处理：过滤有效文件
    valid_files = []
    skipped = []
    for fp in task["files"]:
        fmt = detect_format(fp)
        if not fmt:
            skipped.append((fp, "无法识别格式"))
            continue
        cat = detect_category(fmt)
        dst_cat = detect_category(task["target_fmt"])
        if cat != dst_cat:
            skipped.append((fp, f"跨类别转换不支持 ({fmt} → {task['target_fmt']})"))
            continue
        valid_files.append((fp, fmt))

    for fp, reason in skipped:
        with _task_lock:
            task["logs"].append(f"跳过: {reason} — {fp}")
            task["results"].append((False, reason))

    if not valid_files:
        with _task_lock:
            task["status"] = "completed"
            task["overall_progress"] = 100
        return

    # 更新任务
    with _task_lock:
        task["total"] = len(valid_files)
        task["files"] = [fp for fp, _ in valid_files]
        task["status"] = "running"

    # 逐个文件转换（顺序执行，避免资源竞争）
    for idx, (fp, src_fmt) in enumerate(valid_files):
        with _task_lock:
            if task["cancelled"]:
                task["status"] = "cancelled"
                return
            task["current_file"] = os.path.basename(fp)

        output_path = str(make_output_path(fp, task["target_fmt"], task["output_dir"]))
        task["logs"].append(f"[{idx + 1}/{len(valid_files)}] 开始: {os.path.basename(fp)}")

        worker = ConvertWorker(idx, fp, src_fmt or task["source_fmt"], task["target_fmt"], output_path)

        # 连接信号
        def make_on_progress(tid, file_idx):
            def on_progress(fi, pct):
                with _task_lock:
                    t = _tasks.get(tid)
                    if t:
                        t["file_progress"] = pct
                        per_file = 100.0 / max(t["total"], 1)
                        t["overall_progress"] = int(t["completed"] * per_file + pct * per_file / 100.0)
            return on_progress

        def make_on_finished(tid):
            def on_finished(fi, out):
                with _task_lock:
                    t = _tasks.get(tid)
                    if t:
                        t["completed"] += 1
                        t["results"].append((True, out))
                        t["overall_progress"] = int(t["completed"] / max(t["total"], 1) * 100)
                        t["logs"].append(f"[{t['completed']}/{t['total']}] 完成: {os.path.basename(out)}")
                        if t["completed"] >= t["total"]:
                            t["status"] = "completed"
                            t["file_progress"] = 100
                            t["overall_progress"] = 100
            return on_finished

        def make_on_error(tid):
            def on_error(fi, msg):
                with _task_lock:
                    t = _tasks.get(tid)
                    if t:
                        t["completed"] += 1
                        t["results"].append((False, msg))
                        t["logs"].append(f"错误: {msg}")
                        if t["completed"] >= t["total"]:
                            t["status"] = "completed"
                            t["overall_progress"] = 100
            return on_error

        worker.progress.connect(make_on_progress(task_id, idx))
        worker.finished.connect(make_on_finished(task_id))
        worker.error.connect(make_on_error(task_id))

        with _task_lock:
            task["workers"].append(worker)

        worker.start()
        worker.wait()  # 同步等待，简化并发控制

        with _task_lock:
            if task["cancelled"]:
                task["status"] = "cancelled"
                return


# ═══════════════════════════════════════════════════════════
# API 路由
# ═══════════════════════════════════════════════════════════

@app.route("/")
def index():
    """返回主页面。"""
    return send_from_directory(str(_WEB_DIR), "index.html")


@app.route("/api/formats")
def get_formats():
    """获取所有受支持格式信息。"""
    categories = {}
    for cat, input_fmts in INPUT_FORMATS.items():
        output_fmts = OUTPUT_FORMATS.get(cat, [])
        categories[cat] = {
            "label": {"data": "数据格式", "audio": "音频格式",
                      "video": "视频格式", "image": "图片格式"}.get(cat, cat),
            "inputs": input_fmts,
            "outputs": output_fmts,
            "filter": CATEGORY_FILTERS.get(cat, "所有文件 (*.*)"),
        }
    return jsonify({
        "categories": categories,
        "all_inputs": {k: v for k, v in INPUT_FORMATS.items()},
        "all_outputs": {k: v for k, v in OUTPUT_FORMATS.items()},
    })


@app.route("/api/convert", methods=["POST"])
def start_convert():
    """创建转换任务。"""
    data = request.get_json(force=True)
    files = data.get("files", [])
    source_fmt = data.get("source_fmt") or None
    target_fmt = data.get("target_fmt", "")
    output_dir = data.get("output_dir") or None

    if not files or not target_fmt:
        return jsonify({"error": "缺少必要参数"}), 400

    task_id = _create_task(files, source_fmt, target_fmt, output_dir)

    # 后台启动转换线程
    t = threading.Thread(target=_run_conversion, args=(task_id,), daemon=True)
    t.start()
    # 记录线程引用
    with _task_lock:
        _tasks[task_id]["_thread"] = t

    return jsonify({"task_id": task_id})


@app.route("/api/task/<task_id>")
def get_task_status(task_id):
    """获取任务状态。"""
    with _task_lock:
        task = _tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404

    # 返回副本，避免暴露内部对象
    return jsonify({
        "id": task["id"],
        "status": task["status"],
        "total": task["total"],
        "completed": task["completed"],
        "overall_progress": task["overall_progress"],
        "file_progress": task["file_progress"],
        "current_file": task["current_file"],
        "results": task["results"][-20:],   # 最新 20 条
        "logs": task["logs"][-50:],         # 最新 50 条
    })


@app.route("/api/task/<task_id>/cancel", methods=["POST"])
def cancel_task(task_id):
    """取消任务。"""
    with _task_lock:
        task = _tasks.get(task_id)
        if task:
            task["cancelled"] = True
            for w in task.get("workers", []):
                if w.isRunning():
                    w.cancel()
    return jsonify({"ok": True})


@app.route("/api/browse-files", methods=["POST"])
def browse_files_dialog():
    """触发文件选择对话框。"""
    from PySide6.QtWidgets import QApplication, QFileDialog
    data = request.get_json(force=True)
    category = data.get("category", "data")
    file_filter = CATEGORY_FILTERS.get(category, "所有文件 (*.*)")
    file_filter += ";;所有文件 (*.*)"

    app = QApplication.instance()
    if not app:
        return jsonify({"files": []})

    paths, _ = QFileDialog.getOpenFileNames(None, "选择文件", "", file_filter)
    return jsonify({"files": list(paths)})


@app.route("/api/browse-dir", methods=["POST"])
def browse_dir_dialog():
    """触发目录选择对话框。"""
    from PySide6.QtWidgets import QApplication, QFileDialog

    app = QApplication.instance()
    if not app:
        return jsonify({"dir": ""})

    directory = QFileDialog.getExistingDirectory(None, "选择输出目录")
    return jsonify({"dir": directory})

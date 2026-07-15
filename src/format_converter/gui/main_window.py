"""主窗口 — 全功能桌面格式转换程序。

使用 PySide6 构建，包含四个标签页（数据/音频/视频/图片），
支持批量文件转换、拖放、进度反馈和错误处理。

依赖：
  - PySide6 — LGPL License
    https://wiki.qt.io/Qt_for_Python
"""

import os
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QGroupBox, QPushButton, QFileDialog,
    QLabel, QLineEdit,
)
from PySide6.QtCore import Qt

from format_converter.gui.widgets.drop_zone import DropZone
from format_converter.gui.widgets.format_selector import FormatSelector
from format_converter.gui.widgets.progress_panel import ProgressPanel
from format_converter.gui.widgets.task_list import TaskList
from format_converter.gui.styles.theme import apply_theme, Theme
from format_converter.utils.file_utils import (
    detect_format, detect_category, make_output_path,
    CATEGORY_FILTERS, OUTPUT_FORMATS, INPUT_FORMATS,
)
from format_converter.utils.worker import ConvertWorker


# ── 每个标签页的独立组件数据 ──────────────────────────────

class _TabData:
    """存储单个分类标签页的组件引用。"""
    __slots__ = ("format_selector", "drop_zone", "task_list",
                 "output_dir_edit", "btn_convert")

    def __init__(self, format_selector, drop_zone, task_list,
                 output_dir_edit, btn_convert):
        self.format_selector = format_selector
        self.drop_zone = drop_zone
        self.task_list = task_list
        self.output_dir_edit = output_dir_edit
        self.btn_convert = btn_convert


# ═══════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    """Format Converter 主窗口。"""

    CATEGORIES = ["data", "audio", "video", "image"]
    TAB_LABELS = ["📊 数据格式", "🎵 音频格式", "🎬 视频格式", "🖼️ 图片格式"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Format Converter — 全功能格式转换工具")
        self.resize(900, 700)
        self.setMinimumSize(700, 550)

        # 内部状态
        self._workers: list[ConvertWorker] = []
        self._completed_count = 0
        self._total_count = 0
        self._tabs: dict[str, _TabData] = {}

        # 构建 UI
        self._build_ui()

    # ═══════════════════════════════════════════════════════
    # UI 构建
    # ═══════════════════════════════════════════════════════

    def _build_ui(self):
        """构建主窗口界面。"""
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(12)

        # 标题
        title = QLabel("Format Converter")
        title.setObjectName("titleLabel")
        root_layout.addWidget(title)

        subtitle = QLabel("数据 · 音频 · 视频 · 图片 — 一站式格式转换")
        subtitle.setStyleSheet("color: #6c7086; font-size: 12px; margin-bottom: 4px;")
        root_layout.addWidget(subtitle)

        # 标签页
        self.tab_widget = QTabWidget()
        for category, label in zip(self.CATEGORIES, self.TAB_LABELS):
            tab, tab_data = self._build_category_tab(category)
            self.tab_widget.addTab(tab, label)
            self._tabs[category] = tab_data
        root_layout.addWidget(self.tab_widget, stretch=1)

        # 进度面板
        self.progress_panel = ProgressPanel()
        self.progress_panel.cancel_requested.connect(self._on_cancel)
        root_layout.addWidget(self.progress_panel)

    def _build_category_tab(self, category: str) -> tuple[QWidget, _TabData]:
        """构建单个分类标签页，返回 (tab_widget, TabData)。"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(10)

        # 格式选择器
        format_selector = FormatSelector(category)
        layout.addWidget(format_selector)

        # 文件操作区
        file_group = QGroupBox("文件列表")
        file_layout = QVBoxLayout(file_group)
        file_layout.setSpacing(8)

        drop_zone = DropZone()
        drop_zone.files_dropped.connect(
            lambda paths: self._on_files_dropped(category, paths))
        file_layout.addWidget(drop_zone)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ 添加文件")
        btn_add.clicked.connect(lambda: self._on_add_files(category))
        btn_row.addWidget(btn_add)
        btn_row.addStretch()

        btn_row.addWidget(QLabel("输出目录:"))
        output_dir_edit = QLineEdit()
        output_dir_edit.setPlaceholderText("留空则与源文件同目录")
        output_dir_edit.setFixedWidth(200)
        btn_row.addWidget(output_dir_edit)

        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(lambda: self._on_browse_output(category))
        btn_row.addWidget(btn_browse)

        file_layout.addLayout(btn_row)
        layout.addWidget(file_group)

        # 任务列表
        task_list = TaskList()
        task_list.files_changed.connect(
            lambda: self._on_files_changed(category))
        layout.addWidget(task_list, stretch=1)

        # 转换按钮
        convert_row = QHBoxLayout()
        convert_row.addStretch()
        btn_convert = QPushButton("▶ 开始转换")
        btn_convert.setObjectName("btnConvert")
        btn_convert.setEnabled(False)
        btn_convert.clicked.connect(lambda: self._on_convert(category))
        convert_row.addWidget(btn_convert)
        convert_row.addStretch()
        layout.addLayout(convert_row)

        # 格式支持说明
        info_label = QLabel(self._build_format_info(category))
        info_label.setStyleSheet("color: #585b70; font-size: 11px; padding-top: 4px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        tab_data = _TabData(format_selector, drop_zone, task_list,
                           output_dir_edit, btn_convert)
        return tab, tab_data

    def _build_format_info(self, category: str) -> str:
        """生成格式支持说明文本。"""
        input_fmts = INPUT_FORMATS.get(category, [])
        output_fmts = OUTPUT_FORMATS.get(category, [])
        cat_names = {
            "data": "数据格式", "audio": "音频格式",
            "video": "视频格式", "image": "图片格式",
        }
        name = cat_names.get(category, category)
        input_str = "、".join(f.upper() for f in input_fmts)
        output_str = "、".join(f.upper() for f in output_fmts)
        deps = {
            "data":  "依赖: PyYAML, xmltodict, tomli/tomli-w（均为 MIT 许可）",
            "audio": "依赖: pydub (MIT) + ffmpeg (LGPL/GPL)",
            "video": "依赖: ffmpeg-python (Apache-2.0) + ffmpeg (LGPL/GPL)",
            "image": "依赖: Pillow (HPND)",
        }
        return (
            f"支持的{name}输入: {input_str}\n"
            f"支持的{name}输出: {output_str}\n"
            f"{deps.get(category, '')}"
        )

    # ═══════════════════════════════════════════════════════
    # 属性访问辅助 — 获取当前或指定分类的组件
    # ═══════════════════════════════════════════════════════

    def _get_current_category(self) -> str:
        """获取当前活动标签页的分类。"""
        return self.CATEGORIES[self.tab_widget.currentIndex()]

    def _tab(self, category: str) -> _TabData:
        """获取指定分类的标签页数据。"""
        return self._tabs[category]

    # ═══════════════════════════════════════════════════════
    # 事件处理
    # ═══════════════════════════════════════════════════════

    def _on_files_dropped(self, category: str, paths: list[str]):
        """处理拖放文件。"""
        filtered = self._filter_files(paths, category)
        if filtered:
            self._tab(category).task_list.add_files(filtered)

    def _on_add_files(self, category: str):
        """添加文件按钮点击。"""
        file_filter = CATEGORY_FILTERS.get(category, "所有文件 (*.*)")
        file_filter += ";;所有文件 (*.*)"
        paths, _ = QFileDialog.getOpenFileNames(
            self, f"选择文件", "", file_filter
        )
        if paths:
            filtered = self._filter_files(paths, category)
            if filtered:
                self._tab(category).task_list.add_files(filtered)

    def _filter_files(self, paths: list[str], category: str) -> list[str]:
        """过滤出属于当前分类的文件。"""
        valid_formats = INPUT_FORMATS.get(category, [])
        result = []
        for p in paths:
            fmt = detect_format(p)
            if fmt and fmt in valid_formats:
                result.append(p)
        return result

    def _on_browse_output(self, category: str):
        """选择输出目录。"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self._tab(category).output_dir_edit.setText(directory)

    def _on_files_changed(self, category: str):
        """文件列表变化时更新按钮状态。"""
        td = self._tab(category)
        td.btn_convert.setEnabled(td.task_list.count() > 0)

    def _on_convert(self, category: str):
        """开始转换。"""
        td = self._tab(category)
        files = td.task_list.get_files()
        if not files:
            return

        target_fmt = td.format_selector.get_target_format()
        source_fmt = td.format_selector.get_source_format()
        output_dir = td.output_dir_edit.text().strip() or None

        # 禁用所有 tab 的控件
        for t in self._tabs.values():
            t.btn_convert.setEnabled(False)
        self.tab_widget.setEnabled(False)
        self.progress_panel.reset()
        self.progress_panel.show_cancel_button(True)
        self.progress_panel.set_status("正在转换...", "#f9e2af")

        # 创建 workers
        self._workers.clear()
        self._completed_count = 0
        self._total_count = len(files)

        for i, filepath in enumerate(files):
            src_fmt = source_fmt or detect_format(filepath)
            if not src_fmt:
                self.progress_panel.append_log(f"跳过: 无法识别格式 — {filepath}")
                self._completed_count += 1
                continue

            src_cat = detect_category(src_fmt)
            dst_cat = detect_category(target_fmt)
            if src_cat != dst_cat:
                self.progress_panel.append_log(
                    f"跳过: 跨类别转换不支持 ({src_fmt} → {target_fmt}) — {filepath}"
                )
                self._completed_count += 1
                continue

            output_path = str(make_output_path(filepath, target_fmt, output_dir))

            worker = ConvertWorker(i, filepath, src_fmt, target_fmt, output_path)
            worker.progress.connect(self._on_file_progress)
            worker.finished.connect(self._on_file_finished)
            worker.error.connect(self._on_file_error)
            worker.log.connect(self.progress_panel.append_log)
            worker._category = category  # 记录所属分类用于恢复
            self._workers.append(worker)

        if not self._workers:
            self._on_all_complete(category)
            return

        self._total_count = len(self._workers)
        self._completed_count = 0
        for w in self._workers:
            w.start()

    def _on_file_progress(self, file_index: int, percent: int):
        """单文件进度更新。"""
        self.progress_panel.set_file_progress(percent)
        per_file = 100.0 / max(self._total_count, 1)
        overall = int((self._completed_count * per_file) + (percent * per_file / 100.0))
        self.progress_panel.set_overall_progress(overall)

    def _on_file_finished(self, file_index: int, output_path: str):
        """单文件转换完成。"""
        self._completed_count += 1
        self.progress_panel.set_overall_progress(
            int(self._completed_count / max(self._total_count, 1) * 100)
        )
        if self._completed_count >= self._total_count:
            category = getattr(self._workers[0], '_category', 'data') if self._workers else 'data'
            self._on_all_complete(category)

    def _on_file_error(self, file_index: int, error_msg: str):
        """单文件转换错误。"""
        self._completed_count += 1
        self.progress_panel.append_log(f"错误: {error_msg}")
        if self._completed_count >= self._total_count:
            category = getattr(self._workers[0], '_category', 'data') if self._workers else 'data'
            self._on_all_complete(category)

    def _on_all_complete(self, category: str):
        """全部转换完成。"""
        total = self._total_count
        # 成功数 = 总数 - 错误数（通过日志消息推算，这里简化处理）
        success = self._completed_count

        if total > 0:
            self.progress_panel.set_status(
                f"完成: {self._completed_count}/{total} 个文件已处理",
                "#a6e3a1"
            )
        else:
            self.progress_panel.set_status("没有可转换的文件", "#f38ba8")

        # 恢复控件
        for t in self._tabs.values():
            t.btn_convert.setEnabled(t.task_list.count() > 0)
        self.tab_widget.setEnabled(True)
        self.progress_panel.show_cancel_button(False)
        self.progress_panel.set_overall_progress(100 if total > 0 else 0)

    def _on_cancel(self):
        """取消所有正在进行的转换。"""
        for w in self._workers:
            if w.isRunning():
                w.cancel()
        self.progress_panel.set_status("已取消", "#f38ba8")
        self.progress_panel.append_log("转换已取消。")
        category = getattr(self._workers[0], '_category', 'data') if self._workers else 'data'
        self._on_all_complete(category)

    # ═══════════════════════════════════════════════════════
    # 窗口事件
    # ═══════════════════════════════════════════════════════

    def closeEvent(self, event):
        """关闭窗口时等待 worker 线程结束。"""
        for w in self._workers:
            if w.isRunning():
                w.cancel()
                w.wait(2000)
        event.accept()

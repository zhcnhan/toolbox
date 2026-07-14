"""应用程序主题/样式表。

提供深色主题的 QSS 样式表，使应用美观现代。
"""

from enum import Enum


class Theme(Enum):
    DARK = "dark"
    LIGHT = "light"


# ── 深色主题 QSS ──────────────────────────────────────────

_DARK_QSS = """
/* ── 全局 ─────────────────────────────── */
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}

/* ── 主窗口 ───────────────────────────── */
QMainWindow {
    background-color: #1e1e2e;
}

/* ── 标签页 ───────────────────────────── */
QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #1e1e2e;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #181825;
    color: #6c7086;
    padding: 10px 24px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 14px;
    font-weight: 500;
}

QTabBar::tab:selected {
    color: #cdd6f4;
    border-bottom: 2px solid #89b4fa;
    background-color: #1e1e2e;
}

QTabBar::tab:hover:!selected {
    color: #a6adc8;
    background-color: #252536;
}

/* ── 分组框 ───────────────────────────── */
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
    font-size: 13px;
    color: #a6adc8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}

/* ── 按钮 ─────────────────────────────── */
QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #585b70;
}

QPushButton:pressed {
    background-color: #313244;
}

QPushButton:disabled {
    background-color: #313244;
    color: #585b70;
}

QPushButton#btnConvert {
    background-color: #89b4fa;
    color: #1e1e2e;
    font-size: 15px;
    font-weight: bold;
    padding: 10px 32px;
}

QPushButton#btnConvert:hover {
    background-color: #b4d0fb;
}

QPushButton#btnConvert:pressed {
    background-color: #74a0e8;
}

QPushButton#btnConvert:disabled {
    background-color: #45475a;
    color: #6c7086;
}

/* ── 下拉框 ───────────────────────────── */
QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-width: 120px;
}

QComboBox:hover {
    border-color: #585b70;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #313244;
    border: 1px solid #45475a;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
}

/* ── 列表 ─────────────────────────────── */
QListWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    padding: 8px 10px;
    border-radius: 4px;
    margin: 2px 0;
}

QListWidget::item:selected {
    background-color: #45475a;
}

QListWidget::item:hover {
    background-color: #313244;
}

/* ── 进度条 ───────────────────────────── */
QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    font-size: 11px;
    color: #cdd6f4;
}

QProgressBar::chunk {
    background-color: #a6e3a1;
    border-radius: 6px;
}

/* ── 文本编辑 ─────────────────────────── */
QPlainTextEdit {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 8px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
    color: #a6adc8;
}

/* ── 标签 ─────────────────────────────── */
QLabel {
    color: #cdd6f4;
}

QLabel#titleLabel {
    font-size: 16px;
    font-weight: bold;
    color: #cdd6f4;
}

/* ── 文件路径输入 ─────────────────────── */
QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}

QLineEdit:focus {
    border-color: #89b4fa;
}

/* ── 滚动条 ───────────────────────────── */
QScrollBar:vertical {
    background-color: #181825;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #181825;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ── 工具提示 ─────────────────────────── */
QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px 8px;
    border-radius: 4px;
}
"""


def apply_theme(app, theme: Theme = Theme.DARK):
    """应用主题样式表到 QApplication。"""
    if theme == Theme.DARK:
        app.setStyleSheet(_DARK_QSS)
    # LIGHT 暂用系统默认

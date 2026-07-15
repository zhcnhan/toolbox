"""进度面板组件。

显示转换进度条、日志输出区域，以及取消按钮。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QProgressBar, QPlainTextEdit,
    QPushButton, QHBoxLayout, QLabel,
)
from PySide6.QtCore import Signal


class ProgressPanel(QWidget):
    """进度面板。

    Signals:
        cancel_requested: 用户点击取消时发送
    """

    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 顶部：状态标签 + 取消按钮
        top_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #a6adc8; font-weight: bold;")
        top_layout.addWidget(self.status_label)
        top_layout.addStretch()
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        top_layout.addWidget(self.btn_cancel)
        layout.addLayout(top_layout)

        # 整体进度条
        self.overall_bar = QProgressBar()
        self.overall_bar.setMinimum(0)
        self.overall_bar.setMaximum(100)
        self.overall_bar.setValue(0)
        layout.addWidget(self.overall_bar)

        # 单文件进度条
        self.file_bar = QProgressBar()
        self.file_bar.setMinimum(0)
        self.file_bar.setMaximum(100)
        self.file_bar.setValue(0)
        layout.addWidget(self.file_bar)

        # 日志输出
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(500)
        self.log_output.setMinimumHeight(100)
        layout.addWidget(self.log_output)

    def set_status(self, text: str, color: str = "#a6adc8"):
        """设置状态文本。"""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def set_overall_progress(self, value: int):
        """设置整体进度 (0-100)。"""
        self.overall_bar.setValue(value)

    def set_file_progress(self, value: int):
        """设置单文件进度 (0-100)。"""
        self.file_bar.setValue(value)

    def append_log(self, message: str):
        """追加日志。"""
        self.log_output.appendPlainText(message)
        # 自动滚动到底部
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def show_cancel_button(self, visible: bool):
        """显示/隐藏取消按钮。"""
        self.btn_cancel.setVisible(visible)

    def reset(self):
        """重置进度面板。"""
        self.overall_bar.setValue(0)
        self.file_bar.setValue(0)
        self.set_status("就绪", "#a6adc8")
        self.btn_cancel.setVisible(False)

"""文件拖放区域。

支持拖拽文件进入，显示提示信息。
"""

from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent


class DropZone(QLabel):
    """可拖放文件的区域。

    Signals:
        files_dropped: (file_paths: list[str]) 文件拖入时发送
    """

    files_dropped = Signal(list)

    def __init__(self, text: str = "拖放文件到此处\n或点击下方「添加文件」按钮", parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #45475a;
                border-radius: 12px;
                background-color: #181825;
                color: #6c7086;
                font-size: 14px;
                padding: 20px;
            }
            QLabel:hover {
                border-color: #89b4fa;
                color: #a6adc8;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #89b4fa;
                    border-radius: 12px;
                    background-color: #1e2a3a;
                    color: #89b4fa;
                    font-size: 14px;
                    padding: 20px;
                }
            """)

    def dragLeaveEvent(self, event):
        self._reset_style()

    def dropEvent(self, event: QDropEvent):
        self._reset_style()
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        if paths:
            self.files_dropped.emit(paths)

    def _reset_style(self):
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #45475a;
                border-radius: 12px;
                background-color: #181825;
                color: #6c7086;
                font-size: 14px;
                padding: 20px;
            }
            QLabel:hover {
                border-color: #89b4fa;
                color: #a6adc8;
            }
        """)

"""任务列表组件。

展示待转换文件列表，支持选中、移除操作。
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QAbstractItemView, QLabel,
)
from PySide6.QtCore import Signal, Qt


class TaskList(QWidget):
    """文件任务列表。

    Signals:
        files_changed: 文件列表发生变化时发送
    """

    files_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setAlternatingRowColors(False)
        layout.addWidget(self.list_widget)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_remove = QPushButton("移除选中")
        self.btn_remove.setFixedWidth(80)
        self.btn_remove.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.btn_remove)

        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.setFixedWidth(80)
        self.btn_clear.clicked.connect(self._clear_all)
        btn_layout.addWidget(self.btn_clear)

        btn_layout.addStretch()

        count_label = QLabel(f"共 {self.list_widget.count()} 个文件")
        count_label.setStyleSheet("color: #6c7086;")
        btn_layout.addWidget(count_label)

        layout.addLayout(btn_layout)

    def add_files(self, paths: list[str]):
        """添加文件到列表（自动去重）。"""
        existing = {self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(self.list_widget.count())}
        added = False
        for path in paths:
            abs_path = os.path.abspath(path)
            if abs_path not in existing:
                item = QListWidgetItem(os.path.basename(path))
                item.setToolTip(abs_path)
                item.setData(Qt.ItemDataRole.UserRole, abs_path)
                self.list_widget.addItem(item)
                existing.add(abs_path)
                added = True
        if added:
            self.files_changed.emit()

    def get_files(self) -> list[str]:
        """获取所有文件路径列表。"""
        return [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.list_widget.count())]

    def count(self) -> int:
        """文件数量。"""
        return self.list_widget.count()

    def _remove_selected(self):
        for item in self.list_widget.selectedItems():
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)
        self.files_changed.emit()

    def _clear_all(self):
        self.list_widget.clear()
        self.files_changed.emit()

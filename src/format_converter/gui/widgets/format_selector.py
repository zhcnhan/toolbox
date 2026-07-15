"""格式选择器组件。

提供源格式和目标格式的下拉选择框。
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLabel, QSizePolicy
from PySide6.QtCore import Qt

from format_converter.utils.file_utils import INPUT_FORMATS, OUTPUT_FORMATS


class FormatSelector(QWidget):
    """格式选择器 — 源格式 → 目标格式。

    Args:
        category: 格式分类 ('data', 'audio', 'video', 'image')
    """

    def __init__(self, category: str, parent=None):
        super().__init__(parent)
        self.category = category

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 源格式
        src_label = QLabel("源格式:")
        src_label.setStyleSheet("font-weight: bold; color: #a6adc8;")
        layout.addWidget(src_label)

        self.src_combo = QComboBox()
        self.src_combo.addItem("自动检测")
        src_formats = INPUT_FORMATS.get(category, [])
        for fmt in src_formats:
            self.src_combo.addItem(fmt.upper(), fmt)
        layout.addWidget(self.src_combo)

        # 箭头
        arrow = QLabel("→")
        arrow.setStyleSheet("font-size: 18px; color: #89b4fa; font-weight: bold;")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(arrow)

        # 目标格式
        dst_label = QLabel("目标格式:")
        dst_label.setStyleSheet("font-weight: bold; color: #a6adc8;")
        layout.addWidget(dst_label)

        self.dst_combo = QComboBox()
        dst_formats = OUTPUT_FORMATS.get(category, [])
        for fmt in dst_formats:
            self.dst_combo.addItem(fmt.upper(), fmt)
        self.dst_combo.setCurrentIndex(0)
        layout.addWidget(self.dst_combo)

        layout.addStretch()

    def get_source_format(self) -> str | None:
        """获取选中的源格式，None 表示自动检测。"""
        idx = self.src_combo.currentIndex()
        if idx == 0:
            return None
        return self.src_combo.currentData()

    def get_target_format(self) -> str:
        """获取选中的目标格式。"""
        return self.dst_combo.currentData()

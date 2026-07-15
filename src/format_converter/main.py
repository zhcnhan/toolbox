"""应用程序入口。

启动方式：
    format-converter          (pip install 后)
    python -m format_converter
    python src/format_converter/main.py
"""

import sys
import os

# 确保项目根目录在 sys.path 中
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def main():
    """启动 Format Converter GUI 应用程序。"""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from format_converter.gui.main_window import MainWindow

    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Format Converter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Toolbox")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

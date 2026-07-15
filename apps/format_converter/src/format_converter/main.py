"""应用程序入口 — 混合架构。

启动方式：
    format-converter          (pip install 后)
    python -m format_converter
    python main.py

架构：
    QWebEngineView (桌面壳) ←→ Flask REST API ←→ ConvertWorker 线程
         ↓                          ↓
    [HTML/CSS/JS 前端]        [converters/ 引擎]
"""

import sys
import os
import threading

# 确保项目根目录在 sys.path 中
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _start_server(port: int):
    """在后台线程启动 Flask 服务。"""
    from format_converter.server import app

    # 禁用 Flask 的请求日志
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def main():
    """启动 Format Converter GUI。"""
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtWebEngineWidgets import QWebEngineView

    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # ── 找可用端口 ─────────────────────────────────
    import socket
    def _find_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    port = _find_free_port()

    # ── 启动 Flask 后台线程 ─────────────────────────
    server_thread = threading.Thread(
        target=_start_server, args=(port,), daemon=True
    )
    server_thread.start()

    # ── 创建 Qt 应用 ────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("Format Converter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("zhcnhan")

    # ── 主窗口 — 纯 Web 渲染 ────────────────────────
    window = QMainWindow()
    window.setWindowTitle("Format Converter — 全功能格式转换工具")
    window.resize(1000, 760)
    window.setMinimumSize(780, 580)

    # WebView
    webview = QWebEngineView()
    webview.setUrl(QUrl(f"http://127.0.0.1:{port}"))

    central = QWidget()
    layout = QVBoxLayout(central)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(webview)
    window.setCentralWidget(central)

    window.show()

    # 注意：不依赖 Flask server_thread.join() — daemon 线程会随进程退出。
    code = app.exec()

    sys.exit(code)


if __name__ == "__main__":
    main()

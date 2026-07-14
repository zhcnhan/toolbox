"""异步转换工作线程。

使用 QThread 在后台执行转换任务，通过信号机制向前端传递进度和结果。
"""

from PySide6.QtCore import QThread, Signal


class ConvertWorker(QThread):
    """单个文件转换工作线程。

    Signals:
        progress:   (file_index, percent)  进度百分比
        finished:   (file_index, output_path)  完成
        error:      (file_index, error_message)  错误
        log:        (message)  日志消息
    """

    progress = Signal(int, int)   # file_index, percent
    finished = Signal(int, str)   # file_index, output_path
    error = Signal(int, str)      # file_index, error_message
    log = Signal(str)             # message

    def __init__(self, file_index: int, input_path: str, source_fmt: str,
                 target_fmt: str, output_path: str, parent=None):
        super().__init__(parent)
        self.file_index = file_index
        self.input_path = input_path
        self.source_fmt = source_fmt
        self.target_fmt = target_fmt
        self.output_path = output_path
        self._is_cancelled = False

    def cancel(self):
        """取消当前任务。"""
        self._is_cancelled = True

    def run(self):
        """在线程中执行转换。"""
        from format_converter.converters import convert_file

        try:
            if self._is_cancelled:
                return

            self.log.emit(f"[{self.file_index + 1}] 开始转换: {self.input_path}")

            # 进度回调
            def on_progress(pct: int):
                if not self._is_cancelled:
                    self.progress.emit(self.file_index, pct)

            result = convert_file(
                input_path=self.input_path,
                source_fmt=self.source_fmt,
                target_fmt=self.target_fmt,
                output_path=self.output_path,
                progress_callback=on_progress,
            )

            if self._is_cancelled:
                return

            self.progress.emit(self.file_index, 100)
            self.finished.emit(self.file_index, result)
            self.log.emit(f"[{self.file_index + 1}] 完成: {result}")

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(self.file_index, str(e))
                self.log.emit(f"[{self.file_index + 1}] 失败: {e}")

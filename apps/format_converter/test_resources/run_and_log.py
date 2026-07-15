"""运行完整测试并输出结果到文件。"""
import sys
import os

# 设置编码
os.environ["PYTHONIOENCODING"] = "utf-8"

# 设置 PATH（LibreOffice / ffmpeg 等）
extra_paths = [
    r"C:\Program Files\GTK3-Runtime Win64\bin",
    r"C:\Program Files\LibreOffice\program",
]
for p in extra_paths:
    if os.path.exists(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

# 重定向输出到文件
base = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(base, "test_result.log")
err_path = os.path.join(base, "test_stderr.log")

# 清空旧日志
open(log_path, "w", encoding="utf-8").close()
open(err_path, "w", encoding="utf-8").close()

log_file = open(log_path, "w", encoding="utf-8")
err_file = open(err_path, "w", encoding="utf-8")


class TeeStream:
    """同时写入多个流。"""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()


sys.stdout = TeeStream(log_file)
sys.stderr = TeeStream(err_file)

# 运行测试
test_script = os.path.join(base, "run_test.py")
with open(test_script, encoding="utf-8") as f:
    code = compile(f.read(), test_script, "exec")
    exec(code, {"__name__": "__main__"})

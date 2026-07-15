"""运行测试并保存结果到文件。"""
import sys, os

# 设置环境
os.environ["PYTHONIOENCODING"] = "utf-8"
for p in [r"C:\Program Files\GTK3-Runtime Win64\bin", r"C:\Program Files\LibreOffice\program"]:
    if os.path.exists(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

base = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(base, "test_result.log")
err_path = os.path.join(base, "test_stderr.log")

# 重定向输出
log_f = open(log_path, "w", encoding="utf-8")
err_f = open(err_path, "w", encoding="utf-8")


class Tee:
    def __init__(self, *s):
        self.s = s

    def write(self, d):
        for x in self.s:
            x.write(d)
            x.flush()

    def flush(self):
        for x in self.s:
            x.flush()


sys.stdout = Tee(log_f)
sys.stderr = Tee(err_f)

# 运行测试
test_script = os.path.join(base, "run_test.py")
with open(test_script, encoding="utf-8") as f:
    code = compile(f.read(), test_script, "exec")
    exec(code, {"__name__": "__main__"})

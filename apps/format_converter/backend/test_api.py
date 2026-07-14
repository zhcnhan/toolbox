"""自动化功能测试 v2 — Format Converter API (正确轮询)"""
import requests, json, os, tempfile, sys, time

BASE = "http://127.0.0.1:8000"
TMP = tempfile.mkdtemp()
PASSED, FAILED = 0, 0

def log(msg, ok=True):
    global PASSED, FAILED
    PASSED += 1 if ok else 0
    FAILED += 0 if ok else 1
    print(f"  {'[PASS]' if ok else '[FAIL]'} {msg}")

def section(title):
    print(f"\n{'='*50}\n  {title}\n{'='*50}")

def upload_file(filepath, fname):
    with open(filepath, "rb") as f:
        r = requests.post(f"{BASE}/api/upload", files={"files": (fname, f)})
    data = r.json()
    assert r.status_code == 200, f"Upload failed: {r.status_code}"
    assert len(data["files"]) == 1
    return data["files"][0]

def run_conversion(src_fmt, dst_fmt, original_name, temp_path, timeout=30):
    """Start conversion and poll until done."""
    payload = {
        "files": [temp_path],
        "source_fmt": src_fmt,
        "target_fmt": dst_fmt,
        "original_names": [original_name],
    }
    r = requests.post(f"{BASE}/api/convert", json=payload)
    data = r.json()
    task_id = data["task_id"]
    assert r.status_code == 200, f"Convert start failed: {r.status_code}"
    
    # Poll
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{BASE}/api/task/{task_id}")
        task = r.json()
        if task["status"] in ("done", "failed", "cancelled"):
            return task
        time.sleep(0.3)
    return None

# ─── Create test files ───
section("0. Create Test Files")

# JSON
jp = os.path.join(TMP, "test.json")
with open(jp, "w") as f:
    json.dump({"name": "test", "nums": [1,2,3], "meta": {"lang": "zh"}}, f)
log(f"Created test.json", True)

# TXT
tp = os.path.join(TMP, "test.txt")
with open(tp, "w", encoding="utf-8") as f:
    f.write("Hello World\nThis is a test file.\n")
log(f"Created test.txt", True)

# CSV
cp = os.path.join(TMP, "test.csv")
with open(cp, "w") as f:
    f.write("name,age,city\nAlice,30,NYC\nBob,25,LA\n")
log(f"Created test.csv", True)

# PNG
try:
    from PIL import Image
    pp = os.path.join(TMP, "test.png")
    Image.new("RGB", (100, 100), (73, 109, 137)).save(pp, "PNG")
    log(f"Created test.png", True)
    HAS_PNG = True
except:
    log(f"PNG skipped (no PIL)", True)
    HAS_PNG = False
    pp = None

# ─── 1. Health ───
section("1. Health Check")
r = requests.get(f"{BASE}/api/health")
log(f"GET /api/health → {r.status_code} {r.json()}", r.json().get("status") == "ok")

# ─── 2. Formats ───
section("2. Formats API")
r = requests.get(f"{BASE}/api/formats")
cats = list(r.json()["categories"].keys())
log(f"Categories: {cats}", len(cats) >= 5)

# ─── 3. Uploads ───
section("3. File Uploads")
ju = upload_file(jp, "test.json")
tu = upload_file(tp, "test.txt")
cu = upload_file(cp, "test.csv")
log(f"Upload JSON → detected={ju['detected_format']}", ju["detected_format"] == "json")
log(f"Upload TXT → detected={tu['detected_format']}", tu["detected_format"] == "txt")
log(f"Upload CSV → detected={cu['detected_format']}", cu["detected_format"] == "csv")
if HAS_PNG:
    pu = upload_file(pp, "test.png")
    log(f"Upload PNG → detected={pu['detected_format']}", pu["detected_format"] == "png")

# ─── 4. Data Conversions ───
section("4. Data Conversions")
tests = [
    (ju, "json", "yaml"), (ju, "json", "csv"),
    (cu, "csv", "json"), (cu, "csv", "yaml"),
    (ju, "json", "xml"),
]
for u, src, dst in tests:
    task = run_conversion(src, dst, u["original_name"], u["temp_path"])
    if task and task["results"]:
        r = task["results"][0]
        ok = r["success"]
        log(f"{src}→{dst}: {'OK' if ok else r.get('error','?')[:60]}", ok)
    else:
        log(f"{src}→{dst}: timed out or no results", False)

# ─── 5. Image ───
section("5. Image Conversions")
if HAS_PNG:
    for dst in ["jpg", "webp", "bmp", "gif"]:
        task = run_conversion("png", dst, pu["original_name"], pu["temp_path"])
        if task and task["results"]:
            r = task["results"][0]
            ok = r["success"]
            log(f"png→{dst}: {'OK' if ok else r.get('error','?')[:60]}", ok)
        else:
            log(f"png→{dst}: timed out", False)
else:
    log("Skip: no PIL", True)

# ─── 6. Document ───
section("6. Document Conversions")
for dst in ["pdf", "docx"]:
    task = run_conversion("txt", dst, tu["original_name"], tu["temp_path"])
    if task and task["results"]:
        r = task["results"][0]
        ok = r["success"]
        log(f"txt→{dst}: {'OK' if ok else r.get('error','?')[:80]}", ok)
    else:
        log(f"txt→{dst}: timed out", False)

# ─── Summary ───
section("Summary")
print(f"  TOTAL: {PASSED + FAILED} | PASSED: {PASSED} | FAILED: {FAILED}")
if FAILED > 0: sys.exit(1)

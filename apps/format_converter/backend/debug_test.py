import requests, json, tempfile, os, time, sys, io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
PASSED, FAILED = 0, 0
RESULTS = []

def log(msg, ok=True):
    global PASSED, FAILED
    PASSED += 1 if ok else 0
    FAILED += 0 if ok else 1
    tag = "PASS" if ok else "FAIL"
    line = f"[{tag}] {msg}"
    print(line)
    RESULTS.append(line)

def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")

def upload(filepath, fname):
    with open(filepath, "rb") as f:
        r = requests.post(f"{BASE}/api/upload", files={"files": (fname, f)})
    return r.json()["files"][0]

def convert(src_fmt, dst_fmt, orig_name, temp_path, timeout=30):
    payload = {
        "files": [temp_path],
        "source_fmt": src_fmt,
        "target_fmt": dst_fmt,
        "original_names": [orig_name],
    }
    r = requests.post(f"{BASE}/api/convert", json=payload)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:100]}"
    tid = r.json()["task_id"]

    start = time.time()
    while time.time() - start < timeout:
        time.sleep(0.3)
        r = requests.get(f"{BASE}/api/task/{tid}")
        t = r.json()
        if t["status"] in ("done", "failed", "cancelled"):
            r = t["results"][0] if t["results"] else {}
            return r["success"], r.get("error", "")
    return None, "timeout"

# ─── Create test files ───
print("Creating test files...")
tmp = tempfile.mkdtemp()

jp = os.path.join(tmp, "test.json")
with open(jp, "w") as f:
    json.dump({"name": "test", "nums": [1, 2, 3], "meta": {"lang": "zh"}}, f)

tp = os.path.join(tmp, "test.txt")
with open(tp, "w", encoding="utf-8") as f:
    f.write("Hello World\nThis is a test file.\n")

cp = os.path.join(tmp, "test.csv")
with open(cp, "w") as f:
    f.write("name,age,city\nAlice,30,NYC\nBob,25,LA\n")

HAS_IMG = False
try:
    from PIL import Image
    pp = os.path.join(tmp, "test.png")
    Image.new("RGB", (100, 100), (73, 109, 137)).save(pp, "PNG")
    HAS_IMG = True
except:
    pp = None

# ─── 1. Health ───
section("1. Health")
r = requests.get(f"{BASE}/api/health")
log("Health check", r.json().get("status") == "ok")

# ─── 2. Formats ───
section("2. Formats")
r = requests.get(f"{BASE}/api/formats")
cats = list(r.json()["categories"].keys())
log(f"Categories: {cats}", len(cats) >= 5)

# ─── 3. Upload ───
section("3. Upload")
ju = upload(jp, "test.json")
tu = upload(tp, "test.txt")
cu = upload(cp, "test.csv")
log(f"JSON: detected={ju['detected_format']}", ju["detected_format"] == "json")
log(f"TXT: detected={tu['detected_format']}", tu["detected_format"] == "txt")
log(f"CSV: detected={cu['detected_format']}", cu["detected_format"] == "csv")
if HAS_IMG:
    pu = upload(pp, "test.png")
    log(f"PNG: detected={pu['detected_format']}", pu["detected_format"] == "png")

# ─── 4. Data Conversions ───
section("4. Data Conversions")
pairs = [
    (ju, "json", "yaml"), (ju, "json", "csv"), (ju, "json", "xml"),
    (cu, "csv", "json"), (cu, "csv", "yaml"),
]
for u, src, dst in pairs:
    ok, err = convert(src, dst, u["original_name"], u["temp_path"])
    log(f"{src} -> {dst}: {'OK' if ok else err[:60]}", ok)

# ─── 5. Image Conversions ───
section("5. Image Conversions")
if HAS_IMG:
    for dst in ["jpg", "webp", "bmp", "gif"]:
        ok, err = convert("png", dst, pu["original_name"], pu["temp_path"])
        log(f"png -> {dst}: {'OK' if ok else err[:60]}", ok)
else:
    log("Skipped (no PIL)", True)

# ─── 6. Document Conversions ───
section("6. Document Conversions")
for dst in ["pdf", "docx"]:
    ok, err = convert("txt", dst, tu["original_name"], tu["temp_path"])
    log(f"txt -> {dst}: {'OK' if ok else err[:80]}", ok)

# ─── Summary ───
section("Summary")
print(f"  TOTAL: {PASSED + FAILED} | PASS: {PASSED} | FAIL: {FAILED}")
if FAILED > 0:
    sys.exit(1)

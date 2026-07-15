import requests, json, tempfile, os, time, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8001"
tmp = tempfile.mkdtemp()

def test_convert(src_fmt, dst_fmt, content_writer):
    """Create, upload, convert, poll."""
    name = f"test.{src_fmt}"
    fp = os.path.join(tmp, name)
    content_writer(fp)
    
    with open(fp, "rb") as f:
        r = requests.post(f"{BASE}/api/upload", files={"files": (name, f)})
    u = r.json()
    tp = u["files"][0]["temp_path"]
    
    r = requests.post(f"{BASE}/api/convert", json={
        "files": [tp], "source_fmt": src_fmt, "target_fmt": dst_fmt,
        "original_names": [name],
    })
    if r.status_code != 200:
        return False, f"Start failed: {r.status_code} {r.text[:80]}"
    
    tid = r.json()["task_id"]
    
    for _ in range(60):
        time.sleep(0.3)
        r = requests.get(f"{BASE}/api/task/{tid}")
        if r.status_code == 200:
            t = r.json()
            if t.get("status") in ("done", "failed", "cancelled"):
                res = t["results"][0] if t["results"] else {}
                return res.get("success", False), res.get("error", "")
        elif r.status_code == 404:
            time.sleep(0.5)
            continue
    return None, "timeout"

PASS, FAIL = 0, 0

def check(label, ok, err=""):
    global PASS, FAIL
    if ok: PASS += 1; print(f"  [PASS] {label}")
    else: FAIL += 1; print(f"  [FAIL] {label}: {err[:80]}")

# ─── Health ───
r = requests.get(f"{BASE}/api/health")
check("Health", r.json().get("status") == "ok")

# ─── Data ───
ok, err = test_convert("json", "yaml", lambda f: json.dump({"a": 1, "b": [2, 3]}, open(f, "w")))
check("JSON -> YAML", ok, err)

ok, err = test_convert("json", "csv", lambda f: json.dump([{"name":"A","age":1},{"name":"B","age":2}], open(f, "w")))
check("JSON -> CSV", ok, err)

ok, err = test_convert("json", "xml", lambda f: json.dump({"root": {"item": [1,2]}}, open(f, "w")))
check("JSON -> XML", ok, err)

ok, err = test_convert("csv", "json", lambda f: open(f, "w").write("name,age\nA,1\nB,2\n"))
check("CSV -> JSON", ok, err)

ok, err = test_convert("csv", "yaml", lambda f: open(f, "w").write("name,age\nA,1\nB,2\n"))
check("CSV -> YAML", ok, err)

# ─── Image ───
try:
    from PIL import Image
    def make_png(fp):
        Image.new("RGB", (100, 100), (73, 109, 137)).save(fp, "PNG")
    ok, err = test_convert("png", "jpg", make_png)
    check("PNG -> JPG", ok, err)
    ok, err = test_convert("png", "webp", make_png)
    check("PNG -> WEBP", ok, err)
    ok, err = test_convert("png", "bmp", make_png)
    check("PNG -> BMP", ok, err)
    ok, err = test_convert("png", "gif", make_png)
    check("PNG -> GIF", ok, err)
except Exception as e:
    print(f"  [SKIP] Image: {e}")

# ─── Document ───
ok, err = test_convert("txt", "pdf", lambda f: open(f, "w").write("Hello World"))
check("TXT -> PDF", ok, err)

ok, err = test_convert("txt", "docx", lambda f: open(f, "w").write("Hello World"))
check("TXT -> DOCX", ok, err)

print(f"\n{'='*40}")
print(f"  PASS: {PASS} | FAIL: {FAIL}")
if FAIL: sys.exit(1)

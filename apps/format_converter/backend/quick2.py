import requests, json, tempfile, os, time, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
tmp = tempfile.mkdtemp()

# Create and upload JSON
jp = os.path.join(tmp, "test.json")
with open(jp, "w") as f:
    json.dump({"name": "test", "values": [1, 2, 3]}, f)

with open(jp, "rb") as f:
    r = requests.post(f"{BASE}/api/upload", files={"files": ("test.json", f)})
tp = r.json()["files"][0]["temp_path"]

# Convert
r = requests.post(f"{BASE}/api/convert", json={
    "files": [tp], "source_fmt": "json", "target_fmt": "yaml",
    "original_names": ["test.json"],
})
tid = r.json()["task_id"]
print(f"Task ID: {tid}")

# Poll with full response
time.sleep(3)
r = requests.get(f"{BASE}/api/task/{tid}")
print(f"HTTP {r.status_code}")
print(f"Body: {r.text}")

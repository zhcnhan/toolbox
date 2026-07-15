import requests, json, tempfile, os, time, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
tmp = tempfile.mkdtemp()

# Create JSON
jp = os.path.join(tmp, "test.json")
with open(jp, "w") as f:
    json.dump({"name": "test", "values": [1, 2, 3]}, f)

# Upload
with open(jp, "rb") as f:
    r = requests.post(f"{BASE}/api/upload", files={"files": ("test.json", f)})
u = r.json()
tp = u["files"][0]["temp_path"]
print(f"Upload OK: detected={u['files'][0]['detected_format']}")

# Convert: JSON to YAML
r = requests.post(f"{BASE}/api/convert", json={
    "files": [tp],
    "source_fmt": "json",
    "target_fmt": "yaml",
    "original_names": ["test.json"],
})
data = r.json()
print(f"Convert response keys: {list(data.keys())}")
print(f"Task ID: {data.get('task_id')}")

tid = data.get("task_id")
if not tid:
    print("FAIL: no task_id")
    sys.exit(1)

# Poll task
time.sleep(2)
r = requests.get(f"{BASE}/api/task/{tid}")
task_data = r.json()
print(f"Task response keys: {list(task_data.keys())}")
print(f"Status: {task_data.get('status', 'MISSING')}")
print(f"Completed: {task_data.get('completed', 'MISSING')}")
print(f"Failed: {task_data.get('failed', 'MISSING')}")
print(f"Results: {json.dumps(task_data.get('results', []), indent=2, ensure_ascii=False)}")
print(f"Logs: {task_data.get('logs', [])}")

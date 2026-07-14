import json


def json_loads(s: str):
    return json.loads(s)


def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)

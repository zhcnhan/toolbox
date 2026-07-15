import csv
import io
from typing import Any


def csv_loads(s: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(s))
    return [row for row in reader]


def csv_dumps(data: list[dict[str, Any]]) -> str:
    if not data:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(data[0].keys()))
    writer.writeheader()
    writer.writerows(data)
    return buf.getvalue()

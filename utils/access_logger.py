import os
import json
import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "access.jsonl")


def _ensure_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def log(**kwargs):
    _ensure_dir()
    record = {"time": datetime.datetime.now().isoformat(), **kwargs}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

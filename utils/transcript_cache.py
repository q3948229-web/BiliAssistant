import os
import json
import re
import datetime

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "transcripts.json")


def _ensure():
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write("{}")


def _load() -> dict:
    _ensure()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    _ensure()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_bv(source: str) -> str | None:
    m = re.search(r"(BV[a-zA-Z0-9]+)", source)
    return m.group(1) if m else None


def get(bv_id: str) -> str | None:
    data = _load()
    entry = data.get(bv_id)
    return entry["transcript"] if entry else None


def set(bv_id: str, transcript: str):
    data = _load()
    data[bv_id] = {
        "transcript": transcript,
        "cached_at": datetime.datetime.now().isoformat(),
    }
    _save(data)

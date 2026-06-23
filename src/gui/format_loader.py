"""포맷 정의 로더."""
from pathlib import Path

import yaml

FORMATS_DIR = Path(__file__).parent / "formats"
FORMATS_FILE = FORMATS_DIR / "formats.yaml"


def load_formats() -> list[dict]:
    if not FORMATS_FILE.exists():
        return []
    with open(FORMATS_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("formats", [])

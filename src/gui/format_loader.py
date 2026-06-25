"""포맷(텍스트 오버레이 프리셋) 로더.

포맷 = 커버(hook) 슬라이드에 제목을 어떻게 얹을지 정하는 프리셋.
- 선택지는 `formats/thumbnails/` 디렉토리의 이미지들로 자동 생성(디렉토리 기반).
- 각 이미지의 오버레이 파라미터는 formats.yaml 의 `overlays:` 맵(파일명 키)에서 읽음.
  엔트리가 없으면 기본값(가운데·흰색·큰글자·그림자·contain)을 적용.
"""
from pathlib import Path

import yaml

FORMATS_DIR = Path(__file__).parent / "formats"
FORMATS_FILE = FORMATS_DIR / "formats.yaml"
THUMBS_DIR = FORMATS_DIR / "thumbnails"

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")

_VALID_POSITION = {"top", "center", "bottom", "auto"}
_VALID_BG = {"none", "shadow", "bar", "gradient"}
_VALID_FIT = {"cover", "contain"}

# 기본 스타일: 이슈카드 느낌 — 하단, 크게, 흰색, 검은 외곽선, 어두운 그라데이션, 스크린샷 그대로(contain)
DEFAULT_OVERLAY = {
    "text_position": "bottom",
    "text_color": "#FFFFFF",
    "text_size": 64,
    "text_bg": "gradient",
    "image_fit": "contain",
    "text_outline": True,
}


def _load_yaml() -> dict:
    if not FORMATS_FILE.exists():
        return {}
    try:
        with open(FORMATS_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _overlays_map() -> dict:
    raw = _load_yaml().get("overlays", {})
    return raw if isinstance(raw, dict) else {}


def _merge_overlay(raw: dict | None) -> dict:
    """yaml 엔트리(혹은 None)를 기본값과 머지 + 검증. 잘못된 값은 기본값으로."""
    o = dict(DEFAULT_OVERLAY)
    if not isinstance(raw, dict):
        return o

    pos = str(raw.get("text_position", o["text_position"])).lower()
    o["text_position"] = pos if pos in _VALID_POSITION else DEFAULT_OVERLAY["text_position"]

    color = raw.get("text_color")
    if isinstance(color, str) and color.strip():
        o["text_color"] = color.strip()

    try:
        o["text_size"] = int(raw.get("text_size", o["text_size"]))
    except (TypeError, ValueError):
        pass

    bg = str(raw.get("text_bg", o["text_bg"])).lower()
    o["text_bg"] = bg if bg in _VALID_BG else DEFAULT_OVERLAY["text_bg"]

    fit = str(raw.get("image_fit", o["image_fit"])).lower()
    o["image_fit"] = fit if fit in _VALID_FIT else DEFAULT_OVERLAY["image_fit"]

    if "text_outline" in raw:
        val = raw["text_outline"]
        o["text_outline"] = str(val).strip().lower() not in ("false", "0", "no", "none", "")

    return o


def load_format_options() -> list[dict]:
    """thumbnails/ 의 모든 이미지를 선택지로(디렉토리 기반)."""
    if not THUMBS_DIR.exists():
        return []
    overlays = _overlays_map()
    options = []
    for f in sorted(THUMBS_DIR.iterdir()):
        if f.suffix.lower() not in _IMG_EXTS:
            continue
        fname = f.name
        raw = overlays.get(fname)
        ov = _merge_overlay(raw)
        name = raw["name"] if isinstance(raw, dict) and raw.get("name") else f.stem
        options.append({
            "id": fname,            # 파일명 = id (라운드트립 단순)
            "thumbnail": fname,
            "name": name,
            "description": f"{ov['text_position']} · {ov['text_bg']}",
            "overlay": ov,          # 서버용; 프론트는 무시
        })
    return options


def resolve_overlay(format_id: str | None) -> dict:
    """선택된 format_id(=썸네일 파일명) → 머지된 오버레이 파라미터. 미지면 기본값."""
    if not format_id:
        return dict(DEFAULT_OVERLAY)
    return _merge_overlay(_overlays_map().get(format_id))


def load_formats() -> list[dict]:
    """레거시(formats: 리스트) — 하위호환용으로 유지."""
    return _load_yaml().get("formats", [])

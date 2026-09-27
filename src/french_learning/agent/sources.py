"""Сжатые копии исходников в черновике (FR-033; research R6)."""

from __future__ import annotations

import hashlib
import io
import re
import shutil
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from french_learning.agent.staging import op_dir

MAX_SIDE = 1600
JPEG_QUALITY = 80
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"}

_TRANSLIT = dict(
    zip(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        [
            "a",
            "b",
            "v",
            "g",
            "d",
            "e",
            "e",
            "zh",
            "z",
            "i",
            "y",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "r",
            "s",
            "t",
            "u",
            "f",
            "kh",
            "ts",
            "ch",
            "sh",
            "shch",
            "-",
            "y",
            "-",
            "e",
            "yu",
            "ya",
        ],
        strict=True,
    )
)
_TRANSLIT["ъ"] = _TRANSLIT["ь"] = ""


def slugify(name: str) -> str:
    text = "".join(_TRANSLIT.get(ch, ch) for ch in name.lower())
    text = text.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "file"


def _compressed_jpeg(path: Path) -> bytes | None:
    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((MAX_SIDE, MAX_SIDE))
            buffer = io.BytesIO()
            img.save(buffer, "JPEG", quality=JPEG_QUALITY, optimize=True)
            return buffer.getvalue()
    except (OSError, UnidentifiedImageError):
        return None


def store_source(source: Path, lesson: int | None, root: Path, op: str) -> str:
    """Положить сжатую копию в черновик; вернуть путь для `sources[].file`."""
    data = source.read_bytes()
    short_hash = hashlib.sha256(data).hexdigest()[:6]
    stem = slugify(source.stem)
    folder = f"lessons/{lesson:03d}/sources" if lesson else "extra/sources"

    payload, suffix = data, source.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        compressed = _compressed_jpeg(source)
        if compressed is not None and len(compressed) < len(data):
            payload, suffix = compressed, ".jpg"
        elif suffix == ".jpeg":
            suffix = ".jpg"

    relative = f"{folder}/{stem}-{short_hash}{suffix}"
    target = op_dir(root, op) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if payload is data:
        shutil.copyfile(source, target)
    else:
        target.write_bytes(payload)
    return relative

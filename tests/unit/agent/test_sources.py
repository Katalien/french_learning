"""Сжатые копии исходников (FR-033; research R6)."""

from pathlib import Path

from PIL import Image

from french_learning.agent.sources import store_source


def test_large_image_is_resized_and_stripped(materials: Path, store: Path):
    stored = store_source(materials / "Leçon 07/IMG_0001.jpeg", lesson=7, root=store, op="op1")
    assert stored.startswith("lessons/007/sources/img-0001-")
    assert stored.endswith(".jpg")
    path = store / ".staging/op1" / stored
    with Image.open(path) as img:
        assert max(img.size) == 1600
        assert not img.getexif()


def test_small_image_keeps_size(materials: Path, store: Path):
    stored = store_source(materials / "Leçon 07/IMG_0003.jpeg", lesson=7, root=store, op="op1")
    with Image.open(store / ".staging/op1" / stored) as img:
        assert img.size == (800, 600)


def test_bigger_result_falls_back_to_original(tmp_path: Path, store: Path):
    # Шум, сохранённый с очень низким качеством: пересжатие с качеством 80 его увеличит.
    tiny = tmp_path / "tiny.jpeg"
    Image.effect_noise((200, 200), 100).convert("RGB").save(tiny, "JPEG", quality=5)
    stored = store_source(tiny, lesson=7, root=store, op="op1")
    assert (store / ".staging/op1" / stored).read_bytes() == tiny.read_bytes()


def test_pdf_and_docx_are_copied_unchanged(materials: Path, store: Path):
    for name, suffix in (("regles.pdf", ".pdf"), ("avoir.docx", ".docx")):
        source = materials / "Leçon 07" / name
        stored = store_source(source, lesson=7, root=store, op="op1")
        assert stored.endswith(suffix)
        assert (store / ".staging/op1" / stored).read_bytes() == source.read_bytes()


def test_names_are_latin_and_safe(tmp_path: Path, store: Path):
    source = tmp_path / "Частичные артикли (1).pdf"
    source.write_bytes(b"%PDF-1.4 demo")
    stored = store_source(source, lesson=13, root=store, op="op1")
    name = Path(stored).name
    assert name.isascii() and " " not in name
    assert name.startswith("chastichnye-artikli-1-")

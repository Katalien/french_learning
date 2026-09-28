"""Иконка приложения (ярлык на рабочем столе и значок вкладки): «Fr» на переливе палитры 009.

Запуск: `uv run python scripts/make_icon.py` → src/french_learning/web/static/favicon.ico
"""

import contextlib
import itertools
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "french_learning" / "web" / "static"
SIZE = 256
# палитра «Перелив» (specs/009-redesign/design.md)
STOPS = [
    (0.0, (250, 220, 254)),
    (0.4, (199, 243, 246)),
    (0.75, (164, 198, 233)),
    (1.0, (184, 174, 227)),
]
INK = (44, 47, 82)


def _mix(t: float) -> tuple[int, int, int]:
    for (t0, c0), (t1, c1) in itertools.pairwise(STOPS):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return tuple(round(a + (b - a) * k) for a, b in zip(c0, c1, strict=True))
    return STOPS[-1][1]


def make() -> Image.Image:
    gradient = Image.new("RGB", (SIZE, SIZE))
    pixels = gradient.load()
    for y in range(SIZE):
        for x in range(SIZE):
            pixels[x, y] = _mix((x + y) / (2 * (SIZE - 1)))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=56, fill=255)
    icon = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    icon.paste(gradient, (0, 0), mask)
    draw = ImageDraw.Draw(icon)
    font = ImageFont.truetype(str(STATIC / "fonts" / "Lora.ttf"), 150)
    with contextlib.suppress(OSError, AttributeError):
        font.set_variation_by_axes([700])
    draw.text((SIZE / 2, SIZE / 2 + 6), "Fr", font=font, fill=INK, anchor="mm")
    return icon


if __name__ == "__main__":
    target = STATIC / "favicon.ico"
    sizes = [(n, n) for n in (16, 24, 32, 48, 64, 128, 256)]
    make().save(target, sizes=sizes)
    print(f"Иконка: {target}")

"""Gera os 8 PNGs placeholder de overlay (Python puro, sem dependências).

Cria, em assets/overlays/, os arquivos {canto}_border.png e {canto}_logo.png
com fundo transparente:
  - border: brackets em "L" no canto correspondente (branco semi-transparente);
  - logo: disco colorido centralizado (placeholder da marca).

Uso:  python tools/make_placeholders.py
"""

import struct
import zlib
from pathlib import Path

SIZE = 240  # lado do PNG, em px
THICK = 14  # espessura do bracket
LENGTH = 90  # comprimento de cada braço do bracket
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "overlays"

CORNERS = ["top_left", "top_right", "bottom_left", "bottom_right"]


def blank(size):
    """Buffer RGBA totalmente transparente."""
    return bytearray(size * size * 4)


def set_px(buf, size, x, y, rgba):
    if 0 <= x < size and 0 <= y < size:
        i = (y * size + x) * 4
        buf[i : i + 4] = bytes(rgba)


def fill_rect(buf, size, x0, y0, x1, y1, rgba):
    for y in range(max(0, y0), min(size, y1)):
        for x in range(max(0, x0), min(size, x1)):
            set_px(buf, size, x, y, rgba)


def fill_disc(buf, size, cx, cy, r, rgba):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                set_px(buf, size, x, y, rgba)


def draw_border(corner):
    """Bracket em L posicionado no canto indicado."""
    buf = blank(SIZE)
    white = (255, 255, 255, 210)
    left = "left" in corner
    top = "top" in corner

    # Braço horizontal e vertical encostados no canto.
    hx0 = 0 if left else SIZE - LENGTH
    hx1 = LENGTH if left else SIZE
    hy0 = 0 if top else SIZE - THICK
    hy1 = THICK if top else SIZE
    fill_rect(buf, SIZE, hx0, hy0, hx1, hy1, white)  # braço horizontal

    vx0 = 0 if left else SIZE - THICK
    vx1 = THICK if left else SIZE
    vy0 = 0 if top else SIZE - LENGTH
    vy1 = LENGTH if top else SIZE
    fill_rect(buf, SIZE, vx0, vy0, vx1, vy1, white)  # braço vertical
    return buf


def draw_logo():
    """Disco laranja com anel branco — placeholder de logo."""
    buf = blank(SIZE)
    c = SIZE // 2
    fill_disc(buf, SIZE, c, c, 70, (255, 255, 255, 235))  # anel externo
    fill_disc(buf, SIZE, c, c, 58, (255, 140, 0, 255))  # corpo laranja
    return buf


def write_png(path, size, buf):
    def chunk(typ, data):
        body = typ + data
        crc = zlib.crc32(body) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + body + struct.pack(">I", crc)

    raw = bytearray()
    for y in range(size):  # filtro 0 (None) em cada linha
        raw.append(0)
        raw.extend(buf[y * size * 4 : (y + 1) * size * 4])

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # RGBA 8-bit
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(chunk(b"IEND", b""))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for corner in CORNERS:
        write_png(OUT_DIR / f"{corner}_border.png", SIZE, draw_border(corner))
        write_png(OUT_DIR / f"{corner}_logo.png", SIZE, draw_logo())
    print(f"8 PNGs gerados em {OUT_DIR}")


if __name__ == "__main__":
    main()

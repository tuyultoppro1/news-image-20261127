#!/usr/bin/env python3
"""The World Today - 27 November 2026.

Draws a one-page newspaper front page (1024x1024 PNG) summing up the
world news of Friday 27 November 2026. Python 3.13, standard library
only, deterministic: two runs write identical bytes.

The font is a hand-built 5x7 bitmap: each glyph is one 35-character
string of bits, row by row, so the whole face fits in a single table.

Lead: Zelenskyy warns Russia is ready for a new mass attack on
Ukraine's power grid.
Second: US regulators clear SpaceX to launch up to one million
orbital data-centre satellites.
Third: Egypt arrests a man over the Cairo fuel tanker fire.
Also: the EU backs a 45 billion euro loan for Ukraine, Britain
tells 100,000 reservists to prepare, and the day's other stories
in the ALSO TODAY strip.
"""

import os
import struct
import zlib

W = 1024
H = 1024
PAPER = (255, 255, 255)
INK = (0, 0, 0)
RED = (168, 0, 0)
MX = 28          # left margin; content runs MX .. MX + CW
CW = 968         # content width
RX = 528         # right column x
COLW = 464       # column width

# 5x7 bitmap font: one 35-bit string per glyph, rows left to right,
# top to bottom. Uppercase, digits, punctuation.
FONT = {
    "A": "01110100011000111111100011000110001",
    "B": "11110100011000111110100011000111110",
    "C": "01110100011000010000100001000101110",
    "D": "11110100011000110001100011000111110",
    "E": "11111100001000011110100001000011111",
    "F": "11111100001000011110100001000010000",
    "G": "01110100011000010111100011000101111",
    "H": "10001100011000111111100011000110001",
    "I": "01110001000010000100001000010001110",
    "J": "00111000100001000010000101001001100",
    "K": "10001100101010011000101001001010001",
    "L": "10000100001000010000100001000011111",
    "M": "10001110111010110101100011000110001",
    "N": "10001110011010110011100011000110001",
    "O": "01110100011000110001100011000101110",
    "P": "11110100011000111110100001000010000",
    "Q": "01110100011000110001101011001001101",
    "R": "11110100011000111110101001001010001",
    "S": "01111100001000001110000010000111110",
    "T": "11111001000010000100001000010000100",
    "U": "10001100011000110001100011000101110",
    "V": "10001100011000110001100010101000100",
    "W": "10001100011000110101101011010101010",
    "X": "10001100010101000100010101000110001",
    "Y": "10001100010101000100001000010000100",
    "Z": "11111000010001000100010001000011111",
    "0": "01110100011001110101110011000101110",
    "1": "00100011000010000100001000010001110",
    "2": "01110100010000100110010001000011111",
    "3": "11111000100010000010000011000101110",
    "4": "00010001100101010010111110001000010",
    "5": "11111100001111000001000011000101110",
    "6": "01110100001000011110100011000101110",
    "7": "11111000010001000100010000100001000",
    "8": "01110100011000101110100011000101110",
    "9": "01110100011000101111000010000101110",
    " ": "00000000000000000000000000000000000",
    ".": "00000000000000000000000000110001100",
    ",": "00000000000000000000011000010001000",
    "'": "00100001000100000000000000000000000",
    "-": "00000000000000001110000000000000000",
    ":": "00000011000110000000011000110000000",
    ";": "00000011000110000000011000010001000",
    "!": "00100001000010000100001000000000100",
    "?": "01110100010000100110001000000000100",
    "(": "00010001000100001000010000010000010",
    ")": "01000001000001000010000100010001000",
    "/": "00001000100001000100010000100010000",
    "&": "01100100101010001000101011001001101",
    "%": "11001110100001000100010000101110011",
    "$": "00100011111010001110001011111000100",
    "+": "00000001000010001110001000010000000",
    "=": "00000000001111100000111110000000000",
    "*": "00000101010111011111011101010100000",
}


def blank():
    return bytearray(b"\xff" * (W * H * 3))


def set_px(buf, x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = color


def fill_rect(buf, x, y, w, h, color):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            set_px(buf, xx, yy, color)


def hline(buf, x, y, w, color, thick=2):
    fill_rect(buf, x, y, w, thick, color)


def border(buf):
    fill_rect(buf, 0, 0, W, 4, INK)
    fill_rect(buf, 0, H - 4, W, 4, INK)
    fill_rect(buf, 0, 0, 4, H, INK)
    fill_rect(buf, W - 4, 0, 4, H, INK)


def circle(buf, cx, cy, r, color):
    # Midpoint circle outline, 1px thick.
    x, y = 0, r
    d = 3 - 2 * r
    while x <= y:
        for dx, dy in ((x, y), (y, x), (-x, y), (-y, x),
                       (x, -y), (y, -x), (-x, -y), (-y, -x)):
            set_px(buf, cx + dx, cy + dy, color)
        if d < 0:
            d += 4 * x + 6
        else:
            d += 4 * (x - y) + 10
            y -= 1
        x += 1


def globe(buf, cx, cy, r, color):
    circle(buf, cx, cy, r, color)
    # Meridian ellipse (vertical) and equator line.
    for yy in range(cy - r, cy + r + 1):
        t = (yy - cy) / r
        half = int((r * 0.45) * (1 - t * t) ** 0.5)
        set_px(buf, cx - half, yy, color)
        set_px(buf, cx + half, yy, color)
    hline(buf, cx - r, cy, 2 * r, color, 1)


def adv(scale):
    return 6 * scale


def text_w(s, scale):
    return len(s) * adv(scale) - scale if s else 0


def put_text(buf, x, y, s, scale, color):
    cx = x
    for ch in s:
        bits = FONT.get(ch)
        if bits is None:
            cx += adv(scale)
            continue
        for idx, bit in enumerate(bits):
            if bit == "1":
                row, col = divmod(idx, 5)
                fill_rect(buf, cx + col * scale, y + row * scale,
                          scale, scale, color)
        cx += adv(scale)


def put_centered(buf, y, s, scale, color):
    put_text(buf, (W - text_w(s, scale)) // 2, y, s, scale, color)


def wrap_text(s, max_chars):
    lines, cur = [], ""
    for word in s.split(" "):
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= max_chars:
            cur += " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def paragraph(buf, x, y, s, width_px, scale, color, leading):
    lines = wrap_text(s, width_px // adv(scale))
    for i, line in enumerate(lines):
        put_text(buf, x, y + i * leading, line, scale, color)
    return y + len(lines) * leading


def png_chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def save_png(path, buf):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", ihdr)
    png += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += png_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def draw_page():
    buf = blank()
    border(buf)

    # ---- Masthead ----
    put_centered(buf, 30, "THE WORLD TODAY", 6, INK)
    globe(buf, 968, 51, 24, INK)
    hline(buf, MX, 86, CW, RED, 4)
    put_centered(buf, 100, "FRIDAY 27 NOVEMBER 2026", 3, RED)
    hline(buf, MX, 132, CW, INK, 2)

    # ---- Lead story: Zelenskyy warns of new Russian grid attack ----
    put_centered(buf, 148, "ZELENSKYY WARNS OF NEW", 4, INK)
    put_centered(buf, 180, "RUSSIAN GRID ATTACK", 4, INK)
    paragraph(buf, 48, 222,
              "PRESIDENT ZELENSKYY WARNED RUSSIA COULD LAUNCH ANOTHER "
              "MAJOR ATTACK ON UKRAINE'S POWER GRID AND ESSENTIAL "
              "SERVICES, AS MOSCOW READIES A NEW WINTER OFFENSIVE.",
              928, 2, INK, 19)
    hline(buf, MX, 292, CW, INK, 2)

    # ---- Story 2: SpaceX cleared for one million satellites (left) ----
    put_text(buf, 32, 308, "WASHINGTON - SPACE", 2, RED)
    put_text(buf, 32, 330, "US CLEARS SPACEX", 3, INK)
    put_text(buf, 32, 354, "ONE MILLION SATELLITES", 3, INK)
    paragraph(buf, 32, 388,
              "US REGULATORS CLEARED SPACEX TO LAUNCH UP TO ONE "
              "MILLION ORBITAL DATA-CENTRE SATELLITES.",
              COLW, 2, INK, 19)

    # ---- Story 3: Cairo tanker fire arrest (right) ----
    put_text(buf, RX, 308, "CAIRO - JUSTICE", 2, RED)
    put_text(buf, RX, 330, "CAIRO ARREST IN", 3, INK)
    put_text(buf, RX, 354, "TANKER FIRE CASE", 3, INK)
    paragraph(buf, RX, 388,
              "PROSECUTORS ARRESTED A MAN ACCUSED OF CAUSING THE "
              "CAIRO FUEL TANKER FIRE THAT KILLED 31 PEOPLE, EGYPT "
              "SAID.",
              COLW, 2, INK, 19)
    hline(buf, MX, 470, CW, INK, 2)

    # ---- Story 4: EU backs Ukraine loan (left) ----
    put_text(buf, 32, 486, "BRUSSELS - EUROPE", 2, RED)
    put_text(buf, 32, 508, "EU BACKS 45BN", 3, INK)
    put_text(buf, 32, 532, "UKRAINE LOAN", 3, INK)
    paragraph(buf, 32, 566,
              "24 EU STATES BACKED A 45 BILLION EURO LOAN FOR "
              "UKRAINE, WHILE TALKS ON THE 2028-2034 BUDGET "
              "STALLED.",
              COLW, 2, INK, 19)

    # ---- Story 5: UK reservists (right) ----
    put_text(buf, RX, 486, "LONDON - DEFENCE", 2, RED)
    put_text(buf, RX, 508, "UK CALLS UP", 3, INK)
    put_text(buf, RX, 532, "100,000 RESERVISTS", 3, INK)
    paragraph(buf, RX, 566,
              "BRITAIN TOLD 100,000 STRATEGIC RESERVISTS TO "
              "PREPARE FOR A POSSIBLE CALL-UP, A REPORT SAID.",
              COLW, 2, INK, 19)
    hline(buf, MX, 656, CW, INK, 2)

    # ---- ALSO TODAY strip ----
    put_text(buf, 32, 672, "ALSO TODAY", 3, INK)
    items = [
        (32, 708,
         "THANKSGIVING STORM HITS NEW YORK WITH 56-MPH GUSTS"),
        (RX, 708,
         "SPAIN RACES TO STOP OIL SPILL RISK AFTER SHIP CAPSIZES OFF IBIZA"),
        (32, 756,
         "NORTH KOREA EXPELS SWISS DIPLOMAT IN SANCTIONS ROW"),
        (RX, 756,
         "EBOLA IN DR CONGO PASSES 12,000 CASES, NEARLY 6,000 DEAD"),
        (32, 804,
         "NEW ZEALAND COUNT: LABOUR 29.88%, NATIONAL ON 40 SEATS"),
        (RX, 804,
         "US ENVOY: BIGGEST RUSSIA-UKRAINE PRISONER SWAP COMING SHORTLY"),
    ]
    for x, y, s in items:
        fill_rect(buf, x, y + 2, 10, 10, RED)
        paragraph(buf, x + 18, y, s, 446, 2, INK, 19)
    hline(buf, MX, 856, CW, INK, 2)

    # ---- Bottom story: IAEA seeks Zaporizhzhia ceasefire ----
    put_centered(buf, 872, "IAEA SEEKS CEASEFIRE TO REPAIR ZAPORIZHZHIA LINK", 3, INK)
    paragraph(buf, 48, 908,
              "THE IAEA SAID IT IS WORKING WITH RUSSIA AND UKRAINE "
              "ON A CEASEFIRE TO REPAIR A POWER LINK AT THE "
              "ZAPORIZHZHIA NUCLEAR PLANT.",
              928, 2, INK, 19)

    # ---- Footer ----
    put_centered(buf, 962, "THE WORLD TODAY - 27 NOVEMBER 2026", 2, INK)
    return buf


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    save_png(os.path.join(out, "entry.png"), draw_page())


if __name__ == "__main__":
    main()

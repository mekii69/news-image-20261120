#!/usr/bin/env python3
"""Draw a one-page newspaper front page summing up 20 November 2026.

Reads hero.bin (six 288x288 RGB tiles behind one zlib stream, written by
the session that built this entry) and renders a 1024x1024 PNG to the
output directory. Standard library only, no network, fully deterministic:
the same input bytes always produce the same output bytes.
"""
import os
import struct
import sys
import zlib

W, H = 1024, 1024
TILE = 288

PAPER = (245, 240, 225)
CARD = (252, 250, 244)
INK = (26, 26, 26)
RED = (168, 50, 38)
NAVY = (31, 58, 95)
BLUE = (74, 107, 138)
GOLD = (200, 162, 39)
GRAY = (110, 104, 90)
WHITE = (250, 248, 242)
RULE = (26, 26, 26)

# 5x7 bitmap font. Each glyph is seven 5-bit rows, most significant bit
# leftmost. Only the characters the page uses are defined.
GLYPHS = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x01, 0x01, 0x01, 0x01, 0x01, 0x11, 0x0E),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x0A, 0x04, 0x04, 0x04, 0x0A, 0x11),
    "Y": (0x11, 0x0A, 0x04, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    ".": (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ",": (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    ":": (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    ";": (0, 0x0C, 0x0C, 0, 0x0C, 0x04, 0x08),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    "-": (0, 0, 0, 0x1F, 0, 0, 0),
    "/": (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "%": (0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03),
    "|": (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "+": (0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0),
    "=": (0, 0, 0x1F, 0, 0x1F, 0, 0),
    '"': (0x0A, 0x0A, 0x0A, 0, 0, 0, 0),
}


def clean(text):
    """Normalize display text to the glyph set: uppercase, ASCII quotes."""
    out = []
    for ch in text.upper():
        if ch in ("\u2019", "\u2018", "`"):
            out.append("'")
        elif ch in ("\u201c", "\u201d"):
            out.append('"')
        elif ch in ("\u2014", "\u2013"):
            out.append("-")
        elif ch == "\u2022":
            out.append("|")
        else:
            out.append(ch)
    return "".join(out)


class Canvas:
    def __init__(self, w, h, color):
        self.w = w
        self.h = h
        self.px = bytearray(color * w * h)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(max(0, y), min(self.h, y + h)):
            base = (yy * self.w + max(0, x)) * 3
            span = min(self.w, x + w) - max(0, x)
            if span > 0:
                self.px[base:base + span * 3] = bytes(color) * span

    def hline(self, x, y, w, color, thick=1):
        self.rect(x, y, w, thick, color)

    def vline(self, x, y, h, color, thick=1):
        self.rect(x, y, thick, h, color)

    def blit(self, tile, sx0, sy0, sw, sh, dx, dy, dw, dh):
        """Nearest-neighbour crop-and-scale of one RGB tile onto the page."""
        for yy in range(dh):
            sy = sy0 + (yy * sh) // dh
            for xx in range(dw):
                sx = sx0 + (xx * sw) // dw
                i = (sy * TILE + sx) * 3
                self.set(dx + xx, dy + yy, tile[i:i + 3])

    def text(self, x, y, s, scale, color):
        s = clean(s)
        cx = x
        for ch in s:
            rows = GLYPHS.get(ch, GLYPHS[" "])
            for ry in range(7):
                bits = rows[ry]
                for rx in range(5):
                    if bits & (1 << (4 - rx)):
                        self.rect(cx + rx * scale, y + ry * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx

    def text_w(self, s, scale):
        return len(clean(s)) * 6 * scale - scale

    def wrap(self, s, width, scale):
        """Greedy word wrap; explicit newlines force breaks."""
        lines = []
        for para in clean(s).split("\n"):
            words = para.split(" ")
            cur = ""
            for word in words:
                trial = word if not cur else cur + " " + word
                if self.text_w(trial, scale) <= width or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = word
            lines.append(cur)
        return lines

    def para(self, x, y, s, width, scale, color, lh=None):
        if lh is None:
            lh = 8 * scale
        for line in self.wrap(s, width, scale):
            self.text(x, y, line, scale, color)
            y += lh
        return y


def png_bytes(canvas):
    """Deterministic RGB PNG: per-row best filter, fixed zlib level."""
    w, h = canvas.w, canvas.h
    raw = bytearray()
    prev = bytes(w * 3)
    for y in range(h):
        row = bytes(canvas.px[y * w * 3:(y + 1) * w * 3])
        cands = []
        cands.append((0, row))
        sub = bytes((row[i] - (row[i - 3] if i >= 3 else 0)) & 0xFF
                    for i in range(len(row)))
        cands.append((1, sub))
        up = bytes((row[i] - prev[i]) & 0xFF for i in range(len(row)))
        cands.append((2, up))

        def cost(buf):
            return sum(b if b < 128 else 256 - b for b in buf)

        best = min(cands, key=lambda c: cost(c[1]))
        raw.append(best[0])
        raw += best[1]
        prev = row
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def load_tiles():
    """Find hero.bin next to this script, the cwd, or /bot; unpack tiles."""
    cands = []
    try:
        cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "hero.bin"))
    except NameError:
        pass
    cands.append(os.path.join(os.getcwd(), "hero.bin"))
    cands.append("/bot/hero.bin")
    for path in cands:
        if os.path.exists(path):
            with open(path, "rb") as fh:
                raw = zlib.decompress(fh.read())
            need = 6 * TILE * TILE * 3
            if len(raw) != need:
                raise ValueError("hero.bin holds %d bytes, want %d"
                                 % (len(raw), need))
            step = TILE * TILE * 3
            return [raw[i * step:(i + 1) * step] for i in range(6)]
    raise FileNotFoundError("hero.bin not found beside main.py")


# --- The day's stories: every line traced to reporting of 20 Nov 2026. ---
HERO_KICKER = "THE SUMMIT | SHENZHEN, CHINA"
HERO_HEAD = "TRUMP, XI AND PUTIN\nSIGN PEACE DECLARATION"
HERO_BRIEF = ("The three leaders issue a four-point declaration: UN reform, "
              "more refined fuel, court immunity, and a nuclear-risk "
              "dialogue. It names neither Ukraine nor Iran.")
HERO_FOOT = "FIRST TRILATERAL MEETING OF THE THREE NUCLEAR POWERS."

CARDS = [
    ("THE HAGUE", "MYANMAR COMMITTED\nGENOCIDE",
     "ICJ orders reparations; 10,000 killed in 2017."),
    ("KYIV", "KYIV HIT; MISSILES\nLAND IN POLAND",
     "400 drones, 110 missiles; 8 killed, grid cut."),
    ("KERCH STRAIT", "UKRAINE STRIKES\nKERCH BRIDGE AGAIN",
     "Neptune missiles hit road and rail; one track open."),
    ("MARKETS", "ANTHROPIC IPO RAISES\n$81 BILLION",
     "Largest IPO ever; shares open 33% above offer."),
    ("ANTALYA, TURKIYE", "CLIMATE TALKS STALL\nON FOSSIL FUELS",
     "COP31 draft deadlocked; activists denounce it."),
]

NUMBERS = [
    ("400+", "DRONES AND MISSILES FIRED AT UKRAINE"),
    ("30", "KILLED IN KRAMATORSK BUS STRIKE"),
    ("9 HRS", "MICROSOFT OUTAGE, WORLDWIDE"),
    ("$190.4M", "RECORD PRICE: VAN GOGH"),
]

ALSO_1 = ("ALSO: EU-UK SUMMIT IN BRUSSELS | HUNGARY LIFTS UKRAINE VETO "
          "| GREENLAND-US DEAL")
ALSO_2 = ("DUTCH EMBASSY DAMAGED IN KYIV | MICROSOFT OUTAGE: 9 HOURS "
          "| TAIWAN SCRAMBLES JETS")
SOURCES = "SOURCES: THE TIMES, CNN, WSJ, FOX NEWS, HRW, LE MONDE, IIMM - 20 NOV 2026"


def draw_card(cv, x, y, w, h, tile, kicker, head, brief, band_y=54):
    cv.rect(x, y, w, h, CARD)
    cv.rect(x, y, w, 2, INK)
    cv.blit(tile, 0, band_y, TILE, 180, x + 8, y + 10, w - 16, 116)
    ty = y + 134
    cv.text(x + 8, ty, kicker, 2, RED)
    ty += 18
    for line in cv.wrap(head, w - 16, 3):
        cv.text(x + 8, ty, line, 3, INK)
        ty += 25
    ty += 4
    cv.para(x + 8, ty, brief, w - 16, 2, INK, lh=15)


def draw_page():
    tiles = load_tiles()
    cv = Canvas(W, H, PAPER)

    # Masthead.
    cv.text(14, 12, "VOL. I | NO. 325", 2, GRAY)
    right = "FRIDAY EDITION"
    cv.text(W - 14 - cv.text_w(right, 2), 12, right, 2, GRAY)
    title = "THE WORLD IN ONE IMAGE"
    cv.text((W - cv.text_w(title, 6)) // 2, 28, title, 6, INK)
    sub = "FRIDAY, 20 NOVEMBER 2026 | THE DAY IN FULL"
    cv.text((W - cv.text_w(sub, 2)) // 2, 76, sub, 2, RED)
    cv.hline(14, 94, W - 28, RULE, 3)
    cv.hline(14, 99, W - 28, RULE, 1)

    # Hero: the Shenzhen panel, big, with the day's lead story.
    hy = 108
    cv.blit(tiles[0], 0, 0, TILE, TILE, 14, hy, 280, 280)
    cv.rect(14, hy, 280, 3, RED)
    tx = 306
    cv.text(tx, hy + 6, HERO_KICKER, 2, RED)
    yy = hy + 30
    for line in cv.wrap(HERO_HEAD, W - 14 - tx, 5):
        cv.text(tx, yy, line, 5, INK)
        yy += 42
    yy += 6
    yy = cv.para(tx, yy, HERO_BRIEF, W - 14 - tx, 2, INK, lh=16)
    cv.hline(tx, hy + 248, W - 14 - tx, GOLD, 2)
    cv.text(tx, hy + 256, HERO_FOOT, 2, GRAY)

    # Card grid: five illustrated stories plus the numbers box.
    gx, gy = 14, 400
    cw, ch, gap = 324, 264, 12
    for i in range(3):
        draw_card(cv, gx + i * (cw + gap), gy, cw, ch, tiles[1 + i],
                  CARDS[i][0], CARDS[i][1], CARDS[i][2])
    for i in range(3, 5):
        draw_card(cv, gx + (i - 3) * (cw + gap), gy + ch + gap, cw, ch,
                  tiles[1 + i], CARDS[i][0], CARDS[i][1], CARDS[i][2],
                  band_y=84 if i == 3 else 54)
    # Numbers box in the sixth slot.
    nx = gx + 2 * (cw + gap)
    ny = gy + ch + gap
    cv.rect(nx, ny, cw, ch, NAVY)
    cv.text(nx + 12, ny + 12, "BY THE NUMBERS", 2, GOLD)
    cv.hline(nx + 12, ny + 32, cw - 24, GOLD, 2)
    yy = ny + 42
    for num, label in NUMBERS:
        cv.text(nx + 12, yy, num, 3, WHITE)
        cv.para(nx + 12, yy + 25, label, cw - 24, 2, GOLD, lh=14)
        yy += 58

    # Foot: more of the day, and the sources.
    fy = 952
    cv.hline(14, fy, W - 28, RULE, 3)
    cv.text(14, fy + 10, ALSO_1, 2, INK)
    cv.text(14, fy + 28, ALSO_2, 2, INK)
    cv.text(14, fy + 46, SOURCES, 2, GRAY)
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    data = png_bytes(draw_page())
    with open(os.path.join(outdir, "entry.png"), "wb") as fh:
        fh.write(data)
    print("wrote %d bytes" % len(data))


if __name__ == "__main__":
    main()

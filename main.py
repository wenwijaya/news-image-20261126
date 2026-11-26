#!/usr/bin/env python3
"""news-image-20261126 -- sum up Thursday 26 November 2026 world news in
one 1024x1024 newspaper-front-page image.

Pure Python 3 standard library only: no pip packages, no network at runtime.
Hand-written PNG encoder (zlib + struct + CRC32). Deterministic: the same
bytes on every run. Writes entry.png into $MAKEFUN_OUTPUT_DIR (default
/output) and chmods it 0644. Exits 0 even if a render step throws.

Stories depicted (all reported on 25-26 November 2026):
  1. US announces sweeping new tariffs on China, Japan, the EU and others
     (Taiwan faces up to 15%).
  2. Houthis claim strikes on Saudi Arabia's Ras Tanura refinery; Brent
     crude tops $94.
  3. First Pakistani astronaut journeys to China's Tiangong space station.
  4. Close-up images reveal the stadium-sized crater left by Earth's
     asteroid-defence test.
  5. Fuel tanker crash ignites a huge fire on a Cairo highway; at least
     30 killed.
  6. Russia's own figures point to nearly 500,000 dead in the Ukraine war.
Ticker: Duran Duran guitarist Andy Taylor dies at 65; Colombia marks ten
years since its peace deal; US stocks fall as AI fears grow.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- colours
PAPER = (247, 243, 232)   # newsprint off-white
INK = (18, 18, 18)        # near-black
PANEL = (255, 255, 255)   # panel face
MUTED = (90, 86, 76)      # grey-brown for sub text
RULE = (18, 18, 18)
RED = (178, 34, 34)
NAVY = (28, 52, 96)
TEAL = (18, 110, 110)
GOLD = (198, 142, 28)
SKY = (214, 230, 242)
SAND = (238, 226, 200)
ORANGE = (224, 110, 20)
FLAME = (240, 150, 30)
GREY = (120, 120, 118)
DARK = (38, 38, 44)
WHITE = (255, 255, 255)
GREEN = (46, 125, 60)

# ------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 bits ("1" = ink). Uppercase + digits + punctuation.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
}
BLANK = ("00000",) * 7


def text_width(text, scale):
    """Pixel width of text at the given scale (no trailing advance)."""
    if not text:
        return 0
    return len(text) * 6 * scale - scale


def wrap_text(text, max_w, scale):
    """Greedy word wrap; returns a list of lines that fit max_w pixels."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if text_width(trial, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        self.fill(bg)

    def fill(self, color):
        r, g, b = color
        self.buf[:] = bytes((r, g, b)) * (self.w * self.h)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = color

    def rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = color
        row = bytes((r, g, b)) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + len(row)] = row

    def border(self, x, y, w, h, color, t=2):
        self.rect(x, y, w, t, color)
        self.rect(x, y + h - t, w, t, color)
        self.rect(x, y, t, h, color)
        self.rect(x + w - t, y, t, h, color)

    def hline(self, x0, x1, y, color, t=1):
        self.rect(x0, y, x1 - x0, t, color)

    def vline(self, x, y0, y1, color, t=1):
        self.rect(x, y0, t, y1 - y0, color)

    def circle(self, cx, cy, r, color):
        # Filled circle, midpoint scanlines.
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        # Bresenham, with thickness t.
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.rect(x - t // 2, y - t // 2, t, t, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def triangle(self, p1, p2, p3, color):
        # Filled triangle via scanline interpolation.
        pts = sorted([p1, p2, p3], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        if ay == cy:
            return
        def interp(y, p, q):
            if p[1] == q[1]:
                return p[0]
            return p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1])
        for y in range(ay, cy + 1):
            if y < by:
                xa = interp(y, (ax, ay), (bx, by))
            else:
                xa = interp(y, (bx, by), (cx, cy))
            xb = interp(y, (ax, ay), (cx, cy))
            if xa > xb:
                xa, xb = xb, xa
            self.rect(int(xa), y, int(xb) - int(xa) + 1, 1, color)

    def text(self, x, y, s, scale, color):
        """Draw text at scale; s is uppercased (font is uppercase-only)."""
        cx = x
        for ch in s.upper():
            glyph = FONT.get(ch, BLANK)
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx

    def text_center(self, cx, y, s, scale, color):
        self.text(cx - text_width(s, scale) // 2, y, s, scale, color)


# ---------------------------------------------------------------- scenes
# Each scene draws inside the box (x, y, w, h) at the top of its panel.
# Simple flat geometric pictures: bar chart, oil derrick, rocket, asteroid,
# tanker fire, broken skyline.

def scene_tariffs(cv, x, y, w, h):
    cv.rect(x, y, w, h, SKY)
    # Rising bars, one red (the new tariff jump).
    base = y + h - 14
    bars = [(26, 26), (66, 40), (106, 34), (146, 50), (186, 68)]
    for i, (bx, bh) in enumerate(bars):
        col = RED if i == len(bars) - 1 else NAVY
        cv.rect(x + bx, base - bh, 28, bh, col)
    # Upward arrow over the bars, kept inside the scene box.
    ax0, ay0 = x + 14, base - 6
    ax1, ay1 = x + w - 112, y + 16
    cv.line(ax0, ay0, ax1, ay1, RED, 4)
    cv.line(ax1, ay1, ax1 - 18, ay1 + 2, RED, 4)
    cv.line(ax1, ay1, ax1 - 2, ay1 + 16, RED, 4)
    cv.text(x + w - 92, y + 8, "%", 3, RED)


def scene_oil(cv, x, y, w, h):
    cv.rect(x, y, w, h, SAND)
    # Sun / price disc.
    cv.circle(x + w - 46, y + 26, 20, GOLD)
    cv.text(x + w - 62, y + 17, "$94", 2, INK)
    # Derrick: two legs, cross braces, top beam.
    dx, dy = x + 60, y + 12
    cv.line(dx, dy + 72, dx + 22, dy, DARK, 5)
    cv.line(dx + 44, dy + 72, dx + 22, dy, DARK, 5)
    cv.line(dx + 8, dy + 52, dx + 36, dy + 52, DARK, 3)
    cv.line(dx + 12, dy + 32, dx + 32, dy + 32, DARK, 3)
    cv.rect(dx + 16, dy - 6, 12, 8, DARK)
    # Flame at the flare stack.
    cv.triangle((x + 150, y + 84), (x + 162, y + 44), (x + 174, y + 84), FLAME)
    cv.triangle((x + 156, y + 84), (x + 162, y + 62), (x + 168, y + 84), GOLD)
    cv.rect(x + 152, y + 84, 20, 8, DARK)
    # Barrel.
    cv.rect(x + 196, y + 52, 34, 40, (120, 60, 20))
    cv.rect(x + 196, y + 60, 34, 3, INK)
    cv.rect(x + 196, y + 80, 34, 3, INK)
    cv.text(x + 200, y + 64, "OIL", 1, WHITE)


def scene_space(cv, x, y, w, h):
    cv.rect(x, y, w, h, (16, 24, 52))
    # Stars.
    for sx, sy in [(18, 12), (52, 30), (96, 10), (150, 22), (196, 12),
                   (30, 62), (78, 52), (128, 66), (170, 50), (210, 68)]:
        cv.rect(x + sx, y + sy, 3, 3, WHITE)
    # Ringed planet.
    cv.circle(x + 196, y + 30, 16, TEAL)
    cv.line(x + 172, y + 22, x + 220, y + 38, GOLD, 3)
    # Rocket: body, nose, fins, flame.
    rx, ry = x + 96, y + 16
    cv.rect(rx, ry + 12, 18, 42, WHITE)
    cv.triangle((rx, ry + 12), (rx + 18, ry + 12), (rx + 9, ry - 2), RED)
    cv.triangle((rx, ry + 54), (rx - 10, ry + 68), (rx, ry + 50), RED)
    cv.triangle((rx + 18, ry + 54), (rx + 28, ry + 68), (rx + 18, ry + 50), RED)
    cv.circle(rx + 9, ry + 26, 4, NAVY)
    cv.triangle((rx + 3, ry + 54), (rx + 15, ry + 54), (rx + 9, ry + 78), FLAME)
    # Station: small ring + module.
    cv.rect(x + 40, y + 74, 52, 10, (180, 180, 190))
    cv.rect(x + 58, y + 66, 16, 26, (200, 200, 210))
    cv.line(x + 40, y + 79, x + 22, y + 79, GOLD, 3)
    cv.line(x + 92, y + 79, x + 110, y + 79, GOLD, 3)


def scene_asteroid(cv, x, y, w, h):
    cv.rect(x, y, w, h, (22, 22, 30))
    for sx, sy in [(14, 10), (60, 22), (120, 8), (180, 18), (210, 52),
                   (40, 70), (90, 80), (150, 74)]:
        cv.rect(x + sx, y + sy, 3, 3, WHITE)
    # The asteroid, grey with craters; one big fresh crater.
    cv.circle(x + 118, y + 50, 36, (150, 146, 138))
    cv.circle(x + 106, y + 40, 7, (110, 106, 100))
    cv.circle(x + 134, y + 62, 5, (110, 106, 100))
    cv.circle(x + 126, y + 34, 4, (110, 106, 100))
    cv.circle(x + 118, y + 52, 13, (96, 90, 84))
    cv.circle(x + 118, y + 52, 8, (70, 66, 60))
    # Impact flash + probe trail.
    cv.line(x + 40, y + 14, x + 88, y + 34, GOLD, 3)
    cv.circle(x + 88, y + 34, 4, GOLD)
    cv.circle(x + 40, y + 14, 3, WHITE)


def scene_fire(cv, x, y, w, h):
    cv.rect(x, y, w, h, (40, 32, 28))
    # Smoke.
    cv.circle(x + 60, y + 22, 14, GREY)
    cv.circle(x + 84, y + 14, 18, (150, 150, 148))
    cv.circle(x + 112, y + 24, 12, GREY)
    # Flames over the tanker.
    cv.triangle((x + 30, y + 92), (x + 52, y + 34), (x + 74, y + 92), FLAME)
    cv.triangle((x + 62, y + 92), (x + 86, y + 44), (x + 110, y + 92), ORANGE)
    cv.triangle((x + 96, y + 92), (x + 116, y + 52), (x + 136, y + 92), FLAME)
    cv.triangle((x + 52, y + 92), (x + 66, y + 66), (x + 80, y + 92), GOLD)
    # Tanker truck: cab + tank + wheels.
    cv.rect(x + 150, y + 58, 66, 34, (200, 200, 200))
    cv.rect(x + 150, y + 66, 66, 3, INK)
    cv.rect(x + 150, y + 82, 66, 3, INK)
    cv.rect(x + 216, y + 66, 22, 26, RED)
    cv.rect(x + 220, y + 70, 12, 10, SKY)
    cv.circle(x + 166, y + 92, 8, INK)
    cv.circle(x + 196, y + 92, 8, INK)
    cv.circle(x + 226, y + 92, 8, INK)


def scene_war(cv, x, y, w, h):
    cv.rect(x, y, w, h, (226, 222, 214))
    # Broken skyline silhouettes.
    cv.rect(x + 18, y + 44, 34, 52, DARK)
    cv.triangle((x + 18, y + 44), (x + 35, y + 30), (x + 52, y + 44), DARK)
    cv.rect(x + 62, y + 28, 30, 68, (70, 70, 78))
    cv.triangle((x + 62, y + 28), (x + 77, y + 16), (x + 92, y + 28), (70, 70, 78))
    cv.rect(x + 102, y + 58, 40, 38, DARK)
    # Windows, some dark.
    for wx in (26, 38):
        for wy in (54, 66, 78):
            cv.rect(x + wx, y + wy, 5, 6, GOLD)
    for wx in (68, 80):
        for wy in (40, 54, 70):
            cv.rect(x + wx, y + wy, 5, 6, GOLD)
    # The toll, big and plain.
    cv.text(x + 168, y + 18, "500,000", 3, RED)
    cv.text(x + 168, y + 46, "DEAD", 3, INK)
    cv.text(x + 168, y + 72, "PER MOSCOW'S", 1, MUTED)
    cv.text(x + 168, y + 84, "OWN FIGURES", 1, MUTED)


SCENES = {
    "tariffs": scene_tariffs,
    "oil": scene_oil,
    "space": scene_space,
    "asteroid": scene_asteroid,
    "fire": scene_fire,
    "war": scene_war,
}

# ------------------------------------------------------------- the stories
STORIES = [
    {
        "tag": "TRADE", "scene": "tariffs",
        "headline": "US UNVEILS SWEEPING NEW TARIFFS",
        "body": "Washington announces new duties on China, Japan, the EU and others. Taiwan faces up to 15%.",
    },
    {
        "tag": "ENERGY", "scene": "oil",
        "headline": "HOUTHIS CLAIM SAUDI REFINERY STRIKE",
        "body": "Brent crude tops $94 as Yemen's Houthis say they hit Ras Tanura and a Riyadh tower.",
    },
    {
        "tag": "SPACE", "scene": "space",
        "headline": "FIRST PAKISTANI ASTRONAUT REACHES TIANGONG",
        "body": "China's Shenzhou-24 carries Pakistan's first astronaut to its space station.",
    },
    {
        "tag": "SCIENCE", "scene": "asteroid",
        "headline": "ASTEROID DEFENCE TEST LEAVES STADIUM CRATER",
        "body": "Close-up images reveal the crater left by the spacecraft that struck an asteroid.",
    },
    {
        "tag": "DISASTER", "scene": "fire",
        "headline": "CAIRO TANKER FIRE KILLS AT LEAST 30",
        "body": "A fuel tanker crash ignites a huge fire on a highway around the Egyptian capital.",
    },
    {
        "tag": "WAR", "scene": "war",
        "headline": "RUSSIA'S WAR TOLL NEARS 500,000",
        "body": "Moscow's own figures point to almost half a million dead in the Ukraine war.",
    },
]

TICKER = ("ALSO TODAY: DURAN DURAN GUITARIST ANDY TAYLOR DIES AT 65 - "
          "COLOMBIA MARKS 10 YEARS SINCE PEACE DEAL - "
          "US STOCKS FALL AS AI FEARS GROW")


# ---------------------------------------------------------------- layout
def draw_panel(cv, px, py, pw, ph, story):
    cv.rect(px, py, pw, ph, PANEL)
    cv.border(px, py, pw, ph, INK, 3)
    inner = 12
    sx, sy = px + inner, py + inner
    sw, sh = pw - 2 * inner, 118
    # Scene strip.
    SCENES[story["scene"]](cv, sx, sy, sw, sh)
    cv.border(sx, sy, sw, sh, INK, 2)
    # Tag chip, top-left over the scene.
    tag = story["tag"]
    tw = text_width(tag, 1) + 12
    cv.rect(sx + 6, sy + 6, tw, 13, INK)
    cv.text(sx + 12, sy + 9, tag, 1, WHITE)
    # Headline, scale 2, wrapped to two lines max.
    hy = sy + sh + 12
    maxw = pw - 2 * inner
    lines = wrap_text(story["headline"], maxw, 2)[:2]
    for i, ln in enumerate(lines):
        cv.text(px + inner, hy + i * 18, ln, 2, INK)
    # Body, scale 1, up to three lines.
    by = hy + len(lines) * 18 + 6
    blines = wrap_text(story["body"], maxw, 1)[:3]
    for i, ln in enumerate(blines):
        cv.text(px + inner, by + i * 11, ln, 1, MUTED)


def render():
    cv = Canvas(W, H, PAPER)
    # Masthead.
    cv.hline(24, W - 24, 10, RULE, 3)
    cv.text_center(W // 2, 22, "THE WORLD TODAY", 4, INK)
    cv.text_center(W // 2, 62, "THURSDAY 26 NOVEMBER 2026", 3, RED)
    cv.hline(24, W - 24, 92, RULE, 3)
    cv.hline(24, W - 24, 97, RULE, 1)
    cv.text_center(W // 2, 106, "THE DAY'S WORLD NEWS IN ONE IMAGE", 1, MUTED)
    # Six panels: 2 columns x 3 rows.
    pw, ph = 480, 250
    gap_x, gap_y = 16, 14
    top = 126
    for i, story in enumerate(STORIES):
        px = 24 + (i % 2) * (pw + gap_x)
        py = top + (i // 2) * (ph + gap_y)
        draw_panel(cv, px, py, pw, ph, story)
    # Ticker strip.
    ty = top + 3 * ph + 2 * gap_y + 12
    cv.hline(24, W - 24, ty, RULE, 3)
    tlines = wrap_text(TICKER, W - 48, 1)
    for i, ln in enumerate(tlines):
        cv.text(24, ty + 10 + i * 11, ln, 1, INK)
    cv.hline(24, W - 24, H - 12, RULE, 3)
    return cv


# ------------------------------------------------------------ PNG encoder
def png_bytes(w, h, rgb):
    def chunk(ctype, data):
        body = ctype + data
        return (struct.pack(">I", len(data)) + body +
                struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3]
                   for y in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def fallback_image():
    """Minimal valid image if the full render throws: date + one line."""
    cv = Canvas(W, H, PAPER)
    cv.text_center(W // 2, 400, "26 NOVEMBER 2026", 4, INK)
    cv.text_center(W // 2, 460, "THE WORLD TODAY", 2, RED)
    return cv


# ------------------------------------------------------------------ main
def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(outdir, exist_ok=True)
    except Exception:
        outdir = "."
    try:
        cv = render()
    except Exception:
        cv = fallback_image()
    data = png_bytes(W, H, bytes(cv.buf))
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    try:
        os.chmod(path, 0o644)
        os.chmod(outdir, 0o755)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Sum up the world's news of Friday 20 November 2026 in one image.

Draws a newspaper front page (masthead, dated lead story, four more
stories and a briefs strip) with a tiny built-in bitmap font and simple
shape drawings, and writes it to /output/entry.png as a PNG.
Pure standard library, no network, deterministic output.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

PAPER = (246, 241, 227)
INK = (20, 22, 26)
RED = (163, 22, 33)
BLUE = (29, 78, 137)
GRAY = (96, 101, 110)
LIGHT = (222, 214, 192)
WHITE = (255, 255, 255)
GOLD = (214, 164, 32)
SKY = (168, 198, 224)

# ---------------------------------------------------------------- font
# 5x7 bitmap glyphs, rows top to bottom, '#' is ink.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".##..", ".##..", ".#...", "#...."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "%": ("##..#", "##.#.", "....#", "...#.", "..#..", ".#.##", "#..##"),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
}


def text_w(s, scale):
    return len(s) * 6 * scale - scale


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def frame(self, x, y, w, h, c, t=3):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=2):
        dx, dy = x1 - x0, y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        for i in range(steps + 1):
            x = x0 + dx * i // steps
            y = y0 + dy * i // steps
            r = max(t // 2, 1)
            self.rect(x - r, y - r, 2 * r, 2 * r, c)

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill and d2 <= r * r:
                    self.set(xx, yy, c)
                elif not fill and r * r - 2 * r <= d2 <= r * r + 2 * r:
                    self.set(xx, yy, c)

    def text(self, x, y, s, scale, c):
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                for col in range(5):
                    if glyph[row][col] == "#":
                        self.rect(x + col * scale, y + row * scale, scale, scale, c)
            x += 6 * scale
        return x

    def text_c(self, cx, y, s, scale, c):
        return self.text(cx - text_w(s, scale) // 2, y, s, scale, c)

    def text_r(self, xr, y, s, scale, c):
        return self.text(xr - text_w(s, scale), y, s, scale, c)


def wrap(s, scale, max_w):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if text_w(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def para(cv, x, y, s, scale, c, max_w, leading=None):
    leading = leading or (9 * scale)
    for ln in wrap(s, scale, max_w):
        cv.text(x, y, ln, scale, c)
        y += leading
    return y


# ---------------------------------------------------------------- scenes
def flag_us(cv, x, y, w, h):
    sh = h // 7
    for i in range(7):
        cv.rect(x, y + i * sh, w, sh, RED if i % 2 == 0 else WHITE)
    cv.rect(x, y, w * 2 // 5, sh * 4, BLUE)
    for r in range(4):
        for c_ in range(5):
            cv.circle(x + 8 + c_ * (w * 2 // 5 - 12) // 4, y + 6 + r * (sh * 4 - 10) // 3, 2, WHITE)


def flag_cn(cv, x, y, w, h):
    cv.rect(x, y, w, h, RED)
    star(cv, x + w // 5, y + h // 4, 9, GOLD)
    for dx, dy in ((w // 3, h // 10), (w // 3, h // 4), (w // 3, h * 2 // 5)):
        star(cv, x + dx, y + dy, 4, GOLD)


def flag_ru(cv, x, y, w, h):
    t = h // 3
    cv.rect(x, y, w, t, WHITE)
    cv.rect(x, y + t, w, t, BLUE)
    cv.rect(x, y + 2 * t, w, h - 2 * t, RED)


def star(cv, cx, cy, r, c):
    for i in range(5):
        a1 = -math.pi / 2 + i * 2 * math.pi / 5
        a2 = a1 + math.pi / 5
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        x2, y2 = cx + (r // 2) * math.cos(a2), cy + (r // 2) * math.sin(a2)
        cv.line(int(x1), int(y1), int(x2), int(y2), c, 3)
    cv.circle(cx, cy, max(r // 3, 2), c)


def scene_summit(cv, x, y, w, h):
    # three flags on poles above a table, three seated figures
    fw, fh = 92, 58
    xs = [x + 8, x + w // 2 - fw // 2, x + w - fw - 8]
    for fx, draw in zip(xs, (flag_us, flag_cn, flag_ru)):
        cv.rect(fx + fw // 2 - 2, y, 4, h - 60, GRAY)
        draw(cv, fx, y + 2, fw, fh)
    ty = y + h - 62
    cv.rect(x + 4, ty, w - 8, 14, INK)
    for fx in xs:
        cx = fx + fw // 2
        cv.circle(cx, ty - 26, 13, INK)
        cv.rect(cx - 17, ty - 14, 34, 16, INK)


def scene_scales(cv, x, y, w, h):
    cx = x + w // 2
    top = y + 10
    cv.rect(cx - 3, top, 6, h - 40, INK)
    cv.line(cx - w // 3, top + 14, cx + w // 3, top + 14, INK, 6)
    cv.circle(cx, top + 6, 8, GOLD)
    for sx in (cx - w // 3, cx + w // 3):
        cv.line(sx, top + 14, sx - 26, top + 62, INK, 3)
        cv.line(sx, top + 14, sx + 26, top + 62, INK, 3)
        for px_ in range(sx - 30, sx + 31):
            py_ = top + 62 + int(10 * (1 - (px_ - sx) ** 2 / 900.0))
            cv.line(px_, py_, px_, py_ + 3, INK, 3)
    cv.rect(cx - 34, y + h - 22, 68, 8, INK)
    cv.rect(cx - 20, y + h - 32, 40, 10, INK)


def scene_cyclone(cv, x, y, w, h):
    cx, cy = x + w // 2, y + h // 2 - 6
    for i in range(330):
        t = i / 30.0
        r = 3 + t * 5.2
        px_ = cx + int(r * math.cos(t))
        py_ = cy + int(r * math.sin(t) * 0.82)
        cv.circle(px_, py_, 4, BLUE if i % 3 else INK)
    cv.circle(cx, cy, 6, PAPER)
    base = y + h - 10
    for i in range(0, w - 20, 26):
        for k in range(2):
            cv.line(x + i + k * 10, base - (i // 26 % 2) * 4, x + i + 10 + k * 10, base - 8 - (i // 26 % 2) * 4, BLUE, 3)


def scene_tower(cv, x, y, w, h):
    tx, tw = x + w // 2 - 26, 52
    cv.rect(tx, y + 6, tw, h - 12, INK)
    for r in range(9):
        for c_ in range(3):
            lit = (r * 3 + c_) % 4 != 0
            cv.rect(tx + 8 + c_ * 14, y + 16 + r * ((h - 40) // 9), 8, 10, GOLD if lit else GRAY)
    for a in range(12):
        ang = a * math.pi / 6
        x1 = tx + tw + 8 + int(6 * math.cos(ang))
        y1 = y + 34 + int(6 * math.sin(ang))
        x2 = tx + tw + 8 + int(20 * math.cos(ang))
        y2 = y + 34 + int(20 * math.sin(ang))
        cv.line(x1, y1, x2, y2, RED, 3)
    for i in range(9):
        cv.circle(x + 14 + i * 9, y + h - 30 - i * 11, 3, RED)


def scene_missile(cv, x, y, w, h):
    cx, cy = x + w // 2, y + h // 2
    cv.circle(cx, cy, 44, BLUE, fill=False)
    for dx, dy in ((0, -52), (0, 52), (-52, 0), (52, 0)):
        cv.line(cx, cy, cx + dx, cy + dy, BLUE, 5)
    cv.circle(cx, cy, 9, BLUE)
    for i in range(8):
        cv.circle(x + 18 + i * 10, y + 16 + i * 9, 3, RED)
    bx, by = x + 100, y + 92
    for a in range(10):
        ang = a * math.pi / 5
        cv.line(bx, by, bx + int(22 * math.cos(ang)), by + int(22 * math.sin(ang)), RED, 3)


def panel(cv, x, y, w, h, kicker, head_lines, sub, scene, scale=3):
    cv.frame(x, y, w, h, INK, 3)
    cv.text(x + 16, y + 12, kicker, 2, RED)
    hy = y + 40
    for ln in head_lines:
        cv.text(x + 16, hy, ln, scale, INK)
        hy += 8 * scale + 2
    if scene:
        scene(cv, x + w - 164, y + 36, 148, h - 48)
    if sub:
        para(cv, x + 16, hy + 4, sub, 2, GRAY, w - 196)


# ---------------------------------------------------------------- build
def build():
    cv = Canvas(W, H, PAPER)
    # masthead
    cv.rect(24, 22, W - 48, 5, INK)
    cv.text_c(W // 2, 40, "THE WORLD TODAY", 10, INK)
    cv.rect(24, 122, W - 48, 3, INK)
    cv.text(24, 136, "GLOBAL EDITION", 2, GRAY)
    cv.text_c(W // 2, 132, "FRIDAY 20 NOVEMBER 2026", 4, RED)
    cv.text_r(W - 24, 136, "ONE IMAGE", 2, GRAY)
    cv.rect(24, 168, W - 48, 5, INK)

    # lead story: Shenzhen trilateral summit
    x, y, w, h = 24, 186, W - 48, 272
    cv.frame(x, y, w, h, INK, 4)
    cv.text(x + 20, y + 14, "SHENZHEN SUMMIT - DIPLOMACY", 3, RED)
    cv.text(x + 20, y + 52, "THREE POWERS ISSUE", 6, INK)
    cv.text(x + 20, y + 106, "JOINT PEACE CALL", 6, INK)
    para(cv, x + 20, y + 168,
         "TRUMP, XI AND PUTIN MEET FACE TO FACE IN SHENZHEN AND SIGN A JOINT "
         "DECLARATION. GERMANY WARNS EUROPE WILL NOT ACCEPT A NEW YALTA "
         "SETTLED OVER ITS HEAD.", 2, GRAY, 560)
    scene_summit(cv, x + w - 330, y + 112, 300, 150)

    # row of two: ICJ and cyclone
    y2 = 474
    panel(cv, 24, y2, 480, 236, "THE HAGUE - WORLD COURT",
          ["MYANMAR", "RESPONSIBLE", "FOR ROHINGYA", "GENOCIDE"],
          "THE WORLD COURT RULES MYANMAR FORCES COMMITTED "
          "GENOCIDE ON THE ROHINGYA.", scene_scales, scale=3)
    panel(cv, 520, y2, 480, 236, "INDIA - BAY OF BENGAL",
          ["CYCLONE AKVAN", "SLAMS ODISHA", "COAST"],
          "THE STORM CROSSES THE COAST NEAR GOPALPUR. ABOUT 372000 "
          "PEOPLE WERE EVACUATED AHEAD OF LANDFALL.", scene_cyclone, scale=3)

    # row of two: Riyadh and Poland
    y3 = 726
    panel(cv, 24, y3, 480, 168, "SAUDI ARABIA",
          ["MISSILE HITS", "RIYADH TOWER"],
          "HOUTHI MISSILE BLASTS WINDOWS ACROSS EIGHT "
          "FLOORS OF THE TOWER.", scene_tower, scale=3)
    panel(cv, 520, y3, 480, 168, "POLAND - NATO",
          ["RUSSIAN MISSILES", "FALL IN POLAND"],
          "WARSAW: DELIBERATE PROVOCATION. NATO: GRAVE "
          "AIRSPACE VIOLATION.", scene_missile, scale=3)

    # briefs strip
    y4 = 910
    cv.rect(24, y4 - 8, W - 48, 3, INK)
    briefs = [
        ("MARKETS", "AI SELL-OFF: S&P 500 -3.7%, NIKKEI -5.1%"),
        ("IRAN", "TRUMP IN NO RUSH ON NEW STRIKES, EYES 2027"),
        ("SPACE", "VOYAGER 1 NOW ONE LIGHT-DAY FROM EARTH"),
        ("HAITI", "34 GANG SUSPECTS KILLED BY POLICE"),
    ]
    bw = (W - 48) // 4
    for i, (kick, txt) in enumerate(briefs):
        bx = 24 + i * bw
        if i:
            cv.rect(bx - 8, y4 + 2, 2, 84, LIGHT)
        cv.text(bx + 4, y4 + 2, kick, 2, BLUE)
        para(cv, bx + 4, y4 + 28, txt, 2, INK, bw - 20)
    return cv


def png_bytes(cv):
    raw = bytearray()
    row = cv.w * 3
    for yy in range(cv.h):
        raw.append(0)
        raw += cv.px[yy * row:(yy + 1) * row]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def main():
    data = png_bytes(build())
    out = "/output/entry.png"
    try:
        os.makedirs("/output", exist_ok=True)
    except OSError:
        out = os.path.join("output", "entry.png")
        os.makedirs("output", exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    try:
        os.chmod(out, 0o644)
    except OSError:
        pass


if __name__ == "__main__":
    main()

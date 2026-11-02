"""The accent colour of the iPod software (reference version).

Apple's firmware uses one blue for the selection bar and for some pictures. This module changes
that blue to the colour of the owner. The Swift version is `Accent.swift`. The two versions use
the same steps and the same rounding, so that the tests can compare them.

- The selection bar of the Views is a gradient of two colours (APPLE_BOTTOM and APPLE_TOP). The
  gradient gets the new colour at the top and 0.8 times the new colour at the bottom. No channel of
  the top colour is larger than 232, as in Apple's blue.
- The pictures in ACCENT_PICTURES hold Apple's blue (the rating star, a button of the Stopwatch,
  the selected cell of the Screen Lock, the ring of the balls of Brick and so on). Each saturated pixel gets the hue, the saturation and the brightness of the new colour in
  proportion to Apple's blue.

The accent #5898e8 is Apple's blue. With this accent nothing changes.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass

from . import pictures, resources
from .themeimport import Change, Theme, ThemeError, _with_copied_bytes, apply_theme

APPLE_ACCENT = "#5898e8"
APPLE_TOP = bytes.fromhex("5898e8ff")
APPLE_BOTTOM = bytes.fromhex("2864d0ff")

# The pictures of Apple's firmware 1.3 that hold the accent blue.
ACCENT_PICTURES = (13981, 13982, 24279, 24403, 24404, 24405, 24406, 24407, 24408, 24409,
                   25043, 25045, 25046, 25560, 25562,
                   24361, 24362, 24363, 24364, 24365, 24366,
                   22206, 24394)

SAT_MIN, VAL_MIN = 0.35, 0.15
# The largest channel of the top colour of the selection bar. Apple's blue has 232 (0xe8). The owner saw
# yellow pixels at the top of a red bar (255, 69, 58): the code that draws the bar needs room above the colour.
MAX_CHANNEL = 232


class AccentError(ThemeError):
    pass


def parse_hex(text: str) -> tuple[int, int, int]:
    s = text.strip().lstrip("#")
    if len(s) != 6 or any(c not in "0123456789abcdefABCDEF" for c in s):
        raise AccentError(f"The accent colour must have the form #RRGGBB, not \"{text}\".")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def is_apple(text: str) -> bool:
    return parse_hex(text) == parse_hex(APPLE_ACCENT)


def accent_words(text: str) -> tuple[bytes, bytes]:
    """The bottom and the top colour of the selection bar (RGBA bytes)."""
    r, g, b = parse_hex(text)
    if (r, g, b) == parse_hex(APPLE_ACCENT):
        return APPLE_BOTTOM, APPLE_TOP
    top = max(r, g, b)
    if top > MAX_CHANNEL:              # the drawing code needs room above the top colour (see MAX_CHANNEL)
        r, g, b = (int(c * MAX_CHANNEL / top + 0.5) for c in (r, g, b))
    return bytes([int(r * 0.8), int(g * 0.8), int(b * 0.8), 255]), bytes([r, g, b, 255])


def _mod(x: float, m: float) -> float:
    r = math.fmod(x, m)
    return r + m if r < 0 else r


def rgb_to_hsv(r: int, g: int, b: int) -> tuple[float, float, float]:
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(rf, gf, bf), min(rf, gf, bf)
    df = mx - mn
    if df > 1e-9:
        if mx == rf:
            h = _mod((gf - bf) / df, 6.0) / 6.0
        elif mx == gf:
            h = ((bf - rf) / df + 2.0) / 6.0
        else:
            h = ((rf - gf) / df + 4.0) / 6.0
        h = _mod(h, 1.0)
    else:
        h = 0.0
    s = df / mx if mx > 0 else 0.0
    return h, s, mx


def hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    hh = math.floor(h * 6.0)
    i = int(hh) % 6
    f = h * 6.0 - hh
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r, g, b = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))[i]
    return r * 255.0, g * 255.0, b * 255.0


def _byte(x: float) -> int:
    return min(255, max(0, int(math.floor(x + 0.5))))


@dataclass
class Tint:
    """The change from Apple's blue to the accent."""
    hue: float
    sat: float
    val: float

    @classmethod
    def make(cls, text: str) -> "Tint":
        bh, bs, bv = rgb_to_hsv(*parse_hex(APPLE_ACCENT))
        th, ts, tv = rgb_to_hsv(*parse_hex(text))
        return cls(th - bh, ts / max(bs, 1e-6), tv / max(bv, 1e-6))

    def pixel(self, r: int, g: int, b: int) -> tuple[int, int, int]:
        h, s, v = rgb_to_hsv(r, g, b)
        if not (s > SAT_MIN and v > VAL_MIN):
            return r, g, b
        out = hsv_to_rgb(_mod(h + self.hue, 1.0), min(1.0, max(0.0, s * self.sat)), min(1.0, max(0.0, v * self.val)))
        nr, ng, nb = _byte(out[0]), _byte(out[1]), _byte(out[2])
        if nr >= 248 and ng >= 248 and nb >= 248 and not (r == 255 and g == 255 and b == 255):
            return 247, 251, 247           # pure white is the transparent colour of an RGB565 picture
        return nr, ng, nb


def recolour_picture(osos: bytearray, pic: pictures.Picture, tint: Tint) -> bool:
    """Change the accent pixels of one picture. Returns True if a byte changed."""
    if pic.depth != 16:
        return False
    start, end = pic.data_pos, pic.data_pos + pic.bytes_per_row * pic.height
    before = bytes(osos[start:end])
    for y in range(pic.height):
        row = pic.data_pos + y * pic.bytes_per_row
        for x in range(pic.width):
            value = pictures._get(osos, row, x, pic)
            if pic.texture_format == 0x1444:
                if value[3] == 0:
                    continue
                r, g, b = tint.pixel(*value[:3])
                pictures._set(osos, row, x, pic, (r, g, b, value[3]))
            else:
                pictures._set(osos, row, x, pic, tint.pixel(*value))
    return bytes(osos[start:end]) != before


def recolour_views(osos: bytearray, block: resources.ResourceBlock, bottom: bytes, top: bytes) -> list[tuple[str, int, int]]:
    """Put the new gradient in each View. Returns (label, start, end) of each View that changed."""
    touched = []
    for r in block.of_type("View"):
        start = block.abs(r)
        end = start + r.size
        if end > len(osos) or r.size < 4:
            continue
        count = struct.unpack_from("<i", osos, start)[0]
        p, changed = start + 4, False
        for _ in range(max(count, 0)):
            if p + 4 > end:
                break
            size = struct.unpack_from("<I", osos, p)[0]
            for k in range(16, size + 4 - 3, 4):
                if p + k + 4 > end:
                    break
                word = bytes(osos[p + k:p + k + 4])
                if word == APPLE_TOP:
                    osos[p + k:p + k + 4], changed = top, True
                elif word == APPLE_BOTTOM:
                    osos[p + k:p + k + 4], changed = bottom, True
            p += size + 4
        if changed:
            touched.append((f"View {r.id}", start, end))
    return touched


def apply_accent(osos: bytearray, accent: str, block: resources.ResourceBlock) -> list[tuple[str, int, int]]:
    """Change the accent colour of osos. Returns the (label, start, end) of each resource that changed.

    `block` is the main resource block of Apple's firmware. A theme can move a table entry, thus the
    block must come from the firmware without the theme. With the accent of Apple nothing changes."""
    if is_apple(accent):
        return []
    bottom, top = accent_words(accent)
    tint = Tint.make(accent)
    touched = []
    for r in block.of_type("BMap"):
        if r.id in ACCENT_PICTURES:
            pic = pictures.parse(bytes(osos), block.abs(r))
            if pic and recolour_picture(osos, pic, tint):
                touched.append((f"BMap {r.id}", pic.data_pos, pic.data_pos + pic.bytes_per_row * pic.height))
    return touched + recolour_views(osos, block, bottom, top)


def main_block(osos: bytes, apple_length: int) -> resources.ResourceBlock:
    """The main resource block of Apple's firmware."""
    return resources.main_block(resources.scan(bytes(osos[:apple_length])))


def with_accent(theme: Theme, osos: bytes, accent: str, original_sha256: str, apple_length: int) -> Theme:
    """The theme with the accent colour. `osos` is the firmware without the theme.

    `apple_length` is the length of Apple's program in osos (`FirmwarePartition.apple_os_length`).

    The result holds the changes of the theme with the accent colour, and new changes for the
    bytes that the theme does not change, for example the selection bar of the Apple Views.
    With the accent of Apple the result is the theme itself."""
    parse_hex(accent)
    if is_apple(accent):
        return theme
    themed = bytearray(osos)
    apply_theme(theme, themed, original_sha256)
    final = bytearray(themed)
    touched = apply_accent(final, accent, main_block(osos, apple_length))
    base = [_with_copied_bytes(c, osos) for c in theme.with_old_bytes(osos).effective_changes()]
    covered = bytearray(len(final))
    changes = []
    for c in base:
        end = c.offset + len(c.new)
        covered[c.offset:end] = b"\x01" * len(c.new)
        changes.append(Change(c.resource, c.offset, c.old, bytes(final[c.offset:end])))
    for label, start, end in touched:
        i = start
        while i < end:
            if themed[i] == final[i] or covered[i]:
                i += 1
                continue
            j = i
            while j < end and themed[j] != final[j] and not covered[j]:
                j += 1
            changes.append(Change(label, i, bytes(osos[i:j]), bytes(final[i:j])))
            i = j
    out = Theme(theme.name, theme.source_sha256, theme.osos_sha256, changes, list(theme.skipped), list(theme.imported),
                [], [], keep_highlight=False)
    return out

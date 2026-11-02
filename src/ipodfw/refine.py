"""Corrections of the built-in dark theme "Classic Dark".

The dark builder of the owner changed some pictures in a way that does not work on the iPod. This
module gives the corrections. `refine_theme` applies them to a theme file, and the result is the
file in `themes/`. Run it with `ipodfw refine-theme`. A second run on the result changes nothing.

1. Clock. The faces (24403 to 24408) and the hands (25007 to 25042) stay Apple's art. The theme
   changed the hands, and many of them became black squares or white squares that hide the face.
2. Balls. The ball pictures of the game Brick (24361 to 24366) get a ring in the colour of Apple's
   blue (an accent picture) in place of the light pixels around the ball.
3. Cells. The cells of the Screen Lock (24393, and 24394 for the selected cell) have a white line at
   the bottom. The line gets the colour of the cell.
4. The Screen Lock dial (24395 to 24399). The grey metal of the bezel and of the knob is dark grey, so
   that the dial does not look like a white disc on the black screen.
5. The button 22206 (Start, and the blue button of other screens). The builder gave it yellow and white
   pixels at the corners and the bottom. The picture is new: a flat body and a ring.
6. Backgrounds. Four screens (the Stopwatch, the Screen Lock and its set-up screens) draw a light
   metal texture in code (Draw 24553). The background picture 21997 takes its place, and the dark
   style of text (Type 22199) gets white text.
"""

from __future__ import annotations

import struct
from dataclasses import replace

from . import pictures, resources
from .partition import FirmwarePartition
from .themeimport import Change, Theme, ThemeError, apply_theme

# Apple's art stays for these pictures.
KEEP_APPLE_PICTURES = tuple(range(24403, 24409)) + tuple(range(25007, 25043))
BALL_PICTURES = tuple(range(24361, 24367))
# The Views whose first element is the light texture (Draw 24553), and the picture that replaces it.
TEXTURE_VIEWS = (22157, 22401, 22402, 22533)
TEXTURE_ID, BACKGROUND_ID = 24553, 21997
DRAW_FLAGS, DRAW_PICTURE_FIELD = bytes.fromhex("80120000"), bytes.fromhex("08000000")
WHITE_TEXT_TYPES = (22199,)
CELL_PICTURES = (24393, 24394)
DIAL_PICTURES = tuple(range(24395, 24400))
DIAL_KNOB, DIAL_BEZEL, DIAL_DARKEN = 30.0, 53.5, 0.38      # the radii (in pixels) of the metal parts
BUTTON_PICTURE, BUTTON_BODY = 22206, (33, 97, 206)
RING = (24, 60, 148)          # a dark blue of Apple's hue: the accent changes it
WHITE = (255, 255, 255)       # the transparent colour of an RGB565 picture


def _ring(osos: bytearray, pic: pictures.Picture) -> None:
    """The pixels next to the transparent pixels get the ring colour."""
    w, h = pic.width, pic.height
    grid = [[pictures._get(osos, pic.data_pos + y * pic.bytes_per_row, x, pic) for x in range(w)] for y in range(h)]

    def clear(x: int, y: int) -> bool:
        return not (0 <= x < w and 0 <= y < h) or grid[y][x] == WHITE

    for y in range(h):
        for x in range(w):
            if grid[y][x] == WHITE:
                continue
            if any(clear(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy):
                pictures._set(osos, pic.data_pos + y * pic.bytes_per_row, x, pic, RING)


def _darken_dial(osos: bytearray, stock: bytes, pic: pictures.Picture) -> None:
    """The pixels of the bezel (outside DIAL_BEZEL) and of the knob (inside DIAL_KNOB) are Apple's
    pixels, darker. A second run gives the same bytes, because the pixels come from Apple's picture."""
    cx, cy = (pic.width - 1) / 2, (pic.height - 1) / 2
    for y in range(pic.height):
        for x in range(pic.width):
            r = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if DIAL_KNOB < r < DIAL_BEZEL:
                continue
            row = pic.data_pos + y * pic.bytes_per_row
            px = pictures._get(stock, row, x, pic)
            if px != WHITE:
                dark = tuple(min(246, int(c * DIAL_DARKEN)) for c in px)
                pictures._set(osos, row, x, pic, dark)
            else:
                pictures._set(osos, row, x, pic, WHITE)


def _new_button(osos: bytearray, stock: bytes, pic: pictures.Picture) -> None:
    """A flat button: the transparent pixels of Apple's picture, a ring at the edge and a flat body."""
    w, h = pic.width, pic.height
    grid = [[pictures._get(stock, pic.data_pos + y * pic.bytes_per_row, x, pic) for x in range(w)] for y in range(h)]

    def clear(x: int, y: int) -> bool:
        return not (0 <= x < w and 0 <= y < h) or grid[y][x] == WHITE

    for y in range(h):
        for x in range(w):
            if grid[y][x] == WHITE:
                value = WHITE
            elif any(clear(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy):
                value = RING
            else:
                value = BUTTON_BODY
            pictures._set(osos, pic.data_pos + y * pic.bytes_per_row, x, pic, value)


def _flatten_bottom_line(osos: bytearray, pic: pictures.Picture) -> None:
    """The last row of the picture gets the pixels of the row above."""
    n = pic.bytes_per_row
    last = pic.data_pos + (pic.height - 1) * n
    osos[last:last + n] = osos[last - n:last]


MERGE_GAP = 16      # two runs with a gap of at most this many same bytes become one run


def _runs(old: bytes, new: bytes, start: int) -> list[tuple[int, int]]:
    """The (start, end) of each run of bytes that are not the same."""
    out, i = [], 0
    while i < len(old):
        if old[i] == new[i]:
            i += 1
            continue
        j = i
        while j < len(old) and old[j] != new[j]:
            j += 1
        if out and start + i - out[-1][1] <= MERGE_GAP:
            out[-1] = (out[-1][0], start + j)
        else:
            out.append((start + i, start + j))
        i = j
    return out


def refine_theme(theme: Theme, fw: FirmwarePartition, original_sha256: str) -> Theme:
    """The theme with the corrections. `fw` is the Apple firmware 1.3."""
    stock = fw.image("osos")
    block = resources.main_block(resources.scan(stock[:fw.apple_os_length()]))
    themed = bytearray(stock)
    apply_theme(theme, themed, original_sha256)
    final = bytearray(themed)
    extents: dict[str, tuple[int, int]] = {}        # resource label -> byte range that is rebuilt
    pics = {r.id: r for r in block.of_type("BMap")}

    for rid in KEEP_APPLE_PICTURES:
        r = pics.get(rid)
        if r is None:
            raise ThemeError(f"The firmware has no picture {rid}.")
        extents[f"BMap {rid}"] = (block.abs(r), block.abs(r) + r.size)
        final[block.abs(r):block.abs(r) + r.size] = stock[block.abs(r):block.abs(r) + r.size]
    for rid in BALL_PICTURES:
        r = pics.get(rid)
        pic = pictures.parse(bytes(final), block.abs(r)) if r else None
        if pic is None:
            raise ThemeError(f"The firmware has no picture {rid}.")
        extents[f"BMap {rid}"] = (block.abs(r), block.abs(r) + r.size)
        _ring(final, pic)
    for rid in CELL_PICTURES:
        r = pics.get(rid)
        pic = pictures.parse(bytes(final), block.abs(r)) if r else None
        if pic is None:
            raise ThemeError(f"The firmware has no picture {rid}.")
        extents[f"BMap {rid}"] = (block.abs(r), block.abs(r) + r.size)
        _flatten_bottom_line(final, pic)
    for rid in DIAL_PICTURES:
        r = pics.get(rid)
        pic = pictures.parse(bytes(final), block.abs(r)) if r else None
        if pic is None:
            raise ThemeError(f"The firmware has no picture {rid}.")
        extents[f"BMap {rid}"] = (block.abs(r), block.abs(r) + r.size)
        _darken_dial(final, stock, pic)
    r = pics.get(BUTTON_PICTURE)
    pic = pictures.parse(bytes(final), block.abs(r)) if r else None
    if pic is None:
        raise ThemeError(f"The firmware has no picture {BUTTON_PICTURE}.")
    extents[f"BMap {BUTTON_PICTURE}"] = (block.abs(r), block.abs(r) + r.size)
    _new_button(final, stock, pic)
    views = {r.id: r for r in block.of_type("View")}
    for vid in TEXTURE_VIEWS:
        r = views.get(vid)
        start = block.abs(r) if r else 0
        if r is None or struct.unpack_from("<i", stock, start)[0] < 1 or struct.unpack_from("<h", stock, start + 4 + 12)[0] != TEXTURE_ID:
            raise ThemeError(f"The View {vid} does not start with the texture.")
        # The same fields as the element of View 24506, which shows the background picture in the theme.
        element = start + 4
        final[element + 4:element + 8] = DRAW_FLAGS
        final[element + 16:element + 20] = DRAW_PICTURE_FIELD
        struct.pack_into("<h", final, element + 12, BACKGROUND_ID)
        extents[f"View {vid}"] = (start, start + r.size)
    types = {r.id: r for r in block.of_type("Type")}
    for tid in WHITE_TEXT_TYPES:
        r = types.get(tid)
        if r is None:
            raise ThemeError(f"The firmware has no text style {tid}.")
        final[block.abs(r) + 8:block.abs(r) + 12] = b"\xff\xff\xff\xff"
        extents[f"Type {tid}"] = (block.abs(r), block.abs(r) + r.size)

    changes = []
    for c in theme.changes:
        inside = [lo <= c.offset < hi for lo, hi in extents.values()]
        if not any(inside):
            changes.append(c)
    for label, (lo, hi) in extents.items():
        for a, b in _runs(stock[lo:hi], bytes(final[lo:hi]), lo):
            changes.append(Change(label, a, bytes(stock[a:b]), bytes(final[a:b])))
    kept = {f"BMap {rid}" for rid in KEEP_APPLE_PICTURES}
    imported = (set(theme.imported) - kept) | (set(extents) - kept)
    return replace(theme, changes=changes, imported=sorted(imported), skipped=list(theme.skipped), edits=list(theme.edits))

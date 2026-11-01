"""Build the firmware for the appearance "Switch on iPod": light at the start, with a Dark Mode
item in Settings.

RetailOS makes its screens one time, at the start, from the View resources. Thus the dark theme
cannot change while the iPod runs. The patch patches/dark-mode applies a switch table at the
start, before the first View is read, if the file iPod_Control/iTunes/iPodFirmDarkMode contains
'1'. The Settings item writes that file and restarts the iPod.

The build puts these items after the end of osos (below OSOS_LIMIT):
    the theme data that is outside osos (for example the background picture: in both modes)
    the switch table: "IFD2", u32 count N, u32 total size, N entries with the new bytes of one change
                      each, as an LZ4 block or as bytes (refer to `switch_table`)
    the Settings menu with the Dark Mode item (the resource table entry points to it)
    the code of the patch (its symbol dark_table is the address of the table)
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from . import patcher
from .themeimport import OSOS_LIMIT, Change, Theme, _Image, _with_copied_bytes, apply_theme, moved_layout
from .partition import FirmwarePartition

MAGIC = 0x32444649                  # "IFD2"
SETTINGS_MENU = ("main", "Menu", 24598)
TEMPLATE_KEY = 0x600060B7           # the Sound Check item: an On/Off item
INSERT_AFTER_KEY = 0x60006088       # the Clicker item
DARK_KEY = 0x600060E0               # the key of the Dark Mode item (patch: KEY)
LABEL_ID = 0x7E00                   # the label "Dark Mode" (patch: LABEL_ID)
PATCH_AREA_END = 0x736800           # the other patches use the area before this address
SETTING_FILE = "iPod_Control/iTunes/iPodFirmDarkMode"


class DarkModeError(Exception):
    pass


def _align(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def layout_parts(theme: Theme, layout: Theme, osos: bytes, end: int) -> tuple[int, bytes, Change, list]:
    """The Split layout for "Switch on iPod", with its View at `end`: (address, light View, table
    entry change, list of (address, light bytes, dark bytes) for the switch table)."""
    at = _align(end, 16)
    place = bytes(at)
    light = _with_copied_bytes(moved_layout(layout, place).changes[0], osos).new
    themed = bytearray(osos)
    apply_theme(theme, themed, theme.osos_sha256)
    dark = _with_copied_bytes(moved_layout(layout, place, dark=True).changes[0], bytes(themed)).new
    extra, i = [], 0
    while i < len(light):
        j = i
        while j < len(light) and light[j] != dark[j]:
            j += 1
        if j > i:
            extra.append((at + i, light[i:j], dark[i:j]))
        i = max(j, i + 1)
    return at, light, moved_layout(layout, place).changes[1], extra


def _varint(v: int) -> bytes:
    out = bytearray()
    while v >= 0x80:
        out.append(v & 0x7F | 0x80)
        v >>= 7
    out.append(v)
    return bytes(out)


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    v = shift = 0
    while True:
        b = data[pos]
        pos += 1
        v |= (b & 0x7F) << shift
        if not b & 0x80:
            return v, pos
        shift += 7


def _lz4_extra(out: bytearray, n: int) -> None:
    """The bytes after a nibble of 15: n is the value minus 15."""
    while n >= 255:
        out.append(255)
        n -= 255
    out.append(n)


def _lz4_sequence(out: bytearray, literals: bytes, offset: int, length: int) -> None:
    """One LZ4 sequence. length is the match length (at least 4), or 0 for the last sequence."""
    lit, match = len(literals), max(length - 4, 0)
    out.append(min(lit, 15) << 4 | (min(match, 15) if length else 0))
    if lit >= 15:
        _lz4_extra(out, lit - 15)
    out += literals
    if length:
        out += struct.pack("<H", offset)
        if match >= 15:
            _lz4_extra(out, match - 15)


def lz4_compress(src: bytes) -> bytes:
    """An LZ4 block. The algorithm is simple, and the Swift version (DarkMode.lz4Compress) is the same,
    so both give the same bytes: a table of 4096 positions, a hash of 4 bytes, the first match, no
    search inside a match. The last 5 bytes are bytes, and no match starts in the last 12 bytes."""
    n = len(src)
    out = bytearray()
    table = [-1] * 4096
    anchor = ip = 0
    start_limit, end_limit = n - 12, n - 5
    while ip < start_limit:
        v = int.from_bytes(src[ip:ip + 4], "little")
        h = ((v * 2654435761) & 0xFFFFFFFF) >> 20
        ref = table[h]
        table[h] = ip
        if ref >= 0 and ip - ref <= 65535 and int.from_bytes(src[ref:ref + 4], "little") == v:
            length = 4
            while ip + length < end_limit and src[ref + length] == src[ip + length]:
                length += 1
            _lz4_sequence(out, src[anchor:ip], ip - ref, length)
            ip += length
            anchor = ip
        else:
            ip += 1
    _lz4_sequence(out, src[anchor:], 0, 0)
    return bytes(out)


def lz4_decompress(block: bytes, length: int) -> bytes:
    """The reference decoder (the patch does the same). Raises DarkModeError if the block is not correct."""
    out = bytearray()
    pos = 0
    try:
        while pos < len(block):
            token = block[pos]
            pos += 1
            lit, match = token >> 4, token & 15
            if lit == 15:
                while True:
                    b = block[pos]
                    pos += 1
                    lit += b
                    if b != 255:
                        break
            if pos + lit > len(block):
                raise DarkModeError("An LZ4 block is not correct.")
            out += block[pos:pos + lit]
            pos += lit
            if pos == len(block):
                break
            offset = block[pos] | block[pos + 1] << 8
            pos += 2
            if offset == 0 or offset > len(out):
                raise DarkModeError("An LZ4 block is not correct.")
            if match == 15:
                while True:
                    b = block[pos]
                    pos += 1
                    match += b
                    if b != 255:
                        break
            for _ in range(match + 4):
                out.append(out[-offset])
    except IndexError:
        raise DarkModeError("An LZ4 block is not correct.") from None
    if len(out) != length:
        raise DarkModeError("An LZ4 block has the wrong length.")
    return bytes(out)


def switch_table(theme: Theme, osos: bytes, extra: tuple | list = ()) -> tuple[bytes, int]:
    """The switch table for the changes inside osos, with the rules of apply_theme: a change is
    applied if the bytes are the old bytes, and left out if they are already the new bytes (the
    same change two times) or other bytes (an edit by the owner). `extra` adds runs of the layout.
    Returns (table, number of changes left out because of an edit).

    The table holds the new bytes (the patch only changes the light osos to the dark osos):
        "IFD2", u32 count, u32 total size, then for each change
        varint zigzag(address - end of the previous change), varint length * 2 + (1 if LZ4),
        varint size of the LZ4 block (only with LZ4), the block or the bytes."""
    changes, skipped = [], 0
    work = bytearray(osos)
    for c in theme.with_old_bytes(osos).effective_changes():
        if c.offset + len(c.old) > len(osos):
            continue
        cur = bytes(work[c.offset:c.offset + len(c.old)])
        if cur != c.old:
            if cur != c.new:
                skipped += 1
            continue
        work[c.offset:c.offset + len(c.new)] = c.new
        changes.append((c.offset, c.new))
    for at, _old, new in extra:
        changes.append((at, new))
    body, prev_end = bytearray(), 0
    for at, new in changes:
        delta = at - prev_end
        body += _varint(delta << 1 if delta >= 0 else ((-delta - 1) << 1) | 1)
        packed = lz4_compress(new)
        if len(packed) < len(new):
            body += _varint(len(new) * 2 + 1) + _varint(len(packed)) + packed
        else:
            body += _varint(len(new) * 2) + new
        prev_end = at + len(new)
    return struct.pack("<III", MAGIC, len(changes), 12 + len(body)) + bytes(body), skipped


def apply_switch_table(osos: bytearray, table: bytes) -> None:
    """What the patch does at the start (for tests). Raises DarkModeError if the table is not correct."""
    magic, n, total = struct.unpack_from("<III", table, 0)
    if magic != MAGIC or total != len(table):
        raise DarkModeError("The switch table is not correct.")
    pos, prev_end = 12, 0
    for _ in range(n):
        zz, pos = _read_varint(table, pos)
        len2, pos = _read_varint(table, pos)
        length, size = len2 >> 1, len2 >> 1
        if len2 & 1:
            size, pos = _read_varint(table, pos)
        at = prev_end + ((zz >> 1) ^ -(zz & 1))
        data = table[pos:pos + size]
        if len(data) != size or at < 0 or at + length > len(osos):
            raise DarkModeError("The switch table is not correct.")
        osos[at:at + length] = lz4_decompress(data, length) if len2 & 1 else data
        pos += size
        prev_end = at + length
    if pos != total:
        raise DarkModeError("The switch table is not correct.")


def settings_menu(menu: bytes) -> bytes:
    """Menu 24598 with a Dark Mode item after Clicker (a copy of the Sound Check item)."""
    count = struct.unpack_from("<I", menu, 0)[0]
    keys = [struct.unpack_from("<I", menu, 4 + 40 * i + 0x1C)[0] for i in range(count)]
    if DARK_KEY in keys:
        raise DarkModeError("The Settings menu already has the Dark Mode item.")
    if TEMPLATE_KEY not in keys or INSERT_AFTER_KEY not in keys:
        raise DarkModeError("The Settings menu is not the menu of firmware 1.3.")
    return patcher.insert_settings_item(menu, DARK_KEY, LABEL_ID, INSERT_AFTER_KEY, TEMPLATE_KEY)


def build(fw: FirmwarePartition, osos: bytes, theme: Theme, patch_dir: str | Path,
          original_sha256: str, layout: Theme | None = None) -> tuple[bytes, dict]:
    """The osos for "Switch on iPod". `osos` can have edits of the owner; `fw` gives its resources.
    With `layout`, both modes have the Split main menu."""
    if original_sha256 != theme.osos_sha256:
        raise DarkModeError(f"The theme \"{theme.name}\" is for a different firmware.")
    out = bytearray(osos)
    # 1. theme data outside osos: in both modes
    end = PATCH_AREA_END
    for c in theme.with_old_bytes(osos).effective_changes():
        if c.offset + len(c.old) > len(osos):
            if len(out) < c.offset + len(c.new):
                out += bytes(c.offset + len(c.new) - len(out))
            out[c.offset:c.offset + len(c.new)] = c.new
            end = max(end, c.offset + len(c.new))
    # The layout: in both modes. The switch table changes only its colours and text styles.
    extra = []
    if layout:
        view_at, view, entry, extra = layout_parts(theme, layout, osos, end)
        out += bytes(max(0, view_at + len(view) - len(out)))
        out[view_at:view_at + len(view)] = view
        out[entry.offset:entry.offset + len(entry.new)] = entry.new
        end = view_at + len(view)
    # 2. the switch table
    table, skipped = switch_table(theme, osos, extra)
    table_at = _align(end, 16)
    # 3. the Settings menu
    image = _Image(fw)
    if SETTINGS_MENU not in image.res:
        raise DarkModeError("The firmware has no Settings menu (Menu 24598).")
    res, block = image.res[SETTINGS_MENU], image.block_of[SETTINGS_MENU]
    menu = settings_menu(bytes(osos[block.abs(res):block.abs(res) + res.size]))
    menu_at = _align(table_at + len(table), 16)
    patch_at = _align(menu_at + len(menu), 16)
    # 4. the patch, then the table and the menu
    patched, report = patcher.apply(bytes(out), patch_dir, OSOS_LIMIT, load_address=patch_at,
                                    symbols={"dark_table": table_at}, original_sha256=original_sha256)
    out = bytearray(patched)
    if any(out[table_at:patch_at]):
        raise DarkModeError("The space for the switch table is not empty.")
    out[table_at:table_at + len(table)] = table
    out[menu_at:menu_at + len(menu)] = menu
    struct.pack_into("<II", out, res.table_pos + 4, menu_at - block.data_start, len(menu))
    info = {"table": [table_at, len(table)], "menu": [menu_at, len(menu)], "patch": report["code"],
            "changes_left_out": skipped, "end": len(out)}
    return bytes(out), info


def stock_sha256(fw: FirmwarePartition) -> str:
    return hashlib.sha256(fw.image("osos")).hexdigest()

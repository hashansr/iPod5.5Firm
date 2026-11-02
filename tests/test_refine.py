"""The corrections of Classic Dark (ipodfw.refine) on the real Apple firmware."""

import os
import struct
from pathlib import Path

import pytest

from ipodfw import accent, pictures, refine, themeimport

REPO = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(not os.environ.get("IPODFW_IPSW"), reason="set IPODFW_IPSW")


def _load():
    fw, _ = themeimport.load_firmware(os.environ["IPODFW_IPSW"])
    stock = fw.image("osos")
    theme = themeimport.Theme.from_json((REPO / "themes/Classic Dark.ipodtheme").read_text())
    block = accent.main_block(stock, fw.apple_os_length())
    out = bytearray(stock)
    done, conflicts = themeimport.apply_theme(theme, out, theme.osos_sha256)
    assert conflicts == 0
    return fw, stock, theme, block, bytes(out)


def test_the_clock_pictures_are_apples_art():
    _, stock, _, block, out = _load()
    for r in block.of_type("BMap"):
        if r.id in refine.KEEP_APPLE_PICTURES:
            assert out[block.abs(r):block.abs(r) + r.size] == stock[block.abs(r):block.abs(r) + r.size], r.id


def test_the_ball_pictures_have_a_ring_and_no_light_pixel_at_the_edge():
    _, _, _, block, out = _load()
    for r in block.of_type("BMap"):
        if r.id not in refine.BALL_PICTURES:
            continue
        pic = pictures.parse(out, block.abs(r))
        grid = [[pictures._get(out, pic.data_pos + y * pic.bytes_per_row, x, pic) for x in range(pic.width)] for y in range(pic.height)]
        edge = [grid[y][x] for y in range(pic.height) for x in range(pic.width) if grid[y][x] != refine.WHITE and (
            x in (0, pic.width - 1) or y in (0, pic.height - 1) or any(
                grid[y + dy][x + dx] == refine.WHITE for dx in (-1, 0, 1) for dy in (-1, 0, 1)))]
        assert edge and all(p == refine.RING for p in edge), r.id
        assert r.id in accent.ACCENT_PICTURES


def test_four_screens_show_the_background_picture_and_the_text_is_white():
    _, _, _, block, out = _load()
    views = {r.id: r for r in block.of_type("View")}
    for vid in refine.TEXTURE_VIEWS:
        assert struct.unpack_from("<h", out, block.abs(views[vid]) + 16)[0] == refine.BACKGROUND_ID
    types = {r.id: r for r in block.of_type("Type")}
    for tid in refine.WHITE_TEXT_TYPES:
        assert out[block.abs(types[tid]) + 8:block.abs(types[tid]) + 12] == b"\xff\xff\xff\xff"


def test_the_cells_of_the_screen_lock_have_no_white_line():
    _, _, _, block, out = _load()
    for r in block.of_type("BMap"):
        if r.id in refine.CELL_PICTURES:
            pic = pictures.parse(out, block.abs(r))
            n = pic.bytes_per_row
            last = pic.data_pos + (pic.height - 1) * n
            assert out[last:last + n] == out[last - n:last]


def test_the_dial_of_the_screen_lock_is_dark_outside_the_face():
    _, _, _, block, out = _load()
    for r in block.of_type("BMap"):
        if r.id not in refine.DIAL_PICTURES:
            continue
        pic = pictures.parse(out, block.abs(r))
        cx, cy = (pic.width - 1) / 2, (pic.height - 1) / 2
        for y in range(pic.height):
            for x in range(pic.width):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                px = pictures._get(out, pic.data_pos + y * pic.bytes_per_row, x, pic)
                if (d <= refine.DIAL_KNOB or d >= refine.DIAL_BEZEL) and px != refine.WHITE:
                    assert max(px) <= 110, (r.id, x, y, px)


def test_the_button_22206_has_no_light_pixel():
    _, stock, _, block, out = _load()
    r = [r for r in block.of_type("BMap") if r.id == refine.BUTTON_PICTURE][0]
    pic = pictures.parse(out, block.abs(r))
    old = pictures.parse(stock, block.abs(r))
    colours = set()
    for y in range(pic.height):
        for x in range(pic.width):
            px = pictures._get(out, pic.data_pos + y * pic.bytes_per_row, x, pic)
            was = pictures._get(stock, old.data_pos + y * old.bytes_per_row, x, old)
            assert (px == refine.WHITE) == (was == refine.WHITE)       # the same transparent pixels
            colours.add(px)
    assert colours == {refine.WHITE, refine.RING, refine.BUTTON_BODY}


def test_a_second_run_changes_nothing():
    fw, _, theme, _, _ = _load()
    again = refine.refine_theme(theme, fw, theme.osos_sha256)
    assert again.to_json(stripped=True) == theme.to_json(stripped=True)

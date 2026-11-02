"""The accent colour (ipodfw.accent). The Swift test has the same hashes."""

import hashlib
import os
from pathlib import Path

import pytest

from ipodfw import accent, themeimport

REPO = Path(__file__).resolve().parent.parent

# The hash of the result of Tint.pixel for each colour of a grid. The Swift test (testTintPixel) has the same values.
GRID = {
    "#ff3b30": "b9e9a7323dbba6053ddfd623d6d5ab143f325460b3bc39386e93d75816131921",
    "#30d158": "279e551d6704051a7ebe7da93b90ccf419183cbb7e48f4f061b4996ceaeecbc6",
    "#bf5af2": "e5e8ff4b5cc2b1d2dd1047c883010b2b137e3688c1f8032d08e5f09775e238d2",
}
# The hash of osos with Classic Dark and the accent. The Swift test (testClassicDarkWithAccent) has the same values.
OSOS = {
    "#ff3b30": "c289f447b1368471620a258fb3316623b6f3ac7190e9ca7b7d439dbc813dbe6c",
    "#bf5af2": "d019d4a6eeaa2ebf96b062d62a1870634c8ac1d868eabd4296f27f054620ecab",
}


def test_the_colour_must_have_the_form_rrggbb():
    for bad in ("", "red", "#12345", "#12345g", "1234567"):
        with pytest.raises(accent.AccentError):
            accent.parse_hex(bad)
    assert accent.parse_hex(" #FF3b30 ") == (255, 59, 48)


def test_the_accent_of_apple_changes_nothing():
    assert accent.is_apple("#5898E8") and not accent.is_apple("#5898e9")
    assert accent.accent_words("#5898e8") == (accent.APPLE_BOTTOM, accent.APPLE_TOP)
    theme = themeimport.Theme("t", "", "x")
    assert accent.with_accent(theme, bytes(16), "#5898e8", "x", 16) is theme


def test_the_gradient_has_the_colour_at_the_top_and_a_darker_colour_at_the_bottom():
    bottom, top = accent.accent_words("#ff3b30")
    assert top == bytes([232, 54, 44, 255]) and bottom == bytes([185, 43, 35, 255])   # the largest channel is 232
    assert accent.accent_words("#30d158")[1] == bytes([48, 209, 88, 255])             # a colour below the limit stays


def test_the_tint_keeps_grey_and_dark_pixels_and_moves_blue():
    tint = accent.Tint.make("#ff3b30")
    for grey in ((0, 0, 0), (128, 128, 128), (255, 255, 255), (10, 10, 20)):
        assert tint.pixel(*grey) == grey
    r, g, b = tint.pixel(0x58, 0x98, 0xE8)
    assert r > g and r > b                            # the blue becomes red
    assert accent.Tint.make("#5898e8").pixel(0x58, 0x98, 0xE8) == (0x58, 0x98, 0xE8)


@pytest.mark.parametrize("colour", sorted(GRID))
def test_tint_pixel_gives_the_hash(colour):
    tint, h = accent.Tint.make(colour), hashlib.sha256()
    for r in range(0, 256, 17):
        for g in range(0, 256, 17):
            for b in range(0, 256, 17):
                h.update(bytes(tint.pixel(r, g, b)))
    assert h.hexdigest() == GRID[colour]


@pytest.mark.skipif(not os.environ.get("IPODFW_IPSW"), reason="set IPODFW_IPSW")
@pytest.mark.parametrize("colour", sorted(OSOS))
def test_classic_dark_with_accent_gives_the_same_bytes_as_the_direct_change(colour):
    fw, _ = themeimport.load_firmware(os.environ["IPODFW_IPSW"])
    stock, length = fw.image("osos"), fw.apple_os_length()
    theme = themeimport.Theme.from_json((REPO / "themes/Classic Dark.ipodtheme").read_text())
    sha = theme.osos_sha256
    derived = accent.with_accent(theme, stock, colour, sha, length)
    assert derived.keep_apple == [] and derived.keep_highlight is False
    out = bytearray(stock)
    done, conflicts = themeimport.apply_theme(derived, out, sha)
    assert conflicts == 0 and done == len(derived.effective_changes())
    direct = bytearray(stock)
    themeimport.apply_theme(theme, direct, sha)
    touched = accent.apply_accent(direct, colour, accent.main_block(stock, length))
    assert bytes(out) == bytes(direct) and len(touched) > 100
    assert hashlib.sha256(bytes(out)).hexdigest() == OSOS[colour]

"""The list keep_apple of a theme: the pictures for which the theme keeps Apple's art."""
from pathlib import Path

from ipodfw import themeimport
from ipodfw.themeimport import Change, Theme

REPO = Path(__file__).resolve().parents[1]


def _theme(keep=None) -> Theme:
    t = Theme("t", "", "", keep_apple=keep)
    t.changes = [Change("BMap 24342", 0x100, b"\x01", b"\x02"), Change("BMap 100", 0x200, b"\x01", b"\x02")]
    return t


def test_default_list_keeps_apples_progress_bar():
    assert [c.resource for c in _theme().effective_changes()] == ["BMap 100"]


def test_empty_list_uses_the_progress_bar_of_the_theme():
    assert [c.resource for c in _theme([]).effective_changes()] == ["BMap 24342", "BMap 100"]


def test_the_list_survives_json():
    assert Theme.from_json(_theme([]).to_json()).keep_apple == []
    assert Theme.from_json(_theme().to_json()).keep_apple is None


def test_highlight_rule_keeps_blue_but_not_for_grey_controls():
    blue = bytes.fromhex("2864d0ff5898e8ff")
    grey = bytes.fromhex("2864d0ff343434ff")
    assert themeimport._keep_highlight(Change("View 5", 76, blue, grey)).new == blue
    assert themeimport._keep_highlight(Change("View 5" + themeimport.GREY_CONTROLS, 76, blue, grey)).new == grey


def test_builtin_classic_dark():
    t = Theme.from_json((REPO / "themes/Classic Dark.ipodtheme").read_text())
    assert t.keep_apple == []
    assert any(c.resource == "BMap 24342" for c in t.changes)
    assert any(c.resource.endswith("(table entry)") for c in t.changes)
    assert len([c for c in t.changes if c.resource.endswith(themeimport.GREY_CONTROLS)]) == 36
    assert Theme.from_json((REPO / "themes/Dark Gray.ipodtheme").read_text()).keep_apple is None

"""The list keep_apple of a theme: the pictures for which the theme keeps Apple's art."""
from pathlib import Path

import pytest

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


def test_borrow_pictures_replaces_the_picture_of_the_theme():
    mine = Theme("mine", "", "x", [Change("BMap 24351", 100, b"\x01\x02", b"\x0a\x0b"), Change("BMap 5", 300, b"\x01", b"\x02")])
    other = Theme("other", "", "x", [Change("BMap 24351", 100, b"\x01\x02", b"\x20\x21"), Change("BMap 9", 500, b"\x01", b"\x02")])
    themeimport.borrow_pictures(mine, other, [24351])
    assert [(c.resource, c.new) for c in mine.changes] == [("BMap 5", b"\x02"), ("BMap 24351", b"\x20\x21")]
    assert "BMap 24351" in mine.imported


def test_borrow_pictures_refuses_a_picture_that_the_source_does_not_change():
    mine = Theme("mine", "", "x", [])
    with pytest.raises(themeimport.ThemeError):
        themeimport.borrow_pictures(mine, Theme("other", "", "x", []), [24351])
    with pytest.raises(themeimport.ThemeError):
        themeimport.borrow_pictures(mine, Theme("other", "", "y", [Change("BMap 24351", 1, b"a", b"b")]), [24351])


def test_builtin_classic_dark():
    t = Theme.from_json((REPO / "themes/Classic Dark.ipodtheme").read_text())
    assert t.keep_apple == []
    assert any(c.resource == "BMap 24342" for c in t.changes)
    assert any(c.resource.endswith("(table entry)") for c in t.changes)
    # the scrollbar thumb comes from Dark Gray
    gray = Theme.from_json((REPO / "themes/Dark Gray.ipodtheme").read_text())
    thumb = lambda th: [(c.offset, c.new) for c in th.changes if c.resource == "BMap 24351"]
    assert thumb(t) and thumb(t) == thumb(gray)
    assert Theme.from_json((REPO / "themes/Dark Gray.ipodtheme").read_text()).keep_apple is None

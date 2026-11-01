"""Tests for the "Switch on iPod" build (ipodfw.darkmode)."""

import os
import struct
from pathlib import Path

import pytest

from ipodfw import darkmode, themeimport
from ipodfw.partition import FirmwarePartition

REPO = Path(__file__).resolve().parent.parent


def test_switch_table_gives_the_dark_bytes_and_keeps_edits():
    osos = bytearray(range(64))
    th = themeimport.Theme("t", "", "x", [
        themeimport.Change("View 1", 4, bytes([4, 5, 6]), bytes([9, 9, 9])),
        themeimport.Change("BMap 2", 20, bytes([20, 21]), bytes([0, 0])),
        themeimport.Change("BMap 3", 40, bytes([99]), bytes([1])),          # the owner changed this byte
        themeimport.Change("View 1", 4, bytes([4, 5, 6]), bytes([9, 9, 9])),  # the same change again
    ])
    table, skipped = darkmode.switch_table(th, bytes(osos))
    assert skipped == 1
    dark = bytearray(osos)
    darkmode.apply_switch_table(dark, table)
    assert dark[4:7] == bytes([9, 9, 9]) and dark[20:22] == bytes([0, 0]) and dark[40] == 40
    assert dark[:4] == osos[:4] and dark[7:20] == osos[7:20]


def test_lz4_roundtrip_and_known_bytes():
    import random
    rnd = random.Random(1)
    for n in (0, 1, 4, 5, 12, 13, 17, 40, 300, 5000, 70000):
        for data in (bytes(rnd.getrandbits(8) for _ in range(n)), (b"abcabcab" * n)[:n],
                     bytes(rnd.choice(b"ab\x00") for _ in range(n)), bytes(n)):
            assert darkmode.lz4_decompress(darkmode.lz4_compress(data), len(data)) == data
    # A fixed input gives fixed bytes. The Swift test (testLZ4KnownBytes) has the same value.
    sample = (b"Dark Mode " * 8) + bytes(range(40)) + (b"Dark Mode " * 5)
    assert darkmode.lz4_compress(sample).hex() == KNOWN_LZ4
    with pytest.raises(darkmode.DarkModeError):
        darkmode.lz4_decompress(b"\x10", 1)              # a literal that is not there
    with pytest.raises(darkmode.DarkModeError):
        darkmode.lz4_decompress(darkmode.lz4_compress(sample), len(sample) + 1)


KNOWN_LZ4 = "af4461726b204d6f6465200a0033ff19000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20212223242526276e001a504d6f646520"


def _compiler():
    """The command of a host C compiler (with the SDK on macOS), or None."""
    import shutil
    if shutil.which("xcrun"):
        return ["xcrun", "clang"]
    return ["cc"] if shutil.which("cc") else None


HARNESS = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define RAM_END 0x10000u
%s
/* stdin: image file name is argv[1], table position argv[2]. Then cases: u32 length, table bytes. */
int main(int argc, char **argv)
{
    unsigned char *pristine = malloc(RAM_END), *img = malloc(RAM_END);
    unsigned long table_at = strtoul(argv[2], 0, 10);
    FILE *f = fopen(argv[1], "rb");
    unsigned len;
    if (!f || fread(pristine, 1, RAM_END, f) != RAM_END) return 2;
    fclose(f);
    while (fread(&len, 4, 1, stdin) == 1) {
        unsigned char *table = malloc(len);
        int ok;
        if (fread(table, 1, len, stdin) != len) return 3;
        memcpy(img, pristine, RAM_END);
        memcpy(img + table_at, table, len);
        ok = walk_table(img + table_at, (unsigned long)img, 0);
        if (ok)
            walk_table(img + table_at, (unsigned long)img, 1);
        putchar(ok);
        fwrite(img, 1, RAM_END, stdout);
        free(table);
    }
    return 0;
}
"""


def _synthetic_case(seed=7):
    import random
    rnd = random.Random(seed)
    osos = bytearray(rnd.getrandbits(8) for _ in range(0xD000)) + bytearray(0x3000)
    changes, at = [], 0x40
    for size in (3, 1, 200, 17, 4000, 12, 600, 9, 2500, 50):
        old = bytes(osos[at:at + size])
        if size >= 100:
            new = bytes(rnd.choice(b"\x00\x10\x20\x30") for _ in range(size))     # compresses well
        else:
            new = bytes(rnd.getrandbits(8) for _ in range(size))
        changes.append(themeimport.Change(f"BMap {size}", at, old, new))
        at += size + rnd.randrange(0, 700)
    changes.append(themeimport.Change("View 9", 0x30, bytes(osos[0x30:0x34]), b"\xff\xfe\xfd\xfc"))   # before the first: a negative step
    th = themeimport.Theme("t", "", "x", changes)
    return bytes(osos), th


@pytest.mark.skipif(_compiler() is None, reason="no C compiler")
def test_decoder_in_dark_mode_c_agrees_with_python_and_refuses_bad_tables(tmp_path):
    """Compiles the decoder from patches/dark-mode/dark_mode.c with the host compiler and address
    sanitizer. A correct table gives the same bytes as the Python decoder. A table that is not
    correct changes no byte, or the same bytes as Python. The code never reads or writes outside."""
    import random
    import subprocess
    src = (REPO / "patches/dark-mode/dark_mode.c").read_text()
    code = src[src.index("/* DECODER BEGIN"):src.index("/* DECODER END */")]
    (tmp_path / "h.c").write_text(HARNESS % code)
    exe = tmp_path / "h"
    r = subprocess.run([*_compiler(), "-O1", "-g", "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                        "-Wno-pointer-to-int-cast", str(tmp_path / "h.c"), "-o", str(exe)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    osos, th = _synthetic_case()
    table, skipped = darkmode.switch_table(th, osos)
    assert skipped == 0 and len(table) < 0x3000
    table_at = 0xD000
    image = osos[:table_at] + bytes(0x3000)
    (tmp_path / "img.bin").write_bytes(image)

    rnd = random.Random(3)
    cases = [table]
    for _ in range(400):
        bad = bytearray(table)
        kind = rnd.randrange(4)
        if kind == 0:
            bad[rnd.randrange(len(bad))] ^= 1 << rnd.randrange(8)
        elif kind == 1:
            del bad[rnd.randrange(12, len(bad)):]
        elif kind == 2:
            for _ in range(3):
                bad[rnd.randrange(12, len(bad))] = rnd.getrandbits(8)
        else:
            bad[rnd.randrange(4, 12)] = rnd.getrandbits(8)
        cases.append(bytes(bad))
    stdin = b"".join(struct.pack("<I", len(c)) + c for c in cases)
    out = subprocess.run([str(exe), str(tmp_path / "img.bin"), str(table_at)], input=stdin, capture_output=True)
    assert out.returncode == 0, out.stderr.decode()[-2000:]
    size = 0x10000
    results = [(out.stdout[i * (size + 1)], out.stdout[i * (size + 1) + 1:(i + 1) * (size + 1)]) for i in range(len(cases))]
    assert len(out.stdout) == len(cases) * (size + 1)

    def reference(c):
        img = bytearray(image)
        img[table_at:table_at + len(c)] = c
        try:
            darkmode.apply_switch_table(img, c)
        except (darkmode.DarkModeError, IndexError, struct.error):
            return None
        return bytes(img)

    ok, img = results[0]
    assert ok == 1 and img == reference(table)
    dark = bytearray(image)
    darkmode.apply_switch_table(dark, table)
    assert img != image and img[:table_at] == bytes(dark[:table_at])
    refused = accepted = 0
    for k, (c, (ok, img)) in enumerate(zip(cases[1:], results[1:]), 1):
        before = bytearray(image)
        before[table_at:table_at + len(c)] = c
        if not ok:
            refused += 1
            assert img == bytes(before), f"case {k}: a refused table changed bytes"
        else:
            accepted += 1
            assert img == reference(c), f"case {k}: the C decoder and Python do not agree"
    assert refused > 50 and accepted > 20, (refused, accepted)       # the cases test both paths


def test_settings_menu_gets_the_item_after_clicker():
    def item(key, label):
        it = bytearray(40)
        struct.pack_into("<III", it, 0x18, label, key, label)
        return bytes(it)
    menu = struct.pack("<I", 3) + item(darkmode.TEMPLATE_KEY, 0xFF69) + item(darkmode.INSERT_AFTER_KEY, 0xFF68) + item(0x600060AD, 0xFF67)
    new = darkmode.settings_menu(menu)
    assert struct.unpack_from("<I", new, 0)[0] == 4
    keys = [struct.unpack_from("<I", new, 4 + 40 * i + 0x1C)[0] for i in range(4)]
    assert keys == [darkmode.TEMPLATE_KEY, darkmode.INSERT_AFTER_KEY, darkmode.DARK_KEY, 0x600060AD]
    assert struct.unpack_from("<I", new, 4 + 80 + 0x18)[0] == darkmode.LABEL_ID
    with pytest.raises(darkmode.DarkModeError):
        darkmode.settings_menu(new)


ENV = ("IPODFW_THEME", "IPODFW_THEME_BASE", "IPODFW_IPSW")


@pytest.mark.skipif(not all(os.environ.get(k) for k in ENV),
                    reason="set IPODFW_THEME, IPODFW_THEME_BASE and IPODFW_IPSW")
def test_switch_build_gives_the_dark_theme_at_the_start():
    theme_fw, sha = themeimport.load_firmware(os.environ["IPODFW_THEME"])
    base_fw, _ = themeimport.load_firmware(os.environ["IPODFW_THEME_BASE"])
    fw, _ = themeimport.load_firmware(os.environ["IPODFW_IPSW"])
    th = themeimport.make_theme(theme_fw, base_fw, fw, "test", sha)
    stock = fw.image("osos")
    osos, info = darkmode.build(fw, stock, th, REPO / "patches/dark-mode", th.osos_sha256)
    assert info["changes_left_out"] == 0 and len(osos) <= themeimport.OSOS_LIMIT
    # the start in dark mode: the table applied in RAM
    dark = bytearray(osos)
    table_at, table_len = info["table"]
    darkmode.apply_switch_table(dark, bytes(osos[table_at:table_at + table_len]))
    built_in = bytearray(stock)
    themeimport.apply_theme(th, built_in, th.osos_sha256)
    menu_entry = None
    image = themeimport._Image(fw)
    r = image.res[darkmode.SETTINGS_MENU]
    menu_entry = range(r.table_pos + 4, r.table_pos + 12)
    patched = set(range(0x21f254, 0x21f258)) | set(range(0x66c94c, 0x66c954))
    diff = [i for i in range(len(stock)) if dark[i] != built_in[i] and i not in menu_entry and i not in patched]
    assert diff == []
    # the start in light mode: Apple's bytes, except the hooks and the menu entry
    diff = [i for i in range(len(stock)) if osos[i] != stock[i] and i not in menu_entry and i not in patched]
    assert diff == []
    fw.make_room(len(osos))
    fw.replace_image("osos", osos)
    assert FirmwarePartition(fw.to_bytes()).checksum_ok("osos")

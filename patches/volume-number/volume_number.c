/* volume-number: the volume bar of Now Playing shows the volume as a number. Refer to re/numeric-volume.md.
 *
 * The property method 0x1e804c gives the text of a `Str` element by its ID. For the ID 0x63ef the
 * firmware gives a number only if the switch byte of _show_numeric_volume is not 0, and it takes the
 * number from a field of the application object. The "bytes" in patch.json turn the
 * test of the byte on. This patch gives the number that the owner wants: the volume from 0 to 100.
 *
 * The field + 0x758 (the level that 0x1e9e88 keeps) is 0 when the wheel changes the volume, because the
 * slider sets the volume directly. The field + 0x40c (the output volume, 0 to 256) is the value that the
 * slider shows, so it is always correct. The number is the output volume x 100 / 256, rounded.
 *
 * The "bytes" in patch.json turn the test of the byte on (0x1e8a24).
 *
 * The hook (bl, at the instruction that loads the field):
 *   0x1e8a30: `ldr r2, [r5, #0x40c]` in the case of the ID 0x63ef.
 * r5 is the provider (the application object). The result is in r2. The function does not change the flags.
 * The new `Str` element in View 24544 (patch.json, "view_elements") shows the number.
 */

__attribute__((naked)) unsigned hook_volume_level(void)
{
    __asm__ volatile(
        "ldr  r2, [r5, #0x40c]\n"
        "mov  r3, #100\n"
        "mul  r2, r3, r2\n"
        "add  r2, r2, #128\n"
        "mov  r2, r2, lsr #8\n"
        "bx   lr\n");
}

# Numeric volume: the hidden switch

Status (3 November 2026): the patch `volume-number` is a test patch. The owner tested version 0.1 on a real iPod: no number in Now Playing. Version 0.2 adds a text element to the volume bar of Now Playing. It is not tested. The research is static (disassembly of `osos` with `llvm-objdump`).

All addresses are osos offsets.

## Result

- The firmware already has a text element for the volume as a number, in the volume bar. Apple hid it behind the switch byte 0x1081dfde (the file `_show_numeric_volume`).
- The element is the `Str` 0x63f1 (25585) in View 24658. The text is the volume level, 0 to 100 (application object + 0x758).
- The patch changes 1 instruction so that the switch is always on. The firmware then gives the text, and the volume bar shows it. No file and no new View are necessary.

## How it works

The property method of the main provider is 0x1e804c. It gives the value of an element by its ID and its tag (`Str`, `Cntl`). A jump table at 0x1e835c handles the IDs 0x63ef to 0x63f7:

| ID | Tag | Address | Result |
|---|---|---|---|
| 0x63ef (25583) | `Cntl` | 0x1e8a0c | The address of the output volume (app + 0x40c, 0 to 256): the volume slider of Views 22594 and 24544. |
| 0x63ef | `Str` | 0x1e8a1c | If the switch byte is not 0: the text of app + 0x40c. Else an empty text. |
| 0x63f0 (25584) | `Cntl` | 0x1e89f8 | The address of a value (+ 0x358): the volume slider of View 24658. |
| 0x63f1 (25585) | `Str` | 0x1e89d8 | If the switch byte is not 0 (the `ldrb r0, [r2]` at 0x1e89e0): the text of app + 0x758, the volume level. Else an empty text. The text format is "%d" (0x1e8c58). |
| 0x63ee (25582) | `Cntl`, `Str` | 0x1e8a38 | The brightness slider (sun pictures), and a text of + 0x418 behind the same switch. No View has the `Str` element. |

The volume methods keep the notices:

- 0x1e9e88 (set the level) keeps the level at app + 0x758, calls 0x1eee50, and then sends the notices for 0x63f0 and 0x63f1 to the UI. Thus the number changes while the owner turns the wheel.
- 0x1eee50 (set the output volume) keeps app + 0x40c and sends the notice for 0x63ef.
- The setter 0x191fac calls method + 0x54 only if the switch is not 0. The patch does not need it.

The Views:

| View | Elements | Part of |
|---|---|---|
| 24658 | `Str` 0 (title), `Str` 0x63f1, `Str` 0x63ef, speaker, caps, `Cntl` 0x63f0 (260 wide), speaker, BMap 25567 (background) | View 24085, element 82. This is the volume overlay. |
| 22594 | speaker, `Cntl` 0x63ef, speaker, `Str` 0x63ef | View 22542 |
| 24544 | speaker, caps, `Cntl` 0x63ef (260 wide), speaker | View -344 (inside Now Playing) |

The texts of View 24658 (Type 24170, Pixo size 7, bold) are in one row under the title. The text 0x63f1 is at the left (left edge: parent + 25). The text 0x63ef is at the right (right edge: parent − 25). The patch gives only the text 0x63f1, because the text 0x63ef is the output volume (0 to 256), not the level.

The dark theme (Classic Dark and Dark Gray) sets the byte at element + 92 of each `Str` element of these Views from 0 to 0x0c, and recolours the speaker pictures. Thus the Apple themes already make this text light. The patch changes no style.

## The patch

| At | Old | New | Meaning |
|---|---|---|---|
| 0x1e89e0 | `ldrb r0, [r2]` (0xe5d20000) | `mov r0, #1` (0xe3a00001) | The text of the level is always on. |

The size is 0 (no code). The test `testVolumeNumberForcesTheSwitch` checks the bytes.

## Open questions

- Which layout shows when the owner turns the wheel? If it is View 22594 or 24544 (no text for the level), the patch shows no number. Then a change of these Views is necessary.
- If the number is too small, too far left, or has too little contrast, change the style of the `Str` element 0x63f1 (the Type, and the edges in the element).

## A test without the patch

Add the empty files `_enable_options` and `_show_numeric_volume` to `iPod_Control/Device/` on the iPod, and restart. The volume overlay shows the text of the level (and the raw volume at the right). Delete the files to stop the test.

## Real iPod test of version 0.1 and the change in version 0.2 (3 November 2026)

The owner switched on version 0.1 and saw no number on the volume bar. The reason: the volume bar of Now Playing is View 24544 (inside View -344, inside View 25522). This View has no text element. The Views 22594 and 24658 have text elements, but the iPod does not use them in Now Playing.

Version 0.2:

1. It adds a `Str` element (ID 0x63ef) to View 24544 after the slider, with `view_elements` (refer to [../docs/patch-system.md](../docs/patch-system.md#view-elements)). The element has the rectangle of the slider, 6 pixels lower and 8 pixels high. Its Type is 24171 (Pixo, size 7, bold, centred, black).
2. It also turns on the text of the element 0x63ef (0x1e8a24) and gives it the level (0x1e8a30 uses app + 0x758, not app + 0x40c). The notice 0x63ef from the volume methods changes the number with the slider.
3. The slider (the grey track and the blue fill) is the same in Apple, Classic Dark and Dark Gray (Dark Gray makes the fill dark grey). Thus the black text is easy to read on the grey track, and fair on the blue fill.

Not known until a test on the real iPod: the vertical position of the number, if the number fits, and the contrast on the blue fill.

## Real iPod test of version 0.2 and the change in version 0.3 (3 November 2026)

The owner sent photos of version 0.2. The number shows on the slider in Now Playing, but:

- It is 0 at each volume. The field app + 0x758 is 0 when the wheel changes the volume. The slider sets the volume with the property setter (0x191fac, then 0xb4078), not with 0x1e9e88. The field app + 0x40c (the output volume, 0 to 256) is the value that the slider shows, so it is correct. Version 0.3 gives the number as the output volume × 100 / 256, with a `bl` hook at the two loads.
- The digit is cut off at the bottom. The box was 8 pixels high. Pixo 7 draws the digits in the rows 2 to 8 of the box (the same as in the battery text), so a box needs at least 9 rows. Version 0.3 uses 10 rows, and the top of the box is 4 pixels below the top of the slider, so the digits are in the rows 6 to 12 of the 20 rows.
- The text is black, and the owner asks if it must be white. The slider has a grey track (light) and a blue fill (from #2864d0 to #5898e8). The centre of the number is over the track below 50 % volume and over the fill above 50 %. Black has a contrast of approximately 4 to 12 with these colours. White has a contrast of approximately 1.5 with the grey track, so it would not show at low volume. Version 0.3 keeps black.
- The digit is approximately 2 pixels left of the centre in the photo. The box is the rectangle of the slider and the Type is centred, so the cause is not known. A second photo of a larger number shows if this is a constant offset.

The brightness icons were still dots in the photo of the owner. The cause: version 0.2 put the new sun pictures into `edits` of the theme file. `ImportedTheme.updatedCopy` compares only `changes` and keeps the `edits` of the copy of the owner, so the copy of the theme was not updated. The pictures are now in `changes`. The copy gets the new theme at the next start of the app.

## Version 0.4: the default font (3 November 2026)

The owner asked for the default font of the iPod, black in the light look and white in the dark looks. Version 0.4 uses the Type 24223 (Podium Sans, size 18, bold, centred). The Types 24222, 24223 and 24225 are black in Apple's firmware, and Classic Dark and Dark Gray change their colour to white. The Dark Mode switch also changes them at run time.

The measures (the file `PodiumSans18.ttf` of rsrc, read with `Fat16`; the clusters of the file are in a row, and `Fat16.read` stops after the first cluster, so the bytes come from the first cluster and the size of the entry):

| Size | Ascent | Descent | Digits (top, bottom) in the line | Width of "100" |
|---|---|---|---|---|
| 18 | 14 | 5 | rows 2 to 15 (13 pixels) | 30 pixels |

The element is 19 pixels high (one line), and its top is 1 pixel below the top of the slider. The digits are then in the rows 3 to 15 of the slider. This assumes that the label puts the line at the top of its box. The battery text with Pixo 7 behaved in this way (digits in the rows 2 to 8 of the box). This is not proved for Podium Sans.

The white number is not easy to read over the light grey track (below half volume). The owner knows this.

## Version 0.5: the vertical position and the colour (3 November 2026)

The owner tested version 0.4 (Podium Sans 18, Type 24223). The number was "66", easy to read in size, centred across, but low in the bar with the bottom of the digits cut off, and black.

The vertical position. The text draw routine 0x2438bc reads flags from the view object (+ 0x20). The bits 0x1000000, 0x2000000 and 0x4000000 select how the text is placed up and down. Without the bit 0x1000000 the routine puts the text at the bottom of the box (`y = bottom − text height`, 0x2439f8). With the bit it centres the text (`(box height − text height) / 2`, 0x243a04 to 0x243a18). The bits come from the field at element + 24 (the byte + 27 has the bit 0x01 for the elements that centre their text, for example the battery text 0x08020001). The element of version 0.4 copied the field 0x0a00 from a Pixo label (View 22594), so the text was at the bottom of its box. The digits were then about 7 pixels lower than the middle, and 1 pixel was past the bottom of the box. The photo agrees: the top of the digits was at row 8 of the 20 rows of the slider. Version 0.5 uses the field 0x01000a00 and a box of 19 pixels from 1 pixel below the top of the slider to the bottom of the slider. The text then has the middle of the digits at row 10.

The colour. The Type 24223 is white in the dark looks (Classic Dark and Dark Gray, and in the switch table: a build of the table with the theme Classic Dark contains the colour at 0x4cafd4). The title text of Now Playing uses the same Type and it was white. The new element was black. The cause is not known. A difference is the byte + 92 of the element: Classic Dark changes it from 0 to 0x0c in each text element that it handles, but only at the old place of the View, not in the new copy. The battery text (Pixo, black Type) has the byte at 0x0c in dark and the digits did not turn white, so the byte does not set the colour alone. Version 0.5 uses the Type 24224 (white in Apple's firmware, also in the light look) to find out: if the number is white, the colour of the Type 24223 is not applied to the new element (a problem that is not understood). If the number is still black, the colour comes from another place.

The size is not changed. The owner asked if a smaller font is necessary. With the number centred up and down, the digits (13 pixels) fit in the slider (20 pixels), so a smaller size is not necessary. A smaller Podium Sans does not exist in the firmware (refer to [battery.md](battery.md)).

## Versions 0.5 and 0.6: no change on the iPod (3 November 2026)

The owner flashed version 0.5 (and reset the iPod) and version 0.6. The number did not change in style, colour or position.

Checks:

- The log of the app shows the builds and the flashes ("Wrote and verified"). The staged image `flash.bin` of each flash has the new element with the new Type (24224), the new flags (0x01000a00) and the new ID (0x63f1). The backup before the flash of version 0.5 has the old bytes (Type 24223). The flash changed the bytes.
- Thus the number that the owner sees does not come from the new element, or the new element is not drawn.

Observations:

- The slider (`Cntl` 0x63ef) of View 24544 has the data group 0x2b00 (element + 16). The new element has the data group 0x6380 (copied from a Pixo label). The data group selects the provider that gives the value. The Now Playing elements (the title, the slider) use 0x2b00.
- The number is correct (66, 70). The hooks give the number from the output volume, so a `Str` request for 0x63ef reaches the hooks with the correct provider. The black number depends on the switch for the ID 0x63ef (versions before 0.2 had no number).
- The style of the black number (Podium Sans, bold, black, the bottom cut off) is not the style of any `Str` element with the ID 0x63ef (all use Pixo 7). The slider class (0x24xxxx, the property function 0x240e30 to 0x241208) answers requests with the tag `Str `. It is possible that the slider draws the number itself.

Version 0.7 turns on only the text 0x63f1 (the test and the hook at 0x1e89e0 and 0x1e89e8), leaves the text 0x63ef off, and gives the new element the data group 0x2b00. Outcomes:

| What the owner sees | Meaning |
|---|---|
| No black number, and a white centred number | The black number came from the request for 0x63ef. The new element works. |
| No black number, and no white number | The black number came from the request for 0x63ef. The new element is not drawn (or its value is empty). |
| The black number as before | The black number comes from the request for 0x63f1, or from another place. |

## Version 0.7: no number (3 November 2026)

The owner flashed version 0.7 and saw no number at all.

Meaning: the black number came from the request for the ID 0x63ef, because version 0.7 turns that request off. The new element (ID 0x63f1, data group 0x2b00) did not draw a number. Two causes are possible:

- The new copy of View 24544 is not used, or its new element is not drawn.
- The new element is drawn, but the request for 0x63f1 gives no text with this data group.

Facts from the firmware data (version 0.8 work):

- The photos show the black number on the slider of Now Playing, in the middle across, and cut off by the bottom of the slider. This is the place of View 24544.
- No stock element has the ID 0x63ef and the box of the slider. The `Str` elements with 0x63ef are in View 22594 (under its slider), View 24658 (the overlay) and View 25522 (the header of Now Playing, element 6, Pixo 7, black). All of them use Type 24170 (Pixo 7).
- Thus the black Podium Sans number is not one of these elements. It agrees with the owner's photos of version 0.4 to 0.6, where the new element had other types and the number did not change.
- The dark themes change the bytes of element 6 of View 25522 (Dark Gray: the colours, the Type word and the byte + 92; Classic Dark: the byte + 92). A patch that changes that element must not change the same bytes.

## Version 0.8: a probe with four elements (3 November 2026)

Version 0.8 turns on both texts (the ID 0x63ef at 0x1e8a24 and 0x1e8a30, the ID 0x63f1 at 0x1e89e0 and 0x1e89e8). It adds four `Str` elements to the copy of View 24544. The boxes are 50 × 18 pixels at 1 pixel below the top of the slider, with the edges relative to the parent View. The elements differ in the ID, the data group and the Type (refer to [../docs/modifications.md](../docs/modifications.md#volume-number)).

How to read the photo of the volume bar:

| What the owner sees | Meaning |
|---|---|
| No new number, only the black number in the middle | The copy of the View is not used, or the elements are not drawn. Test with a marker that is not a text. |
| White numbers at the positions 1 and 3 | The data group 0x6380 works for the ID 0x63ef and for the ID 0x63f1. The Type and the centring work. |
| Black numbers at the positions 2 and 4 | The data group 0x2b00 works. |
| A number only at the positions 1 and 2 (the ID 0x63ef) | The request for the ID 0x63f1 is not answered, or it is not changed on the wheel path. |
| A number only at the positions 3 and 4 (the ID 0x63f1) | The request for the ID 0x63ef is answered only for the slider. |

## Version 0.8 result: numbers show, the bar breaks (3 November 2026)

The owner flashed version 0.8. The photo shows numbers on the bar, so the copy of View 24544 is used and the new elements draw. The numbers are dark, also those with the white Type 24224. The speaker picture and the cap of the slider are in the middle of the bar, and the slider is short. The cause is the place of the new elements: they are after element 2, and the elements 3 and 4 (the cap and the speaker) use "the previous element" for their edges. With the new elements before them, their edges moved.

The owner also asks for a black battery text. The dark looks set the byte + 92 of the text element to 0x0c, and the battery text (Type 24171, black) is white. Together with the dark numbers (Type 24224 is white), this shows that the colour of a text element probably comes from the byte + 92 and not from the Type.

## Version 0.9: the elements at the end, a test of the byte + 92 (3 November 2026)

Version 0.9 puts the four elements after the last element (index 4), so no old element moves. All have the ID 0x63ef and the Type 24223. They differ in the data group (0x6380 or 0x2b00) and in the byte + 92 (0 or 0x0c). The elements are at the left edges 26, 86, 146 and 206 pixels. Battery Display 0.9 sets the byte + 92 of its text to 0 in the same build, as a second test of the same idea.

| What the owner sees | Meaning |
|---|---|
| The numbers 2 and 4 (byte 0x0c) are white, 1 and 3 are black | The byte + 92 sets the colour. The final patch uses 0x0c in a dark look and 0 in a light look. |
| All are black | The byte + 92 is not the cause. The colour comes from another place. |
| Only the numbers 1 and 2, or 3 and 4, show | The data group decides which elements are drawn. |

## Version 0.9 result and version 0.10 (3 November 2026)

The owner flashed version 0.9. The bar is normal again. The four numbers show the volume (83). The numbers 1 and 3 (byte + 92 = 0) are black, and the numbers 2 and 4 (byte 0x0c) are white. The data group does not change the result. Thus:

- The byte + 92 of a text element sets the colour, and the Type record does not.
- The firmware draws no number of its own. The black number of the versions 0.2 to 0.6 was the new element with the byte 0.
- The digits (Podium Sans 18) are too large and low in the slider (about 3 pixels).

The battery text is still white with the byte set to 0. The switch table of Classic Dark uses the change 0 to 0x0c if the byte is 0, so it makes the byte 0x0c again. Version 0.10 of Battery Display uses 0x10, a value that no change of a theme has as its old value.

Version 0.10 of Volume Number has one element: ID 0x63ef, group 0x6380, Type 24227 (Podium Sans 16, bold, centred), byte + 92 = 0x0c (white), box from 17 pixels, 18 pixels high, 131 to 181 pixels across. The gate and the hook of the ID 0x63f1 are removed. They were not necessary.

## Version 0.10 result and version 0.11 (4 November 2026)

The owner flashed version 0.10. The font, the size and the alignment are correct. The number is black. The Type 24227 is black in Apple's firmware, and the byte + 92 is 0x0c. Together with version 0.9 (Type 24223 white, byte 0x0c: white, and byte 0: black) this shows that a text with the byte 0x0c has the colour of its Type record. Version 0.11 changes the colour of the Type 24227 (osos 0x4cb014) from 000000 to ffffff. No stock View uses the Type 24227.

The battery text is white for another reason (refer to [battery.md](battery.md)): the switch table of Switch on iPod wrote the byte + 92 again at the start of the iPod, because the table was made from Apple's firmware and not from the firmware with the patches. A test (`testSwitchTableKeepsPatchBytes`) shows the byte 0x0c after the table without the new rule, and the byte 0 with it.

# Classic Dark theme: how it is made

This document tells how the built-in theme "Classic Dark" in `themes/` is made. The target is Apple RetailOS 1.3 for the iPod Video 5.5G.

## Source

The owner has a dark builder for the stock firmware (the project `iPod5-5.5-Classic-dark`, version 0.5.3). The builder changes pictures, the selector colour and the text colour of a firmware partition. The default accent is the Apple blue (`#5898e8`).

## Steps

1. Build the dark firmware with the builder from the base image `5.5G_1.3_bghack_v1.1`. The base image has the SHA-256 `19190c21…557d62`.
2. Import the result with the Apple firmware 1.3 as the base and as the target:

```sh
ipodfw import-theme dark.fw iPod_25.1.3.ipsw iPod_25.1.3.ipsw --own-progress-bar --grey-tolerance 4 --borrow "themes/Dark Gray.ipodtheme" --borrow-ids 24351 --name "Classic Dark" -o classic-dark.json
ipodfw strip-theme classic-dark.json -o "themes/Classic Dark.ipodtheme"
ipodfw refine-theme iPod_25.1.3.ipsw "themes/Classic Dark.ipodtheme" -o "themes/Classic Dark.ipodtheme"
```

3. The result has 3948 changes in format 2. It holds no byte of the Apple firmware. The step `refine-theme` is the same on a second run.

## What the import adds

The import of an iPodWizard theme skips three items of this theme. Two options of `make_theme` in [themeimport.py](../src/ipodfw/themeimport.py) give them back:

| Item | Reason for the skip | Option |
|---|---|---|
| BMap 24342 and 24343 (the progress bar) | The Dark Gray theme makes the bar almost invisible. Classic Dark has a lit track, so that the seek diamond shows. | `--own-progress-bar`. The theme gets `"keep_apple": []`. |
| View 24529 (the charging screen) | The builder moves the table entry of the View to the data of an unused View. The import compares the structure of the View, so it refused. | Automatic if the base and the target are the same osos. The change is the 8 bytes of the table entry. |

## The scrollbar thumb

The owner prefers the scrollbar of Dark Gray. In Classic Dark the thumb is blue. In Dark Gray it is grey.

- First try (2 November 2026): a change of the highlight colours of the `Cntl` elements (21 changes). Second try: `Cntl`, `Draw` and `StSt` elements (36 changes). The photos of the owner showed that the thumb stayed blue. The cause of the first photos was an old copy of the theme in the folder of the owner. Refer to [../docs/modifications.md](../docs/modifications.md#dark-theme). The cause of the later photo was that the thumb is a picture. Both tries are removed.
- Picture 24351 (11 × 11) is the thumb. In the owner's Classic Dark photo the thumb has the colour (41, 101, 206), the flat blue of this picture. Dark Gray has (33, 36, 33). The track (picture 24350) is black in both themes.
- Option `--borrow "themes/Dark Gray.ipodtheme" --borrow-ids 24351` of `import-theme` replaces the changes for picture 24351 with those of Dark Gray.

Check: the only resources that differ from the image of the dark builder are picture 21997 (the background, stored smaller) and picture 24351 (the thumb).

Real iPod 5.5G (owner, 3 November 2026), with "Switch on iPod": the thumb is grey. The owner confirms that the problem is solved.

## Check

Apply the theme to the stock firmware with `ipodfw apply-theme`. The result has 0 changes that cannot apply, and `ipodfw verify` accepts it. The result differs from the image of the builder in 13 ranges (113,719 bytes). The largest ranges are near 0x502df4 to 0x52a000. Per [dark-theme.md](dark-theme.md), the background picture of the base image overwrites font data there. The theme stores this picture after the end of osos. This was not checked byte for byte.

Not tested on a real iPod: the theme in this app. The builder itself ran on a real iPod 5.5G.

## Corrections

The photos of the owner (3 November 2026) showed 6 faults. `src/ipodfw/refine.py` corrects them in the theme file. The tests are in `tests/test_refine.py`.

| Fault | Cause | Correction |
|---|---|---|
| The Clock list showed a black square in place of the clock face. | The builder changed the hands (25007 to 25042) with tone curves. Some hands became black squares or near-white squares that cover the face, and some hands disappeared. | The faces (24403 to 24408) and the hands are Apple's art. Apple's faces and hands agree with each other by day and by night. |
| The balls of Brick had light pixels around them. | The ball pictures (24361 to 24366) have a ring of light grey pixels at the transparent edge. | Each pixel next to a transparent pixel gets a ring colour, a dark blue of the hue of Apple's blue. The pictures are accent pictures, thus the ring follows the accent. |
| The Time screen had a light background and a blue button. | Four Views draw a light metal texture in code (Draw 24553): 22157 (probably the Stopwatch, its text style is 22199), 22401 and 22402 (probably the Screen Lock) and 22533 (not identified). The Views have no text with the name of the screen, thus the names come from the nearness of the string IDs. The text style 22199 is black. The button is picture 22206. | The element 0 of each View shows the picture 21997 (the fields as in View 24506). The style 22199 has white text. The picture 22206 is an accent picture. |
| The Screen Lock cell had a white line. | The pictures 24393 and 24394 (the cell and the selected cell, 40 × 37) have a light last row. | The last row has the pixels of the row above. The picture 24394 is an accent picture. |
| The Screen Lock dial looked like a white disc. | The bezel and the knob are light grey metal. | The pixels outside 53.5 px and inside 30 px of the centre of the pictures 24395 to 24399 are Apple's pixels at 0.38 times the brightness. |
| The button Start had a white and yellow border. | The builder's picture 22206 has the corners (255, 255, 206) and white pixels at the bottom. The accent made them yellow. | The picture is new: the transparent pixels of Apple's picture, a ring and a flat body. |
| Yellow pixels at the top of a red selection bar (3 November 2026). | The cause is not known. A red bar (255, 69, 58) has a channel at 255. The bar of Apple has at most 232. | The accent is limited to 232 per channel (`accent.MAX_CHANNEL`). Not tested. If the pixels stay, try another colour to find the rule. |

Not corrected (open):

- The Contacts card keeps its light background. The card draws two textures in code (BMap 28021 and 28022 in View −538, not pictures of the firmware). The text style 27972 is black.
- The white border of the selected number in Date & Time. The cell is not picture 24394 (it follows the accent). The View of the screen is not found yet.

Not tested on a real iPod: all four corrections.

## Size with "Switch on iPod"

Version 1.1 of the `dark-mode` patch stored the data of all changes in the switch table (old XOR new). Classic Dark has 783,663 bytes of new data after the background is stored as a 4-bit grey picture. With no other patch, the code of the patch ended 29,425 bytes after the limit 0x7F8000.

Version 2.0 stores the new bytes with LZ4 and decodes them at the start. Refer to [dark-mode-compression.md](dark-mode-compression.md) and [../docs/modifications.md](../docs/modifications.md#dark-mode-switch). Measured on 2 November 2026:

| Theme | Switch table | "Switch on iPod" adds | Free below 0x7F8000 |
|---|---|---|---|
| Classic Dark | 256,547 bytes | 299,008 bytes | 493,568 bytes |
| Dark Gray | 268,867 bytes | 311,296 bytes | – |

The decoder was run on the real image of Classic Dark, with the host compiler and the address sanitizer. The result is the same as the theme applied to the Apple firmware, outside the hooks and the menu entry. Real iPod 5.5G (owner, 3 November 2026): the decoder operates with "Switch on iPod". Not tested: the decoder in the emulator.

## Not in the theme

The builder can set any accent colour (`--accent`). The theme has the default Apple blue only. A different accent needs a different theme file.

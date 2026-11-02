# Classic Dark theme: how it is made

This document tells how the built-in theme "Classic Dark" in `themes/` is made. The target is Apple RetailOS 1.3 for the iPod Video 5.5G.

## Source

The owner has a dark builder for the stock firmware (the project `iPod5-5.5-Classic-dark`, version 0.5.3). The builder changes pictures, the selector colour and the text colour of a firmware partition. The default accent is the Apple blue (`#5898e8`).

## Steps

1. Build the dark firmware with the builder from the base image `5.5G_1.3_bghack_v1.1`. The base image has the SHA-256 `19190c21…557d62`.
2. Import the result with the Apple firmware 1.3 as the base and as the target:

```sh
ipodfw import-theme dark.fw iPod_25.1.3.ipsw iPod_25.1.3.ipsw --own-progress-bar --grey-tolerance 4 --grey-controls "themes/Dark Gray.ipodtheme" --name "Classic Dark" -o classic-dark.json
ipodfw strip-theme classic-dark.json -o "themes/Classic Dark.ipodtheme"
```

3. The result has 4597 changes in format 2. It holds no byte of the Apple firmware.

## What the import adds

The import of an iPodWizard theme skips three items of this theme. Two options of `make_theme` in [themeimport.py](../src/ipodfw/themeimport.py) give them back:

| Item | Reason for the skip | Option |
|---|---|---|
| BMap 24342 and 24343 (the progress bar) | The Dark Gray theme makes the bar almost invisible. Classic Dark has a lit track, so that the seek diamond shows. | `--own-progress-bar`. The theme gets `"keep_apple": []`. |
| View 24529 (the charging screen) | The builder moves the table entry of the View to the data of an unused View. The import compares the structure of the View, so it refused. | Automatic if the base and the target are the same osos. The change is the 8 bytes of the table entry. |

## Grey controls

The owner prefers the scrollbar of Dark Gray. In Dark Gray the second highlight colour (+80) of the `Cntl` elements is grey (`ff343434`). In Classic Dark it is Apple's blue. Option `--grey-controls "themes/Dark Gray.ipodtheme"` of `import-theme` adds one change for each `Cntl` element, with the label "View N (grey controls)". The change gives the element the colours of Dark Gray. The highlight rule skips changes with this label (`GREY_CONTROLS`, `ThemeImport.greyControls`).

Result of 2 November 2026: 21 changes, 23 `Cntl` elements equal to Dark Gray, and no other highlight word is different from Apple's blue. Not known: if the `Cntl` elements are the scrollbar. The list of the elements is a test. Not tested on a real iPod.

## Check

Apply the theme to the stock firmware with `ipodfw apply-theme`. The result has 0 changes that cannot apply, and `ipodfw verify` accepts it. The result differs from the image of the builder in 13 ranges (113,719 bytes). The largest ranges are near 0x502df4 to 0x52a000. Per [dark-theme.md](dark-theme.md), the background picture of the base image overwrites font data there. The theme stores this picture after the end of osos. This was not checked byte for byte.

Not tested on a real iPod: the theme in this app. The builder itself ran on a real iPod 5.5G.

## Size with "Switch on iPod"

Version 1.1 of the `dark-mode` patch stored the data of all changes in the switch table (old XOR new). Classic Dark has 783,663 bytes of new data after the background is stored as a 4-bit grey picture. With no other patch, the code of the patch ended 29,425 bytes after the limit 0x7F8000.

Version 2.0 stores the new bytes with LZ4 and decodes them at the start. Refer to [dark-mode-compression.md](dark-mode-compression.md) and [../docs/modifications.md](../docs/modifications.md#dark-mode-switch). Measured on 2 November 2026:

| Theme | Switch table | "Switch on iPod" adds | Free below 0x7F8000 |
|---|---|---|---|
| Classic Dark | 275,992 bytes | 317,440 bytes | 475,136 bytes |
| Dark Gray | 268,867 bytes | 311,296 bytes | – |

The decoder was run on the real image of Classic Dark, with the host compiler and the address sanitizer. The result is the same as the theme applied to the Apple firmware, outside the hooks and the menu entry. Not tested: the decoder on a real iPod or in the emulator.

## Not in the theme

The builder can set any accent colour (`--accent`). The theme has the default Apple blue only. A different accent needs a different theme file.

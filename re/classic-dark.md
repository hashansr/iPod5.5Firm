# Classic Dark theme: how it is made

This document tells how the built-in theme "Classic Dark" in `themes/` is made. The target is Apple RetailOS 1.3 for the iPod Video 5.5G.

## Source

The owner has a dark builder for the stock firmware (the project `iPod5-5.5-Classic-dark`, version 0.5.3). The builder changes pictures, the selector colour and the text colour of a firmware partition. The default accent is the Apple blue (`#5898e8`).

## Steps

1. Build the dark firmware with the builder from the base image `5.5G_1.3_bghack_v1.1`. The base image has the SHA-256 `19190c21…557d62`.
2. Import the result with the Apple firmware 1.3 as the base and as the target:

```sh
ipodfw import-theme dark.fw iPod_25.1.3.ipsw iPod_25.1.3.ipsw --own-progress-bar --name "Classic Dark" -o classic-dark.json
ipodfw strip-theme classic-dark.json -o "themes/Classic Dark.ipodtheme"
```

3. The result has 4576 changes in format 2. It holds no byte of the Apple firmware.

## What the import adds

The import of an iPodWizard theme skips three items of this theme. Two options of `make_theme` in [themeimport.py](../src/ipodfw/themeimport.py) give them back:

| Item | Reason for the skip | Option |
|---|---|---|
| BMap 24342 and 24343 (the progress bar) | The Dark Gray theme makes the bar almost invisible. Classic Dark has a lit track, so that the seek diamond shows. | `--own-progress-bar`. The theme gets `"keep_apple": []`. |
| View 24529 (the charging screen) | The builder moves the table entry of the View to the data of an unused View. The import compares the structure of the View, so it refused. | Automatic if the base and the target are the same osos. The change is the 8 bytes of the table entry. |

## Check

Apply the theme to the stock firmware with `ipodfw apply-theme`. The result has 0 changes that cannot apply, and `ipodfw verify` accepts it. The result differs from the image of the builder in 13 ranges (113,719 bytes). The largest ranges are near 0x502df4 to 0x52a000. Per [dark-theme.md](dark-theme.md), the background picture of the base image overwrites font data there. The theme stores this picture after the end of osos. This was not checked byte for byte.

Not tested on a real iPod: the theme in this app. The builder itself ran on a real iPod 5.5G.

## Size with "Switch on iPod"

The switch table holds the data of all changes. Classic Dark has 783,663 bytes of new data after the background is stored as a 4-bit grey picture. Dark Gray has 699,106 bytes. With no other patch, the code of `dark-mode` ends 29,425 bytes after the limit 0x7F8000. The patches of the owner need approximately 53,000 bytes more. Thus Classic Dark works only with the appearance Dark.

To use Classic Dark with "Switch on iPod", compress the table. Refer to [dark-mode-compression.md](dark-mode-compression.md). That change needs a decoder in `dark_mode.c`, and a test on a real iPod.

## Not in the theme

The builder can set any accent colour (`--accent`). The theme has the default Apple blue only. A different accent needs a different theme file.

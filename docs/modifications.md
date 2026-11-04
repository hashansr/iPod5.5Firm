# The modifications

This document describes each change that iPodFirm can make to the firmware. For each change, it gives the user interface, the changed bytes, the hooks, the runtime logic, the limits and the test status.

All addresses are osos offsets for Apple firmware 1.3. Refer to [The address rule](README.md#the-address-rule). For the hook kinds and the linker, refer to [patch-system.md](patch-system.md).

## Summary

| Change | Type | Pane in iPodFirm | Hooks or bytes | Tested on a real iPod |
|---|---|---|---|---|
| [Picture replacement](#picture-replacement) | Resource data | Pictures | Pixel bytes of one BMap | Not recorded |
| [Text replacement](#text-replacement) | Resource data | Text | One Str area | Not recorded |
| [Software version](#software-version) | Code | Patches > Software Version | 2 instructions, or 1 function body | Yes (28 October 2026) |
| [backlight-60s](#backlight-60s) | Data patch | Patches | 16 byte runs and 21 strings | Version 1.1: yes (28 October 2026) |
| [album-art](#album-art) | Code patch (extended) | Patches | 2 vtable words and 1 `bl` | Version 1.0: yes. Version 2.9: yes (27 October 2026). Version 3.0: covers loaded slowly. Version 3.1: yes (27 October 2026). Version 3.2: yes (28 October 2026) |
| [sleep-now](#sleep-now) | Code patch | Patches | 1 vtable word and 2 `bl` | Version 1.2: yes (28 October 2026) |
| [flash-keep-awake](#flash-keep-awake) | Code patch | Patches | 4 `bl` | Version 1.1: yes (28 October 2026) |
| [flash-wake-on-input](#flash-wake-on-input) | Code patch | Patches | 1 `bl` | Version 1.2: yes (28 October 2026) |
| [volume-unlimit](#volume-unlimit) | Data patch | Patches | 2 bytes | No |
| [click-speaker-only](#click-speaker-only) | Data patch | Patches | 1 instruction word | Yes (2026-10-27) |
| [shuffle-fixes](#shuffle-fixes) | Code patch (extended) | Patches | 2 `bl` and 4 instruction words | Version 2.1: yes (28 October 2026) |
| [shuffle-album-mix](#shuffle-album-mix) | Code patch (extended) | Patches | 3 `bl`, 3 `b` and 3 vtable words (all 6 with `chain`), 1 instruction word, 2 menus | Version 1.1: partly, the order of one album. Version 1.2: yes (28 October 2026) |
| [album-artists](#album-artists) | Code patch | Patches | 6 `b`, 4 `bl` and 3 vtable words (4 with `chain`), 3 menus | Version 1.1: yes. Version 1.2: the Main Menu setting is lost at a restart with Menu+Select. Version 1.3: yes (28 October 2026) |
| [cover-flow](#cover-flow) | Code patch | Patches | 3 words (2 vtable slots and 1 literal) | Version 0.6.7: yes (27 October 2026). Version 0.6.8: yes (28 October 2026) |
| [up-next](#up-next) | Code patch (extended) | Patches | 1 `bl`, 1 `b` and 2 vtable words (3 with `chain`), a Settings menu | Version 0.4: yes. Version 0.5: yes (28 October 2026) |
| [custom-eq](#custom-eq) | Code patch (extended) | Patches | 1 `bl`, 1 `b`, 2 words (`bytes`) | Version 0.1: yes, a basic test by the owner. Version 0.2 and later: no |
| [battery-display](#battery-display) | Code patch (test, extended) and data | Patches | 4 `bl` and 12 data changes | Version 0.3 and 0.4: partly (3 November 2026). Version 0.5: failed (the iPod restarted). Versions 0.6 to 0.10: start (0.8 to 0.10: white digits). Version 0.11: works |
| [wheel-guard](#wheel-guard) | Code patch (test, extended) | Patches | 3 `word` and 1 `b` (all with `chain`), a Settings item | Version 0.1: yes (owner, 3 November 2026). Version 0.2: no |
| [volume-number](#volume-number) | Code patch (test, extended), data and a View | Patches | 1 `bl`, 1 instruction word, 1 View element, 1 Type colour | Versions 0.1 to 0.4: partly. Versions 0.5 to 0.8: no. Version 0.9: the colour is known, the size is too large. Version 0.10: right size, but black. Version 0.11: works (owner, 4 November 2026) |
| [usb-audio-out](#usb-audio-out) | Code patch | Patches | 17 `bl`, 2 `b` and 4 words (3 with `chain`), a Settings menu | Yes (2026-10-17) |
| [Dark theme](#dark-theme) | Resource data | Patches > iPod Appearance | BMap, View and Type bytes | Yes |
| [Dark Mode switch](#dark-mode-switch) | Code and data | Patches > iPod Appearance | 1 `b` and 2 vtable words, a compressed table and a menu | Version 1.1: yes (28 October 2026). Version 2.0: yes (3 November 2026). Accent colour: not tested on a real iPod |
| [Move of rsrc](#move-of-rsrc) | Partition layout | Automatic | 1 directory entry | Yes |

## The build sequence

iPodFirm does not change the opened file. It keeps the edits in memory and makes a new firmware partition when you save, flash, export an `.ipsw` or start the emulator. `AppModel.outputOSOS` in [AppModel.swift](../mac/Sources/iPodFirm/AppModel.swift) does these steps in this sequence:

1. Start with the osos of the editor. This osos has the picture and text edits.
2. Apply the appearance:
   - Light: no change.
   - Dark: apply the theme changes (`ImportedTheme.apply`).
   - Switch on iPod: run `DarkMode.build`.
3. Apply the switched-on patches (`Patcher.apply`), sorted by name.
4. Apply the software version (`FirmwareVersion.apply`), if it is not 1.3.

Then `AppModel.outputPartition` moves rsrc if osos is larger (`FirmwarePartition.makeRoom`). Then it replaces osos and calculates the new checksum (`replaceImage`).

Each step examines the bytes before it changes them. A step that finds unexpected bytes stops the build with an error. No partial result goes to the iPod.

## Picture replacement

**User interface.** Pictures pane: "Replace…", "Export PNG…", "Export All…" and "Import Folder…". The "Dark Theme" switch shows the pictures of the selected dark theme.

**Change.** `Picture.encode` in [Pictures.swift](../mac/Sources/IPodFWKit/Pictures.swift) writes new pixel bits into the BMap data. It does not change the 28-byte header or the row padding.

**Limits.**

- The new image must have the same width and height as the old picture.
- The pixel format does not change. iPodFirm converts the image to RGB565, ARGB4444 or grey levels.
- A grey picture (1, 2 or 4 bits) loses colour.

An edit of a dark theme picture goes into the theme file, not into osos. Refer to [Edits of the dark theme](#edits-of-the-dark-theme).

## Text replacement

**User interface.** Text pane. A gauge shows the free bytes of each language.

**Change.** `Resources.writeStrings` in [Resources.swift](../mac/Sources/IPodFWKit/Resources.swift) packs all the strings of one language block again. Each string is UTF-8, ends with a zero byte and starts on a 4-byte boundary. The function writes the new offsets and sizes into the resource table.

**Limits.**

- The strings must fit in the area that the language already has.
- To make one text longer, make other text in the same language shorter.
- The function refuses an unknown string ID.

## Software version

**User interface.** Patches pane > Software Version. The section "Letters" shows the letter of each patch:

- "Show a different version on the About screen", with a text field (for example `1.3.1`).
- "Add a letter for each switched-on patch".

Both settings are off by default.

**Ghidra result.** The firmware does not keep the text "1.3". `FUN_0009ee70` makes a version object. The instruction `mov r1, #1` at 0x9ee90 gives the major number. The instruction `mov r2, #0x30` at 0x9ee94 gives the minor number and the fix number (`minor << 4 | fix`). The version object writes the text. It can add only the stage texts "d", "a", "b" and "fc" (`FUN_00188d94`, table 0x4fc298).

**Change without letters.** `FirmwareVersion.apply` in [FirmwareVersion.swift](../mac/Sources/IPodFWKit/FirmwareVersion.swift) replaces the two `mov` instructions. It first makes sure that they are `0xe3a01001` and `0xe3a02030`.

**Change with letters.** The function writes a new body into `FUN_0009ee70` (0x9ee70–0x9eed8, 104 bytes). First, it makes sure that the 104 bytes are the Apple bytes. The new body does these steps:

1. It copies a fixed C string at 0x9eea0 into a Pascal string (`FUN_00092948`).
2. It copies the Pascal string into the About string (`FUN_000934c4`).

The Apple function also ends with these two calls.

Each patch has one letter (`version_letter` in `patch.json`). The letters are sorted, for example "1.3.1abkw".

**Limits.**

- The major number is 0–255. The minor number and the fix number are 0–15.
- The text has a maximum of 24 characters (`maxTextLength`).
- iTunes and Finder continue to see version 1.3. The VisibleBuildID that the iPod sends to the computer comes from other instructions. iPodFirm does not change them.

## backlight-60s

**User interface.** Patches pane > 60-Second Backlight, letter `b`.

**Effect.** Settings > Backlight Timer shows Off, 5, 10, 15, 20 and 60 Seconds, and Always On. The 2 Seconds item is removed.

**Research.** Refer to [re/backlight-timer.md](../re/backlight-timer.md).

- The menu is Menu −138 (data at 0x4b069c). It has 7 items of 40 bytes.
- The conversion from the item value to seconds is not in ARM code. A script in `TCmd` 9088 does it with a switch at 0x4ba9f9.
- The value 0x6039 has no Apple item. Its case pushes 0xfffe (at 0x4baa76). The idle controller uses 10 seconds for this value.
- The native method 0x1eb65c writes the seconds to the application object at +0x444. The idle controller (0x1d847c, 0x12ec5c) starts its timer with `seconds × 1000` ms.

**Change.** This patch has no C code. It uses the `bytes` and `strings` keys of `patch.json`:

- The case for 0x6039 pushes 60 (`58 00 3c`) in place of 0xfffe.
- Menu items 1–4 get the value and the string ID of the next item (5, 10, 15 and 20 Seconds).
- Menu item 5 gets the value 0x6039 and the string ID −140.
- String −140 becomes "60 Seconds" in each of the 21 languages that have it. Finnish uses "60s", because "60 s" does not fit in the string area.

**Test status.** The emulator showed the new menu, and the selection operated. The emulator does not model the dimmer, so it cannot measure the backlight time. Real iPod 5.5G (owner, 28 October 2026, version 1.1): the patch operates.

## album-art

**User interface.** Patches pane > Album Artwork, letter `a`, version 3.6. The patch has no option. Version 2.8 removed the option `source` ("Album Thumbnail Source"). `"ui": { "tools": ["album-thumbnails"] }` gives the detail these sections:

- "Thumbnails": "Write Thumbnails to iPod" writes the thumbnail file for the playlists. The albums do not need this file. "Eject iPod" ejects the iPod.
- "Playlist Artwork" sets a custom image for each playlist ("Choose Image…", "Use Automatic", or drag an image).

**Effect.** Each row in an album list and in a playlist list shows a 20 × 20 thumbnail at its left side.

**The thumbnails.**

- An album gets its thumbnail from the artwork that iTunes or Finder put on the iPod: `iPod_Control/Artwork/ArtworkDB` and the 100 × 100 images (format 1028) in `F1028_N.ithmb`. The patch makes a 20 × 20 thumbnail with the average of each 5 × 5 square.
- The cache (version 2.8): when each album with artwork has its thumbnail in memory, the patch writes all thumbnails to `iPod_Control/iTunes/iPodFirmAlbumCache`. The format is the format of `iPodFirmAlbumArt`. At the next start, the patch reads the cache into memory. Then it does not make the album table and does not read the artwork.
- The stamp of the cache is the FNV-1a hash of the first 0x40 bytes of `ArtworkDB` and of the album names of all tracks (the album pool db + 0x138; version 3.1). Versions 2.8–3.0 used the album list of the library, which exists only after the first open of the Albums list. A sync that changes the artwork or the albums gives a different stamp. Then the patch does not use the old cache, fills the covers again and writes a new cache. The patch writes the stamp last, thus a write that stops leaves a cache that the patch does not use.
- The patch writes the cache only if all albums fit in the 1 MB of thumbnails (1310 albums). With more albums, it operates as version 2.7.
- A playlist gets its thumbnail from the file `iPodFirmAlbumArt`, if the file has it (a custom image or the collage of iPodFirm). Else the patch makes a collage (version 3.0): the first 4 different albums of the playlist that have a thumbnail, in a 2 × 2 square, as iPodFirm does. With 1 to 3 albums, the first thumbnail alone. On-The-Go also gets a collage. The patch finds the playlist by the hash of its name in the list at db + 0x2c, and makes the collage again when the item count changes. Refer to [../re/playlist-art.md](../re/playlist-art.md).
- A folder of the patch [playlist-folders](#playlist-folders) gets a fixed folder icon (version 3.4). The icon is in the patch, so it needs no thumbnail file. Refer to [../re/playlist-folders.md](../re/playlist-folders.md#folder-icon).
- An album without artwork on the iPod also uses the file, if the file has it.
- The file is optional. Without the file, the albums show their thumbnails and the playlists show their collages.
- The order for an album (version 2.9): the file, then a valid cache, then the artwork. Thus the file that the owner wrote comes first, and the patch fills the gaps. The cache always has all albums with artwork. If a cover changes in iTunes and the file is not written again, the old cover in the file comes first. Version 2.8 used the order: a valid cache, the artwork, the file.
- The patch makes the album table only at the first album row that needs the artwork, and only if the cache is not valid.
- The open file (version 2.8): the open of `F1028_N.ithmb` is slow if the file has one image for each track (104 MB for 5201 tracks on the iPod of the owner). The patch keeps the file open while it fills covers. It closes the file when the background fill has no more work, 30 s after the last read (2 s in version 2.8), after a failed read, and after a USB session before the next use. The firmware also keeps its own `ArtworkDB` handle open during a USB session (0xb4fe4 frees it with 0x91164).
- Late fill: while the wheel moves, a row whose thumbnail needs the disk shows a grey square of 20 × 20. The table build also waits. At the end of the movement (wheel event with the step 0), the patch calls `view_invalidate` (0x21ac04) on the list, and the visible rows get their thumbnails. A step that is older than 0.3 s does not count as a movement. The real wheel often sends no end event. Thus the patch also uses the 100 ms timer of the list (list + 0xcc) as a tick: a tick 0.3 s after the last step draws the list again. The list uses this timer for the blink of the selected row. The patch takes only the events of a timer that it started, and does not start it in the first 1 s after a key push.
- Background fill: while the wheel does not move, each tick that comes to the visible list of the last album row makes one thumbnail. It starts near that row and stops when the memory for thumbnails is full.

The research is in [../re/album-art-v2.md](../re/album-art-v2.md).

**Load address.** `extended` (refer to [patch-system.md](patch-system.md#the-extended-area)). The compiled code and data are 16412 bytes. Version 3.2 switches the measurement off (`ALBUM_ART_STATS` 0); with it, version 3.1 was 16552 bytes. To measure again, refer to [../re/album-art-v2.md](../re/album-art-v2.md#the-measurement-how-to-switch-it-on-again). Version 1.0 used the fixed area 0x7358d0–0x73658c (3080 bytes). Thus a build with this patch moves rsrc.

**Hooks.**

| Kind | At | Expect | To | Replaced method |
|---|---|---|---|---|
| `word` | 0x66e470 | 0x001bb260 | `hook_row_label_draw` | Draw method of the list-row label class (type 0x3180) |
| `word` | 0x677a14 | 0x00244924 | `hook_label_draw` | Draw method of the general label class (type 0x1580) |
| `bl` | 0xb4ad4 | 0xeb057c60 | `hook_db_loaded` | The call of `log_event` (event 0xf, "Exit Disk Mode") in the music database load 0xb4a64 |
| `word` | 0x6772c0 | 0x0023b704 | `hook_list_event` (`chain`: `list_event`) | Event method (slot +0x30) of the browse-list class 0x677290. `cover-flow` chains to the same word. |

The list-row label scrolls a long title on the highlighted row from a cached image of the text. Thus the patch wraps the complete method `0x1bb260`, not only its call to `0x244924`.

**Firmware calls.** The patch calls these firmware functions:

| Address | Name in the patch | Function |
|---|---|---|
| 0x244924 | `label_draw` | Original draw of the general label |
| 0x1bb260 | `row_label_draw` | Original draw of the list-row label |
| 0x255ac4 | `view_bounds` | Gets the rectangle of a view |
| 0x21a27c | `gc_prepare` | Sets the origin and the clip of the graphics context for a view |
| 0x2106e4 | `gc_set_color` | Sets the fill colour (R, G, B, A bytes) |
| 0x210290 | `gc_set_mode` | Sets the draw mode |
| 0x211a00 | `gc_fill_rect` | Fills a rectangle (only if the target is not RGB565) |
| 0x210114 | `gc_blit` | Copies the pixels of a source gc into a gc |
| 0x09bc6c | `lib_resolve` | Resolves the library reference of the main provider |
| 0x09eff8 | `pool_copy` | Copies the UTF-16 text of a string pool entry |
| 0x25a974, 0x25a8e4 | `fw_alloc`, `fw_free` | Memory from the pool at 0x1081da00 |
| 0x07ccd0, 0x07cd6c | `fw_memset0`, `fw_strcpy` | Memory and string functions |
| 0x08f38c, 0x08f464, 0x08f5c4, 0x08f184 | `file_open`, `file_read`, `file_seek`, `file_close` | File access on the iPod disk |
| 0x213c5c | `log_event` | Adds an event to the usage log |

**Runtime logic.** For each draw of a label, the wrapper does these steps:

1. If the parent of the label (view + 0x10) does not have the class 0x66b4dc (a list cell), call the original method and stop. This rule applies only to the general label. It prevents a thumbnail in Now Playing.
2. Read the element ID at view + 0x1c. Continue only for 0x6421 (album name) or 0x6425 (playlist name).
3. Make the album table if it is not made. Load the thumbnail file if it is not loaded.
4. Make sure that the label is at the left edge (x ≤ 8).
5. Calculate the FNV-1a hash of the text. For a playlist, start the hash with the byte 0x01.
6. For an album, find the hash in the album table (binary search). If the thumbnail is not in memory, read the 100 × 100 image and make the thumbnail.
7. If there is no thumbnail from the artwork, find the hash in the index of the file.
8. Make sure that the label has the height of a list row.
9. Add 24 pixels to the left edge of the label (view + 0x5c). Call the original method. Subtract the 24 pixels again.
10. Call `gc_prepare`. Then draw the thumbnail with one call of the blit 0x210114.

**The album table.** At the first album or playlist label after a database load, the patch makes the table:

1. For each track in the RAM database (db + 0x20, count at db + 0x1c), it calculates the FNV-1a hash of the UTF-8 form of the album name (pool db + 0x138). This is the same hash as the hash of the label text.
2. It sorts the tracks by their dbid (track + 0x108).
3. It reads ArtworkDB through a 32 KB window. For each image (mhii) of a track with an album, it keeps the hash, the file number N and the offset of the format-1028 image.
4. It sorts the entries by the hash and keeps one entry for each album.

The table has 12 bytes for each album with artwork. While the table is made, the patch also uses 12 bytes for each track and the 32 KB window.

**The draw.** The blit gets a source gc: a 0x44-byte gc with zero origins, with a bitmap descriptor around the thumbnail. The descriptor has the same format word as the target, so the blit copies the pixels and does not convert them. The firmware clips with gc + 0x34 and marks the damaged area. If the target is not 16 bits for each pixel with the format 0x565, the patch draws runs of filled rectangles, as version 1.0 did.

Some draws of a highlighted row pass a structure, not text. The first byte of the structure is less than 0x20. Then the patch uses the thumbnail of the last draw of the same view (32 view slots).

**Draw mode.** The patch uses mode 0, which replaces the pixels. Mode 1 darkens. With mode 1 the thumbnails were not visible on the dark theme.

**Reload after a sync.** The firmware loads the music database at the start and after each USB session. The hook at 0xb4ad4 in this load sets a flag. At the next album label or playlist label, the patch clears the flag, makes the album table again and reads the 16-byte header of the file again. If the header changed, it frees the old data and loads the file again. If there was no file, the patch tries to load it again. Without a USB session, the patch does not read the file again.

**Memory.**

- The artwork: the patch makes each thumbnail at its first draw (one read of 20000 bytes) and keeps it. It keeps a maximum of 1 MB of thumbnails (1310 albums). Above this limit, a new thumbnail replaces the oldest one.
- The file: if all its thumbnails are 1 MB or less, the patch loads all of them. Otherwise it keeps a cache of 64 thumbnails.

A mark of the label for a new draw (`view_invalidate` 0x21ac04) during a draw does not start a new draw. Thus the patch cannot delay a read to a later draw. It reads each thumbnail at its first draw.

### The thumbnail file

iPodFirm writes `iPod_Control/iTunes/iPodFirmAlbumArt` on the mounted iPod volume (`AlbumArt.build` in [AlbumArt.swift](../mac/Sources/IPodFWKit/AlbumArt.swift)). All values are little-endian.

| Offset | Size | Content |
|---|---|---|
| 0x00 | 4 | `IFAT` |
| 0x04 | 2 | Version: 1 |
| 0x06 | 2 | Thumbnail size S in pixels (20) |
| 0x08 | 4 | Count N |
| 0x0C | 4 | Stamp: the FNV-1a hash of all the bytes after the header (the entries and the thumbnails) |
| 0x10 | 8 × N | Entries {u32 hash, u32 file offset of the pixels}, sorted by hash |
| then | 2 × S × S × N | The thumbnails, RGB565, row by row |

The hash of an album is FNV-1a of the UTF-8 album name. The hash of a playlist is FNV-1a of the byte 0x01 and the name.

`MusicImport.writeThumbnails` in [MusicImport.swift](../mac/Sources/IPodFWKit/MusicImport.swift) gets the data from the iPod itself:

1. It reads the tracks of `iPod_Control/iTunes/iTunesDB`.
2. For each album, it reads the cover of one of the first three tracks. It reads MP4 tags first, then AVFoundation metadata.
3. For each playlist, it uses the custom image, or a 2 × 2 collage of the covers of the first four albums.
4. It writes the file with an atomic write.

The custom playlist images are PNG files in `iPod_Control/iTunes/iPodFirmPlaylistArt/<FNV-1a of the name, 8 hex digits>.png`. Each image is a centre square of a maximum of 200 × 200 pixels.

### The Now Playing artwork

The large artwork in Now Playing does not come from the patch. RetailOS reads `iPod_Control/Artwork/ArtworkDB` and the files `F1028_1.ithmb` (100 × 100) and `F1029_1.ithmb` (200 × 200). iPodFirm writes these files only for the emulator library (`ArtworkDB.build` in [ArtworkDB.swift](../mac/Sources/IPodFWKit/ArtworkDB.swift)). The layout follows libgpod. On a real iPod, iTunes or Finder writes them.

**Limits.**

- On-The-Go has no thumbnail, because iTunesDB does not contain it.
- A song row never gets a thumbnail, also if the song has the same name as an album.
- Two names with the same FNV-1a hash share one thumbnail. The second name is ignored.

**Test status.** Version 1.0: tested in the emulator and on a real iPod 5.5G, with the light theme and with the dark theme. Version 2.0: tested in the emulator (refer to [../re/album-art-v2.md](../re/album-art-v2.md)). Version 2.1: installed on a real iPod 5.5G with flash storage. The owner reports that the Albums list scrolls more slowly than without the patch, also on the second pass (9 October 2026). Version 2.2: measured on the same iPod on 9 October 2026. Each new album reads its image from the disk in approximately 22 ms, and the first Albums list stops for approximately 0.8 s. With the thumbnails in memory, the patch adds approximately 4–5 % to each row. Refer to [../re/album-art-v2.md](../re/album-art-v2.md). Version 2.3 with "iPodFirm Thumbnail File": tested on the same iPod on 10 October 2026. The owner reports a much better scroll. The stats show one disk read in approximately 1500 album rows. Version 2.4: tested in the emulator (late fill, the row "All", and with `cover-flow` 0.6.1). On the real iPod with the file mode and `cover-flow` 0.6.1 (10 October 2026): no table build at the first open (the slowest album row was 45.6 ms, 813 ms in version 2.3), no fill from the ithmb file, and Cover Flow operated. The artwork mode on the real iPod with the file present (10 October 2026): no grey squares, 26 fills from the ithmb file, but only 2 end events of the wheel in approximately 28 s. Without the file (10 October 2026): the scroll is smooth, but most rows show a grey square until a stop. 768 waits, 5 end events, 5 redraws, 45 fills. Version 2.5 (background fill with type 0xd): on the real iPod, the covers did not load (type 0xd comes only each 3–4 s there). Version 2.6 (the list timer as the tick): tested in the emulator without type 0xd; 0 waits, all covers loaded. Tested on the real iPod with `cover-flow` 0.6.2 on 14 October 2026: the owner reports that it works well. Version 2.8 (the cache and the open file): tested in the emulator on 27 October 2026. The first start filled 138 covers with one file open and wrote the cache. The second start used the cache: no table build, no fill and no grey square. A changed `ArtworkDB` gave a new stamp and a new cache. On the real iPod (27 October 2026): the cache operates, and rows from the cache are as fast as the original draw. A sync made a new cache. The open of the 104 MB `F1028_1.ithmb` takes 0.93 s. During a fill, the 2 s close gave 7 more opens, each a stop of approximately 1 s. Version 2.9 (the file first, the close after 30 s): tested in the emulator on 27 October 2026. The rows came from the file, and the patch still made the complete cache. On the real iPod (27 October 2026): the owner reports that it works great. Version 3.0 (the playlist collages): tested in the emulator on 27 October 2026 with 2 playlists and On-The-Go. On the real iPod (27 October 2026): the collages showed, but the Albums list loaded each cover only after a stop. Cause: Playlists opened before Albums, the album list of the library did not exist, and the patch marked the cache and the album hashes not valid for the session. Version 3.1 corrects this. Emulator (27 October 2026): with Playlists first, the cache loaded, the background fill ran, and after a restart the cache was valid at the Playlists list. On the real iPod (27 October 2026): the owner reports that it works well. Version 3.2 (the measurement off): tested in the emulator on 27 October 2026 (the Albums list and the playlist collages). Real iPod 5.5G (owner, 28 October 2026), version 3.2: the patch operates.

**Measurement build (versions 2.2 and 2.3).** The patch times its parts with `USEC_TIMER` (`ALBUM_ART_STATS 1` in `album_art.c`). After each 256 album or playlist row draws, it writes one record to `iPod_Control/iTunes/iPodFirmAlbumArtStats` with `file_open_rw` (0x08f3f8) and `file_write` (0x08f6f4). The script [../re/album-art-stats.py](../re/album-art-stats.py) shows the records. The write can stop the scroll for a short time. Version 2.3 also records the value of `source`. Version 2.4 also records the waits, the end events and the redraws (record version 3). Version 2.5 also records the background fills (record version 4). The measurement is for the test only. Remove it in a later version.

## sleep-now

**User interface.** Patches pane > Sleep Now, letter `s`.

**Effect.** The Sleep item puts the iPod to sleep at once. On a charger, on USB power or during a voice memo, Sleep operates as in the Apple firmware.

**Problem.** In the Apple firmware, the Sleep item (0x1d83fc) turns the backlight off and starts the idle timer (500 ms). The idle timer handler (0x1d8a40) sleeps only if a gate passes (0x1d938c → 0x1d8444 → 0x1d8670, 0x1d8718). The gate can refuse the sleep for a long time, for example after a computer session. Then the screen stays on and the wheel does not respond. Refer to [re/sleep.md](../re/sleep.md).

**Load address.** 0x73658c. The compiled code is 181 bytes.

**Hooks.**

| Kind | At | Expect | To | Function |
|---|---|---|---|---|
| `word` | 0x69fd2c | 0x001d83fc | `hook_sleep_item` | A table entry that points to the Sleep item handler |
| `bl` | 0x1e8ce8 | 0xebffbdc3 | `hook_sleep_item` | App command 7 (0x1e8cd4) calls the Sleep item handler here |
| `bl` | 0x1ee930 | 0xebfff8d5 | `hook_power_test` | The external-power test in 0x1ee8d0 |

**Runtime logic.**

1. `hook_sleep_item` calls the Apple handler 0x1d83fc.
2. If a voice memo records (byte +0x66 of the object from 0x1c1f5c), it stops.
3. It stops the timers at controller + 0x48 and + 0x74 (0x151c98).
4. It calls 0x1d9308, the sleep part of the timer handler 0x1d8cd0. This part saves the settings, writes the cache and calls the sleep function 0xb43dc.
5. During this call, `hook_power_test` reads the power pins directly, not the saved copy:
   - GPIOL bit 0x08 low: FireWire or charger power.
   - GPIOL bit 0x10 high, and 0x265698 does not return 1: USB power.
6. If it finds power, the Apple behaviour stays: the display stays on and the sleep waits.

Outside a forced sleep, `hook_power_test` calls the Apple test 0x1ecc8c.

**Test status.** In the emulator, the hook ran and the firmware wrote the cache to the disk (ATA 0xCA). Then 0xb43dc turned the display off. The emulator does not model the hardware sleep, so the test stops there. The settings were kept after a restart. Real iPod 5.5G (owner, 28 October 2026, version 1.2): the patch operates. Version 1.3 (selected time), real iPod 5.5G (30 October 2026, app 0.1.189): the iPod starts and plays. The build used the default time. A short time is not tested.

## flash-keep-awake

**User interface.** Patches pane > SSD Mode, letter `k`. The pane shows a warning if the iPod probably has the original hard drive. Refer to [Storage type](#storage-type). The section Storage Time gives the time: 1, 2, 5, 10, 30 (default) or 60 minutes. To change the time on the iPod, flash it again.

**Effect ("SSD mode").**

- The storage stays on for the selected time after each access, not for approximately 1 second.
- When the iPod wakes from sleep, the iPod starts the storage at once.
- Before the storage power goes off, the iPod waits 0.5 seconds.

**Problem.** A flash adapter needs 3–6 seconds to start its cards after a power cut. The Apple firmware cuts the storage power approximately 1 second after the last access. Thus the first song after a pause starts late. The firmware itself needs only approximately 15 ms for a wake. Refer to [re/play-latency.md](../re/play-latency.md).

**Load address.** 0x736480. The compiled code and the variable are 200 bytes. The functions use `__attribute__((minsize))`. Before version 1.2, the load address was 0x736644. The space there was 188 bytes, and the variable made the patch too large.

**Option.** `time` (variable `keep_awake_ms`, in milliseconds). The values are 60000, 120000, 300000, 600000, 1800000 (default) and 3600000.

**Hooks.**

| Hook | Kind | At | Expect | To | Original instruction |
|---|---|---|---|---|---|
| 1 | `bl` | 0x284c7c | 0xe5941018 | `hook_keep_awake_time` | `ldr r1, [r4, #0x18]` in the keep-awake task 0x284b0c |
| 2 | `bl` | 0xb45f4 | 0xeb0412c7 | `hook_after_wake` | `bl 0x1b9118`, the last call of the sleep function 0xb43dc |
| 3 | `bl` | 0x1d871c | 0xebfaf172 | `hook_storage_in_use` | `bl 0x94cec` in the sleep gate |
| 5 | `bl` | 0x23344c | 0xeb00ca1d | `hook_drive_power_off` | `bl 0x265cc8` (power off) in the "set power" method 0x233358 |

Hook 4 is in the separate patch [flash-wake-on-input](#flash-wake-on-input).

**Runtime logic.**

- **Hook 1** is a `naked` function. It loads the time of a type-2 keep-awake message, as the original instruction did. If the time is less than `keep_awake_ms`, it sets `keep_awake_ms`. It does not change 0, 1 or 0xffffffff. It changes only `r1` and `ip`, because the caller uses `r0`, `r2` and `r4` after the hook.
- **Hook 2** calls the original function 0x1b9118. Then it sends "always on" (0x94e6c) and "on for `keep_awake_ms`" (0x94d80) for slot 40. No firmware code uses slot 40 as a constant.
- **Hook 3** replaces the "any slot active" test of the sleep gate. It returns 1 only if a slot is active and its time is 0xffffffff (a client that uses the storage now). A timed slot does not stop the sleep.
- **Hook 5** waits 500 ms (task sleep 0x11c9fc). Then it calls 0x265cc8 with 0 (power off). The firmware sends STANDBY IMMEDIATE before this call. The wait gives the flash card time to complete its writes.

**Why hook 3 is necessary.** The first version had only hook 1. On the real iPod, Sleep then did not operate for 30 minutes. The cause:

1. The helper 0x94d80 sends `time + 1`. A client that releases its slot thus sends 1 ms.
2. Hook 1 changed 1 ms to 30 minutes.
3. The sleep gate refuses the sleep while any slot is active (0x94cec).

The fix has two parts: hook 1 does not change 0, 1 or 0xffffffff, and hook 3 ignores timed slots.

**Limits.**

- More battery use while the storage is on.
- The emulator cannot sleep. Thus hook 2 and hook 3 have no full test in the emulator.
- The owner reported slower scroll in lists with this patch. The emulator showed that the patch code does not run during a scroll. The cause is not known.

**Test status.** The 2-minute version of hook 1 was tested on a real iPod (2 October 2026). Real iPod 5.5G (owner, 28 October 2026, version 1.1, with hooks 2, 3 and 5): the patch operates. Version 1.2 (selected time, new load address), real iPod 5.5G (30 October 2026, app 0.1.189, with 17 patches): the iPod starts and plays. The build used the default time. A short time and Sleep are not tested.

## flash-wake-on-input

**User interface.** Patches pane > Wake Storage on Input, letter `w`. The pane shows the same storage warning as for `flash-keep-awake`. The section Storage Time gives the time that the storage stays on after a wake: 1, 2, 5, 10, 30 (default) or 60 minutes. This selection is separate from the selection of SSD Mode, because each patch also operates alone. Set the same time in the two patches.

**Effect.** When you push a button after a long pause, the iPod starts the storage at once. A turn of the wheel does not start the storage.

**Load address.** 0x736700. The compiled code and the variables are 144 bytes. They end at 0x736790.

**Option.** `time` (variable `wake_ms`, in milliseconds), with the same values as `flash-keep-awake`.

**Hook.**

| Hook | Kind | At | Expect | To | Original instruction |
|---|---|---|---|---|---|
| 4 | `bl` | 0x1d8344 | 0xebffff7c | `hook_user_event` | `bl 0x1d813c` in the UI event handler 0x1d81cc |

0x1d813c starts the idle timer again and turns the display on. The event handler calls it for a button event. It does not call it for the wheel events (codes 0x10 and 0x1c).

**Runtime logic.**

1. Call the original 0x1d813c.
2. Read `USEC_TIMER` (0x60005010). If the time since the last check is less than the check gap, stop.
3. If a keep-awake slot is active (0x94cec), set the check gap to 1 second and stop.
4. Send "always on" and "on for `wake_ms`" for slot 40.
5. Set the check gap to `wake_ms`. The maximum, 3,600,000,000 µs, fits in 32 bits.

The unsigned subtraction is correct when the 32-bit counter wraps (each 71.6 minutes).

**Test status.** Emulator: one button push turned on the storage power 0.05 ms later. 60 wheel steps did not run the hook. Real iPod 5.5G (owner, 28 October 2026, version 1.2): the patch operates. Version 1.3 (selected time), real iPod 5.5G (30 October 2026, app 0.1.189): the iPod starts and plays. The build used the default time. A short time is not tested.

## cover-flow

**User interface.** Patches pane > Cover Flow, letter `c`, version 0.6.9. The patch needs no file of iPodFirm: it uses the albums, the names and the artwork that the iPod already has. The research is in [../re/cover-flow.md](../re/cover-flow.md).

**Effect.**

1. Hold Select in the Albums list for 0.5 s. Cover Flow opens at the selected album.
2. Turn the click wheel. Each 6 wheel ticks move the target one cover (approximately 16 covers for each turn). Each wheel event that moves the target gives the click of the lists, as the Clicker setting gives. A timer moves the covers smoothly to the target: a fast turn catches up quickly, and each stop slows down softly.
3. The centre cover is flat. Four covers at each side are slanted and a little darker. Each cover has a reflection. The album name and the artist (grey) show below the covers, centred, in the font of the list rows. They change when the covers stop.
4. Push Select. The album at the centre opens, as from the list.
5. Push Menu. The Albums list shows again.

The background is white with the light theme and black with the dark theme. On white, the reflections fade to white. The text has the colour of the list rows of the theme.

A short push of Select opens the album as usual. Play/Pause operates as usual. If the iPod shows a new screen (for example Now Playing), Cover Flow closes.

**Debug log.** Versions 0.6.5 to 0.6.7 had a debug log. It measured the open, each frame, each cover load, the timer ticks and the wheel events, and wrote a text file on the iPod. The log found the cause of the slow Cover Flow after a restore with iTunes. Version 0.6.8 removes the log. [../re/cover-flow.md](../re/cover-flow.md#how-to-add-the-debug-log-again) tells how to add it again.

Since version 0.6.4, the patch [up-next](#up-next) can take the hold. At each push of Select in the Albums list, Cover Flow reads `iPod_Control\iTunes\iPodFirmHoldSelect` (`hold_is_cover_flow`). It keeps the push only if the file does not exist or contains '3' (Settings > Hold Select = Cover Flow). Otherwise the push goes to the firmware, and the hold goes to Up Next.

**Load address.** `extended` (refer to [patch-system.md](patch-system.md#the-extended-area)). The compiled code and data are 11384 bytes. Since version 0.6.7, the textures are in columns, so that `draw_cover` reads each column in sequence. Since version 0.6.6, the `.ithmb` file stays open while Cover Flow shows (`art_open`); the close of Cover Flow closes it. The functions that run once for each event or each open have `__attribute__((minsize))`; the pixel loop `draw_cover` stays fast code. The framebuffer copy (153600 bytes), the cover cache (11 covers of 128 × 128, 360448 bytes), the read buffer (80000 bytes) and the placeholder cover come from the allocator 0x25a974 when Cover Flow opens. They are released when it closes. The album table (about 9 bytes for each album) stays in memory while the database does not change. While the table is made, the patch also uses 12 bytes for each track and a 32 KB read window.

**Hooks.**

| Kind | At | Expect | To | Replaced |
|---|---|---|---|---|
| `word` | 0x6772c0 | 0x0023b704 | `hook_list_event` (`chain`: `list_event`) | Event method (slot +0x30) of the browse-list class 0x677290. `album-art` also hooks this word. Since version 0.6.1, the hook has `chain`, so that the two patches operate together. Since version 0.6.2, the hook takes a timer event of the list only in the first 0.3 s after the close of Cover Flow. |
| `word` | 0x6701f0 | 0x001d81cc | `hook_ui_event` | The UI event handler 0x1d81cc |
| `word` | 0x17ef8c | 0x0017ef98 | `hook_display_damage` | The literal of the damage callback, which the display registers at the start |

**Firmware functions.**

| Address | Name in the patch | Function |
|---|---|---|
| 0x23b704 | `list_event` | Original event method of the browse lists |
| 0x1d81cc | `ui_event` | Original UI event handler |
| 0x17ef98 | `display_damage` | Original damage callback |
| 0x1647c0 | `display_server` | Returns the display server |
| 0x164878 | `display_bind` | Binds a layer of the display |
| 0x1650f8 | `display_flush` | Sends the dirty rows to the LCD |
| 0x0c9a84, 0x0c9b58 | `display_lock`, `display_unlock` | The mutex of the display server |
| 0x21ac04 | `view_invalidate` | Marks a view for a new draw |
| 0x13d524 | `dispatch_event` | Event dispatcher |
| 0x1d813c | `ui_activity` | Starts the idle timer again and turns the display on |
| 0x0a69dc | `ui_click` | The click of the lists (follows the Clicker setting) |
| 0x09bc6c | `lib_resolve` | Resolves the library reference of the main provider |
| 0x09eff8 | `pool_copy` | Copies a UTF-16 string from a string pool of the database |
| 0x244924 | `label_draw` | Draws the text of a label (the caption) |
| 0x25a974, 0x25a8e4 | `fw_alloc`, `fw_free` | Memory from the pool |
| 0x07ccd0, 0x07cd6c | `fw_memset0`, `fw_strcpy` | Memory and string functions |
| 0x08f38c, 0x08f464, 0x08f5c4, 0x08f184 | `file_open`, `file_read`, `file_seek`, `file_close` | File access on the iPod disk |

**Runtime logic.**

1. `hook_ui_event` records its first argument (the UI object). The UI handler gets each key event before the list.
2. A push of Select (type 4, key 0x6f) in the Albums list (element ID 0x6382, visible) goes to `hook_list_event`. The hook keeps a copy of the event and does not give it to the firmware.
3. When the firmware reports the hold (type 6 at `hook_ui_event`, 0.5 s after the push), the patch opens Cover Flow. If no type 6 comes, an event at the list 0.7 s after the push (usually its timer, type 9) also opens it. If the release (type 7) comes first, the hook sends the kept push through the dispatcher 0x13d524. The copy has its own vtable with an empty delete slot. `hook_ui_event` skips the copy of the push, because the UI handler had the original. Then the album opens as usual.
4. To open, the patch makes the album table (only the first time, or after the database changed), allocates the memory and copies the framebuffer. It starts at the selected row − 1 (row 0 is "All") if the list has one row more than the table has albums. Else it starts at the first album.
5. Each frame: clear the framebuffer, load the new covers from the centre outward, draw the covers from the farthest to the centre, draw the caption, then bind the layer, set the dirty rows 0–240 under the lock, and flush. The patch does not call the damage callback, because the callback can bind the layer again and wait for itself.
6. While Cover Flow shows, `hook_display_damage` ignores the damage of the firmware. If the Albums list is not visible, it closes Cover Flow and gives the damage to the firmware.
7. A wheel event (type 0xf) moves the target one cover in its direction (event + 0xc) and calls the click 0xa69dc. It does not draw (only the first frame of a movement), so the event handler returns at once.
8. The animation uses the timer of the list (list word 0x33, 100 ms for the list): stop 0x151c98, set 0x151c24 (15 ms), start 0x151694. Each timer event (type 9, event word 2 = the timer) goes to `hook_list_event`. Each tick starts the timer again first, then moves the position 5/8 of the remaining distance (at least 20/256 of a cover) and draws one frame. When the position is at the target, each tick loads one more cover near the centre (centre ± 4), then the timer stops. Each frame loads at most one new cover, the nearest to the centre first. The first frame at the open loads up to 3 covers: the centre and its two neighbours. A cover that is not loaded yet shows the grey square for that frame. If a cover is missing after the first frame, the open starts the timer, and each tick loads one more cover (since version 0.6.3). The caption is drawn one time for each centre album and copied in the other frames. On close, the patch stops the timer and sets 100 ms again. A timer event that comes after the close is swallowed if the repeat count of the list (byte list + 0xf8) is 0, because the list would count down from 255. The patch takes the wheel events, thus it calls 0x1d813c for each of them, as the UI handler does. Then the backlight and the sleep timer start again. The UI handler gets the key events, so it does this for them itself.
9. Select (type 4, key 0x6f) opens the centre album: the patch calls the method +0x138 of the list (0x23a04c, set the selected row) with the row of the album (the album index + 1, because row 0 is "All"). Then it closes Cover Flow and gives the push to the original list method. The push then goes on through the chain, and the firmware opens the selected album. If the list does not have one row more than the table has albums, Select does nothing.
10. The theme: at the open, the patch examines the left margin of the list rows (x = 2, every 8 rows below y = 40) in the copy of the screen. If most pixels are bright (green ≥ 32 of 63), the background is white. Else it is black.
11. Menu (type 4, key 0x6e) closes Cover Flow: the patch puts the framebuffer copy back, sends it, and marks the top view of the list for a new draw (0x21ac04). The UI handler acts on Menu at type 6 or 7, thus `hook_ui_event` swallows these events of the key and decreases the key count at UI object + 0x44 at the release, as 0x1d820c does.

The draw uses no division instruction (the ARM7TDMI has none). `udiv` is a shift-and-subtract loop. A table gives (S << 16) / h for each cover height.

### The data

The album table:

1. The library is `lib_resolve(*(provider + 0x1c))`, with the main provider at RAM 0x1081da18. Library + 0xcf8 is the database.
2. Library + 0xc60 points to the album list of the firmware: one album pool index for each row of the Albums list without "All", in the order of the list. Library + 0xc6c is the count. Thus the patch has the order of the firmware, also for names that start with punctuation or digits.
3. The album pool (db + 0x138) has one UTF-16 entry for each track. The patch makes an FNV-1a hash of the name of each row, and of the album name of each track (the track list starts at db + 0x20, the count is at db + 0x1c, the next track is at track + 4). A binary search over the hashes of the rows gives the row of each track. The first track of a row gives the artist (pool db + 0xe0, index at track + 0x2c).
4. The patch keeps the dbid (track + 0x108) and the row of each track, sorted by the dbid.

The artwork:

1. The patch reads `iPod_Control/Artwork/ArtworkDB` through a 32 KB window: mhfd, mhsd (type 1), mhli, then each mhii. An mhii has the dbid of its track at + 0x14.
2. If the dbid belongs to an album without a 200 × 200 cover, the patch looks at the children of the mhii: a container mhod (type 2) with an mhni gives the offset in the .ithmb file (mhni + 0x14). The patch takes format 1029 (200 × 200, size 80000, the Now Playing artwork). It takes format 1028 (100 × 100, size 20000) only if the album has no 1029 image. The file name (`:F1029_N.ithmb`, UTF-16, in the mhod after the mhni) gives N.
3. At each new cover, the patch reads the image from `iPod_Control/Artwork/F1029_N.ithmb` (or `F1028_N.ithmb`) into the read buffer. Then it makes a 128 × 128 texture, the size of the centre cover. From 200 × 200: the average of 2 × 2 pixels, in packed RGB565. From 100 × 100: bilinear filtering. Thus the centre cover shows 1:1 without steps. An album without artwork gets a grey square with a lighter frame.

Version 0.4 used the 100 × 100 image and enlarged it without filtering. The covers then had visible steps. Emulator times for each new cover (one for each wheel step): the read of 80 KB takes 9.5 ms, and the 2 × 2 average 7.1 ms (a bilinear filter took 15.7 ms). The first frame at the open (5 covers) took 144 ms with the bilinear filter.

The caption:

1. The patch takes the album label (element 0x6421) of the template cell of the list (list word 0x2a, children at + 0x80, count at + 0x7c).
2. For the draw, it attaches the label to the top view and sets its rectangle (view + 0x58: top, left, bottom, right) to the line below the covers. It calls 0x244924 with the name in UTF-8. Then it puts back the parent, the rectangle, the flags and the byte at + 0x1b8.
3. The label draws at the left. The patch then moves the text pixels of the line to the centre. The background is exactly white or black, so each other pixel is text. For the artist line, it also mixes each text pixel halfway to the background (grey).

Before version 0.4, iPodFirm wrote a cover file (`iPod_Control/iTunes/iPodFirmCoverFlow`, 12 MB for 326 albums). Version 0.4 does not read it. You can delete it from the iPod.

**Limits.**

- In the Albums list, a long push of Select does not add the album to the On-The-Go playlist.
- In the album list of one artist, Cover Flow starts at the first album and shows all the albums.
- In the album list of one artist, Select does nothing.
- If the iPod has no image in format 1029 or 1028 for an album, the album shows the grey square.
- If two album names have the same hash, the second album gets no artwork and no artist.

**Test status.** Emulator (8 October 2026), with the emulator test library (6 albums) and a cover file from `MusicImport.writeCoverFlow`:

- A hold of Select opened Cover Flow at the hold event (0.506 s), at the selected album.
- The wheel moved the covers. The covers stopped at the first and at the last album.
- Menu closed Cover Flow. The Albums list showed again, with the highlight.
- A short push of Select (0.3 s) opened the album as usual. A short push of Menu went back as usual.

Real iPod 5.5G (owner, 8 October 2026, version 0.1, 326 albums): a hold of Select opened Cover Flow, the wheel moved the covers, and Menu went back to the Albums list. It also operated with Dark Mode.

Emulator (8 October 2026), version 0.4, with the FolderLibrary (1000 tracks, 138 albums, ArtworkDB with formats 1028 and 1029, no cover file):

- The first 8 rows of the table were "(III)", "<I°_°I>", "1:15 - Single", "10,000 gecs", "2019", "A Brief Inquiry Into On…", "After Laughter", "Ai Need Your Love - Sin…": the order of the Albums list.
- The real covers showed. The caption showed the album name and the artist in the font of the list rows, centred.
- The first open made the table in 35 ms (emulated time; the emulated disk is fast). The next open took no time.

Not tested: version 0.4 on the real iPod, a pop-up or a new screen while Cover Flow shows, and a database from iTunes or Finder.

Real iPod 5.5G (owner, 25–27 October 2026, version 0.6.4, after a restore with iTunes and a new sync): Cover Flow operates, but it is very slow. The open takes several seconds, the frame rate is low, and one album step needs approximately two turns of the wheel. The log of version 0.6.5 showed the cause: the patch opened `F1029_1.ithmb` (416 MB, one image for each of 5201 tracks) for each cover, and each open took 1.1 s. Version 0.6.6 keeps the file open. The log of version 0.6.6 showed 1.1 s only at the open, 30 ms for each cover load and 69 ms for each frame. Word 3 of a wheel event counts the wheel ticks, so version 0.6.6 lost wheel steps. Version 0.6.7 counts the ticks and draws faster. Real iPod (27 October 2026), version 0.6.7: the owner reported that Cover Flow feels very fast. The wheel moves the covers, and a frame takes approximately 80 ms with a cover load. Version 0.6.8 removes the debug log and does not change the function. Real iPod (owner, 28 October 2026), version 0.6.8: Cover Flow operates.

## usb-audio-out

**Effect.** Settings has the item "USB-C Audio" (On/Off) after Clicker. Off is the default after each start: the USB port operates as usual (sync, disk mode, charging). On: the iPod operates as the USB host and plays its music through USB Audio Class 2 headphones (for example the Apple USB-C EarPods) through a USB-C dock or OTG adapter with power. The click wheel sets the volume of the headphones. The buttons of the headphones operate the iPod: volume + and −; the middle button one time is play/pause, two times the next song, three times the previous song. A disconnection pauses the song, and after a new connection the music goes to the headphones again. Off gives the port back to the device mode at once. Since version 1.3, Settings > Main Menu has a USB-C Audio row after Sleep. On puts the item "USB-C Audio: Off" in the main menu, after Settings. The default is Off. A selection of the item switches USB-C Audio On or Off. The item shows the state: Off, On, 44.1 kHz or 48 kHz.

**User interface.** Patches pane > Audio > USB-C Audio, letter `u`. The section "Use USB-C Audio" gives the steps.

**Load address.** `extended`. The compiled code and data are 15924 bytes (version 1.9). The control page (8 KB) and the siTDs (32 KB) come from 0xad80c at the first On, the music buffers (12 KB) at the first route start. After the code, the patcher writes three menus: Settings with the new item, the main menu and Settings > Main Menu.

**Option.** "Sample Rate" (`option_rate`): 44.1 kHz (the default) or 48 kHz (version 1.1). `music_start` sends SET_CUR with the rate of the option first, and the other rate if the headphones refuse it. Apple's converter (0x1e2f60) makes the output rate. At 48 kHz a packet has 192 bytes (two start splits). Version 1.2 sends GET_CUR sampling frequency after SET_CUR. The Settings value shows that rate (see below). Caution (version 1.9, the text of the option): make sure that the Sample Rate matches the music in the library. If the rates are different, Apple's rate converter runs; on the real iPod it used about 12 % of core 0, and the scrolling was less smooth.

**Settings item.** Key 0x600060e8, label ID 0x7e06 ("USB-C Audio"), value text IDs 0x7e07 ("On (44.1 kHz)") and 0x7e08 ("On (48 kHz)"), after Clicker (0x60006088), a copy of Sound Check (`settings_items`). The key 0x600060e8 is not a 32-bit word in osos 1.3. The value is in RAM only, thus each start gives Off. While the music goes to the headphones, the value is "On (44.1 kHz)" or "On (48 kHz)" from GET_CUR (version 1.2). If GET_CUR fails, the value shows the rate that the patch sent. Without a music route, or at a different rate, the value is "On". The text changes when the menu shows again.

**Main menu item (version 1.3).** The method of [album-artists](#album-artists), with these values:

| Menu | Template | New label | Key | Place |
|---|---|---|---|---|
| 24094 (main menu) | Backlight (0x5f93) | 0x7e0a | – | After Settings (0xff84) |
| 24600 (Settings > Main Menu) | Sleep (0xff47) | 0x7e06 | 0x60007e09 | After Sleep |

1. The main menu mask bit is 0x80000000. The firmware does not use it, and it is outside the merge mask 0x1fffffff (0xaf838). `album-artists` uses 0x40000000.
2. `hook_menu_bit` replaces the first instruction of 0x105a04 (label → bit; `sub r0, r0, #0x5c00`) with `chain`. The label 0x7e0a gets the bit. The `bl` hooks of `album-artists` at 0x193488 and 0x19353c call 0x105a04, thus both patches operate together.
3. `hook_set_visible` wraps 0x19ed58 with `chain`. When the UI script sets Artists (0x5f7c) in Menu 24094, the patch also sets 0x7e0a from the bit (0x193470).
4. `hook_activate` (vtable slot 0x6776f8, `chain`) sees a selection of the item 0x7e0a. It switches USB-C Audio, calls 0x239f7c(list, row, 0) to draw the row again, and does not call the Backlight action.
5. `hook_lookup` gives the text of 0x7e0a from the state: "USB-C Audio: Off", "USB-C Audio: On", "USB-C Audio: 44.1 kHz" or "USB-C Audio: 48 kHz".
6. Hooks get and set give the row 0x7e09 its value (On or Off from the bit) and its action (0x19351c, then 'Bool'). For other questions, the patch asks the firmware with the key of Sleep (0x5f94).

A copy of the Settings row (Sound Check) in the main menu is not usable: in the emulator the highlight did not stop on it.

**Hooks.**

| Kind | At | Expect | To | Chain | Function |
|---|---|---|---|---|---|
| `b` | 0x21f254 | 0xe92d40f8 | `hook_lookup` | `lookup_next` | The label "USB-C Audio", the value texts and the main menu text |
| `b` | 0x105a04 | 0xe2400b17 | `hook_menu_bit` | `menu_bit_next` | The main menu bit 0x80000000 for 0x7e0a |
| `b` | 0x19ed58 | 0xe92d401c | `hook_set_visible` | `visible_next` | The main menu item is visible from the bit |
| `word` | 0x6776f8 | 0x0023ca4c | `hook_activate` | `activate_next` | A selection of the main menu item switches On or Off |
| `word` | 0x66c94c | 0x00190b00 | `hook_settings_get` | `get_next` | On or Off (0x602e, 0x602f) |
| `word` | 0x66c950 | 0x001919d8 | `hook_settings_set` | `set_next` | Changes the value, makes the task "USBAudioOut" at the first change, sends 'Bool' |
| `bl` | 0xd399c, 0x10c204, 0xe2be0 | 0xeb0018d2, 0xebff36b8, 0xebffdc41 | `hook_usb_message` | | No USB host message while host mode runs |
| `bl` | 0x170fc8, 0x170fe0 | 0xeb0370fd, 0xeb03712d | `hook_device_start`, `hook_device_stop` | | No device session start or stop while host mode runs |
| `bl` | 0xb9614 | 0x0b032c84 | `hook_mode_stop` | | The USB mode task does not stop host mode at a new VBUS while USB-C Audio is On |
| `bl` | 0xd33b0 | 0xeb0693cf | `hook_host_receive` | | Version 1.4: while the route runs, the USB host task waits at most 8 ticks for a message, not 1 tick |
| `bl` | 0x1320d4, 0x132154 | 0xeb02c3e2, 0xeb02c3c2 | `hook_fill` | | Version 1.9: the fast fill of the packets at equal rates |
| `bl` | 0xd28f0, 0x10e75c | 0xeb005422, 0xebff6487 | `hook_port_status` | | A disconnection stops the route (in USBAudioTask) |
| `bl` | 0x97364 | 0xeb073d0a | `hook_chip_check` | | Full speed while host mode runs |
| `bl` | 0x9741c | 0xeb03cd13 | `hook_irq_install` | | The host interrupt handler while host mode runs; else Apple's 0x18a870 |
| `bl` | 0x9761c, 0x96d14 | 0xeb017997, 0xeb017bd9 | `hook_periodic_insert` | | The periodic insert fix (r1 = r0) |
| `bl` | 0x1320fc, 0x13217c, 0x13218c, 0x1321d0 | as `usb-host-probe` | `hook_usb_send`, `hook_usb_wait_if_sent`, `hook_usb_wait` | | The music route in USBAudioTask |
| `b` | 0xcb118 | 0xe92d40fe | `hook_completion` | | The configuration of a new device (`track_call`) |
| `word` | 0x6c882c, 0x6c8830 | 0x00096f64, 0x00096ffc | `hook_uim_control_endpoint`, `hook_uim_control_transfer` | | The control transfers for `track_call` |

**Logic.**

1. The Settings "set" hook changes `audio_wanted` and returns at once. The task "USBAudioOut" (0x11c808, priority 0x20) does the change.
2. On: the USB mode manager stops the device mode (mode 1; the patch waits at most 2.5 s for Apple's stop of the session while VBUS is present). The patch sets `host_running` and the settings of the host stack (hubs allowed, the composite class EF/02, no storage driver), and the manager starts the host client (mode 2), which starts the host stack.
3. When the headphones are enumerated (`find_audio`, `parse_hid`), the task starts the music route (`music_start`: SET_INTERFACE, the sample rate, the volume, the HID polling, the siTDs, Apple's USB audio source). After a disconnection and a new connection, the route starts again in the same way.
4. The code of the route, the volume, the buttons, the pause at a disconnection and the device hooks is the code of `usb-host-probe` 1.27, without the log, the tones and the test tone.
5. Off: USBAudioTask stops the route (the song pauses), the manager stops the host client (Apple's host stop 0x28608c), the patch restores the settings of the host stack, and the manager starts the device mode if USB power is present.
6. Version 1.4: fewer wakes while the route runs. Apple's USB host task (0xd3390) waits at most 1 tick for a message (0x2782f4), then polls the host stack (0xb9004): about 1000 times each second. `hook_host_receive` gives 8 ticks while `music_mode` is set: about 125 polls each second. A message ends the wait at once. `music_wait` sleeps only above 40 frames in front (`AHEAD_HIGH`), thus USBAudioTask makes two sets of 12 packets in each wake: about 41 wakes each second, not 83.
7. Version 1.9: a fast fill. `bl` hooks at 0x1320d4 and 0x132154, the two calls of Apple's fill 0x1e3064 in the stream loop, go to `hook_fill`. While the route runs, without the test signal (source + 1), and when the input rate (source + 4) equals the output rate (source + 0xc), it does the steps of 0x1e3064 and 0x1e2c90 with word loops: a pool buffer (0xd3e70), the check 0x1e2f74, the frames from the 6-entry queue, the decoder buffer back (0xfed68). Else (the option 48 kHz with a 44.1 kHz song) it calls 0x1e3064, and Apple's rate converter runs. The measurement builds 1.5–1.8 of the branch `usb-audio-speed` (the task "USBMeasure" and the tags 76–78 in iPodFirmUSBLog) are in [re/usb-host.md](../re/usb-host.md#the-slower-scrolling-with-usb-c-audio-on-2026-10-17); version 1.9 does not have them.

**Conflicts.** `usb-host-probe` uses the same hook sites (17 hooks without `chain`). The app does not turn on both (`Patcher.conflicts`; the Patches pane shows "Changes the same place as …"), and a build with both stops at the first shared hook. The test `testUSBAudioOutConflictsWithProbe` keeps this.

**Test status.** Swift and Python tests pass (also with the IPSW). Emulator (2026-10-17): Settings shows "USB-C Audio" Off after Clicker; On and Off change the value; the iPod does not freeze, and the wheel and Now Playing operate after On. After the first Off, the emulator runs at about 0.2× real time: Apple's UIM stop (0x97230) waits with no limit for HCHalted, and the emulator has no USB controller. On the real iPod, Off works. Real iPod, version 1.0 (2026-10-17): **all test steps passed** (the owner: "flawlessly"): Off after the start and a sync; On with the dock and the EarPods, the music without a button press, the volume and the buttons; a pause at a disconnection and Play after a reconnection; Off, then the Mac sees the iPod; On, Off, On again. The iPod charges from the dock while USB-C Audio plays. Version 1.1 with the option 48 kHz: tested on the real iPod (2026-10-17). The owner heard no problems. Version 1.1 kept no log, so the accepted rate was not known. Version 1.2 shows the rate in Settings: not tested yet. Emulator, version 1.3 with `album-artists` 1.3 and `instant-save` (2026-10-17): Settings > Main Menu showed "USB-C Audio" Off after Sleep; On put "USB-C Audio: Off" in the main menu after Settings; a selection changed it to "USB-C Audio: On" at once, and a second selection to Off. Real iPod, version 1.3: not tested yet. Emulator, version 1.4 (a variant with the condition On in place of the route, because the emulator has no USB device): the host poll interval was 8.17 ms (1.02 ms before); the busy instructions with On were 300 M in 30 s (364 M before, 298 M with Off); the menus operated, and Off gave Off. Real iPod, version 1.4 (2026-10-17): still stuttery while USB music plays. The owner's comparison: music through the headphone jack is smooth; On with the music paused is smooth; USB music at 48 kHz and at 44.1 kHz stutters. Emulator, version 1.5: one timing record each second reached the log file. Real iPod, version 1.5 (2026-10-17): the measurement is in [re/usb-host.md](../re/usb-host.md#the-slower-scrolling-with-usb-c-audio-on-2026-10-17). Core 0 idle without scrolling: jack music 58–60 %, USB music 42–44 %, USB route paused 78 %, Off paused 94 %. The longest fill of 12 packets in Apple's code was 1.7–2.6 ms. Emulator, version 1.6: both records each second reached the log (0 USB interrupts, about 980 timeouts of the host task each second without the route). Real iPod, version 1.6 (2026-10-17): 1 USB interrupt each second (the frame list rollover), 0 siTD errors, the host task 90–120 timeouts and no messages each second, and Apple's packet fill about 129 ms in each second (13 % of core 0), with the music playing and paused. Real iPod, version 1.7 (2026-10-17): the sound was correct, the scrolling was not better, and the log had no packet of the fast fill (the fill still about 130 ms each second): `hook_fill` always called Apple's fill. Probable cause: the converter flag. Real iPod, version 1.8 (2026-10-17): the sound correct, the scrolling not better; the option Sample Rate was 48 kHz, thus the converter must run (input 44100 Hz, output 48000 Hz, Apple's fill about 122 ms each second). Real iPod, version 1.8 at 44.1 kHz (2026-10-17): the fast fill made all packets, the fill about 28 ms each second (about 130 ms before), core 0 idle without scrolling 51–55 % (before 42–44 %, the jack 58–60 %); the sound correct; the owner: the scrolling better. Version 1.9 (the fast fill without the measurement), real iPod (2026-10-17): the iPod did not find the headphones and the hub of the dock; after a new connection and On again, the iPod crashed. The cause is not known. Version 1.9, real iPod (2026-10-27): works well (the owner: "works great"). The versions 1.4–1.8 were not tested with a disconnection and a new connection.

## volume-unlimit

**User interface.** Patches pane > Sound > No EU Volume Limit, letter `v`. The pane shows a caution about hearing damage.

**Effect.** On an iPod for the EU, the full position of the volume control gives the full volume. Without the patch, it gives 84% of the full volume. On other iPods, the patch changes nothing. The setting Settings > Volume Limit continues to operate.

**Research.** Refer to [re/volume-limit.md](../re/volume-limit.md).

- `0xa0348` returns bit 0 of the flags word +0x94 of the device information object (0x108710dc). This bit is the EU limit.
- The settings load `0xaf698` writes the maximum volume to its object at +0xb78: 0xd8 (216) with the limit, 0x100 (256) without it.
- `0x88ff8` calculates the output volume as `level × maximum / 100`.
- The iAP reply 0x25 (`0x1a3254`, case 0x24) tells an accessory if the limit is set.

**Change.** This patch has no C code. It uses the `bytes` key of `patch.json`. It is the same change as goPod and iPodWizard:

| At | Expect | Value | Instruction after the change |
|---|---|---|---|
| 0xa0350 | `0100` | `0001` | `and r0, r0, #0` |

Thus `0xa0348` always returns 0. The other match of the iPodWizard pattern, at 0x9f0f8, is a different function. The patch does not change it.

**Test status.** A script applied the change to osos 1.3 and ran the iPodWizard search: "capped" before, "uncapped" after. The emulator cannot show the effect. Not tested on a real iPod. The test needs an iPod for the EU.


## click-speaker-only

**User interface.** Patches pane > Sound > Click Only on the Speaker, letter `p`, version 1.1.

**Effect.** The click of the click wheel plays only from the piezo speaker. It does not play in the headphones. Settings > Clicker continues to turn the click on and off. The other sounds of the iPod do not change.

**Research.** Refer to [re/clicker.md](../re/clicker.md).

- RAM 0x1081d9c4 holds the Clicker word: bit 0 (value 1) the speaker, bit 1 (value 2) the headphones. The default is 3.
- The click 0xa69dc tests bit 1 at 0xa6a90. With bit 1, it plays the click on the audio path (0x1b9168), and also on the piezo if bit 0 is set. Without bit 1, it plays only the piezo tone if bit 0 is set.

**Change.** This patch has no C code. It uses the `bytes` key of `patch.json`:

| At | Expect | Value | Instruction after the change |
|---|---|---|---|
| 0xa6a90 | `020010e3` | `000010e3` | `tst r0, #0x0` |

Thus the click always takes the path without the headphones bit. The size on the iPod is 0 bytes. The Python patcher changed only the byte offset 0xa6a90 of the Apple osos 1.3 image (27 October 2026).

**Test status.** Not tested in the emulator (it has no audio). Real iPod 5.5G (owner, 27 October 2026, version 1.0): the click plays from the piezo speaker and not in the headphones.

## shuffle-fixes

**User interface.** Patches pane > Playback > Shuffle Fixes, letter `f`. Version 1.0 had the name `shuffle-large-library` and corrected only Bugs 1 and 4.

**Effect.** The patch corrects the four bugs of the shuffle in [re/shuffle.md](../re/shuffle.md#known-bugs-in-the-firmware):

- Bug 4: Shuffle Songs and Shuffle Albums operate correctly with more than 32767 songs.
- Bug 1: an index equal to n becomes n − 1. Without the patch, the swap uses the word after the end of the list.
- Bug 2: the seeds 0, 0x7fffffff and 0x80000001 do not stop the generator.
- Bug 3: the inner album shuffle (settings byte `+0x93`) uses the correct positions.

With 32767 songs or fewer, the order for a given seed is the same as without the patch, except in the rare case of Bug 1.

The stock Settings menu has no item that sets `+0x93`. The patch [shuffle-album-mix](#shuffle-album-mix) adds this item.

**Research.** Refer to [re/shuffle.md](../re/shuffle.md#the-patch-shuffle-fixes).

- The random index `0xe5978` cuts n to 16 bits. Then it jumps to the generator `0xaf4b4`, which also cuts its result to 16 bits.
- The callers in `0x94440` give a full 32-bit n and use a 32-bit index.
- `0xe5978` reads the seed one time, with the `bl` at `0xe59a0`.
- In the inner album shuffle, r8 is the start of the album at the `bl` at `0x946d8`.

**Change.** C file `shuffle_fixes.c`, 64 bytes after osos (`load_address` "extended").

| Kind | At | Expect | To |
|---|---|---|---|
| `bl` | 0xe59a0 | `0xebfefd9d` (`bl 0xa501c`, then `b 0x55c`) | `hook_seed`: a bad seed becomes `seed ^ 1` |
| `bl` | 0x946d8 | `0xeb0144a6` (`bl 0xe5978`) | `hook_album_index`: the index plus r8 |

The `bytes` key changes 4 instruction words:

| At | Expect | Value | Instruction after the change |
|---|---|---|---|
| 0xe59b0 | `0518a0e1` | `0510a0e1` | `mov r1, r5` (n with no cut) |
| 0xe59bc | `4118a0e1` | `0000a0e1` | `mov r0, r0` (no operation) |
| 0xaf514 | `0008a0e1` | `070050e1` | `cmp r0, r7` (the index against n) |
| 0xaf518 | `4008a0e1` | `010047a2` | `subge r0, r7, #1` (an index of n becomes n − 1) |

The card game deck shuffle `0x12d494` also uses `0xaf4b4` and `0x55c`. It cuts its own n to 16 bits, n is a maximum of 52, and it has its own call of `0x55c`. Thus the card game does not change.

**Test status.** Emulator (20 October 2026). Version 1.0: with 60 tracks, the order is the same as the stock firmware; with 40000 tracks, the shuffle completes and the state agrees with the model. Version 2.0, 60 tracks: the seed 0 of the emulator becomes 1; a fixed seed gives the stock order; the inner album shuffle (a test firmware sets `+0x93`) gives the first tracks of the model. The emulator has no audio, thus it cannot play the songs. Real iPod 5.5G (owner, 28 October 2026, version 2.1): the patch operates. That test used Next. Version 2.2 (30 October 2026, 5202 songs): a song plays to its end and the next song starts. A library near the limit of a 32 MB iPod is not tested. Static checks with a large library found no fault (refer to [re/shuffle.md](../re/shuffle.md#checks-of-the-shuffle-patches-with-a-large-library)).

## shuffle-album-mix

**User interface.** Patches pane > Playback > Album Mix Shuffle, letter `x`. The patch needs [shuffle-fixes](#shuffle-fixes) (`needs`). The Patches pane turns on Shuffle Fixes with it.

**Effect.** Settings > Shuffle has a 4th value: Off → Songs → Albums → Album Mix → Off. Album Mix plays the albums in a random order, as Albums. It also shuffles the songs in each album. The iPod saves the value with the other settings. Accessories see Album Mix as Albums.

Version 1.2 adds a main menu item "Shuffle: <value>" after Shuffle Songs. Select goes to the next value, as in Settings > Shuffle. The item does not start the music. Shuffle Songs does not change. Settings > Main Menu has a Shuffle row after Shuffle Songs that shows or hides the item. The default is Off. To keep the row after a restart with Menu+Select, install [instant-save](#instant-save).

**Research.** Refer to [re/shuffle.md](../re/shuffle.md#the-patch-shuffle-album-mix).

- Album Mix is the hidden mode `+0x93` of the shuffle. No menu item of the firmware sets it.
- The value text of the Shuffle item is the string `0x6058 + mode`. The string 0x605b exists in no language, but it is the key of the Repeat item. Thus the patch uses the string 0x7e10.
- The Settings controller keeps the mode at `controller + 0x1c`. It loads the mode from 0x9edb0.

**Change.** C file `shuffle_album_mix.c`, 1615 bytes after osos (`load_address` "extended"). After the code, the patcher writes two menus: the main menu and Settings > Main Menu.

| Kind | At | Expect | To |
|---|---|---|---|
| `bl` | 0x1929a0 | `0xebfc3102` (`bl 0x9edb0`) | `hook_get_mode`: 3 if the mode is 2 and `+0x93` is set |
| `bl` | 0x193b9c | `0xebfc2c83` (`bl 0x9edb0`) | `hook_get_mode` |
| `bl` | 0x191eb0 | `0xebfc86d3` (`bl 0xb3a04`) | `hook_set_mode`: writes `+0x93`, marks the change, then calls the setter with mode 2 for Album Mix |
| `word` (`chain`) | 0x66c94c | `0x00190b00` (get method) | `hook_settings_get`: for the Shuffle item in mode 3, the text ID 0x7e10 |
| `b` (`chain`) | 0x21f254 | `0xe92d40f8` | `hook_lookup`: the string 0x7e10 is "Album Mix". The string 0x7e11 is "Shuffle: " and the value. The string 0x7e12 is "Shuffle" |
| `word` (`chain`) | 0x66c950 | `0x001919d8` (set method) | `hook_settings_set`: the Settings > Main Menu row 0x7e13 toggles the bit of the item |
| `word` (`chain`) | 0x6776f8 | `0x0023ca4c` (activate method) | `hook_activate`: Select on the item 0x7e11 sets the next value |
| `b` (`chain`) | 0x105a04 | `0xe2400b17` | `hook_menu_bit`: the item 0x7e11 has the bit 0x20000000 |
| `b` (`chain`) | 0x19ed58 | `0xe92d401c` | `hook_set_visible`: the item follows its bit when the UI script sets Artists |

The `bytes` key changes 0x191e9c from `cmp r0, #2` to `cmp r0, #3`, so that Select wraps after Album Mix.

Before a flash or a restore of a firmware without this patch, the app switches off Album Mix in `iPod_Control/Device/Preferences` (byte 0x8b). Else the firmware still loads the setting and shuffles the songs in each album with no menu item to stop it. Refer to [safety.md](safety.md).

The setter 0xb3a04 does nothing for a change between Albums and Album Mix, because `+0x20` and `+0x92` do not change. For this change the hook calls 0xa983c (the settings are saved at the next sleep) and the refresh 0x11147c.

**Main menu item (version 1.2).** The method of [usb-audio-out](#usb-audio-out), with these values:

| Menu | Template | New label | Key | Place |
|---|---|---|---|---|
| 24094 (main menu) | Shuffle Songs (0x5f9e) | 0x7e11 | – | After Shuffle Songs |
| 24600 (Settings > Main Menu) | Shuffle Songs row (0xff49) | 0x7e12 | 0x60007e13 | After the Shuffle Songs row |

1. The main menu mask bit is 0x20000000. The firmware does not use it, and it is outside the merge mask 0x1fffffff (0xaf838).
2. `hook_activate` reads the mode with `hook_get_mode`, adds 1 (after Album Mix: Off) and calls `hook_set_mode`. It also writes the mode to the Settings controller (`settings_object() + 0x1c`). Then Settings > Shuffle shows the same value. It calls 0x239f7c(list, row, 0) to draw the row again, and does not call the action of Shuffle Songs.
3. The main browser (the `app` of 0xb3a04) is `settings_object() + 0x98`.
4. The text of the item is the string −135 ("Shuffle"), ": " and the value text 0x6058 + mode in the language of the iPod. "Album Mix" is in English.
5. For other questions about the row 0x7e13, the get hook asks the firmware with the key of Shuffle Songs (0x5f9e).

**Test status.** Emulator (20 October 2026, with `shuffle-fixes` and the fixed seed, 60 tracks): Select on Shuffle gives Off → Songs → Albums → Album Mix → Off, and the bytes `+0x20`, `+0x92` and `+0x93` agree with each value. In Album Mix, Shuffle Songs played Test Song 43 first, as the model. The Repeat row stays correct. With all 13 patches that are not `internal` or `test` (20 October 2026): the firmware starts, Music has Album Artists, Settings shows Album Mix, Repeat Off, USB-C Audio Off and Something Comforting Play, and Album Mix gives the same order as the model. Real iPod (20 October 2026): the owner played one album with Album Mix on. The songs of the album played in a random order. With Repeat All, the album plays with no end, and the songs stay shuffled. Not tested yet: a list with many albums, and if each pass has a new order. Version 1.2, emulator (22 October 2026, with `shuffle-fixes`, 60 tracks; again with `album-artists` and `usb-audio-out`): the item is hidden by default. Settings > Main Menu > Shuffle = On shows "Shuffle: Off" after Shuffle Songs. Select gives Songs → Albums → Album Mix → Off. Settings > Shuffle then shows the same value. Select on Settings > Shuffle changes the main menu item too. Shuffle Songs still starts the music with shuffle on. Real iPod 5.5G (owner, 28 October 2026), version 1.2: the patch operates.

## album-artists

**User interface.** Patches pane > Display > Album Artists, letter `l`. The section "Use the Album Artists List" gives the steps on the iPod. The design comes from osos-lab (RepriseOS) for the iPod Classic. The research is in [re/album-artist.md](../re/album-artist.md#album-artists-menu-item-15-october-2026).

**Effect.** The Music menu has an Album Artists item after Artists. It opens a list with one row for each Album Artist, in alphabetical order. A song without an Album Artist is under its Artist. A row opens the albums and the songs of that Album Artist. The Artists list, Now Playing and the sort indexes of the database do not change. The list has no letters for the fast scroll. Since version 1.2, Settings > Main Menu has an Album Artists row under Music. On puts Album Artists in the main menu. The default is Off.

**Load address.** `extended`. The compiled code and data are 3688 bytes (alone: 0x736800–0x737668). After the code, the patcher writes three menus: the Music menu with 11 items (444 bytes; alone at 0x737800), the main menu with 32 items (1284 bytes; at 0x738000) and Settings > Main Menu with 29 items (1164 bytes; at 0x738800). The osos then ends at 0x739000.

**Menu items** (`menu_items`, refer to [patch-system.md](patch-system.md#menu-items)). The copies open the Artists screen, because the firmware finds the action of an item in the item data.

| Menu | Copy of | New label | Key | Position |
|---|---|---|---|---|
| 24440 (Music) | Artists (0xff82, -126) | 0x7e03 | – | After Artists |
| 24094 (main menu) | Artists (0x5f7c) | 0x7e03 | – | After Artists |
| 24600 (Settings > Main Menu) | Artists (0xff5e, -162) | 0x7e04 | 0x60007e05 | After Artists |

**Hooks.**

| Hook | Kind | At | Expect | To | Chain |
|---|---|---|---|---|---|
| A | `b` | 0xd7ea0 | 0xea0000d1 | `hook_mhod22` | – |
| B | `bl` | 0xafc8c | 0xeb009efd | `hook_load_tracks` | – |
| C | `word` | 0x6776f8 | 0x0023ca4c | `hook_activate` | `activate_next` |
| G | `b` | 0x1e7b98 | 0xe92d4010 | `hook_reset` | – |
| H | `b` | 0xa34b8 | 0xe92d4070 | `hook_clear` | – |
| K | `b` | 0x19ed58 | 0xe92d401c | `hook_set_visible` | `visible_next`; default `visible_original` (version 1.3) |
| D | `b` | 0xd080c | 0xe92d5fff | `hook_build` | – |
| E | `bl` | 0x114354 | 0xebfe2d6a | `hook_filter_text` | – |
| L | `word` | 0x66c94c | 0x00190b00 | `hook_settings_get` | `get_next` |
| M | `word` | 0x66c950 | 0x001919d8 | `hook_settings_set` | `set_next` |
| I | `bl` | 0x193488 | 0xebfdc95d | `hook_menu_bit` | – |
| J | `bl` | 0x19353c | 0xebfdc930 | `hook_menu_bit` | – |
| F | `b` | 0x21f254 | 0xe92d40f8 | `hook_lookup` | `lookup_next`; default `lookup_original` (`push {r3-r7, lr}`, then 0x21f258) |

The `b` hooks G, H, K and D replace the first instruction of a function. Each has a wrapper in the patch that runs the replaced `push` and continues at the next instruction.

**Runtime logic.**

1. Hook A replaces the mhod 22 (Album Artist) entry of the jump table of the track parser. Apple's code skips this string. The patch reads it into the artist string pool (track data + 0xe0) with 0x10db84, into a slot on the stack. If the text is not empty and not the text of the Artist (track + 0x2c), `aa_store` keeps the index in a side table. Each track has its own pool index, also for the same text, thus `aa_store` compares the texts. Then the loop continues at 0xd821c.
2. The side table uses open addressing. The key is the track pointer. It grows at 3/4 full (`fw_alloc` 0x25a974). Hook B clears it before each call of the track parser 0xd7888, thus before each load of the database.
3. Hook C is the `activate` method of the menu lists (vtable 0x6775b8 + 0x140). For a list with menu data (list + 0x144), it gets the item of the row with 0x2183ec. If the label of the item is 0x7e03, `aa_pending` is 1. For all other items, `aa_pending` and `aa_browser` are 0. Composers, Genres and Playlists do not run the reset 0x1e7b98, thus this clear is necessary.
4. Hook G is the browser reset 0x1e7b98 at the start of a browse. If `aa_pending` is 1, the native browser of the browse (JS browser + 0x1c) becomes `aa_browser`, and `aa_pending` becomes 0. A reset without a pending selection does not change `aa_browser`, because the main menu item runs the reset two times. Album artist mode is `browser == aa_browser`.
5. Hook D wraps the list build 0xd080c. For field 4 (Artist) and the browser `aa_browser`, `build_album_artists` collects the tracks of sort list 7 that pass the filter 0x1142a8. It takes the Album Artist index of each track, or the Artist index. It removes the same texts with an FNV-1a hash (one pass), sorts the unique names with the text compare 0x91c7c (a heap sort), and joins the names that compare as equal. It writes the indexes to browser + 0xc48, 0 to + 0xc4c (no letter table) and the count to + 0xc50, and keeps the list in `aa_list`. The native code then shows the names (0x9cabc) and selects a row (0xb2620).
6. The browser keeps one Artists list. If the list is not of the current mode, hook D clears it first (0xa34b8). Hook H wraps 0xa34b8: if it frees `aa_list`, `aa_list` becomes 0. With the build, 0xa34b8 is the only code that writes browser + 0xc48, thus `aa_list` is exactly the list of the patch.
7. Hook E replaces the call of the Artist text in the filter. A wrapper passes r5 (the browser). For `aa_browser`, the filter compares the selected name (browser + 0x228) with the Album Artist of the track. The Albums and Songs levels then show the songs of the Album Artist.
8. Hook F gives "Album Artists" for 'Str ' 0x7e03 (the label), U+2003 U+2060 "Album Artists" for 'Str ' 0x7e04 (the indented Settings row, as Str -162), and "Album Artists" for 'Str ' -30 (the title of the Artists screen) while `aa_browser` is set. For all other lookups it calls `lookup_next`.
9. The main menu mask is at (main browser + 0xca0) + 0xb34. Hooks I and J replace the two calls of 0x105a04 (label → bit): the label 0x7e03 gets bit 0x40000000. The firmware does not use this bit, and the default mask (0x0e180201 in the emulator) does not have it.
10. Hook K wraps 0x19ed58 (show or hide an item of a menu). The UI script calls it for each Apple item of the main menu at the start and each time the main menu shows. When it sets Artists (0x5f7c) in Menu 24094, the patch also sets 0x7e03 from the bit (0x193470). Since version 1.3, hook K has `chain`, because `usb-audio-out` 1.3 also hooks 0x19ed58.
11. Hooks L and M give the Settings row its value and its action. The key 0x7e05 is not a label ID, because the list asks the value text with the resource lookup ('Str ', key), and hook F answers the label IDs first. For 'prID' and 'Str ', hook L gives On (0x602e) or Off (0x602f). For all other questions it asks the firmware with the key of Artists (0x5f7c). Hook M switches the bit with 0x19351c and sends the 'Bool' notice (settings method +0x54), as the firmware does at 0x192774.

**Limits.**

- A sync changes the Album Artists only after the iPod reads the database again (as for all lists).
- "Compilations" in Settings does not hide the compilations in the Album Artists list.
- The list has no letter table. The fast scroll operates as with a database without mhod 53.
- The emulator keeps no settings after a cold start. Thus the save of the Main Menu bit is not tested in the emulator.

**Test status.** Emulator (2026-10-16), the 7-track library of the [emulator test](../re/album-artist.md#emulator-test-6-october-2026):

- Music showed Album Artists after Artists.
- Album Artists showed All, Aardvark, Bravo, Echo and Various Artists, with the title "Album Artists".
- Various Artists showed the 3 songs of Zeta Hits. Aardvark showed Apple One and Apple Two.
- After this, Artists showed the 8 track artists. Mike Moe showed only Comp Two.
- Now Playing showed the track Artist (Zulu feat. Kilo) and "2 of 2".
- Genres > Test showed the 8 track artists.
- With `album-art`, `cover-flow` and `something-comforting`, Album Artists and the Settings item "Something Comforting" operated.

Real iPod (owner, 16 October 2026), version 1.0: the Album Artists item showed, and the list was correct. But the iPod stopped for approximately 6 seconds when Album Artists opened.

Version 1.1 corrects the speed. Emulator (2026-10-16), 4000 tracks: the first open after a start took 0.95 s (0.85 s of it is the firmware sort of the Artist order, as for the native Artists list), and each later open 0.11 s (the native Artists list: 0.12 s). Version 1.0 took 1.6 s for each open. The 7-track library gave the same results as version 1.0. Refer to [re/album-artist.md](../re/album-artist.md#speed-16-october-2026).

Real iPod (owner, 16 October 2026), version 1.1: works well.

Version 1.2, emulator (2026-10-16):

- Settings > Main Menu showed "Album Artists" after Artists, with Off. A selection changed it to On.
- The main menu then showed Album Artists after Videos. Before, it did not show it.
- The main menu item opened the Album Artists list. Various Artists showed the 3 songs of Zeta Hits.
- After this, Music > Artists showed the 8 track artists, Music > Album Artists showed the Album Artists, and Genres > Test showed the 8 track artists.
- 4000 tracks: the first open took 0.95 s, a later open 0.10 s (the same as version 1.1).

Real iPod (owner, 16 October 2026), version 1.2: after Settings > Main Menu > Album Artists = On and a restart with Menu+Select, the item was off again. The Apple row Songs had the same result. The firmware saves the settings only at a sleep or a disk change, not at each change (refer to [re/album-artist.md](../re/album-artist.md#the-save-of-the-settings-real-ipod-16-october-2026)).

Real iPod 5.5G (owner, 28 October 2026), version 1.3: the patch operates.

## up-next

**User interface.** Patches pane > Playback > Up Next, letter `n`, version 0.6. The option "Hold Select" gives the value that the iPod uses before the first change in Settings: Cover Flow (default), Play Next, Play Last or On-The-Go. Without the Cover Flow patch, the value Cover Flow acts as Play Next. On the iPod: Settings > Hold Select, after Clicker. Each push of Select moves to the next value. The research is in [../re/play-next.md](../re/play-next.md).

**Effect.** Hold Select on a song, an album or an artist while music plays:

- Play Next: the songs play directly after the current song.
- Play Last: the songs play after the last song of the list that plays now.
- On-The-Go: the songs go into the On-The-Go playlist, as without the patch.
- Cover Flow (only with [cover-flow](#cover-flow)): in the Albums list, the hold opens Cover Flow. In the other lists, the hold does Play Next.

When no music plays, the hold adds the songs to On-The-Go. With Shuffle on, the songs also get the correct play positions.

**The value.** The patch keeps the value in `iPod_Control\iTunes\iPodFirmHoldSelect`: '0' On-The-Go, '1' Play Next, '2' Play Last, '3' Cover Flow. It reads the file at the first View lookup after the start (the first screen). If the file does not exist, it writes the value of the option, so that `cover-flow` reads the same value. At a change, it makes the file again with 0xe468c (as the firmware does for `OTGPlaylistInfo`) and writes the value with 0x8f3f8 and 0x8f6f4. Without the file, it uses the option `hold_default`. The value Cover Flow is available only if the word at 0x6701f0 is not 0x1d81cc; else it becomes Play Next. Only `cover-flow` changes that word.

**Load address.** `extended`. The compiled code and data are 1807 bytes, then the Settings menu.

**Hooks.**

| Kind | At | Expect | To |
|---|---|---|---|
| `bl` | 0x1eb5b4 | 0xebfb097f | `hook_add`: the call of "Add to On-The-Go" (0xadbb8) in its script function 0x1eb5a4. r0 is the browser, r1 the row (−1 for all rows). |
| `b` | 0x21f254 | 0xe92d40f8 | `hook_lookup` (`chain`: `lookup_next`, `chain_default`: `lookup_original`): the strings 0x7e0b "Hold Select", 0x7e0c "Play Next", 0x7e0d "Play Last", 0x7e0e "Cover Flow" |
| `word` | 0x66c94c | 0x00190b00 | `hook_settings_get` (`chain`: `get_next`): the value text of the key 0x7e0f |
| `word` | 0x66c950 | 0x001919d8 | `hook_settings_set` (`chain`: `set_next`): the next value |

The Settings item has the key 0x60007e0f and the label 0x7e0b (`settings_items`, after Clicker). The value On-The-Go uses the firmware string 0x63cc.

**Runtime logic of a hold.**

1. The script function of the hold (0x1eb5a4) calls `hook_add` in place of 0xadbb8.
2. If the value is On-The-Go, or no song plays (play list 0x196418: no track list, or the index + 0x14 is −1), the patch calls 0xadbb8.
3. The patch calls the add method of the play list (vtable 0x66cad4 + 0x10) with the browser, the row, the list of the browser (0x9bb98), its sort (0xa00d0) and its reverse byte (browser + 0xc38). The songs go to the end of the track list.
4. Under the lock of the play list (+ 0x1c), the patch finds the new items (after the old last child of the root):
   - Shuffle off, Play Next: it links the new items after the current item.
   - Shuffle off, Play Last: no change.
   - Shuffle on: it gives the new items the positions (item + 0x24) after the current item (Play Next) or after the last position (Play Last), and adds the count to each later position.
5. It frees the sorted arrays of the track list (0x1137c4) and writes the new index of the current item (0x9e57c (item, 0x33, 0)) to + 0x14.

**Limits.** An item in a group (an audiobook chapter, for example) is not changed: the patch then adds the songs to On-The-Go. The patch has no pop-up menu yet.

**Test status.** Refer to [safety.md](safety.md). Emulator (2026-10-21), see the list in [../re/play-next.md](../re/play-next.md#emulator-tests-of-the-patch). Real iPod (2026-10-21), version 0.4 with `cover-flow` 0.6.4: the Settings item and its value after a restart, Play Next with Shuffle Off and Shuffle Songs (the song plays at the natural end of the current song), an album or an artist, Play Last, the hold in the Albums list with Cover Flow and with Play Next, the value On-The-Go, and a hold with no music (On-The-Go) all passed. The row blinks after a hold, Now Playing shows the new count, the artwork stays correct, and the iPod did not stop or restart. Real iPod 5.5G (owner, 28 October 2026), version 0.5: the patch operates.

## custom-eq

**User interface.** Patches pane > Playback > Custom EQ, letter `q`, version 0.12, 1690 bytes. The user can have up to 5 EQs, each with a name. The section "Custom EQ" has almost no text: tooltips give the details. It has a picker with Add, Rename and Delete, a curve, Simple and Advanced views, Prevent Clipping and Reset Bands. Simple is the default: sliders with fixed bands, Bass (low shelf 100 Hz), Mids (peak 1000 Hz) and Treble (high shelf 8000 Hz). The default is 3 bands, because Apple presets use a maximum of 3 filters. Use All 5 Bands adds Warmth (peak 400 Hz) and Clarity (peak 3000 Hz) after the user agrees to a warning (`CustomEQ.allBandsWarning`, option `all_bands`). Without the option, `CustomEQ.bands` and Python `bands_from_options` set the gain of the 2 other bands to 0, so that the build cannot use them. An imported file that uses these bands shows the same warning. Advanced shows the type, frequency, gain and Q of each band. The two views use the same 5 bands, so the code on the iPod does not change. On the iPod, each name shows in Settings > EQ, sorted with the Apple presets. A name must be different from the other EQs and from the items of the iPod, because the saved selection is the name. To change the bands, flash the iPod again.

**The range of gain.** By default, a band has the range of the Apple presets, −7 to +7.5 dB (`CustomEQ.appleGainRange`, from `applePresets`). Go Beyond Apple's Limits gives −12 to +12 dB for one EQ, after the user agrees to `CustomEQ.fullGainWarning`. Without the agreement, `NamedEQ.activeBands` limits each gain, so the build cannot go past the range. A saved gain stays in the app. An imported file that goes past the range shows the warning.

**Apple presets.** Start From Apple Preset sets the bands from `CustomEQ.applePresets`, in the 3 standard positions, and opens the Advanced view. The app asks first only if the user edited the bands (`CustomEQ.isUnedited`). The maximum difference from an Apple curve is in [re/custom-eq.md](../re/custom-eq.md#the-apple-presets-as-bands). The script `re/fit-apple-presets.py` measures the table.

**Share an EQ.** Export EQ… writes the selected EQ to a `.ipodeq` file. Import EQ… or a double-click on the file reads it. A sheet shows the name and the curve before the app adds a new EQ. If the name exists, the app adds a number. The file is JSON of a maximum of 4 KB with `format` (1), `name`, 5 `bands` (`type`, `frequency`, `gain`, `q`), `preventClipping` and `view`. It has no user data. `SharedEQ.decode` examines each value with the limits of the editor, because a received file is not trusted. The app uploads nothing. The name in the file becomes the name of the new EQ.

**The firmware.** A preset is a list of up to 5 filter numbers. Refer to [re/custom-eq.md](../re/custom-eq.md).

| Site | Kind | Function |
|---|---|---|
| 0xa6d68 | `bl` | `hook_presets` calls 0xa6bd0, then adds each EQ of `custom_eq_list` with 0xd83d0. |
| 0xdbd84 | `b` | `hook_filter` gives the patch records for the numbers 55 to 79, and the firmware records for the other numbers. |
| 0xf90fc | `bytes` | The count function returns 80. |

Each active band of each EQ gets the next filter number (`CustomEQ.library`). 5 EQs with 5 bands use 25 numbers, so the limit of 96 in 0x1446e8 is not a problem. A saved list with more than 5 EQs keeps the first 5. A band at 0 dB is off and uses no CPU time.

**The records.** `CustomEQ.records` (Python `custom_eq.records`) calculates the biquads for 44100 Hz and 48000 Hz at the build, and `CustomEQ.library` writes `custom_eq_records` (25 records) and `custom_eq_list` (5 entries of 70 bytes). The Python build writes one EQ "Custom". By default there is no precut, as in Apple presets, and a strong boost can clip. If Prevent Clipping is on (option `precut` = 1), the app scales the numerator of the first active band, so that the highest point of the curve is 0 dB. The owner found that this always-on precut in version 0.1 made the music sound quiet. The absolute limits are ±12 dB, 20 Hz to 20 kHz, and Q 0.3 to 8.

**Limits.** The EQ operates only on 16-bit music at 44100 Hz or 48000 Hz. The firmware rounds down in its filter loop, so a low band gives a small DC value (−37 PCM counts at 60 Hz +6 dB, −481 at 20 Hz +12 dB). It is not audible. The name of an EQ is the same in all languages.

**Removal.** After a flash without the patch, the saved name has no preset, and the firmware clears the EQ setting (0x9421c).

**Move from an older version.** At the first start, the app moves the bands from `patchOptions` to the EQ "Custom" in `customEQs`. A firmware list from an older version gives the same EQ.

**Test status.** Emulator, version 0.7 (31 October 2026): the firmware starts with 14 EQs and 42 filters, and the list in memory has all the names in sorted sequence with correct values, to filter 96. Version 0.9 repeats the test with 5 EQs and 25 filters. The owner reports that multiple EQs operate (version 0.7, 31 October 2026). The report does not say if an EQ above filter 59 was selected. Emulator, version 0.1 (31 October 2026): the firmware starts, and the list has "Custom" between "Classical" and "Dance" with the value 5500 for one band. Real iPod, version 0.1 (the owner, 31 October 2026): the patch operates. The precut made the music quieter. The band settings are not recorded. App, version 0.4 (the owner, 31 October 2026): export and import, a double-click on the file, and the rejection of a damaged file operate. Version 0.2, the CPU load with 5 bands and USB-C audio are not tested on the real iPod.

## volume-number

**User interface.** Patches pane > Volume Number, letter `e`, version 0.11 (a test version), 24 bytes. It is a test patch: turn on **Enable Test Patches** to see it. It has no option.

**Effect.** The volume bar of Now Playing shows the volume as a white number from 0 to 100, in the middle of the bar, in Podium Sans 16 (bold). The number changes while the owner turns the wheel.

**Research.** Refer to [re/numeric-volume.md](../re/numeric-volume.md).

**Changes.**

| Kind | At | Expect | Value | Meaning |
|---|---|---|---|---|
| bytes | 0x1e8a24 | `0000d2e5` | `0100a0e3` | The test of the switch byte for the `Str` 0x63ef is `mov r0, #1`. |
| bytes | 0x4cb014 | `000000` | `ffffff` | The colour of the Type 24227 (Podium Sans 16, bold, centred) is white. |
| `bl` | 0x1e8a30 | 0xe595240c | `hook_volume_level` | In place of `ldr r2, [r5, #0x40c]`: the number for the `Str` 0x63ef. |

`hook_volume_level` (naked, 6 instructions) gives `(output volume × 100 + 128) >> 8` in r2, where the output volume is app + 0x40c (0 to 256). It does not change the flags. The field app + 0x758 is 0 when the wheel changes the volume, because the slider sets the volume directly. Thus the patch does not use it.

**New element.** `view_elements` adds one `Str` element at the end of the element list of View 24544, the volume bar of Now Playing (96 bytes). The ID is 0x63ef and the data group is 0x6380. The box is 50 × 18 pixels, 17 pixels below the top of the 73-pixel View, with the centre at the centre of the slider (the left edge is 131 pixels). The field at element + 24 is 0x01000a00. The bit 0x01000000 makes the label centre its text up and down (`0x2438bc`). The Type is 24227 (Podium Sans 16, bold, centred). The byte + 92 is 0x0c.

**Colour.** Version 0.9 showed four elements with the Type 24223 (white in Classic Dark): with the byte + 92 = 0 the number was black, and with 0x0c it was white. Version 0.10 used the Type 24227 (black) with 0x0c, and the number was black. Thus a text with the byte 0x0c has the colour of its Type, and a text with the byte 0 is black. Version 0.11 changes the colour of the Type 24227 to white (osos offset 0x4cb014, `bytes` entry). No stock View uses this Type. The black number of the versions 0.2 to 0.6 was the new element itself, with the byte 0. The firmware draws no number of its own.

**Position.** Version 0.9 (Podium Sans 18, a box from 20 to 38) showed the digits about 3 pixels too low and too large. Version 0.10 uses the size 16 and moves the box up by 3 pixels. The patcher puts the new copy of View 24544 after the end of the image. Refer to [View elements](patch-system.md#view-elements).

**Limits.** The copy of the View does not follow the Dark Mode switch. The number is white in each look. White is easy to read on the blue part of the bar and less easy on the light grey part (a low volume). With the Apple limit of the volume (no `volume-unlimit` patch), the highest output volume gives 84.


**Test status.** Swift tests (3 November 2026), with the real firmware: the changed words, the hook, and the copy of View 24544 with the new element. Real iPod (the owner, 3 November 2026): version 0.1 showed no number in Now Playing. Version 0.2 showed the number, but it was always 0, black, cut off at the bottom and not centred. Version 0.3 (Pixo 7, black): the owner asked for the default font, white in the dark looks. Version 0.4 (Podium Sans 18, Type 24223): the size was good, but the number was low in the bar, the bottom of the digits was cut off, and the text was black in the dark look. Version 0.5 (Type 24224, white, and the centring bit): the number did not change, also after a hard reset (the image on the iPod had the new bytes). Version 0.6 (the new element has the ID 0x63f1): no change. Version 0.7 (only the text 0x63f1 is on, and the data group of the new element is 0x2b00, as the slider has): no number at all. Thus the black number came from the request for the ID 0x63ef, and the new element did not draw. Version 0.8 (a probe with four elements and both texts on): the numbers showed, but the bar broke (the new elements were in the middle of the list). Version 0.9 (the owner, 3 November 2026): the bar is normal, the numbers with the byte 0x0c are white, and the others are black. The size is too large and the digits are low. Version 0.10 (the owner, 4 November 2026): the size, the alignment and the font are correct, but the number is black. Version 0.11 (the owner, 4 November 2026): works. The number is white, centred and the right size. Swift tests, with the real firmware: the changed words, one hook, the white Type, and the copy of View 24544 with 6 elements.

## wheel-guard

**User interface.** Patches pane > Wheel Wake Guard, letter `g`, version 0.2, 1115 bytes. It is a test patch: turn on **Enable Test Patches** to see it. It has no option in the app. On the iPod, Settings > Wheel Guard (after Clicker) turns the guard On or Off. A selection of the item changes the value.

**Effect.** When the screen light is off, the wheel does nothing until the owner pushes a button. The time of the screen light is the time of Settings > Backlight Timer. The buttons operate as before. With Backlight Timer Off or Always On, or with Wheel Guard Off, the patch does nothing.

**Research.** Refer to [re/wheel-guard.md](../re/wheel-guard.md).

**Settings item.** Key 0x60007e20, label ID 0x7e21 ("Wheel Guard"), after Clicker (0x60006088), a copy of Sound Check (`settings_items`). The value text is the firmware text "On" (0x602e) or "Off" (0x602f), so it follows the language of the iPod. The label is in English for all languages. The iPod keeps the value in the file `iPod_Control/iTunes/iPodFirmWheelGuard` (one character, `0` or `1`). The patch reads it at the first View lookup. Without the file, the guard is On and the patch writes the file. A selection of the item changes the value, writes the file, and sends the notice `Bool` (method + 0x54 of the settings object), as `up-next` does.

**Hooks.**

| Kind | At | Expect | To | Function |
|---|---|---|---|---|
| `word` (`chain`: `ui_next`) | 0x6701f0 | 0x001d81cc | `hook_ui_guard` | The slot of the UI event handler. `cover-flow` uses the same slot, so the guard chains to it. |
| `b` (`chain`: `lookup_next`, `chain_default`: `lookup_original`) | 0x21f254 | 0xe92d40f8 | `hook_lookup` | The general lookup: the label text, and the first read of the file. |
| `word` (`chain`: `get_next`) | 0x66c94c | 0x00190b00 | `hook_settings_get` | The value text of the item. |
| `word` (`chain`: `set_next`) | 0x66c950 | 0x001919d8 | `hook_settings_set` | The change of the value. |

**Runtime logic.**

1. At the first event, `started` is set and `last_use` is the time now. The time is the microsecond timer 0x60005010.
2. A key push (type 4) sets `last_use`.
3. A wheel event (type 0xf) reads the Backlight Timer at app + 0x444 (the application object is at UI + 0x18). The limit is the time plus 1 second. 0xfffe is 10 seconds. 0, 0xffff and values above 3600 give no limit. If Wheel Guard is Off, there is no limit.
4. If the time since `last_use` is the limit or more, the hook returns 1 and the event stops. `last_use` does not change. Else it sets `last_use`.
5. All other events, and the accepted events, go to the chain.
6. A change of Wheel Guard to On sets `last_use`, so that the wheel works for the first Backlight Timer.

**Limits.** The screen light can still come on at a touch of the wheel. The timer wraps after 71 minutes, and then the wheel works until the next push.

**Test status.** Swift tests (3 November 2026), with the real firmware: the slot points to the hook, the guard chains to `cover-flow`, and the Settings menu has the key after Clicker together with the item of `up-next`. Real iPod, version 0.1 (the owner, 3 November 2026): the guard works. Version 0.2 (the Settings item): not tested on a real iPod.

## battery-display

**User interface.** Patches pane > Battery Display, letter `t`, version 0.11. It is a test patch: turn on **Enable Test Patches** to see it. The option "Display" gives Icon or Icon + Percent (the default). The option "Battery Data" gives Apple or Custom Battery. The option "Smoothing" gives Off (the default) or On. The tool `battery-curve` gives the section "Battery Curve": **Import Log File…** and **Use the Built-In Curve**. This fork does not have the patch `battery-log`. Thus the log file comes from the `upstream/battery-display` branch, or from an earlier log. To change an option or the curve, flash the iPod again.

**Effect.** The status bar shows the Apple battery icon. Below 100 %, the percentage shows inside the icon. At 100 %, the iPod shows only the Apple picture of a full battery. The text uses the Pixo font, size 7, bold and centred, in the middle of the icon body. It is black and has no "%" sign. The icon pictures are the Apple pictures, with no change. The icon body is light in the Apple look, in Classic Dark and in Dark Gray. Thus the black text is easy to read in each look. During a charge, the iPod shows the Apple charge icon with no percentage. With Custom Battery, the battery picture and the percentage use a curve from a larger battery. The firmware logic for a low battery does not change.

**Data bytes.** The patch changes 5 values in each of the Views 25598 and 25599. They are in the `Str` element 0x63fc (the last element, index 27), at element + 36, + 48, + 60, + 72 and + 86:

| At element + | Old | New | Meaning |
|---|---|---|---|
| 36 | 0 | 1 | The top edge of the text: 1 pixel inside the icon. |
| 48 | 0 | 2 | The left edge: 2 pixels inside. |
| 60 | 0 | −3 | The bottom edge: 3 pixels inside. |
| 72 | 0 | −5 | The right edge: 5 pixels inside. The icon tip is at the right. |
| 86 | 24223 | 24171 | The Type of the text: Pixo, size 7, bold, centred, black. |

The text box is then x = 2 to 22 and y = 1 to 10. The text of Pixo 7 is bottom-aligned in this box, so its digits are in the rows 3 to 9, which is the middle of the inner part of the icon (rows 2 to 10). The patch changes no font record (no `Type` resource). The osos offsets of the View values are 0x4e4b00, 0x4e4b0c, 0x4e4b18, 0x4e4b24 and 0x4e4b32 (View 25598), and 0x4e564c, 0x4e5658, 0x4e5664, 0x4e5670 and 0x4e567e (View 25599). Classic Dark and Dark Gray change other bytes of the same elements (colours and + 92), but they keep these bytes.

**Text colour.** Versions 0.8 to 0.10 showed white digits in the dark look. The cause was the switch table of Switch on iPod: it was made from Apple's firmware, and at the start of the iPod it wrote the flag byte + 92 of the text (Classic Dark: 0 to 0x0c) again over the value of the patch. A Pixo text with the flag 0x0c is white, also with a black Type. Version 0.11 sets the byte + 92 to 0 in both Views (osos offsets 0x4e4b38 and 0x4e5684), and the switch table now leaves out the changes at the bytes of a patch (refer to the section Switch on iPod). The `bytes` entry has `also_expect` 0c, because a dark look that the app applied before the patch (Dark) gives 0x0c.

**Fonts.** The firmware finds a font by its family, its size and its style. If the firmware has no font with these values, the lookup gives no font, and the iPod restarts (0x221e24, refer to [../re/battery.md](../re/battery.md)). Use only a font, a size and a bold value that a stock View uses. Pixo size 7 bold is used by the Views 22594, 24658 and 25522 (Type 24170). The alignment byte of a Type is not part of the lookup, so Type 24171 (the centred variant of 24170) uses the same font. The smallest Podium Sans in the firmware is size 14. It is too large for the icon.

**Method.** 4 `bl` hooks. 0xb4abc sets the byte of `_show_voltage` after the read of the switches. The firmware then selects the text child of the battery view. 0x1e8af8 gives the text of the percentage. 0x1ae838 gives the icon value of the battery picture, for Custom Battery in the mode Icon. 0x1ae6b8 shows the icon child (child 4 + the icon value) together with the text child. The icon is the earlier child, so the text is drawn on top of it. At 100 % (the last percentage, or an estimate from the raw value before the first text), the hook shows only the icon child, which is the Apple picture of a full battery. The icon value comes from the last text. Before the first text, the hook calculates it from the raw value. Apple data is the icon value × 5. Custom Battery uses the average of the last 8 raw values, read at most each 30 seconds, and a curve of 16 points. Smoothing uses 32 values and hides a rise of less than 5 %. With Apple data, Smoothing calculates a line between the 15 limits of the firmware table. The patch asks the firmware for the icon value one time for each text, because the firmware lets the icon fall only one step for each call. `BatteryCurve.make` makes a curve from the longest run of a log. The run starts at its highest value.

**Caution.** The built-in Custom Battery curve is provisional. It does not start from a full charge, and it is for one battery. An imported log must start from a full charge and continue until the iPod stops. The app cannot prove this.

**Test status.** Swift tests (3 November 2026), with the real firmware: the data changes, the 4 hook words, no change in any Type resource, and a build after Classic Dark and after Dark Gray. Version 0.3, real iPod 5.5G (owner, 3 November 2026): the percentage showed, but it replaced the icon, and the text was cut ("10…"). Version 0.4: the percentage showed inside the icon, but it was not centred, in the Espy Sans font and too large. Version 0.5 (Podium Sans, size 9, a changed Type record): the iPod restarted again and again at the Apple logo, and a restore was necessary. Version 0.6 (Espy Sans 10, centred): the iPod started and showed the number. Version 0.7 (Pixo 7 bold, box y = 2 to 11): the owner reports that it looks much better, but the number is 1 pixel too low, the icon looks darker, and the number must show only below 100 %. Version 0.8 moves the box up by 1 pixel and shows only the full icon at 100 %. Version 0.8 (owner, 3 November 2026): the digits are white in a dark look, and the owner wants black. Version 0.9 sets the byte + 92 to 0, and version 0.10 sets it to 0x10: the digits stayed white (the switch table wrote 0x0c again). Version 0.11 keeps the byte at 0 with the new rule: works (owner, 4 November 2026).

**Research.** Refer to [re/battery.md](../re/battery.md).

## Storage type

The two flash patches are not for the original hard drive. iPodFirm does not read the storage model. It uses the size of the iPod disk:

- `IPodDisk.likelyOriginalHDD` in [Device.swift](../mac/Sources/IPodFWKit/Device.swift) returns a size if the disk is within 5 GB of 30, 60 or 80 GB.
- Then the Patches pane shows a warning (`hdd_warning`), and asks for a confirmation before it switches on the patch.
- A flash card of a near size (for example 64 GB) also gives the warning. You can then switch on the patch.

An earlier version read the ATA IDENTIFY data in the firmware (a hook at 0x142f94). It was removed on 6 October 2026 to free 205 bytes.

## Dark theme

**User interface.** Patches pane > iPod Appearance:

- "Import iPodWizard Theme…" (also in the File menu).
- The appearance control: Light, Dark or Switch on iPod.
- The Layout control: Stock or Split. Refer to [Split layout](#split-layout).
- The "Dark theme" picker, "Show Import Report" and "Delete Theme…". "Delete Theme…" asks for a confirmation.
- The "Accent Colour" control: 7 colours and a colour panel. Refer to [Accent colour](#accent-colour).

**Built-in themes.** The app has two themes in [themes/](../themes/). The app copies each theme into `~/Library/Application Support/iPodFirm/Themes/`. At each start it compares the copy with the built-in theme. If they differ, the copy gets the changes of the built-in theme and keeps the owner's `edits` (`ImportedTheme.syncBuiltIn`, `ImportedTheme.updatedCopy`). Before 2 November 2026 the copy of an earlier app stayed, so a changed built-in theme did not reach the iPod. "Classic Dark" is the default (`AppModel.defaultThemeName`). "Dark Gray" is the older theme. Both fit "Switch on iPod" since patch version 2.0. Classic Dark comes from the dark builder of the owner. Refer to [../re/classic-dark.md](../re/classic-dark.md). It differs from Dark Gray in these points:

- The theme file has `"keep_apple": []`. Thus the theme keeps its own progress bar pictures (BMap 24342 and 24343). Dark Gray has no `keep_apple` list and keeps Apple's pictures (`ThemeImport.keepApple`).
- The theme file changes the table entry of View 24529 (the charging screen). The entry points at a new element list: a black background and the battery box. The change has the label "View 24529 (table entry)".
- The theme has dark art for the status icons and the charging screen.
- Both themes have changes (in `changes`) for the brightness pictures BMap 24286 and 24287 (the sun icons of the brightness bar). Apple draws the rays in dark grey, so the rays do not show on the black background, and the icons looked like two yellow dots. The changes colour the rays gold (255, 204, 51). The rays are the dark pixels outside the body of the sun (more than 1.2 pixels from the farthest light pixel). The pictures 24294 and 24295 (white suns) are not changed. An update of a built-in theme reaches the owner only through `changes` (`ImportedTheme.updatedCopy` compares `changes`). A change in `edits` stays in the file of the repository and does not reach the copy of the owner. The test `SunIconTests` checks the pixels.
- The scrollbar thumb (BMap 24351, 11 × 11) is the picture of Dark Gray: grey, not blue. The theme file takes its changes for this picture from Dark Gray (`--borrow`, `borrow_pictures`).
- Corrections (3 November 2026, `refine.py`, `ipodfw refine-theme`): the clock faces and hands are Apple's art again, the balls of Brick have a ring in the accent colour, the cells of the Screen Lock have no white line, the dial of the Screen Lock has a dark bezel and knob, the button 22206 is new (flat, with a ring), the icon "New Clock" (24407 and 24408) is new (smooth, ARGB4444), and four screens show the dark background in place of the light metal texture. Refer to [../re/classic-dark.md](../re/classic-dark.md#corrections).

**Accent colour.** The owner can change the blue of Apple to another colour. The control "Accent Colour" in the Dark Theme section sets `AppModel.accent` (the key `accent`, a text `#rrggbb`). The accent works with the appearances Dark and Switch on iPod, and with each theme. The accent #5898e8 is Apple's blue: with it nothing changes, and the build is the same as without the control.

- The selection bar of the Views is a gradient of two colours: 28 64 d0 ff (bottom) and 58 98 e8 ff (top). The theme keeps these colours (`APPLE_HIGHLIGHT`). With an accent, each aligned word with one of these colours in a View element gets the new colours. The top is the accent. The bottom is 0.8 times the accent. No channel of the top is larger than 232 (`MAX_CHANNEL`), as in Apple's blue: a red bar (255, 69, 58) had yellow pixels at its top edge. The owner has not yet tested the limit.
- 23 pictures hold Apple's blue (`Accent.pictures`, for example the rating star, the blue button of the Stopwatch, the selected cell of the Screen Lock and the ring of the balls of Brick). Each pixel that has a saturation above 0.35 and a brightness above 0.15 gets the hue of the accent. The saturation and the brightness change in proportion to Apple's blue. Alpha stays. A pixel never becomes the pure white of the transparent colour of an RGB565 picture. The scrollbar thumb (BMap 24351) is not in the list. Brick, its bricks and the progress bar are not in the list.
- `ImportedTheme.withAccent` (Swift) and `accent.with_accent` (Python) make a derived theme. The derived theme applies the theme to the firmware, changes the accent, and then holds the changes of the theme with the new bytes. It adds changes for the bytes that the theme leaves as Apple's bytes. The derived theme has `keep_apple = []` and `keepsHighlight = false`: the highlight rule must not put Apple's blue back. The file of the theme does not change.
- The build uses the derived theme for Dark and for Switch on iPod (`AppModel.accentedTheme`, with a cache). The accent adds approximately 3600 changes. For Classic Dark with #ff3b30, the switch table has 277,322 bytes (258,354 bytes with Apple's blue), and "Switch on iPod" adds 319,488 bytes (301,056 bytes with Apple's blue). The space below the limit is then 473,088 bytes.
- The iPodFirm list has the key `accent` if the accent is not Apple's blue. The Patches pane then shows a different appearance when the accent on the iPod and the selected accent are not the same.
- A grey accent (saturation 0) makes the selection bar and the pictures grey.

**Source.** An iPodWizard theme is a complete firmware partition for an older firmware, usually 1.2.1. iPodFirm needs the theme and the Apple firmware that the theme came from ("base"). The target is always the Apple firmware 1.3. Refer to [re/dark-theme.md](../re/dark-theme.md).

**Import.** `ThemeImport.make` in [ThemeImport.swift](../mac/Sources/IPodFWKit/ThemeImport.swift) does these steps:

1. It makes sure that the theme and the base are different, and that 90 % of the resources have the same size. Otherwise the base is not the correct firmware.
2. It records program code changes as "skipped". It never applies them.
3. It maps the resources of the base to the resources of the target (`idMap`):
   - Pass 1: the same ID with the same data, or the only resource within ±8 IDs with the same data.
   - Pass 2: the shift of the nearest mapped resource of the same type.
4. For each changed resource, it makes a list of byte changes (`ThemeChange`: offset, old bytes, new bytes):
   - **BMap** with the same header: the changed pixel runs.
   - **BMap** that the theme made larger: the picture goes into the free area after the end of osos, below 0x7F8000 (`ThemeImport.ososLimit`). If all pixels are grey, iPodFirm stores a 4-bit grey copy. Then the resource table entry gets the new offset and size.
   - **View**: the changed fields of each element. A field changes only if the target has the base value. The import translates the resource IDs in the fields.
   - **Type**: each changed 32-bit word, only if the target has the base value.
   - Other types (for example `TCmd` and `Menu`): skipped.
5. It writes the theme file `~/Library/Application Support/iPodFirm/Themes/<name>.ipodtheme` (JSON, format 1).

**The two formats of a theme file.** A file in format 1 holds, for each change, the old bytes and the new bytes. The old bytes are bytes of the Apple firmware, so the repository cannot hold such a file. A file in format 2 holds the SHA-256 of the old bytes in place of the old bytes, so the file has no byte of the Apple firmware. The repository holds the built-in themes in format 2 ([themes/](../themes/)); the app ships them in `Contents/Resources/Themes`. The command `ipodfw strip-theme` writes format 2 from format 1. `withOldBytes` takes the old bytes from the firmware again and checks the hash, so both formats apply the same and both keep an edit of the owner.

**A change after the end of osos.** A change can start after the end of Apple's osos. The built-in Dark Gray theme has a picture at 0x736800, and Apple's osos 1.3 ends at 0x736000. `withOldBytes` uses zeros for the old bytes after the end of osos, because the apply step adds zeros there first. Up to app version 0.1.171, the app stopped with a crash here when the theme was in format 2 (GitHub issue 1). The test `testChangePastTheEndOfOsosDoesNotCrash` checks this case.

**Rules when the theme is applied.**

- Each change is applied only if the bytes are the old bytes. If they are already the new bytes, the change counts as done. Other bytes are an edit of the owner, and the change is left out.
- Pictures 24342 and 24343 (the progress bar in Now Playing) keep the Apple version (`keepApple`). The dark themes make them almost invisible.
- The highlight bar keeps the Apple blue colours `0xFFD06428` and `0xFFE89858` (`appleHighlight`). The grey bar of the theme was difficult to see on the real iPod.

### The View format

A View is a u32 count and a list of elements. Each element has this layout:

| Offset | Content |
|---|---|
| +0 | u32: element size − 4 |
| +4 | u32: flags |
| +8 | Tag, byte-reversed: "BMap", "Str ", "None", "Draw", "Cntl" or "StSt" |
| +12 | i16: resource ID. "BMap" and "Draw" refer to a picture, "Str " to a string, "None" to a sub-View. |
| +60 | u32: height |
| +76, +80 | Colours of the highlight bar (ABGR). Apple 1.3: `0xFFD06428` and `0xFFE89858`. |
| +84 | In a "Str " element: the high i16 is a Type ID (text style). |

Facts from the research:

- View 24069 is the root of the screen. View 24506 is the title bar.
- The theme changes element 0 of View 24506 from `BMap 24379` to `Draw 21997` with a height of 240. Thus the background picture fills the screen behind the list.
- A `Draw` element shows the picture at its own size. It does not stretch or repeat the picture.

### The Menu format

A Menu is a u32 count and items of 40 bytes. +0x18 is the label string ID. +0x1C is the key that the item sends (for example 0x600060b7, Sound Check). [re/backlight-timer.md](../re/backlight-timer.md) gives the full item layout.

### Edits of the dark theme

In the Pictures pane, the "Dark Theme" switch shows the theme pictures. "Replace…" on a theme picture stores the new pixels in the `edits` list of the theme file. An edit replaces each theme change in the same bytes. "Use Theme Picture" removes the edit. The light pictures do not change.

**Limits.**

- 23 Views have fields that do not agree with 1.3. The import report lists them.
- The rating stars in Now Playing stay almost invisible. The source of the star colour is not found.
- The theme 1.2.1 also changes 17 bytes of program code. The changes are not a part of the theme. iPodFirm does not apply them.

**Test status.** Tested on a real iPod 5.5G on 2 October 2026, with and without `album-art`.

## Dark Mode switch

**User interface.** Patches pane > iPod Appearance > Switch on iPod. On the iPod: Settings > Dark Mode.

**Effect.** The firmware starts light. The Dark Mode item changes between light and dark. The iPod saves its settings and restarts.

**Why a restart is necessary.** RetailOS makes its main screens one time, at the start, from the View resources. The views copy the positions, the heights and the colours when the firmware makes them (`FUN_0021a4f4`). A language change does not make the screens again. Thus the patch applies the dark changes at the start, before the first View is read.

**Build.** `DarkMode.build` in [DarkMode.swift](../mac/Sources/IPodFWKit/DarkMode.swift) puts these items after 0x736800, below 0x7F8000:

1. The theme data outside osos (for example the background picture). It is in the image for both modes.
2. The switch table, aligned to 16 bytes.
3. The new Settings menu (Menu 24598), aligned to 16 bytes. The resource table entry points to it.
4. The code of the `dark-mode` patch, aligned to 16 bytes. The build gives the symbol `dark_table` the address of the switch table.

The switch table has this format (little-endian). Version 2.0 of the patch replaced the older table "IFDM" with this one:

| Field | Content |
|---|---|
| u32 | `IFD2` (0x32444649) |
| u32 | Count N |
| u32 | Total size of the table |
| N entries | The new bytes of one change (see below) |

Each entry has these parts:

| Part | Content |
|---|---|
| varint | The address, as a step from the end of the previous entry. Zigzag: 0, −1, 1, −2 … are 0, 1, 2, 3 … The first entry counts from 0. |
| varint | The length × 2, plus 1 if the bytes are an LZ4 block |
| varint | The size of the LZ4 block (only with an LZ4 block) |
| bytes | The LZ4 block, or the bytes |

A varint has 7 bits in each byte, low bits first. A byte with bit 7 set has a next byte. The builder uses an LZ4 block only if it is smaller than the bytes. The table holds the new bytes, not old XOR new. The iPod loads the light osos from the flash at each start, so the patch only changes light to dark. A change that the owner edited is left out.

The builders use the same simple LZ4 compressor: `darkmode.lz4_compress` in [darkmode.py](../src/ipodfw/darkmode.py) and `DarkMode.lz4Compress` in [DarkMode.swift](../mac/Sources/IPodFWKit/DarkMode.swift). Both give the same bytes (the tests `test_lz4_roundtrip_and_known_bytes` and `testLZ4KnownBytes`).

**Decoder.** `walk_table` in [dark_mode.c](../patches/dark-mode/dark_mode.c) goes through the table two times. The first time it changes nothing and examines each entry. The second time it writes. The patch stops at the first pass if one of these is true:

- The table does not start with `IFD2`, or its size is wrong.
- A varint is not complete.
- An address or a length is not below 0x800000.
- An entry would change the table.
- An LZ4 block reads or writes outside its range, or does not give exactly the length.

The iPod then starts in the light mode. The test `test_decoder_in_dark_mode_c_agrees_with_python_and_refuses_bad_tables` compiles this part of `dark_mode.c` with a host compiler and the address sanitizer. It gives 401 tables, one correct and the others with errors. The C code and the Python decoder give the same bytes, and a refused table changes no byte.

**Size.** Patches pane > iPod Appearance > Dark Theme shows the new space for each appearance:

- "Size on iPod (Dark)": the theme data after 0x736800 (`ImportedTheme.addedSize`).
- "Size on iPod (Switch on iPod)": items 1 to 4 above, with the alignment (`DarkMode.addedSize`). It needs the open firmware 1.3.

**Bytes of the patches.** The build applies the patches after the switch table is made. The switch table leaves out each change of the theme that touches a byte that a patch changes (`DarkMode.patchRanges`, the `bytes` section of the patch). This is also correct if the patch writes the value that Apple's firmware has. Without this rule, the table wrote the old value of the theme again when the iPod started in the dark mode, and it undid the change of the patch. The test `testSwitchTableKeepsPatchBytes` makes sure of this. The size that the app shows for Switch on iPod does not include this rule and can be a few bytes too large.

The tooltip of the row "Size on iPod (Dark)" gives the bytes inside osos that the theme changes (`ImportedTheme.changedSize`). These changes use no new space. The measured values for the theme "Dark Gray" are 38,428 bytes (Dark), 311,296 bytes (Switch on iPod, with the compressed table of patch version 2.0; it was 738,593 bytes with the XOR table of version 1.1) and 660,678 changed bytes. For "Classic Dark" the table has 258,354 bytes and "Switch on iPod" adds 301,056 bytes (3 November 2026, after the corrections). The limit of the area is 792,576 bytes (0x736800–0x7F8000; 759,808 bytes before 9 October 2026). The test `testExtendedPatchAfterSwitchBuild` makes sure that `DarkMode.addedSize` agrees with `DarkMode.build`.

The new Settings menu is a copy of the Apple menu with one more item after Clicker (key 0x60006088). The new item is a copy of the Sound Check item (key 0x600060b7) with the key 0x600060e0 and the label ID 0x7e00.

**Hooks.**

| Kind | At | Expect | To | Function |
|---|---|---|---|---|
| `b` | 0x21f254 | 0xe92d40f8 | `hook_lookup` | First instruction of the general resource lookup |
| `word` | 0x66c94c | 0x00190b00 | `hook_settings_get` | "Get" method of the settings object |
| `word` | 0x66c950 | 0x001919d8 | `hook_settings_set` | "Set" method of the settings object |

**Runtime logic.**

- `hook_lookup`, at the first lookup of a `View`: read `iPod_Control\iTunes\iPodFirmDarkMode`. If the first byte is `1`, apply the switch table.
- `hook_lookup`, for `Str ` with ID 0x7e00: return "Dark Mode".
- `hook_lookup`, all other lookups: run `push {r3-r7, lr}` and continue at 0x21f258.
- `hook_settings_get`, for key 0x60e0: return the string "On" (0x602e) or "Off" (0x602f) for the operations `prID` and `Str `.
- `hook_settings_set`, for key 0x60e0:
  1. Write the other value to the file (open for read and write, 0x08f3f8). The open function makes the file if it does not exist.
  2. Save all settings (0x1ee8b8 with the application object at 0x1081da18).
  3. Prepare a restart (0x094e08).
  4. Restart (0x001630). This writes 4 to `DEV_RS` (0x60006004).

**Test status.** Emulator: the item changed the mode in both directions, and the settings were kept. The same result came without the file on the disk. The Swift build and the Python build give the same osos. Real iPod 5.5G (owner, 28 October 2026, `dark-mode` version 1.1): the three appearances Light, Dark and Switch on iPod operate.

## Move of rsrc

**When.** The dark theme and the Dark Mode switch make osos larger than 0x736800. In Apple's layout, rsrc starts there.

**Change.** `FirmwarePartition.makeRoom` in [Partition.swift](../mac/Sources/IPodFWKit/Partition.swift) does this:

- **iPod partition** (it has free space after the last image): copy rsrc to the first all-zero area that fits it, at or after the last image, aligned to 0x800. aupd and hibe do not move. The start code of the iPod can remove the `hibe` entry; the hibernation area then stays in this space as data without a directory entry. Refer to [../re/hibernation-restore.md](../re/hibernation-restore.md). The move does not write into old data. When the partition has no all-zero area for rsrc, the move stops with an error.
- **Firmware file** (no free space): move rsrc and all images after it forward by the same aligned value. The file becomes longer.

Then the function writes the new devOffset into the rsrc directory entry. The content of rsrc does not change.

**Flash.** A firmware file has aupd at a different position than the iPod. `FirmwareFlasher.fitLayout` in [Device.swift](../mac/Sources/IPodFWKit/Device.swift) puts the new osos and rsrc into the layout of the iPod. On the iPod, aupd never moves. When the file and the iPod differ in the hibe image, the result follows the iPod. Thus a file with a hibe image also fits an iPod that a restore reduced to three images.

**Ghidra result.** RetailOS finds rsrc through the directory, by its type and ID. The code loads the tag `crsr` at 0xaf548 and 0x1afe44. Both call 0xfc3bc, which calls 0xc60ec. 0xc60ec reads the directory and selects the entry by type (+4) and ID (+8), not by its index. Rockbox `ipodpatcher` also moves rsrc.

**Test status.** Emulator: yes. Real iPod (2 October 2026): yes. After the iTunes restore (25 October 2026): two flashes moved rsrc to dev 0x4d44000, past the stale hibernation dump, and both started the iPod. Refer to [../re/hibernation-restore.md](../re/hibernation-restore.md#test-on-the-real-ipod-25-october-2026).

**Test status.** Tested on a real iPod 5.5G on 2 October 2026.

## row-marker (removed)

The project removed this test patch on 2026-10-08. The last commit with the patch is a87c3fa. To get it back, run `git checkout a87c3fa -- patches/row-marker`.

The patch drew a red bar, 6 pixels wide, at the left of each label. It showed that the compiler, the linker, the hooks and the draw functions operate. It used the load address 0x7358d0, the same address as `album-art`. Its hooks were a `bl` at 0x1bb434 (expect 0xeb02253a) and the vtable word 0x677a14 (expect 0x00244924), both to `hook_label_draw`. The hook called the label draw 0x244924, then filled a red rectangle with 0x255ac4 (bounds), 0x2106e4 (colour), 0x210290 (mode) and 0x211a00 (fill). `build-app.sh` did not copy it into the app. The tests now use `album-art` for the load address test and a copy of `album-art` for the conflict test.

## Proposed: USB audio

This change does not exist yet. The research found a USB Audio Class 1 source in firmware 1.3. The stock firmware enables it only for an iAP accessory with the Digital Audio lingo. Refer to [re/usb-audio.md](../re/usb-audio.md) for the functions and the open items.

## Split layout

**Function.** The main menu shows the list at the left, and the cover, the song, the artist, the album and the count at the right. Stock Now Playing and all other screens stay stock. The panel needs no code: the elements get their data from the firmware.

**Status.** Tested in the emulator and on a real iPod (31 October 2026). All items operate. The cover sometimes takes approximately 1 s to show, most often after Previous.

**User interface.** Patches pane > iPod Appearance > Layout. Split operates with Light, Dark and Switch on iPod. The pane shows the size.

**Data.** `themes/layouts/Split.ipodtheme` is a theme in format 2. `re/home-screen-views.py` makes it. The build copies it to `Contents/Resources/Layouts`, so it is not in the list of dark themes. It has 2 changes:

1. A new View of 704 bytes at 0x736800, after the patch area.
2. The offset and the size in the table entry of View 24430 (0x337428, 8 bytes).

The first change has a `copy` list. The file holds zeros in these ranges: the 200 bytes of the stock scroll bar and list. At the build, the app takes the bytes from the open firmware and checks each SHA-256. A wrong hash stops the build. Thus the file holds none of these bytes. Six colour bytes have no hash, because a dark theme changes them.

With Dark, the build puts the View after the theme data (`movedLayout`), because the dark background is at 0x736800. The panel text uses Type 24223 (size 18) in place of Type 24227 (size 16), because the dark theme makes only the styles of size 18 white.

With Switch on iPod, the build puts the View after the theme data, in its light form. The table entry stays the same in the 2 modes. The switch table has extra runs for the colours and the text styles of the View. The `dark-mode` patch does not change.

The osos becomes 0x737000 bytes, and rsrc moves, as with the dark theme. The research is in [../re/home-screen.md](../re/home-screen.md).

**Limits.** The Split layout operates only on the original Apple firmware 1.3.

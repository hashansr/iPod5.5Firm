# Handoff: FLAC playback and a Music folder for iPodFirm

This note gives the state of the FLAC project to a new Claude Code session. Read it first. Then read [flac-playback.md](flac-playback.md) and [flac-emulator-recipe.md](flac-emulator-recipe.md).

## Goal

The owner wants these features in iPodFirm, on the stock Apple firmware 1.3 (iPod Video 5.5G):

1. The iPod plays FLAC files. The owner does not want to convert them.
2. The owner copies music to a `Music` folder on the mounted iPod. The iPod plays it. iTunes and Finder are not necessary.
3. The iPod keeps the Apple look and all the patches, for example Dark Mode.

## Decision

Do not write a new operating system. Add patches to RetailOS 1.3, as for the other patches.

- The Apple user interface stays identical, because the Apple code draws it.
- The patch tools, the emulator and the recovery procedure already exist.
- A new operating system needs the Apple pictures and fonts. [CLAUDE.md](../CLAUDE.md) does not allow this in the repository.

## Plan

### Patch 1: FLAC playback (idea 10 in [patch-ideas.md](patch-ideas.md))

1. Find where playback selects the decoder. This is the open task of [flac-playback.md](flac-playback.md).
2. Add a FLAC decoder as a new format.
   - Use a decoder with a licence that agrees with GPL-2.0. The Rockbox FLAC decoder is GPL-2.0 and is made for ARM7TDMI. libFLAC (BSD) is the other choice. Do not copy code from another project without a licence check.
   - Use fixed-point arithmetic. The CPU has no FPU.
   - Put only the hot loop in IRAM if the speed is not sufficient. The Apple MP3 and AAC decoders run from IRAM.
3. Convert the audio to the format of the output.
   - The host list of the firmware gives 48000 Hz as the maximum sample rate (0x176088).
   - The EQ works only with 16-bit audio at 44100 Hz or 48000 Hz ([custom-eq.md](custom-eq.md)).
   - Thus a 24-bit or 88.2/96 kHz file needs a dither to 16 bits and a conversion of the sample rate.
4. Add the seek (fast forward and rewind). Use the SEEKTABLE, or a binary search.
5. Make the iTunesDB track entry visible. The firmware stores a file type in the mhit (offset 0x18) and in the mhod type 6. Find out if the firmware hides an unknown type.
6. Add FLAC to `MusicImport.swift`. It accepts only `.m4a` and `.mp4` now. Read the Vorbis comments and the picture.

Free space: the extended area is 0x736800 to 0x7F8000, and other patches use it. Measure the free space with all patches on before you start.

### Patch 2: a Music folder

The firmware plays only the tracks in `iPod_Control/iTunes/iTunesDB`. The iPod must thus make the database.

1. Stage 1, low risk: let the Mac app scan a folder and write iTunesDB and ArtworkDB. [../mac/Sources/IPodFWKit/MusicImport.swift](../mac/Sources/IPodFWKit/MusicImport.swift) does most of this. Add FLAC. This stage is also the reference for stage 2.
2. Stage 2, the real goal: a patch that runs after the disk mode ends.
   - It shows "Updating library…".
   - It walks `/Music` and reads the tags: Vorbis comments for FLAC, ID3 for MP3, and the MP4 parser of the firmware (0x1ca110) for M4A.
   - It writes iTunesDB and ArtworkDB. It must be incremental, because the owner's iPod has 1 TB of flash storage.
   - Rockbox tagcache is a design reference.
3. Questions to answer first:
   - Does the firmware play a track whose path is not in `iPod_Control/Music/F00`?
   - Can the firmware write to the HFS+ volume of the owner? The FAT code is the better known write path.
   - Which function runs when the USB disk mode ends? This is the hook.

## State on 5 November 2026

| Item | State |
|---|---|
| Branch | `flac-playback-research` (not merged, no pull request) |
| Research note | [flac-playback.md](flac-playback.md). The functions 0x1e738c, 0x145834 and 0x24addc are confirmed in Ghidra. The rest is Static. |
| Emulator recipe | [flac-emulator-recipe.md](flac-emulator-recipe.md) with `make-format-library.py` and `trace-formats.sh`. Nobody has run the recipe. |
| Library script | Tested with `ffmpeg`. The eight libraries and their file type IDs were checked. |
| Trace script | Checked for syntax and with `shellcheck`. Not run. |
| Tests on the real iPod | None. |

## What the research found

- The function 0x1e738c maps the file extension to a kind: `mp3` = 0, `aif`, `afc`, `aiff`, `aifc` = 1, `m4a`, `m4b`, `m4p`, `mp4` = 2. The kinds `.wav`, `.flac` and `.aa` are not known.
- The kinds have three classes with their own vtables: MP3 0x66beb0, AIFF 0x66d234 and M4A 0x6727ec.
- The only user of these classes is the `TrackCacheReadTask` (method 0xe1dbc). It probably finds the start and the size of the audio data. It does **not** probably select the decoder.
- The MP3 and AAC decoders run as tasks with IRAM code (`mp3dec_sync`, `mp4_aacdec_sync`).
- The audio engine has a command switch with 55 entries at 0x24addc. The play commands are 0xd, 0xe, 0x10 and 0x11. The two source slots (0x149e37e4, 0x149e3780) look like user interface objects, not decoders.
- Where playback selects the decoder is **not yet found**.

## Next steps

1. Run the emulator recipe on the Mac. Read the traces. The code blocks that run only for one format show the decoder.
2. Write a tool to compare the `hist` files. The format of `hist`, `regs` and `evlog` is not recorded in this repository. Look at the real files first.
3. Find the decoder selection. Then find the place for the FLAC class.
4. Update [flac-playback.md](flac-playback.md). Copy confirmed results to [../docs/firmware-functions.md](../docs/firmware-functions.md).

## Notes for the work on the Mac

- Ghidra 12.1.4 and the project `osos13` are on the Mac of the owner. Use the guide [../docs/ghidra-guide.md](../docs/ghidra-guide.md).
- The research in the cloud used the same settings: `ARM:LE:32:v4t`, base address 0, `SetArmOptions.java`.
- The cloud session could download Ghidra only after the owner allowed the GitHub download hosts. The command `gh release download` did not work there. This does not apply to the Mac.
- Follow [CLAUDE.md](../CLAUDE.md): STE, no Apple firmware in git, a version and a size for each patch, and no closing of the running app.
- Do not publish any document to a web service.

## Prompt to start the new session

```text
Read re/flac-handoff.md, re/flac-playback.md and re/flac-emulator-recipe.md on the branch
flac-playback-research. Then help me run the emulator recipe and find where RetailOS 1.3
selects the decoder for a track.
```

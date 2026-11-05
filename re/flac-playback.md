# FLAC playback: first research of RetailOS 1.3

This note gives the first research for the patch idea "FLAC playback" (idea 10 in [patch-ideas.md](patch-ideas.md)). The goal is to find how RetailOS 1.3 selects a decoder for a file. A FLAC patch must add one more format at this point.

The addresses are offsets in the osos image. The CPU address of the code is the offset plus 0x10000000.

## Method and status

- Firmware: `iPod_25.1.3.ipsw`, `Firmware-25.6.3`, osos size 0x736000 bytes.
- Tools: `ipodfw` to extract osos, `strings`, and short Python scripts with Capstone (ARM mode, base address 0).
- Evidence level: **Static**. The research did not use the emulator or a real iPod.
- Ghidra 12.1.4 confirmed the functions 0x1e738c, 0x145834 and 0x24addc (project `osos13`, language `ARM:LE:32:v4t`, base address 0). The evidence of these functions is **Ghidra**. The other results are still **Static**.
- The scripts are not in the repository. Repeat each remaining result in Ghidra before you copy it to [../docs/firmware-functions.md](../docs/firmware-functions.md).

## Summary

1. Firmware 1.3 selects a format class from the file extension. The function is at 0x1e738c.
2. The firmware has 3 format classes: MP3, AIFF and M4A. Each class has its own vtable. WAV and Audible do not use this function.
3. The MP3 and AAC decoders run as tasks. Their code, stacks and objects are in IRAM (0x40000000 and up).
4. The audio engine has a command switch with 55 entries at 0x24addc.
5. The research has not yet found where playback selects a decoder. This is the next step.

## The extension table

The function 0x1e738c has the arguments (unused, path, out). It writes a kind to the byte at `out`. It returns 0 if the extension is known, and 1 if not.

| Extension | Kind | Evidence |
|---|---|---|
| mp3 | 0 | Static |
| aif, afc, aiff, aifc | 1 | Static |
| m4a, m4b, m4p, mp4 | 2 | Static |
| any other | no write, returns 1 | Static |

- The extension strings are at 0x1e74e8 to 0x1e7510.
- The code compares the last 3 or 4 characters of the path with a chain of compares. The chain is code, not a data table.
- The function does not know `.wav`, `.flac` or `.aa`.
- The function 0x1e7514 (base, path, out) calls 0x1e738c. For kind 0, 1 and 2 it writes `base + 0x10 * kind` to `out`. It returns 0.

## The three format classes

| Kind | Constructor | Vtable | Slot 0 (parse) | Notes |
|---|---|---|---|---|
| 0 MP3 | 0x18b2e8 | 0x66beb0 | 0x18b148 | Slots 6 and 7 point to IRAM (0x40008c50, 0x40008cec). |
| 1 AIFF | 0x1a1c74 | 0x66d234 | 0x1a1af8 | |
| 2 M4A | 0x1ff0f0 | 0x6727ec | 0x1fef54 | The code at 0x1fef64 loads the constant `moov`. |

- All 3 constructors call the same base constructor 0x1458d0. Then they write their own vtable to the first word of the object.
- The function 0x1e7574 makes the three objects in one block: at +0, +0x10 and +0x20. The function 0x1e7594 destroys them.
- The vtable slots 1 to 7 are different for each class. The slot meaning is not yet known.

## The one caller

The function 0x101814 is the only caller of 0x1e7514 (at 0x101850).

1. It makes the block of three objects (0x1e7574).
2. It gets the object for the path at `this + 0x4c`.
3. It calls 0x145834 (object, path, &a, &b). That function opens a file stream (buffer 0x400 bytes, read mode), calls slot 0 of the object with two output pointers, and closes the stream.
4. It writes the two results to `this + 0x168` and `this + 0x16c`.
5. If the second result is not 0, it sends the event 0x63800032 (call to 0x1300f4).
6. It destroys the block (0x1e7594).

The meaning of the two results is not known. The function reads information from a file. It is possibly not the playback path.

## Decoders in IRAM

The strings `mp3dec_sync` (0x25dbd0) and `mp4_aacdec_sync` (0x25e418) are names of two objects. The constructors are at 0x25db20 and 0x25e370.

| Decoder | Object name | Constructor | IRAM values in the constructor | Value 0x10 |
|---|---|---|---|---|
| MP3 | mp3dec_sync | 0x25db20 | 0x40003714, 0x40004824 | 0x700 |
| AAC | mp4_aacdec_sync | 0x25e370 | 0x40003cb4, 0x40003d08 | 0x2c8 |

- No other name with `dec` is in the image. No name exists for ALAC, AIFF or WAV.
- The EQ code is also in IRAM ([custom-eq.md](custom-eq.md)). Thus the firmware keeps the hot decoder code in IRAM.
- A FLAC decoder in SDRAM is slower than IRAM code. Put only the hot loop in IRAM if the speed is not sufficient.

## The audio engine

- The function 0x24ab48 is the decoder step ([custom-eq.md](custom-eq.md)). It gives each output buffer to the object at `state + 0x909c`.
- This object is a static C++ object at 0x149cb1ac. It is the output side. It is **not** a codec. The pointer comes from `object + 0x44` and is written at 0x2407d0.
- The command switch of the engine is at 0x24addc. It has 55 entries (command 0 to 0x36). The jump table is at 0x24ae34. The default case is 0x24b328.
- The command is the byte at `engine + 0x12f8`. The arguments are at `engine + 0x12fc` and up.
- The task creation and the engine constructor (0x24b6e0 and up) are not yet read.

### The play commands

| Command | Source object | Byte `engine + 0x1954` | Evidence |
|---|---|---|---|
| 0xd | `*(engine + 0x196c)` (slot A) | 0 | Ghidra |
| 0xe | `*(engine + 0x1968)` (slot B) | 1 | Ghidra |
| 0x10, 0x11 | `0x23f178(engine + 0x2e5c)`, which returns `pipeline + 0x78` | 2 | Ghidra |

- All four commands write the source object to `engine + 0x1950`. They copy the arguments to `engine + 0x1958` and up.
- The slots A and B are probably the current song and the next song for gapless play. This is not proved.
- The function 0x249f48 sends an event to a queue. The function 0x249fe4 stops the pipeline and clears flags.
- The commands do not take a file extension or a codec name. The decoder is thus probably part of the source object. The code that makes the objects is not yet found.

## Other facts for the FLAC patch

| Fact | Value | Evidence |
|---|---|---|
| Capability list for the host: AIFF, MP3, WAV, AAC (LC), AppleDRM, AppleLossless, Audible | at 0x176088 | Static |
| Maximum sample rate in the list | 0xbb80 = 48000 Hz | Static |
| Audible codec names | `acelp85`, `acelp16`, `mp332` at 0x25fbb0 | Static |
| WAV (RIFF, WAVE, fmt) code | loads at 0xd55cc, 0x159fc8 | Static |
| AIFF (FORM) code | loads at 0x1dfca0, 0x1e7070 | Static |
| iTunesDB file type | mhod type 6, pool at `db + 0x1bc` ([firmware-functions.md](../docs/firmware-functions.md)) | From earlier notes |

A FLAC file at 88.2 kHz or 96 kHz needs a conversion to 44.1 kHz or 48 kHz. The host list gives 48000 Hz as the maximum.

## Open questions

1. Where does playback select the decoder for a track? The research found the format classes, but not the link from a track to the decoder task.
2. What do the two results of 0x145834 mean?
3. Does the check of the supported formats occur when the database loads, or when the song starts?
4. How do ALAC, AIFF and WAV decode? They have no named decoder task.
5. Does the Broadcom chip take part in the audio decode? The note [firmware-media.md](firmware-media.md) says that the protocol is the same for audio and video.

## Next steps

1. Find the code that writes `engine + 0x1968` and `engine + 0x196c`. Find the classes of these source objects.
2. Find the callers that send the commands 0xd, 0xe, 0x10 and 0x11 to message queue 2.
3. Open 0x18b148, 0x1a1af8 and 0x1fef54 in Ghidra. Find out what they read.
4. Find the reader of the file type in the track record (mhod type 6) and the check that hides unknown formats.
5. Repeat the results of this note in Ghidra. Then update [../docs/firmware-functions.md](../docs/firmware-functions.md).

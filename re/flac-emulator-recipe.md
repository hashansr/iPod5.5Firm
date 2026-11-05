# Recipe: which code plays each audio format

This recipe finds the code that RetailOS 1.3 uses to play MP3, AAC, ALAC, AIFF and WAV files. It also shows what the firmware does with a FLAC file. The result tells us where a FLAC decoder must connect. Refer to [flac-playback.md](flac-playback.md) for the open questions.

The recipe is for the stock firmware 1.3 in the iPodFirm emulator ([emulator.md](emulator.md)). Nobody has run it yet. The script `trace-formats.sh` was checked for syntax only.

## What the runs show

| Run | File | What it shows |
|---|---|---|
| `idle` | none | The code that runs without a song. Use it as the baseline. |
| `mp3`, `aac`, `alac`, `aiff`, `wav` | the format | The code that plays a supported format. |
| `flac` | FLAC | What the firmware does with an unsupported format. |
| `mp3_xyz` | MP3 data, extension `.xyz` | If the decoder depends on the extension or on the data. |
| `aac_as_mp3` | AAC data, extension `.mp3` | The same question, in the other direction. |

- `aac` and `alac` use the same extension (`.m4a`). If their code differs, the decoder selection uses the data in the file.
- If `mp3_xyz` plays, the extension is not necessary. If `aac_as_mp3` fails, the extension is necessary.

## What you need

- A Mac with the iPodFirm app and the emulator installed (Emulator pane, "Install Emulator").
- `ffmpeg` with the encoders for MP3, AAC, ALAC, FLAC and PCM. Install it with `brew install ffmpeg`.
- `uv`, as for the other tools of this repository.
- The stock firmware 1.3 without patches. A patch adds code and changes the result.

## Steps

1. Prepare the emulator drive with no music.
   1. Open the iPodFirm app.
   2. Open the Emulator pane. Set "Music on the test iPod" to "None".
   3. Open the firmware 1.3. Switch off all patches.
   4. Click "Run in Emulator". Wait for the main menu.
   5. Quit the emulator. The drive `ipodfirm-custom.img` is now in the emulator profile.
2. Make the test libraries. Run this command in the root of the repository:

   ```sh
   uv run python re/make-format-library.py ~/format-libs 20
   ```

   The script writes 8 libraries. Each library has one song of 20 seconds.
3. Run the traces. Close the emulator window first. Run this command in the root of the repository:

   ```sh
   re/trace-formats.sh ~/format-libs ~/format-traces
   ```

   - The script runs 9 times. Each run starts the emulator and takes 2 to 4 minutes.
   - To repeat one run, add its name: `re/trace-formats.sh ~/format-libs ~/format-traces aac`.
4. Look at the pictures `NAME-3-playing.png` in the output folder.
   - A song that plays shows Now Playing with a moving time.
   - If a picture shows another screen, the wheel count is wrong. Tell Claude the name of the picture.
5. Send the output folder to Claude. Do not send `base.img`.

## What each run saves

| File | Content |
|---|---|
| `NAME.hist` | The count of instructions in each 64-byte block of code (`IPODFW_PROFILE=1`). |
| `NAME.regs` | The registers at the first 32 calls of 0x145834 (`IPODFW_REGS_AT`). The first register is the object. Its first word is the vtable. |
| `NAME.evlog` | The log with the markers (`IPODFW_MARK_AT`). |
| `NAME.state` | The emulator state at the end. |
| `NAME-*.png` | The screens at four steps. |

The marker byte in `evlog` is the index in this list. The addresses are osos offsets.

| Index | Address | Function |
|---|---|---|
| 0 | 0x1e738c | Extension to format class |
| 1 | 0x101814 | File information for the track cache |
| 2 | 0x145834 | Read the file with a format object |
| 3 | 0x10b894 | Open of the stream |
| 4 | 0x24addc | Command of the audio engine |
| 5 | 0x24ab48 | Decoder step |
| 6 | 0x18b148 | MP3 class, slot 0 |
| 7 | 0x1a1af8 | AIFF class, slot 0 |
| 8 | 0x1fef54 | M4A class, slot 0 |
| 9, 10 | 0x40008c50, 0x40008cec | MP3 class, IRAM methods |
| 11, 12 | 0x1a1e88, 0x1a1e90 | AIFF class methods |
| 13, 14, 15 | 0x1ff144, 0x1ff10c, 0x1ff1a4 | M4A class methods |
| 16 | 0xac6f4 | Play an item |
| 17 | 0xeb610 | Set the song |

## How Claude reads the result

1. Compare each `NAME.hist` with `idle.hist`. The blocks that run only in one format are the decoder of that format.
2. Compare `aac.hist` with `alac.hist`. The blocks that differ show how the firmware tells AAC from ALAC.
3. Compare `flac.hist` with the others. The last new block before the stop shows where the firmware refuses the file.
4. Read the markers in `evlog`. A missing marker 3 means that the firmware refused the file before the open.

## Limits

- The format of the replies to `hist`, `regs` and `evlog` is not recorded in this repository. The script saves the raw replies. Claude writes the compare tool after it sees the files.
- The script goes to the last item of the main menu ("Shuffle Songs") with `wheel 60`. If the menu has another order, the pictures show it.
- The emulator plays a song at approximately 0.7 times real time. The script pauses the song after 15 seconds of host time.
- The emulator has no sound. A song that plays shows a moving time on the screen.
- The control socket measures a button push in host time. A slow emulator can change a short push into a long push ([emulator.md](emulator.md)).

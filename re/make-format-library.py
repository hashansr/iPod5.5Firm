#!/usr/bin/env python3
"""Make one small test library for each audio format. Use the libraries in the emulator.

Usage (from the root of the repository):
    uv run python re/make-format-library.py OUTPUT_FOLDER [SECONDS]

The script needs `ffmpeg` with the encoders libmp3lame, aac, alac, pcm and flac.
Each library has one track. The folder `OUTPUT_FOLDER/NAME/iPod_Control` is ready for the
command `ipod-boot put-files`.

The two control libraries test how the firmware selects the decoder:
- `mp3_xyz`: MP3 data in a file with the extension `.xyz`.
- `aac_as_mp3`: AAC data in a file with the extension `.mp3`.
"""

from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ipodfw.itunesdb import Track, build  # noqa: E402

# name, file extension, ffmpeg codec arguments, iTunesDB file type text, mhit file type ID, MP3 flag
FORMATS = [
    ("mp3", "mp3", ["-c:a", "libmp3lame", "-b:a", "128k"], "MPEG audio file", 0x4D503320, True),
    ("aac", "m4a", ["-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"], "AAC audio file", 0x4D344120, False),
    ("alac", "m4a", ["-c:a", "alac", "-movflags", "+faststart"], "Apple Lossless audio file", 0x4D344120, False),
    ("aiff", "aif", ["-c:a", "pcm_s16be"], "AIFF audio file", 0x41494646, False),
    ("wav", "wav", ["-c:a", "pcm_s16le"], "WAV audio file", 0x57415620, False),
    ("flac", "flac", ["-c:a", "flac"], "FLAC audio file", 0x464C4143, False),
]

# name, source format, new file extension
CONTROLS = [
    ("mp3_xyz", "mp3", "xyz"),
    ("aac_as_mp3", "aac", "mp3"),
]


def encode(path: Path, codec_args: list[str], seconds: int) -> None:
    """Write a stereo sine tone of 44100 Hz. ffmpeg chooses the container from the extension."""
    command = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
               f"sine=frequency=440:sample_rate=44100:duration={seconds}",
               "-ac", "2", "-ar", "44100", *codec_args, str(path)]
    subprocess.run(command, check=True)


def write_library(folder: Path, name: str, audio: Path, extension: str, kind: str, ftype: int,
                  mp3: bool, seconds: int) -> None:
    """Make iPod_Control with one audio file and an iTunesDB with one track."""
    music = folder / "iPod_Control" / "Music" / "F00"
    itunes = folder / "iPod_Control" / "iTunes"
    music.mkdir(parents=True, exist_ok=True)
    itunes.mkdir(parents=True, exist_ok=True)
    target = music / f"T0000.{extension}"
    target.write_bytes(audio.read_bytes())
    track = Track(
        title=f"Test {name}", artist="Test", album="Format Test",
        path=":" + ":".join(target.relative_to(folder).parts), size=target.stat().st_size,
        length_ms=seconds * 1000, track_nr=1, tracks=1, filetype=kind, aac=not mp3)
    database = bytearray(build([track]))
    # `build` writes only the two IDs "M4A " and "MP3 ". Write the ID of this format.
    position = database.find(b"mhit")
    assert position >= 0, "the iTunesDB has no mhit"
    old = struct.unpack_from("<I", database, position + 0x18)[0]
    assert old in (0x4D344120, 0x4D503320), f"unexpected file type ID {old:#x}"
    struct.pack_into("<I", database, position + 0x18, ftype)
    (itunes / "iTunesDB").write_bytes(bytes(database))


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    out.mkdir(parents=True, exist_ok=True)
    sources: dict[str, Path] = {}
    for name, extension, codec_args, kind, ftype, mp3 in FORMATS:
        source = out / f"source-{name}.{extension}"
        encode(source, codec_args, seconds)
        sources[name] = source
        write_library(out / name, name, source, extension, kind, ftype, mp3, seconds)
        print(f"{name}: {source.stat().st_size} bytes")
    by_name = {f[0]: f for f in FORMATS}
    for name, base, extension in CONTROLS:
        _, _, _, kind, ftype, mp3 = by_name[base]
        write_library(out / name, name, sources[base], extension, kind, ftype, mp3, seconds)
        print(f"{name}: control, data of {base}, extension .{extension}")


main()

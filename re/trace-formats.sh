#!/bin/bash
# Play one test song of each audio format in the iPodFirm emulator. Save the traces.
#
# Usage (from the root of the repository):
#   re/trace-formats.sh LIBRARIES OUTPUT [NAME...]
#
# LIBRARIES is the folder that re/make-format-library.py wrote.
# OUTPUT is a new folder for the results.
# NAME is a library name (mp3, aac, alac, aiff, wav, flac, mp3_xyz, aac_as_mp3) or `idle`.
# `idle` starts the emulator and does not play a song. Use it as the baseline.
# Without a NAME, the script runs all libraries and `idle`.
#
# Before you start, read re/flac-emulator-recipe.md. The script was not tested on a Mac.

set -u

LIBRARIES="${1:?Give the folder of the libraries.}"
OUTPUT="${2:?Give a folder for the results.}"
shift 2
if [ "$#" -eq 0 ]; then
  set -- idle mp3 aac alac aiff wav flac mp3_xyz aac_as_mp3
fi

SUPPORT="$HOME/Library/Application Support/iPodFirm"
TOOL="$SUPPORT/emulator-src/target/release/ipod-boot"
PROFILE="$SUPPORT/EmulatorProfile"
DRIVE="$PROFILE/drives/ipodfirm-custom.img"
EMULATOR="/Applications/ipod-emulator.app/Contents/MacOS/ipod-emulator"
SOCKET="/tmp/ipodfirm-trace.sock"

# The addresses are offsets in osos. The index in this list is the marker byte in `evlog`.
MARKS="0x1e738c,0x101814,0x145834,0x10b894,0x24addc,0x24ab48,\
0x18b148,0x1a1af8,0x1fef54,0x40008c50,0x40008cec,0x1a1e88,0x1a1e90,\
0x1ff144,0x1ff10c,0x1ff1a4,0xac6f4,0xeb610"

mkdir -p "$OUTPUT"
for file in "$TOOL" "$DRIVE" "$EMULATOR"; do
  [ -e "$file" ] || { echo "Missing: $file. Read re/flac-emulator-recipe.md, step 1."; exit 1; }
done

# Send one command to the emulator. Write the reply to the standard output.
emu() {
  printf '%s\nquit\n' "$1" | nc -U -w 10 "$SOCKET"
}

# Keep one clean drive. Each run starts from a copy of it.
[ -f "$OUTPUT/base.img" ] || cp "$DRIVE" "$OUTPUT/base.img"

for name in "$@"; do
  echo "=== $name"
  library="$name"
  [ "$name" = "idle" ] && library="mp3"
  [ -d "$LIBRARIES/$library/iPod_Control" ] || { echo "No library: $LIBRARIES/$library"; continue; }

  cp "$OUTPUT/base.img" "$DRIVE"
  "$TOOL" put-files "$DRIVE" "$LIBRARIES/$library/iPod_Control" /iPod_Control || { echo "put-files failed"; continue; }
  rm -rf "$PROFILE/cache/snapshots"
  rm -f "$SOCKET"

  IPOD_EMULATOR_DATA="$PROFILE" IPODFW_RESET_AFTER=1000000000 IPODFW_PROFILE=1 \
    IPODFW_MARK_AT="$MARKS" IPODFW_REGS_AT=0x145834,32 \
    "$EMULATOR" --headless=100000000000000 --control="$SOCKET" >/dev/null 2>&1 &
  pid=$!

  # Wait for the start. The state text has "phase=Running" when the main menu is ready.
  ready=0
  for _ in $(seq 1 300); do
    if emu state 2>/dev/null | grep -q "phase=Running"; then ready=1; break; fi
    sleep 2
  done
  [ "$ready" -eq 1 ] || { echo "The emulator did not start."; kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; continue; }
  sleep 10
  emu "shot $OUTPUT/$name-1-menu.png"

  if [ "$name" != "idle" ]; then
    # Go to the last item of the main menu ("Shuffle Songs"). The library has one song.
    emu "wheel 60"; sleep 2
    emu "shot $OUTPUT/$name-2-selected.png"
    emu "press select"
    sleep 15
    emu "shot $OUTPUT/$name-3-playing.png"
    emu "press play"      # pause. A paused player runs at full speed.
    sleep 3
    emu "shot $OUTPUT/$name-4-paused.png"
  else
    sleep 15
  fi

  emu hist   > "$OUTPUT/$name.hist"
  emu regs   > "$OUTPUT/$name.regs"
  emu evlog  > "$OUTPUT/$name.evlog"
  emu state  > "$OUTPUT/$name.state"

  kill "$pid" 2>/dev/null
  wait "$pid" 2>/dev/null
  wc -c "$OUTPUT/$name".hist "$OUTPUT/$name".regs "$OUTPUT/$name".evlog
done

echo "Done. Send the folder $OUTPUT (without base.img) to Claude."

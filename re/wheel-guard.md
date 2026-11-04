# Wheel wake guard: the wheel after the screen light goes off

Status (3 November 2026): the patch `wheel-guard` is a test patch. The owner reports that version 0.1 works on a real iPod. Version 0.2 adds the Settings item Wheel Guard (On or Off). It is not tested. The emulator is not used. The research is static (disassembly of `osos` with `llvm-objdump`).

All addresses are osos offsets.

## The problem

The iPod with the screen light off, in a pocket, gets touches on the click wheel. A touch can change the volume, skip a song or move a list. The owner wants the wheel to do nothing until a button is pushed.

## What the firmware does

| Item | Address | Result |
|---|---|---|
| UI event handler | 0x1d81cc | Gets each key and wheel event before the focused list. A return value that is not 0 stops the event. `cover-flow` and `playlist-folders` use this. The slot is the word at 0x6701f0. |
| Event types | — | 4 key push, 5 repeat, 6 held, 7 release, 0xf wheel (event + 0x0c: the ticks), 0x10 wheel scroll in a menu (made later by the lists). Refer to [cover-flow.md](cover-flow.md). |
| Wheel in the handler | 0x1d82a0 | For the type 0xf, the handler calls 0x249054 and, if bit 30 of event + 0x10 is set, restarts the idle timer with 0x1d813c(ui, 0). The call with 0 does not turn the display on. |
| Key push in the handler | 0x1d833c | A push (types 4 and 5) calls 0x1d813c(ui, 1). With 1, the function turns the display on (0xb7c64(1)). |
| Backlight Timer | UI + 0x18 → app + 0x444 | The time in seconds. 0xffff is Always On, 0xfffe is 10 seconds, and 0 is Off. The idle controller 0x1d847c starts a timer (UI + 0x1c) with this time. The setting is in [backlight-timer.md](backlight-timer.md). |
| BacklightTask | 0x28453c | A state byte at RAM 0x1081ff40 (0 off, 1 on, 2 and 3 other). Events 0xa6 on, 0xa7 off, 0xa8 change, 0xa9 tick. |

Key codes (bits 16–23 of event + 0x10): Menu 0x6e, Select 0x6f, Play/Pause 0x10. Refer to [cover-flow.md](cover-flow.md).

## The design

The patch does not read the backlight state. The race is not known: the backlight task can set the state to "on" before the UI task gets the wheel event, and then a test of the state always says "on". The patch uses its own time:

1. It keeps the time of the last accepted input (`last_use`). A key push (type 4) and a wheel event that the patch accepts set it.
2. A wheel event (type 0xf) is stopped (the hook returns 1) if the time since `last_use` is the Backlight Timer plus 1 second, or more. The time of the Backlight Timer comes from app + 0x444.
3. A stopped wheel event does not set `last_use`. Thus touches do not unlock the wheel. A key push unlocks it.
4. With Backlight Timer Off (0), Always On (0xffff) or a value above 3600 s, the patch accepts all events.
5. The first event after the start sets `last_use`. Thus the wheel works for the first Backlight Timer after the start.

The hook is a `word` hook with `chain` on the slot 0x6701f0. The name `wheel-guard` sorts after `cover-flow`, so the guard is first and it calls the hook of `cover-flow`.

## Limits and risks

- The screen light can still come on at a touch. The light is outside the UI handler (BacklightTask). The patch stops only the action of the wheel.
- The timer is a 32-bit microsecond counter. It wraps after 71 minutes. After a longer sleep, the time since the last input can look short, and the wheel then works until the next push. This is the safe error.
- If the Backlight Timer is wrong in app + 0x444, the guard locks sooner or later than the screen light. A push of a button unlocks the wheel in each case.
- If the wheel events reach the lists by a path that does not use 0x1d81cc, the patch does nothing. This is not checked.
- The Hold switch is not changed.

## Next steps

- Test on the real iPod with Backlight Timer at 5 seconds: wait 8 seconds, touch the wheel, then push Select, then touch the wheel.
- Check if the screen light comes on at a touch, and if a locked wheel can move the volume.
- If the light comes on, find the post of the backlight-on event (0xa6) in the wheel path (OptoTask, 0x284f90).

## The Settings item (version 0.2)

The owner asked for a way to turn the guard On or Off on the iPod. The patch adds the item "Wheel Guard" to Settings, after Clicker. The design is the design of `up-next` and of the Dark Mode item:

- `settings_items` adds a copy of the Sound Check item with the key 0x60007e20 and the label ID 0x7e21.
- The value text is the Apple text "On" (0x602e) or "Off" (0x602f). The text follows the language of the iPod.
- The value is in the file `iPod_Control/iTunes/iPodFirmWheelGuard` (one character). The patch reads the file at the first View lookup, when the file system is ready. Without the file, the guard is On.
- A selection calls the "set" method (0x66c950). The patch changes the value, writes the file and sends the notice `Bool` to the settings object, so that the row shows the new value at once.

Not tested: the row in the Settings menu, the value after a restart, and the order of the items when `up-next` is also on.

# AC Unity free camera on a Mac, without changing game code (2026-10-12)

Picks up `ACU_CAMERA_HANDOFF_2026-10-12.md`. On the M2 Pro / CrossOver / Rosetta setup, the game dies whenever it
**executes** a changed instruction (tests 1-8). Writing identical bytes and reading memory are fine, and injected code
runs fine in its own memory. So this table changes **no game code at all**:

| Feature | How | What gets written |
|---|---|---|
| Wider FOV / camera farther (normal 3rd-person camera) | edits the current camera mode's curve points: `PointData.fov` and `distanceFromPlayer`, the same fields ACUFixes' FOV hacks edit | floats in heap data, restored exactly on untick |
| Free camera + FOV + roll | **vtable-pointer swap** on the player camera object: our copy of its vtable, with slot `0x288` `ApplyCameraFX(pos, quat, fov)` pointing at a 111-byte hook that calls the game's function, then writes our camera over the result | the object's first 8 bytes (heap data) + memory Cheat Engine allocates. The game's code and vtable are untouched |
| Probe | every other slot goes through a counter stub (`lock inc [n]; jmp [orig]`), so the table can print which virtuals the game calls each frame | same allocation |

Addresses and layouts come from ACUFixes' ACU-RE headers for 1.5.0 (`CameraManager` singleton `0x14521AAD0`,
`ACUPlayerCameraComponent`, `CameraSelectorNode`, `CurvePoints`). Quaternions are x,y,z,w (ACUFixes casts the game's
camera quaternion register straight to its `Quatf`). The free camera works out which local axis is "forward" when you
switch it on, from the game camera's look-at point, so it doesn't depend on a guessed convention.

## Tested here (the cloud can't run the game)
`test_freecam.py` runs the table's Lua (`acu_freecam.lua`) with Cheat Engine's memory functions backed by an
emulated x86-64 process (unicorn). The hook bytes it writes are **executed** through the swapped vtable, the way the
game calls a virtual: values pass through while off, the free camera overrides them while on, all 127 other slots
still reach the game's functions, the probe counts per slot, keys move and turn the camera, FOV/distance restore
exactly, and D1 only touches padding. The hook machine code was assembled and disassembled with GNU as / objdump
(`fx.s`). What only the game can show: whether the game calls slot `0x288` through the vtable (step 2 below tells you
in two seconds).

## Use (game running, save loaded, Cheat Engine 7.7 Windows build in the bottle)
1. Copy `ACU_FreeCam_DataOnly.CT` to `C:\ACU_Photo\`. **Don't** load the integrity table or suspend the integrity
   thread first: nothing here changes code, so the integrity thread doesn't matter. Fewer moving parts.
2. Attach to ACU.exe, File > Load the table, answer **Yes** to "run the table's Lua script".
3. Tick **3. wider FOV** and **4. farther**. Untick to restore. This is the data-only route from handoff §4.3.
4. Tick **1. Probe**, then Table > Show Cheat Table Lua Script... (or Memory View > Lua engine) to read the output.
   It lists each camera virtual's calls per second and `slot 0x288 ApplyCameraFX (hook): N/s`.
5. If the hook line shows about your frame rate: tick **2. FREE CAMERA**. It starts exactly where the game camera is.
   Keys: **I/K** forward/back, **J/L** left/right, **U/O** down/up, **arrows** look, **, .** roll, **[ ]** FOV,
   **Shift** ×5, **Ctrl** ×0.2. If left/right are reversed, tick *Mirror left/right*. HUD: the game's "All Hidden"
   preset. Screenshots: Cmd+Shift+5 (High Resolution Mode on for > 1920×1200).
6. **5. Remove the camera hook** puts the object's original vtable pointer back.

| What happens | Meaning | Next |
|---|---|---|
| FOV/distance entries work | the data-only route works | usable today for wider third-person shots |
| Probe shows `0x288 ... 0/s` | the game calls ApplyCameraFX directly, not through the vtable | send Claude the probe list: the free camera moves to another slot that runs each frame (the hook design stays the same) |
| Crash when ticking 1 or 2 | something checks the camera's vtable pointer | untick nothing else; relaunch, suspend the integrity thread (your table, entry 1), try again; report which |
| Free camera works but the player keeps moving with your keys | the game also reads I/J/K/L... | stand still, or pause with the game's own menu closed via a cutscene-free spot; time-stop is the next item |

## D1: why do code patches crash? (optional, one launch, decides whether code patching can ever work)
Tick **D1** and play two minutes. It changes 16 never-executed padding bytes at `ACU.exe+2E68800` (the cave from test
6), with no jump to them.
- **No crash:** nothing checksums the code. The crashes come from *executing* changed code under Rosetta/Wine, so
  any code-patching mod (ACUFixes, Hattiwatti, the v6.1 table) can't work on this Mac. Data-only is the way.
- **Crash:** a second integrity check scans `.text` (not the thread you suspend). Code patching would need that
  checker found and stopped first; the data-only table above is unaffected either way.

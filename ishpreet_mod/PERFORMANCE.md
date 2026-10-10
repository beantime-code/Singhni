# Assassin's Creed Syndicate on Mac (CrossOver): toward a steady 60 fps without lowering quality

Status: **research done, measurements needed from the Mac.** Last updated 2026-10-10 (cloud session). Known machine:
Apple Silicon (arm64), macOS 15.6, CrossOver bottle "Assassins Creed". Still needed: chip, RAM, CrossOver version.

## 1. Why it chugs even on a fast Mac
Ordered by how much each one likely costs:
1. **CPU-bound engine, translated twice.** Syndicate (AnvilNext 2.0) is heavy on the CPU because of its crowds,
   streaming and simulation. Players hit stutter and high CPU even on Windows PCs, and Ubisoft's own advice was to
   cap the frame rate ([Steam thread](https://steamcommunity.com/app/368500/discussions/1/4326348922706146537/),
   [Steam thread](https://steamcommunity.com/app/368500/discussions/0/1368380934248692576/?l=turkish)). On a Mac,
   every x86 instruction also goes through Rosetta 2, and every Windows sync call goes through Wine. So the frame rate
   is set by the CPU side and by how CrossOver handles thread synchronization, not by the GPU. That's why lowering
   graphics doesn't fix it.
2. **The DirectX 11 translation layer.** CrossOver has four ways to run DX11: **D3DMetal** (Apple GPTK), **DXMT**
   (direct D3D11→Metal, new in CrossOver 25/26), **DXVK** (D3D11→Vulkan→MoltenVK→Metal) and wined3d (slowest). "Auto"
   picks from CodeWeavers' per-game list
   ([CodeWeavers advanced settings](https://support.codeweavers.com/miscellanous/advanced-settings-in-crossover-mac),
   [CrossOver 25 blog](https://www.codeweavers.com/blog/mjohnson/2025/3/11/experience-next-level-gaming-on-mac-with-crossover-25)).
   - DXMT handles synchronization better than D3DMetal, because Metal tracks resource dependencies itself. An Apple
     developer-forum post names *Assassin's Creed Valhalla* as the title that shows D3DMetal's sync problem best
     ([Apple GPTK forum](https://developer.apple.com/forums/tags/game-porting-toolkit)).
   - Early DX11 reports show DXMT much faster on some games and equal or slower on others. **It has to be measured
     for Syndicate.**
3. **Cloth runs at 30 fps.** Capes and coat tails update at 30 fps even when the game runs at 60, which makes motion
   look like it hitches. Patch 1.31 added an AC.ini switch: `FlexibleMotionSimulationFPS=1` under `[OPTIONS]`, off by
   default, may need adding by hand ([Guru3D, patch 1.31](https://www.guru3d.com/story/assassins-creed-syndicate-update-1-31/),
   [GameSpot, patch notes](https://www.gamespot.com/articles/assassins-creed-syndicate-gets-new-pc-patch-see-th/1100-6433360/)).
   This is free smoothness with no quality loss. Ishpreet's chunni and skirt cloth benefit too.
4. **Uneven frame pacing.** A frame rate bouncing between 45 and 60 feels worse than a locked 60. Lock it with
   in-game VSync at the display rate, or a backend frame cap. Guides and Ubisoft support both suggest a limiter
   ([Quora troubleshooting](https://www.quora.com/How-do-I-fix-the-terrible-lag-I-am-getting-while-playing-Assassins-Creed-Syndicate-even-on-optimal-settings)).
5. **NVIDIA-only options do nothing or cost a lot under translation.** TXAA, PCSS/HFTS shadows and HBAO+ were
   NVIDIA-specific on PC. Under Metal they're unavailable or fall back badly. MSAA is expensive in this deferred
   renderer. Use FXAA, or SMAA through ReShade, plus a sharpener.

## 2. Test protocol (one variable at a time; every row is measured, not guessed)
**Instrument:**
- D3DMetal/DXMT: enable Apple's Metal Performance HUD (bottle environment variable `MTL_HUD_ENABLED=1`).
- DXVK: `DXVK_HUD=fps,frametimes`.
- Record average fps and the 1% low (the stutter).

**Benchmark spot:** the same place, same time of day, same settings for each run. For example, a Whitechapel rooftop
looking over a crowded street, then a 30 s carriage ride (the streaming load).

| # | Backend | Sync | AC.ini | Avg fps | 1% low | Notes |
|---|---|---|---|---|---|---|
| 1 | Auto (current) | default | as is | | | baseline |
| 2 | D3DMetal | MSync on | as is | | | |
| 3 | DXMT | MSync on | as is | | | |
| 4 | DXVK | MSync on | as is | | | |
| 5 | best of 2–4 | MSync off | as is | | | sync can help or break a game ([CodeWeavers](https://support.codeweavers.com/miscellanous/advanced-settings-in-crossover-mac)) |
| 6 | best | best | `FlexibleMotionSimulationFPS=1` | | | cloth smoothness (look, don't just measure) |
| 7 | best | best | + VSync / 60 cap | | | frame pacing |

Then raise quality on the winner one setting at a time (environment, shadows, textures, AO, volumetric fog,
reflections), keeping only those that hold the 1% low above about 55.

## 3. ReShade: is it working?
- **How to tell:** ReShade writes `ReShade.log` next to `ACS.exe` when it loads, and shows a banner at the top of the
  screen on start. **No log means it isn't loading.**
- **The catch:** ReShade loads as `dxgi.dll`, but **D3DMetal and DXMT supply their own dxgi/d3d11**, so the
  override fights them. A CodeWeavers forum report says adding ReShade's `dxgi.dll` with D3DMetal crashes the game,
  and that the tutorial that worked was on DXVK
  ([CodeWeavers forum](https://www.codeweavers.com/support/forums/general?t=27&forumcurPos=255&msg=301597)).
- **What works on paper:** DXVK + ReShade installed **for Vulkan**, not for D3D11
  ([Marty's Mods DXVK guide](https://guides.martysmods.com/additionalguides/apiwrappers/dxvk/)). That ties ReShade to
  the DXVK backend.
- **So:** if test 3 (DXMT) or test 2 (D3DMetal) wins, skip ReShade, or accept the DXVK speed cost for it. Decide
  from the numbers.

## 4. "Why does Unity (2014) look so clean?"
- **Different look, same engine family.** Unity's Paris was built with baked global illumination and very dense
  materials. Syndicate's London is deliberately hazy and foggy.
- **Most clean press shots aren't gameplay frames.** They're captured at high resolution and downsampled
  (supersampling), often in cinematics with depth of field. Gameplay at native resolution with FXAA looks softer and
  more aliased.
- **The legitimate way to get close:**
  1. Native Retina resolution (CrossOver's high-resolution mode).
  2. A good post-AA (SMAA) and a light sharpener (CAS) through ReShade, if it can load (see §3).
  3. A locked frame rate with cloth at full rate.
- Running Unity itself on Apple Silicon is GPU-light but similarly CPU-bound: about 30 fps on an M1 Air after the
  GPTK 2 patch ([AppleGamingWiki, AC Unity](https://www.applegamingwiki.com/wiki/Assassin's_Creed_Unity)). For a
  data point on Syndicate: one Mac mini M4 user reports about 40 fps at 1440p High on CrossOver 26 Preview
  ([MacGamers](https://macgamers.org/games/assassins-creed-syndicate)).

## 5. Next steps
1. **Done:** Studio → **8 · Performance**. It reads `AC.ini` from the bottle, shows and edits every setting (with a
   backup in `out/acini_backups/` and the line endings kept), and has one-click *Cloth at full frame rate* and *VSync
   on*. It also shows the bottle's graphics and sync lines (read-only) and whether ReShade really loads.
2. Run the test table (§2) on the Mac and fill it in.
3. If CPU-bound on every backend: look at engine-side CPU costs that don't change the image, such as the
   streaming and LOD distances that trigger hitches during carriage rides, in AC.ini.

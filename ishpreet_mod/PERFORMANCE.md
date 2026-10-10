# Assassin's Creed Syndicate on Mac: a steady 60 fps that looks great, on D3DMetal

Status: **plan + tools ready; needs one measured pass on the Mac.** Constraint from the user (2026-10-10): **CrossOver
only runs the game with D3DMetal**, so every gain has to come from inside D3DMetal, the game, macOS or ReShade.
Machine: Apple Silicon, macOS 15.6, bottle "Assassins Creed". Still needed: chip, RAM, CrossOver version.

Tools: Studio → **8 · Performance**.
- **AC.ini editor** with backups, plus one-click full-rate cloth and VSync.
- **Bottle toggles:** Metal HUD, MSync and a D3DMetal 60 cap, written to `cxbottle.conf [EnvironmentVariables]`, with
  backups.
- **ReShade check:** whether it actually loads.

## 0. Baseline measured 2026-10-10 (user's Metal HUD screenshot): it changes the plan
**Setup:** MacBook Pro 16″ **M2 Pro**, CrossOver **25.1.0.38617** (ships **D3DMetal 2.1**; the HUD shows
"Rosetta x86_64 v2.1 D3D11"), 1728×1080 (exactly 2:1 of the 3456-wide panel, "1.0x Direct"), display 60 Hz,
quiet street. MSync and the cloth fix were not applied yet.

| FPS avg (min–max) | Frame ("Pre") | GPU time | Draw calls / frame | Render encoders / frame | GPU memory |
|---|---|---|---|---|---|
| 22.6 (17.0–32.8) | 44.3 ms (30.5–58.9) | 28.2 ms (13.5–41.0) | **69,288** | 158 | 6.39 GB |

**Reading:**
- **GPU-bound and CPU-bound at once.** The GPU alone needs 28 ms, a ceiling of about 35 fps even with an infinitely
  fast CPU. The other ~16 ms per frame is the GPU waiting for the CPU, translation and sync.
- **The draw-call count is the root cause:** 69k per frame on a quiet street. Each draw is translated D3D11 → Metal
  under Rosetta (CPU). The 158 render passes are also costly on a tile-based GPU (GPU).
- **§1's "spend spare GPU time on looks" doesn't apply at the current settings.** First cut GPU time with the
  settings that cost the most and show the least (§3, and NVIDIA-only options), and cut draw calls (environment
  draw distance, shadow cascades).
- **Realistic target on D3DMetal 2.1:** a steady 30–40 fps that looks clean. For 60, the GPU work must roughly halve:
  the biggest single lever is **CrossOver 26 (D3DMetal 3.0)**, measured with the HUD before and after.
- **Pacing:** the 16″ panel is 120 Hz ProMotion, so a 40 fps cap divides it evenly (3 refreshes per frame) and feels
  smoother than an unsteady 30–45.
- **Next measurement:** the same spot after MSync + cloth, then after each settings change. The user is sending the
  current AC.ini/graphics settings.

## 1. The principle: Syndicate on Mac is CPU-bound, so the GPU has room to spare
(Revised by §0: on the user's M2 Pro at current settings it's *both*. The method below still applies once GPU time is
under about 14 ms.)
- Syndicate's engine is heavy on the CPU (crowds, streaming, simulation). Players hit stutter and high CPU even on
  Windows PCs, and Ubisoft's own advice was to cap the frame rate
  ([Steam thread](https://steamcommunity.com/app/368500/discussions/1/4326348922706146537/),
  [Steam thread](https://steamcommunity.com/app/368500/discussions/0/1368380934248692576/?l=turkish)).
- On a Mac every x86 instruction also goes through Rosetta 2, and every Windows sync call through Wine. Translated
  games need more resources, so Apple recommends 16 GB+ for them
  ([GPTK 2.1 README copy](https://gist.github.com/lynkos/3999f629560219a81d4e2c083a4bf5b1)).
- So the frame rate is set by the CPU side. Lowering graphics doesn't fix it. **Raising** graphics often costs
  nothing, because the GPU is waiting on the CPU anyway.

**Measure that first** with Apple's Metal Performance HUD (Studio → *Metal HUD on*, `MTL_HUD_ENABLED=1`). It shows
frame time and GPU time.
- **GPU time well under frame time** (e.g. GPU 9 ms in a 22 ms frame): CPU-bound. Use the spare GPU time for
  image quality (§3).
- **GPU time ≈ frame time:** GPU-bound. Then resolution is the lever (§3.1).

## 2. CPU-side wins, no image loss (do all of these)
| # | Change | Why | Where |
|---|---|---|---|
| 1 | **MSync on** | Faster Wine thread synchronization. CodeWeavers notes it can help or occasionally break a game, so check stability ([CodeWeavers](https://support.codeweavers.com/miscellanous/advanced-settings-in-crossover-mac)) | Studio → *MSync on*, or CrossOver Advanced Settings |
| 2 | **Ubisoft Connect: in-game overlay off, then minimize the launcher** | The overlay is a known CPU/stutter source, and the launcher's browser processes share the bottle's CPU ([overlay advice](https://www.getdroidtips.com/ubisoft-connect-high-cpu-usage/), [Steam thread](https://steamcommunity.com/app/2239550/discussions/0/4631482745020811870)) | Ubisoft Connect → Settings → General |
| 3 | **True fullscreen, so macOS Game Mode engages** | Game Mode prioritizes the game's CPU/GPU on Apple Silicon ([CodeWeavers](https://www.codeweavers.com/about/news?curPos=70)) | in game: Display mode Fullscreen |
| 4 | **Plugged in; Low Power Mode off; High Power Mode on if the Mac has it** | Avoids clock caps | System Settings → Battery/Energy |
| 5 | **Don't clear D3DMetal's shader cache** | The first visit to an area compiles shaders (one-time hitches). The cache in the user cache's `d3dm` folder removes them on later runs ([GPTK README](https://gist.github.com/lynkos/3999f629560219a81d4e2c083a4bf5b1)) | play an area once, then measure |
| 6 | **Cloth at full rate** | Capes and coats are capped at 30 fps by default, which looks like hitching at 60. Patch 1.31 added `FlexibleMotionSimulationFPS` under `[OPTIONS]` in AC.ini ([Guru3D](https://www.guru3d.com/story/assassins-creed-syndicate-update-1-31/), [GameSpot](https://www.gamespot.com/articles/assassins-creed-syndicate-gets-new-pc-patch-see-th/1100-6433360/)) | Studio → *Cloth at full frame rate* |

## 3. Spend the spare GPU time on looks (in this order, re-checking the HUD each time)
1. **Resolution first, the biggest visual win.** Turn on CrossOver's High Resolution mode so the game sees the real
   Retina pixels, then pick the highest resolution that keeps GPU time under about 14 ms. Resolution is the single
   largest cost in Ubisoft's engine of this era ([NVIDIA guide](https://www.nvidia.com/en-us/geforce/news/assassins-creed-syndicate-graphics-and-performance-guide)).
   On a scaled display, prefer a resolution that maps 1:1 or exactly 2:1 to the panel, which avoids blur.
2. **Shadows High.** PCSS (NVIDIA) cost about 20–35% on PC for little gain
   ([GamersNexus](https://gamersnexus.net/game-bench/2195-assassins-creed-syndicate-gpu-fps-benchmarks)), and
   NVIDIA-only options (PCSS/HFTS, HBAO+, TXAA) aren't valid on Apple GPUs anyway. High is the best real setting.
3. **Environment and textures to Ultra/High.** On PC they cost little GPU
   ([Prima Games](https://primagames.com/featured/assassins-creece-impressions)). They add some CPU (draw distance),
   so watch the frame time.
4. **Anti-aliasing:** FXAA or the game's post-AA, then sharpen with ReShade (§4). MSAA is expensive in this deferred
   renderer: measure it before keeping it.
5. **Ambient occlusion:** SSAO (HBAO+ is NVIDIA-only).

## 4. ReShade on D3DMetal (the "looks amazing" layer)
- **The problem:** ReShade's default install is a `dxgi.dll` in the game folder. Under D3DMetal that fights
  D3DMetal's own DXGI. One CrossOver user reports exactly this crashing on D3DMetal
  ([CodeWeavers forum](https://www.codeweavers.com/support/forums/general?t=27&forumcurPos=255&msg=301597)). The Studio
  shows whether ReShade really loads: no `ReShade.log` next to ACS.exe means it never ran.
- **Untested, but the documented Wine method** is to load ReShade as **`d3d11.dll`**, not `dxgi.dll`, with a
  `d3d11 = native, builtin` override. ReShade wraps the game's D3D11, then calls the bottle's real D3D11, which is
  D3DMetal ([Proton/Wine guide](https://github.com/sonic2kk/steamtinkerlaunch/wiki/ReShade/44f7769c922aa725c3ba8d1cae87b14cd12514e2);
  ReShade supports d3d11.dll as a wrapper name: [ReShade forum](https://reshade.me/forum/general-discussion/1267-using-additional-dll-files)).
  Steps:
  1. Remove ReShade's `dxgi.dll` from the game folder.
  2. Install ReShade for DirectX 10/11/12, then rename its DLL to `d3d11.dll`.
  3. CrossOver → bottle → Wine Configuration → Libraries → add `d3d11`, set to *native, builtin*.
  4. Launch, and check for `ReShade.log` (Studio → Read settings).
- **If it loads, the preset that matters most:** SMAA (clean edges) + CAS or LumaSharpen (crisp detail) + a light
  Tonemap/Vibrance. Skip heavy MXAO/RTGI until the HUD shows GPU headroom.
- **If it doesn't load:** the image gains come from §3 only. Don't keep a broken `dxgi.dll` in the folder.

## 5. Frame pacing: lock it
- **Cap at 60 and sync to it.** A rate swinging between 45 and 60 feels worse than a locked one. Use in-game VSync
  (Studio → *VSync on*) or D3DMetal's cap (`D3DM_MAX_FPS=60`, Studio → *D3DMetal cap 60*). The cap is documented for
  newer GPTK builds ([crossover-dx12-fix README](https://github.com/webmonarch/crossover-dx12-fix)), so check in the
  HUD that your build honours it.
- **On ProMotion (120 Hz) MacBooks, set the display to a fixed 60 Hz while playing.** Several macOS developers report
  fullscreen judder from variable refresh, fixed by locking 60 Hz
  ([GLFW forum](https://discourse.glfw.org/t/mac-fullscreen-issues/2670),
  [Apple forums](https://developer.apple.com/forums/thread/742803)).

## 6. Bigger lever, optional: a newer D3DMetal
CrossOver ships Apple's D3DMetal (CrossOver 26.3 has D3DMetal 3.0). Apple's newer Game Porting Toolkit builds can be
swapped into `CrossOver.app/Contents/SharedSupport/CrossOver/lib64/apple_gptk`, with scripts and rollback
([crossover-dx12-fix](https://github.com/webmonarch/crossover-dx12-fix)).
- **Requirements:** macOS 15+, CrossOver 26.x, and the terminal needs App Management permission.
- **Risk:** a beta GPTK can break other games. Only try it after §2–§5 are measured, and keep the rollback.

## 7. Why the Unity screenshot looks so clean
- **Different look, same engine family.** Unity's Paris used baked global illumination and very dense materials.
  Syndicate's London is deliberately hazy and foggy.
- **That kind of shot is usually not a raw gameplay frame.** Press and cinematic captures are often rendered above
  display resolution and scaled down (supersampling), with depth of field.
- **The honest equivalent on a Mac:** the highest resolution the spare GPU time allows (§3.1), plus SMAA and a
  sharpener (§4), at a locked 60 (§5).
- For calibration: Unity itself ran at about 30 fps on an M1 Air after GPTK 2
  ([AppleGamingWiki](https://www.applegamingwiki.com/wiki/Assassin's_Creed_Unity)). One M4 Mac mini user reports
  Syndicate at about 40 fps at 1440p High on CrossOver 26 Preview
  ([MacGamers](https://macgamers.org/games/assassins-creed-syndicate)).

## 8. Measurement sheet (fill in on the Mac: same spot, same time of day)
Benchmark: a Whitechapel rooftop over a crowded street (10 s still), then a 30 s carriage ride (streaming).

| Step | Change | Avg fps | 1% low | Frame ms | GPU ms | Keep? |
|---|---|---|---|---|---|---|
| 0 | baseline (Metal HUD on only) | | | | | |
| 1 | + MSync | | | | | |
| 2 | + overlay off, launcher minimized | | | | | |
| 3 | + fullscreen/Game Mode, power | | | | | |
| 4 | + cloth full rate | | | | | look |
| 5 | + VSync / cap 60, 60 Hz display | | | | | feel |
| 6 | + resolution up (High Resolution mode) | | | | | |
| 7 | + shadows/environment High/Ultra | | | | | |
| 8 | + ReShade d3d11 (if it loads) | | | | | |

**Rule:** keep a change only if the 1% low stays at or above about 55 fps. Step 8 adds GPU cost, so only after step 6
shows headroom.

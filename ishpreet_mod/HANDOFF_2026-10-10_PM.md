# HANDOFF 2026-10-10 (afternoon): Ishpreet Studio, Ishpreet roadmap, sword style, performance

**Start here.** It replaces nothing: `Duleep_Files/HANDOFF_2026-10-10.md` is still the record for what's installed and how
to roll back. Everything below lives in `ishpreet_mod/` (git: `beantime-code/Singhni`, branch
`claude/kind-tesla-r52xi7`; zip copies were sent to the user).

## 0. Ground rules learned today
- **The user uploads at most ~30 MB per file.** The Studio's bundles and exports stay under 25 MB per part.
- **Work happens in two places.** The cloud session can't reach the Mac: it works from what the user uploads. The
  Desktop session (or the user) runs the Studio and installs.
- Game folders (detected automatically by the Studio):
  `~/CXPBottles/Assassins Creed/drive_c/Program Files (x86)/Ubisoft/Ubisoft Game Launcher/games/Assassin's Creed Unity`
  and `…/games/Assassin s Creed Syndicate` (**space instead of the apostrophe**). Syndicate's DLC forges are in `dlc_NN/`.
- **Never install anything with the game running.** Every install goes through acs_kit `forge.install` and keeps a
  rollback (handoff §0).

## 1. Ishpreet Studio (no Terminal, no installs, no UTM)
- **Launch:** double-click `ishpreet_mod/Ishpreet Studio.command`. The first time, right-click → Open. It opens in the
  browser at 127.0.0.1 and only reads game files. Its own outputs go to `Duleep_Files/ishpreet_mod/out/`.
- **Tabs:**
  1. Setup: folders, self-test.
  2. Browse: forges → packs → files, extract.
  3. Search: pack names across forges; files inside one forge, from a cached index.
  4. Skeletons: bone-hash compare.
  5. Bundle for Claude: under 28 MB; skeletons, Aveline skirt, sword clips, pipeline sources, log.
  6. Builds: **k25**.
  7. Sword: clip catalog, bone check, mapping plan, fight-data export, original-graph export.
  8. Performance: AC.ini editor with backups, cloth-60 and VSync toggles, bottle settings, ReShade check.
  9. Debug log: hex viewer, full tracebacks, also in `out/studio_log.txt`.
- **Tools behind it** (`tools/`, all tested):
  - `anvil_forge.py`: reader for Unity v1 and Syndicate v2 containers; lzo1x/lzo2a/lzo1c; chained pack tables; and
    `rebuild_pack`, which does same-size file replacement with zero-seeded Adler-32 block checksums.
  - `lzo_py.py`: pure-Python decoders, fuzz-tested against liblzo2.
  - `anvil_bones.py`: bone-hash diff.
  - `graph/atomgraph.py`: fight-graph decoders.

## 2. Ishpreet (Evie's Élise slot)
- **Roadmap:** `ROADMAP_ISHPREET.md`. It has the failure catalog F1–F6 from the k23 screenshots and gates G1–G7, which
  a build must pass before the user sees it.
- **Facts from real data:**
  - Aveline's skirt LiteRagdoll = Hips, Spine, both thighs, both shins. All of these bones exist in the Élise skeleton.
  - Élise's coat colliders have no shins. That's the verified cause of the skirt wrapping one leg and balling up.
  - Bone IDs are CRC32 of the bone names.
- **Built, NOT installed:** **k25** (Studio → Builds) = Aveline's ClothSettings and LiteRagdoll inside pack 207 under
  Élise's IDs. Install via acs_kit `forge.install({207: out/k25/dlc14_207_CoatCloth_k25.data})`, game closed.
  Rollback: `Evie/dlc14_207_ChunniCloth_k23.data`. It's a *collider test*, not the final fix: the closed cloth tube
  still breaks gate G6.
- **Next, in order:**
  1. Write gates G1–G6 as `check_build.py`. The user's acs_kit pipeline and the k2x exports are already in the cloud
     (bundle 4 → `scratchpad/bundle4/pipeline/`). Prove each gate by making it fail on k23.
  2. Decode and render Aveline's skirt mesh and cloth (both in bundle 3/4).
  3. k26 via route R1 (Aveline skirt bones as an addon skeleton) or R2 (Aveline's skirt as shipped).

## 3. Sword as a true 4th style (then Heavy, Long)
- **Starting a new session for this?** `SWORD_SESSION_START.md` has what to attach, what to read, the work order and a
  prompt to paste.
- **Plan:** `SWORD_STYLE_PLAN.md` (the 4-link model and experiments E0–E4). **Findings:** `FIGHT_GRAPH_FINDINGS.md`.
- **Verified:**
  - **Animations:** all 55 bones animated by the Unity sword clips exist in Syndicate's male and female base skeletons,
    so it's a direct port.
  - **Weapon definitions** (`4D7A62BB`): the kukri holds Unity's sword class 1, the knuckles hold 4 and the cane holds
    5. Unity's Sword/Heavy/Long also carry a first field 1/2/3 that Syndicate leaves at 0.
  - **Fight graph:** same file ID as Unity's (6426366647). 779 runtime variables, 111k conditions, 55,879 clip
    references, all decoded.
  - **The original graph is in the cloud** (`scratchpad/fight/raw/syn_original/…`). The installed one differs from
    it in 1,459 bytes (the katar edits).
  - **No weapon-value condition sits next to cane, kukri or knuckle clips,** so Syndicate's melee style is chosen
    higher up the state-machine tree, or by code.
- **Next:**
  1. Structural parser: `AtomStateMachineNode` → states → transitions → conditions, giving every clip reference its
     tree path. Use the ACUFixes ACU-RE headers for field order.
  2. Find where cane, kukri and knuckle diverge (original Syndicate graph), and where Sword, Long and Heavy diverge
     (Unity graph).
  3. `graft_style.py`.
  4. E3 (why m2 crashed) and E4 (the item → style test) on the Mac, one game launch each.

## 4. Performance on Mac (CrossOver, **D3DMetal only**: the user says it's the only backend that runs the game)
Goal: a steady 60 fps that looks great, without lowering image quality. Plan, sources and measurement sheet:
`PERFORMANCE.md`. The Studio's **8 · Performance** tab sets the bottle variables (Metal HUD, MSync, D3DMetal cap) and
AC.ini (full-rate cloth, VSync), with backups. Order of work:
1. Metal HUD on, then measure.
2. The CPU-side wins.
3. Spend the GPU headroom on resolution and quality.
4. Lock 60 (and set ProMotion displays to 60 Hz).
5. ReShade loaded as d3d11.dll (untested).
6. Optionally, a newer D3DMetal.

First things to record from the Mac:
- Mac model (chip and RAM), CrossOver version, bottle graphics backend (D3DMetal / DXVK / Auto), macOS version.
- The game's in-game settings, and whether ReShade is actually loading (look for a `ReShade.log` next to ACS.exe).

## 5. Where the data is (cloud scratchpad: lost when the container is recycled; re-upload if missing)
| What | Where |
|---|---|
| Bundles 1–4 | `scratchpad/bundle{1..4}/` (bundle 4 = pipeline sources + Aveline and Élise cloth files) |
| Fight data | `scratchpad/fight/raw/` (both graphs, 2,651 settings records, leftover clips) |
| Original graph | `scratchpad/fight/raw/syn_original/` |
| Community file lists | `scratchpad/atkres/` (AnvilToolkit-Resources clone) |

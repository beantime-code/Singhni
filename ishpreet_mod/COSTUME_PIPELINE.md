# Costume pipeline v2: Ishpreet, Jaspreet and every costume after them

Written 2026-10-11 by the cloud session from:
- the user's acs_kit pipeline (bundle 4: `builds/ishpreet_kameez2.py`, `acs_kit/meshrec.py`, `dbg/qa.py`, `holes.py`);
- the k23–k28 history;
- the 2026-10-11 climbing and standing screenshots.

The tools are in `tools/costume/`, tested by `tools/costume/test_costume.py` (11 tests). The per-build fix plan for
Ishpreet is `ISHPREET_K29_PLAN.md`.

## 1. Why builds kept breaking, by cause

Five causes, each traced to the pipeline code or game data, sorted by how many builds they broke.

| # | Cause | Where | What it produced in game |
|---|---|---|---|
| C1 | **Each piece gets its weights by its own rule**. Kurta: transfer from the naked body. Sash: whatever lands under the radial cinch. Skirt: Aveline cloth bones remapped 50/50 to the thighs. Chunni: blended toward the kurta. Strips and underlays: nearest neighbour. They are only tied together by `follow()` blends over 1–3.5 cm. | `ishpreet_kameez2.py` weights section, `skirt_rule`, `follow`, `sash_cinch` | Joins open in poses the 4 test clips don't reach: armpits (k23–k26), spine gap (k28), floating sash (k28c). On a model of the outfit, the same rules open the waist **5.2 cm** and lift the sash **12.7 cm** when bending forward (§5). |
| C2 | **Clearance only checked in the rest pose.** `push_out` / `torso_fit` / `sash_cinch` push vertices out along the nearest vertex normal around a fixed vertical axis. Skinning then moves layers by different amounts. | `push_out`, `sash_cinch` (cylinder about `(0, yc)`) | Clipping at the shoulders (chunni in idle), sash not hugging the waist, sirwal poking through |
| C3 | **The cloth skirt is a separate mesh with nothing closing the gap above it.** The skirt (pack 200, MotionCloth) and the kurta (pack 201) only meet visually. From below, when climbing, the inside of the outfit shows. | k26 design | Hollow / disjointed area at the spine when climbing (screenshots 1 and 3) |
| C4 | **Texture paint and the game's texture lookup can disagree.** All Élise pieces draw with material `Elise2` (71438840560). Aveline's skirt draws with `ULC_B_Aveline_2S` (298172522943), which has its own textures. Garments were also moved between "free" atlas regions build to build. | material ids from the dlc_14 index; k27 leg, k28 sirwal | Skirt dark grey-brown with cream in game while the offline render was saffron; one leg in kurta colour (k27); dirty, shiny trousers (k28: Élise's breeches texels and their gloss) |
| C5 | **The checks didn't match the failures.** 4 game clips (idle, jog, crouch-walk, climb), pixel tests from a few camera angles, renders using assumed textures. | `dbg/qa.py`, `holes.py`, `readback.py` | Builds passed offline and failed in game, k26–k28 |

## 2. Process for a new costume (either twin)

Each stage has an output and a gate. A build that fails a gate never reaches the game.

0. **Spec (one JSON per costume).**
   - Slot: Evie Élise = dlc_14 packs 201/200/207 + atlas 199/198/197; Jacob's slot for Jaspreet.
   - Pieces, and each piece's fabric name.
   - Which pieces are cloth-simulated.
   - Intended junctions, e.g. `kurta hem under sash`, `skirt top under sash`, `sleeve into gauntlet`.
   - One atlas rectangle per fabric.

1. **Geometry, authored as one outfit (Blender).**
   - **Close-fitting garments are ONE welded shell**: kurta, sleeves, sash band, sirwal waistband. A join is an edge
     both garments share, never two edges side by side. "Merge the model so it doesn't do that" is this rule.
   - **Overlays** (sash knot and tails, chunni, trims) overlap their host by at least 3 cm. Their edges are tucked
     under the host or lie flat on it.
   - **Cloth-simulated pieces** (skirt, coat tails) start under an overlay: at least 4 cm of the cloth's pinned top
     band sits under the sash.
   - The close-fitting shell continues **under** the cloth piece as a closed lining down to mid-thigh. Any gap then
     shows fabric, never the inside of the outfit.
   - Open panels get a real back side: a lining copy with its own normals. Don't offset duplicates by 1 mm; they
     z-fight.
   - Game density: 1–2 cm edges on the body, finer at the openings.

2. **Fit, in more than the rest pose.**
   - Shrink-wrap to the naked body (Evie: London 21687 `ACVI_CHR_P_EvieFrye_NakedBody_LOD0`, record 401137995317).
     Use target offsets: 6 mm over skin, 4 mm per layer.
   - Then check clearance with `costume.qa` G4 in the range-of-motion poses (stage 6) and fix where it fails.
   - Never push along a fixed axis.

3. **Weights: one field for the whole outfit** (`costume.weights`, `costume.reweight`).
   - Transfer from the naked body where the match is confident (≤ 3 cm and normals within 35°).
   - Inpaint everything else over one graph of all pieces, where coincident vertices are one node and overlays are
     linked to their host.
   - Stock pieces the build keeps (hands, boots, gauntlet) are fixed constraints.
   - Bones are limited to those in the outfit skeleton. Missing bones hand their weight to an ancestor.
   - This replaces kNN, `follow`, `weld`, `skirt_rule` and `head_rule`.

4. **Textures.**
   - **One atlas plan for every mesh that draws with the same material** (body and coat both use `Elise2`).
   - Each fabric gets its own rectangle. A garment never reuses another texture's texels unless the spec says it's
     the same fabric.
   - Every painted rectangle gets **all three maps**: diffuse, normal (cloth weave) and mask1 (cloth ≈ 0,255,197,255).
     Otherwise the old gloss/metal shows through, which is what made the trousers shiny.
   - **A mesh moved from another outfit must be pointed at the slot's material, and its UVs remapped into the plan.**
     Aveline's skirt kept either Aveline's material or Aveline's UV layout.

5. **Assemble the records** with acs_kit (`meshrec` append/replace, `forge.Pack`).

6. **QA gates, on the built files, against the stock outfit** (`python3 -m costume.qa`, §4):
   - G1 holes, G2 seam tears, G3 junctions, G4 clipping, G5 views, G6 atlas, G7 weights, G8 materials.
   - Run over 14 range-of-motion poses at 50% and 100%, plus the game clips when you have them.
   - Baseline: the stock outfit in the same slot, so a build is judged against what Ubisoft ships.
   - Read the PNGs from below and behind before anything else.

7. **In-game check, fixed route.** One launch, the game closed before and after. Name each screenshot by its
   number:
   1. menu close-up
   2. stand, front
   3. stand, back
   4. walk
   5. sprint
   6. climb, with the camera **below**
   7. hang, with the camera below
   8. wall run
   9. crouch
   10. fight
   11. carriage
   12. inventory close-up

8. **Log.** PATCH_LOG entry: tag, files, gate report, screenshots, revert command.

## 3. Hard rules (each one prevents one cause)
- **One weight field per outfit** (C1). No piece gets weights by its own rule. Seams have identical weights on both
  sides (G2 = 0).
- **Every junction is shared topology or an overlap of at least 3 cm with copied weights** (C1, C3). G3 must report 0
  junctions opening more than 1 cm in any pose.
- **Clearance is proven in poses, not the rest pose** (C2). G4: no layer more than 3 mm through another.
- **Cloth pieces start under an overlay, with a closed lining under them** (C3). G5 from below may not show more
  garment inside than the stock outfit.
- **Paint goes where the game reads** (C4). G8 materials must match the stock slot (or the change must be
  deliberate). G6: no overlap between differently named pieces. All three maps are painted.
- **Offline previews use the game's material bindings and all three maps**, or they are labelled as not
  representative (C5).
- From before, still valid:
  - one change per build;
  - two failed attempts at the same fix → stop and report;
  - build from the originals;
  - game closed for installs.

## 4. Tools (`tools/costume/`, numpy only: runs in the Mac's Cowork shell and in the cloud)
| File | What it does |
|---|---|
| `mesh.py` | Reads skinned meshes (body stride 40 with 8 influences, cloth stride 32 with 4). Gives positions, UVs, weights, palette and bind matrices, and the material per sub-mesh. `patch_weights()` = same-size weight rewrite (round trip exact on Aveline's skirt). |
| `skel.py` | Skeleton records: bone parents and **rest positions** (match the mesh bind data to 0.0 mm on all 14 skirt bones). |
| `rom.py` | 14 range-of-motion poses (climb reach L/R, hang, wall step L/R, crouch, sprint L/R, straddle, arms back, bend forward/back, twist L/R) by limb aiming, + linear blend skinning. No clips, no VM. |
| `geom.py` | Components, boundary loops, nearest/signed distance, UV rasterising, z-buffer views. |
| `qa.py` | Gates G1–G8, report + PNG sheets. A hole is a boundary no limb, neck or face passes through and nothing covers; holes the stock outfit also has are not counted. |
| `weights.py` | Robust transfer + inpainting over one outfit graph (method: Abdrashitov et al., SIGGRAPH Asia 2023). |
| `reweight.py` | Re-rigs a built outfit in place (body + the coat's top band), with QA before/after; writes only with `--write`. |

```
cd Duleep_Files/ishpreet_mod/tools
python3 -m costume.qa --mesh body=<built 201 .data or .record> --mesh coat=<built 200> \
    --baseline body=<original 201> --baseline coat=<original 200> \
    --skeleton <ACVI_CHR_SHR_Female.bin> --skeleton <Elise outfit skeleton 306812379500.bin> \
    --orig <original 201> --log <build log> --out qa_<tag>
python3 costume/test_costume.py   # self-test: 11 tests, about 2 minutes
```

## 5. What the tools showed before touching Ishpreet's files
- **On Ubisoft's own Aveline skirt:** every gate passes against itself, and the weight rewrite round trip is exact.
- **On a model of the outfit with the k23–k28 weighting rules** (kurta from the body, sash on the hips, skirt 50/50
  on the thighs):
  - the skirt pulls **5.2 cm** away from the kurta at the centre back (the spine gap);
  - the sash pulls **12.7 cm** off the kurta at the front when bending forward, and goes through it;
  - **with one outfit field: 0 openings and 0 clipping across all 14 poses at 50% and 100%.**
- **The cases the gates are built for:** each one fails on its defect and passes on the fixed version (tests).

## 6. Sources
- Robust weight transfer (the stage 3 method):
  - Abdrashitov, Raichstat, Monsen, Hill, "Robust Skin Weights Transfer via Weight Inpainting", SIGGRAPH Asia 2023
    Technical Communications: https://www.dgp.toronto.edu/~rinat/projects/RobustSkinWeightsTransfer/
  - Code: https://github.com/rin-23/RobustSkinWeightsTransferCode. Blender add-on: "Robust Weight Transfer"
    (SentFromSpaceVR). Unreal implements the same idea in its TransferBoneWeights inpaint step.
- Closest point on a triangle: Ericson, *Real-Time Collision Detection*, §5.1.5.

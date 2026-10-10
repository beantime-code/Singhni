# Ishpreet: roadmap to a build with no clipping and no empty portions (2026-10-10)

For the Claude Desktop session and the cloud session. Read with `INDEX_2026-10-10.md` and
`Duleep_Files/HANDOFF_2026-10-10.md`. The rule that runs through this whole roadmap: **a build reaches the user only
after every gate below passes.** One bad screenshot after release means a gate was missing. Add that gate, don't just
patch the build.

## 1. Failure catalog (what "never again" means)

Each failure has a reference picture: the user's k23 screenshots of 2026-10-10.

| ID | Failure | Seen in | Root cause (verified or still to verify) |
|---|---|---|---|
| F1 | Skirt balls up into a ring around the hips when climbing | k23, climb from below | **Verified:** a closed tube of free MotionCloth around both legs, run with Élise's *open-coat* colliders. Nothing in the cloth knows where the shins are (her coat colliders have no LeftLeg/RightLeg capsules). |
| F2 | One leg wrapped by the skirt, patterned like the kameez; legs through the skirt when walking | k23, walk | Same cause as F1. |
| F3 | Hollow, "empty" body seen from below or behind | k23, climb from below | **Verified:** the kurta body is cut at z 1.0 and the sirwal top was hidden (k23 `--sirwal-top 0.96`), so nothing fills the space when the cloth swings away. **To verify:** whether the garment faces are single-sided, so their inside is invisible. |
| F4 | Armpit holes | k19–k23 | **Verified:** the armhole and the sleeve top are two separate open edges, 26–39 mm apart, following different bones. The flaps added in k22–k23 didn't close them. |
| F5 | Grey, untextured triangle on the front of the skirt | k23, standing on rail | **To verify:** the generated skirt's UVs probably land on an empty area of the texture atlas, or a face got the wrong material. |
| F6 | Sash or chunni ends flipping, or showing as a floating ring | k23, climb | **To verify:** which mesh the sash ends belong to (body or cloth), and their weights. |

## 2. Gates. A build ships only if all of them pass

G1 to G6 run automatically, from the Studio's **Check build** step (to be built in Phase 0) or from `acs_kit/dbg/`.
G7 is the in-game gate, which Claude runs on the Mac.

| Gate | Checks | Catches | Pass rule |
|---|---|---|---|
| **G1 Holes** | Every open boundary loop of every garment mesh, classified against an allow-list (hem, cuffs, neck, face opening, intended slits up to their stated height). Plus a seam audit: vertices in the same place with different skin weights. | F4, slit tears | 0 loops outside the allow-list; 0 split seams. |
| **G2 Interior** | Garment faces whose back side can be seen in the camera sweep (below, side, behind, at climb and crouch frames), with no body or inner layer within 2 cm behind them. | F3 | 0 such faces. If any remain, add an inner shell or make the material double-sided, then pass. |
| **G3 Texture** | Every face's UV triangle samples opaque texels that aren't the default colour, in its assigned material's atlas. Material ID per face matches the part it belongs to. | F5 | 0 faces in atlas gaps; 0 wrong-material faces. |
| **G4 Skeleton** | Every bone in each mesh's palette exists in the skeletons the outfit actually loads: the Élise outfit skeleton plus any addon in its BuildTable row, read from the forge with the Studio. Any added addon skeleton has a matching hierarchy (the wiki says a mismatch crashes the game). | the k21 missing-bones class | 0 missing bones; hierarchy identical for shared bones. |
| **G5 Penetration** | Body plus garments skinned on the game's own clips: `NavAnims_elise.glb` (climb, climb idle, idle, jog, sneak walk, crouch idle), plus combat clips once ported. Points of body or sirwal outside the garment, and garment points inside the body, with a margin. | F2 (skinned), clipping | 0 points beyond 5 mm on every frame. Worst frame rendered for the log. |
| **G6 Cloth policy** | A free-simulated cloth may not form a closed loop around both thigh bones. Every cloth's LiteRagdoll must hold capsules for every bone its sim mesh passes. The sim mesh must be manifold. | F1, F2 | Static check passes. The only free cloth allowed is open, hanging pieces (chunni tail, sash ends). |
| **G7 In game** (Claude, CrossOver) | The fixed route: inventory → stand on a rail (like shot 1) → walk → jog → climb, camera from below (like shot 2) → hang → crouch → fight. Eight screenshots, compared side by side with the previous build. | anything left | No item from the failure catalog visible in any of the 8 shots. |

The offline QA (`dbg/qa.py`) already covers part of G5. It **cannot** see cloth physics, which is why G6 forbids the risky
cloth layout outright instead of trying to simulate it.

## 3. Phases

### Phase 0 · Instruments first (no build until this is done)
1. **Pipeline into the cloud.** The next **Bundle for Claude** includes `acs_kit/` (scripts, docs, logs) and the newest
   k2x GLB exports and renders, so the cloud session can write G1–G6 against the real code and meshes.
2. **Build G1, G3, G4 and G6** (deterministic geometry and data checks), then G2 and G5 (the pose sweep), as one
   `check_build.py` the Studio can run on a build tag. Prove each gate by running it on **k23: it must fail with
   exactly F1–F5**. A gate that passes k23 is wrong.
3. **Decode and render Aveline's skirt** (mesh `…Aveline_Skirt_LOD0`, 74 KB, and its Cloth, 166 KB, both already in
   the cloud from bundle 3): its length, its openings, which vertices are cloth and which are skinned, and its 8
   skirt-only bones.

### Phase 1 · k25, data only (built in the Studio, Builds tab)
- **What it does:** Aveline's skirt ClothSettings and LiteRagdoll go into pack 207, under Élise's IDs. The
  colliders become Hips, Spine and both thighs and shins.
- **What it's for:** a **collider test**. It should reduce F1 and F2, but a closed cloth tube is still against G6, so
  k25 is not the final build. It shows whether the shin colliders matter, at no build cost.
- **Ship rule:** G7 only (the mesh is unchanged). Rollback: reinstall `Evie/dlc14_207_ChunniCloth_k23.data`.

### Phase 2 · k26, the structural fix: copy how Ubisoft rigged Aveline's skirt
Choose the route from what Phase 0.3 shows, preferring the one with the fewest new parts:
- **R1 (preferred if Aveline's skirt is mostly skinned):** the lower kameez panels are skinned to Aveline's skirt bones.
  Ubisoft's ball joints, keyed to the legs (`…Aveline_LeftLeg/RightLeg_BallJointCommonData`), drive those bones in
  game. Needs the Aveline outfit skeleton (64 bones: 45 shared with Élise's, 17 new) as an **addon skeleton** in the
  Élise BuildTable. G4 must prove the hierarchy matches. Weights come from Aveline's mesh via `rig.py transfer`, or
  Robust Skin Weights Transfer for the area between the legs. Deterministic, so G5 can check it offline.
- **R2 (if Aveline's skirt depends on its Cloth):** use Aveline's skirt geometry with its own Cloth, settings and
  colliders as shipped, retextured as the kameez skirt. Only the texture and material change; the geometry and sim
  stay untouched, so the sim stays valid. Length and openings are whatever Aveline's are. If that isn't kameez-like
  enough, go back to R1.
- In both routes the chunni stays separate cloth (open, hanging: allowed by G6), with the k23 stiff paint.

### Phase 3 · Body and surface
- **F3:** restore the sirwal top, and run the kurta body down under the skirt (no cut at z 1.0), so the inside is never
  empty. G2 enforces it.
- **F4:** weld the armhole loop to the sleeve-top loop: shared vertices, identical weights. G1 enforces it.
- **F5:** move the UVs of the offending faces into a textured region, or assign the right material. G3 enforces it.
- **F6:** sash ends skinned to the pelvis and spine with proven donor weights, or made cloth with colliders. G5 and G7
  check them.

### Phase 4 · Sword combat (Studio, Sword tab)
- **Facts so far:** every bone the Unity sword clips animate (55 of 55, checked on four real clips) exists in
  Syndicate's male and female base skeletons. So the port is direct, with no retarget.
- **S-1:** map clips in the Sword tab. Attacker and defender clips are linked automatically.
- **S-2:** done (bone check per clip in the tab).
- **S-3:** port one pair first.
  - **Path A:** AnvilToolkit XML export on Unity → XML import on Syndicate, saved over the slot IDs. The wiki's
    sanctioned path; runs in CrossOver, clicks only.
  - **Path B, no ATK:** a raw transplant via `rebuild_pack`. Allowed only after the cloud session compares a real
    Syndicate cane clip with a Unity clip and finds the same layout. That clip is in the next bundle.
- **S-4:** the user decides between replacing the kukri style and a true 4th style.
- **S-5:** port the rest in pairs. G7 includes a fight.

## 4. Working rules
- **One change per build,** named in `PATCH_LOG.md`. When a gate fails, its output is attached to the log entry.
- **Donor-first:** every rig, weight, collider and setting comes from a shipped garment. A hand-made rule
  (`skirt_rule` and the like) is allowed only with a gate that proves it.
- **Two failed attempts at the same fix → stop and report** (handoff rule).
- **Every install keeps a rollback,** written next to the build (the Studio does this for k25).

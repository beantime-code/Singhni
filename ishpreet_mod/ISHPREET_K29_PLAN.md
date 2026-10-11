# Ishpreet k29: fix plan for what the 2026-10-11 screenshots show

For the session linked to the Mac (Cowork shell: numpy + Pillow, no internet). Copy this `ishpreet_mod/` folder into
`Duleep_Files/` first. Method and rules: `COSTUME_PIPELINE.md`. The user's rules still apply:
- one change per build;
- game closed for installs;
- build from the originals;
- two failed attempts at the same fix → stop and report;
- show the user renders before any install.

Installed now: body k28 (pack 201), coat k26 (200, Aveline's skirt), coat cloth k26 (207). Textures: k28.

## What the screenshots show, and the cause of each
| Seen in game | Cause (`COSTUME_PIPELINE.md` §1) | Fix (build) | Gate that proves it |
|---|---|---|---|
| Hollow, disjointed area at the spine when climbing (from below, shots 1 and 3) | C1 + C3: the kurta, sash and cloth skirt top have unrelated weights. Nothing closes the space above the skirt. | k29b weights, k29c lining | G3 kurta↔sash↔skirt = 0 openings; G5 below views ≤ stock |
| Sash floats, not tight to the waist | C1 + C2: a separate ring, pulled in around a vertical axis in the rest pose, with weights not taken from the kurta under it | k29b weights, k29c sash as an offset of the kurta waist | G4 sash/kurta clipping = 0; G3 sash = 0 |
| Skirt dark grey-brown with cream patches (offline it was saffron) | C4: Aveline's skirt draws with material `ULC_B_Aveline_2S` (Aveline's textures), or with `Elise2` but still Aveline's UV layout. Either way the game samples texels the build didn't paint. | k29d | G8 coat material = stock Élise coat (71438840560); G6 skirt vs other pieces = 0 |
| Trousers: even colour now, but dirty and shiny | C4: k28 moved the sirwal onto Élise's breeches texels, which keep their grime and gloss | k29d: own clean rectangle, all 3 maps | G6 sirwal shares texels with nothing; mask1 = cloth |
| Chunni clips at the shoulders in idle | C1 + C2: chunni weights blended toward the arms; clearance only in the rest pose | k29e | G4 chunni vs kurta/sleeves = 0 in arms_back, hang, climb |
| Inventory stance (not yet looked at) | Evie's menu idle pose isn't in our clips | Screenshot the Outfits page, compare with renders at arms ~30° out | User check |

## Build order (one change each)
**k29a: measure, install nothing.**
1. Get the inputs as raw records or `.data` packs:
   - built: body k28 (201, 296181347212) and coat k26 (200, 296181347207);
   - originals from `paths.ORIG_DLC14`: the same two records;
   - skeletons: ACVI_CHR_SHR_Female (101290185321) and the Élise outfit skeleton (306812379500);
   - Evie's NakedBody LOD0 (London 21687, 401137995317).

   One-liner per record, from acs_kit:
   `open(out,'wb').write(forge.Pack.from_file(path).get(rid))`, or `forge.Pack.from_forge(idx, paths.ORIG_DLC14).get(rid)`.
2. `python3 -m costume.qa --mesh body=… --mesh coat=… --baseline body=<orig 201> --baseline coat=<orig 200> --skeleton … --skeleton … --orig <orig 201> --log <k28 build log> --out qa_k28`
3. Send the user `qa_k28/report.txt` and the PNG sheets: `climb_reach_L.png`, `hang_both.png`, `crouch.png`, plus
   the `stock_*` versions. Red = see-through, blue = garment inside.
   **G8 decides the skirt colour question at once:** it prints the coat's material against the stock coat's.

**k29b: weights only (same-size edit of 201 and 200; geometry untouched).**
1. `python3 -m costume.reweight --body … --orig <orig 201> --coat … --coat-band 0.06 --source <NakedBody> --skeleton … --skeleton … --baseline … --out k29b`.
   This is a dry run: it prints QA before → after.
2. If G2/G3/G4 improve and nothing gets worse: run again with `--write`. Put `k29b/body.record` and
   `k29b/coat.record` into the packs (`pack.set(296181347212, bytes)` / `pack.set(296181347207, bytes)`, then save).
   Log it, ask "game closed?", install, verify.
3. User test: shots 6 (climb from below), 7 (hang), 2–3 (stand), and the sash close-up.
4. Revert: reinstall k28 body / k26 coat.

**k29c: geometry at the waist (in the kameez builder; one build).**
- **Close the spine:** weld the kurta's back seam into one piece; no slit, no hidden underlay. G1 = 0 holes on the
  back.
- **Lining:** continue the kurta below the sash as a closed, skinned lining to mid-thigh, under the skirt. Then
  re-run `reweight` so the lining follows the outfit field.
- **Sash:** make it an offset (4–6 mm along normals) of the kurta's own waist band, so it shares that band's
  topology and weights. The knot and tails are overlays on it.
- **Skirt pinned band:** at least 4 cm under the sash (move it up, or move the sash down).
- Gates G1/G3/G4/G5 as above.

**k29d: textures where the game reads them.**
- **Skirt:** point the coat's bone map material at `Elise2` (71438840560). Remap its UVs into a dedicated rectangle
  in the atlas plan. Paint the kameez fabric there, in the diffuse, normal and mask1 maps.
- **Sirwal:** its own clean cream rectangle, with cloth normal and cloth mask, replacing the breeches texels.
- Gates G6 and G8. The preview must render with Elise2's three maps, not the diffuse alone.

**k29e: chunni shoulders.** Clearance ≥ 1.5 cm over the shoulders in arms_back / hang / climb poses. Weights come
from the outfit field (Spine2 and the clavicles, not the arms). Gate: G4 = 0 for the chunni.

## After Ishpreet: Jaspreet and new costumes
Same pipeline with the male skeleton ACVI_CHR_SHR_Male (88892524727) and Jacob's slot. Jacob's naked body is the
weight source: find it with `python3 -m acs_kit.index JacobFrye_NakedBody`. Start each costume from a spec
(`COSTUME_PIPELINE.md` stage 0). Gate reports go in PATCH_LOG with every build.

## Prompt for the Mac-linked session
```
Copy the updated ishpreet_mod/ into Duleep_Files (the user has the zip), then carry out ishpreet_mod/ISHPREET_K29_PLAN.md
starting with k29a: run tools/costume qa on the installed k28 body + k26 coat against the stock Elise body/coat, and show
me report.txt and the climb/hang/crouch PNG sheets before building anything. Follow COSTUME_PIPELINE.md for every build.
```

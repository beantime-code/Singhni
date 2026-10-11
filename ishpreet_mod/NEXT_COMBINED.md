# Next round: gada G6 + katar K1 + Ishpreet k29a/k29b in one command

For the session linked to the Mac (Cowork shell). Copy this `ishpreet_mod/` folder into `Duleep_Files/` first.
The user's rules still apply: game closed for installs, each build logged in PATCH_LOG, two failed attempts → stop.

```
cd ~/mnt/Duleep_Files/ishpreet_mod/tools
python3 next/run_next.py prepare                  # offline only; writes Duleep_Files/Next/REPORT.md
# show the user REPORT.md + Next/k29b/qa_before|qa_after climb_reach_L / hang_both / crouch PNGs, ask "game closed?"
python3 next/run_next.py install --game-closed    # only after "yes"
python3 next/run_next.py revert  --game-closed [--only gada,katar | --only ishpreet]
```

What `prepare` builds (`tools/next/run_next.py`):
- **G6 + K1 → one pack 114 file** (`Next/DataPC_114_G6_K1.data`), from the installed pack 114 (keeps H1/O1/G5):
  - G6: the gada gets blunt multi-kills (`fsw.py add`, ACVI_Gada found by name).
  - K1: the katar's definition (ACVI_Brassknuckle) plays the kukri's multi-kill sets, so it stabs instead of
    punching. Jacob's brass knuckles share it; they already fight with kukri moves since katar m1.
  - Object ids come from a free private range it checks against all of pack 114.
- **k29a + k29b** (dlc_14 201/200): QA of the installed k28 body + k26 coat against stock Élise (= k29a, including the
  G8 skirt-material answer), then the one-field re-weight. k29b is staged only if its gate passes: G2/G3/G4 better and
  no gate worse. Otherwise nothing is installed for Ishpreet and the report says why.
- **W0** (read only): weapon-type bindings and every weapon item's subcategory, into `Next/menu_w0.json`.
- **D0a** (read only, optional): left-arm tracks in the gada's attack clips, if `next_config.json` lists them.

Anything it can't find in the game data or the index stops that part with a message naming the
`Duleep_Files/next_config.json` key to set (`gada_definition`, `first_id`, `records`, `d0`). Nothing is guessed.

One boot tests all three (independent symptoms): gada multi-kills (no stabs), katar multi-kills (stabs), Ishpreet
climb/hang from below. If the game crashes at boot, revert `--only gada,katar` first, then `--only ishpreet`.
To install the gada without K1, run `prepare --only gada,ishpreet` again.

Next after this boot: D0 (one overhead clip in every gada attack slot) decides whether the G5-style table drives
attacks. If it does, talwar T1 = its own table from `data/graph/talwar_map.json`: 40 move families → Unity sword
strikes, guard-chain combos, parries, perfect parries, shoulder charges, wall kills and signature kills, with paired
moves always swapped attacker and enemy together. Then the menu: W0 probe, tab labels and icons.

## Prompt for the Mac-linked session
```
Copy the updated ishpreet_mod/ into Duleep_Files (the user has the zip), read ishpreet_mod/NEXT_COMBINED.md, then run
`python3 next/run_next.py prepare` from ishpreet_mod/tools. Show me Next/REPORT.md and the climb/hang/crouch QA sheets
(before/after and stock). Fix any STOPPED part by setting the key it names in next_config.json, then prepare again.
When I say the game is closed, run install --game-closed and give me the one-boot test list from the report.
```

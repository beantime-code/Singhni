# Sword session: start here

This is everything a fresh Claude session (cloud or Desktop) needs to add sword combat to Syndicate as a true fourth
style, alongside cane, kukri and knuckles, and later Heavy and Long. Paste the prompt at the bottom. Attach the files
in step 2.

## 1. Point the session at
- **Repo:** `beantime-code/Singhni`
- **Branch with all the work:** `claude/kind-tesla-r52xi7`. A new cloud session gets its own branch; it should start
  that branch from `origin/claude/kind-tesla-r52xi7`.
- **Folder:** `ishpreet_mod/`

## 2. Attach these (each file is under 30 MB)
A new session can't see the previous session's uploads. Re-attach them from your Downloads, or regenerate them with
the Studio: double-click `ishpreet_mod/Ishpreet Studio.command`, then open **7 · Sword**.

| Attach | Made by | Contents |
|---|---|---|
| `claude_fight_<time>_part1of2.zip`, `…part2of2.zip` (all parts) | **Export fight data** | Both `NewDemo_DEV` graphs (Syndicate installed + Unity), 2,651 settings records, Syndicate's leftover Sword/Long/Heavy clips |
| `claude_graph_original_<time>_part…zip` (all parts) | **Export original (unmodded) graph** | Syndicate's pre-katar `NewDemo_DEV` (52,770,997 B). Read from DataPC_extra.forge via the reloc log |
| Optional, for E2/E3: a Bundle for Claude (**5 · Bundle**) | **Build bundle** | Pipeline sources (acs_kit, `combat_recon.md`, `PATCH_LOG.md`, reloc JSONs) + sword clips |

Every part has a manifest with sha256. The session should verify it before using anything.

## 3. Read, in this order
1. `HANDOFF_2026-10-10_PM.md` §0 and §3: ground rules, sword status.
2. `SWORD_STYLE_PLAN.md`: the 4-link model (item → WeaponType w → graph branch B(w) → clips; icons; gear tab) and
   experiments E0–E4.
3. `FIGHT_GRAPH_FINDINGS.md`: every verified fact about the graph and weapon records.
4. `tools/graph/atomgraph.py`: decoders for RTCP variables, conditions and clip references.
5. `data/graph/rtcp_syn.json` (779 variables, identical in the original and installed graphs) and
   `data/graph/rtcp_unity.json` (541). A condition's variable reference is an index into these.
   `PrimaryWeaponSelf` = Syndicate #573, Unity #391.
6. `data/acu_sword_clips.csv` (2,036 Unity sword/heavy/long clips), `data/syn_fight_clips.csv` (2,195 Syndicate
   fight clips).
7. From the bundle's `pipeline/`: `combat_recon.md` and `PATCH_LOG.md` (the katar m1–m4 history and the m2 boot crash).

## 4. Prior art to use: ACUFixes (open source, `github.com/NameTaken3125/ACUFixes`)
- `CommonLibACU/ACU-RE/inc/ACU/Atom*.h`: class layouts for `AtomStateMachineNode` (States, InitialStates,
  GlobalTransitions), `AtomInitialState` (condition expression, TargetStateIndex), `AtomStateTransitionTarget`,
  `AtomConditionExpression`, `AtomCondition`, `AtomGraphStateNode`, `AtomLayeringStateNode`. These are **in-memory**
  layouts. Serialized field order usually follows them, but check against the bytes.
- `ACUFixes/src/AnimationTools/DumpAnimationGraph.cpp`: a complete walker for this same graph (`NewDemo_DEV`):
  root state machine → states → transitions → condition chains (including GROUP chains via `SkipConditionsChain`).
  Mirror its traversal in the serialized parser.
- `AnimationTools/README.md`: how a state machine is driven by one RTCP variable (null states, transitions,
  `playbackPercentage`). `States[0]` of the root state machine is the normal gameplay layering state.
- `AnimationTools/AnimationEditor.cpp` + `NewAnimations/*.anim.json`: per-track codec IDs and keyframe JSON. ACUFixes
  imports **Syndicate (ACVI) animations into Unity** with it. The codecs are shared, so it's the reference for E2
  (Unity → Syndicate clip conversion).

## 5. Work order (stop at each "done" and report)
1. **Structural parser** `tools/graph/atomtree.py`. For every `AtomStateMachineNode` (`34ceaeae`): its states,
   initial states (`65eda630`), transitions (`46f2710b`) and condition expressions (`afc60bf7`). Output: the tree
   path of every animation reference, plus the conditions on that path.
   *Done when:* the totals match `FIGHT_GRAPH_FINDINGS.md` §1 (Syndicate 6,633 state machines / 12,278 playback states /
   9,563 transitions / 55,879 clip refs; Unity 5,356 / 9,203 / 6,553 / 45,932), and any unplaced references are counted.
   Add a test.
2. **E0 divergence.** In the *original* Syndicate graph, find the lowest node where the cane, kukri (`Knife`) and
   knuckle sub-trees split, and the variable and value that pick each. Do the same for Sword, Heavy and Long in
   Unity's graph. Map the graph's weapon numbers 0–19 to names.
   *Done when:* each style has a (variable, value, node path) triple. If no variable selects it, then code does:
   find which code path and say so.
3. **E1.** Which w each Syndicate weapon record carries, and how that reaches the graph value from step 2. The
   weapon-definition class values are kukri 1, knuckles 4, cane 5. Unity's first field (1/2/3) is unused in Syndicate.
4. **`tools/graph/graft_style.py (w, φ)`.** Clone the cane combat sub-tree into the Sword branch, with the condition
   w = cane changed to SwordLethal and the clip references remapped through φ (from the Studio's `sword_plan.json`).
   Prefer same-size edits: reuse leftover Sword nodes and existing slots, and swap u64 clip IDs and condition values.
   That's the proven katar path. Heavy and Long must then need only a new (w, φ) table.
   *Done when:* the output re-reads with `atomgraph.py`, every changed byte is listed, and `anvil_forge.rebuild_pack`
   round-trips it.
5. **Hand to the Mac, one game launch each:** E3 (why m2, adding 177 records to pack 6969, crashed at boot) and E4
   (set the cane item's w to Sword; does the graph follow?). Give exact acs_kit install and rollback commands.
6. **E2 clips.** Convert the Unity sword clips to Syndicate's animation format (Syndicate has an extra u32 at +21).
   All 55 animated bones exist in both base skeletons, so no retarget is needed.
7. **Icons.** In `UIEnumBinding WeaponType` (`2e772cd8`, pack 114), point Sword/Heavy/Long at proper icons. In-place
   edit only.
8. **Gear tab** (optional, last): the tabs are hard-coded, so this needs a code patch (the unpacked ACS.exe dump is
   in `re/` on the Mac).

## 6. Rules (from the user's handoff; don't break them)
- **Build from originals** (the original graph export), never from the installed, katar-edited files.
- **Install only with the game closed**, only via acs_kit `forge.install({idx: file}, forge_path=…)`, and always keep
  a rollback.
- **Pack 114 (Game Bootstrap Settings):** in-place edits only.
- **Pack 6969 (`NewDemo_DEV`):** never add records until E3 explains the m2 crash. Same-size edits are fine.
- Atk and Dfn (attacker/defender) clip pairs always move together.
- No guesswork builds: each build passes an offline check before one in-game test.
- Two failed attempts at the same fix → stop and report.
- Don't create CrossOver bottles. Never close the AnvilToolkit console. Keep `dlc_21/Extracted` and `Backups`.
- The user uploads at most ~30 MB per file. Anything you ask for must come from a Studio button.
- Commit to your branch; no pull request unless asked.

## 7. Prompt to paste
```
Repo beantime-code/Singhni. Start your branch from origin/claude/kind-tesla-r52xi7 and work in ishpreet_mod/.
Read ishpreet_mod/SWORD_SESSION_START.md first and follow it: read the files in §3 in order, obey the rules in §6,
and do the work in §5 starting at step 1 (the structural AtomGraph parser), stopping to report at each "done".
Attached: the Studio's fight-data export (all parts) and the original (unmodded) graph export. Verify their sha256
manifests before using them. Use ACUFixes (github.com/NameTaken3125/ACUFixes) as described in §4.
Goal: sword combat in Assassin's Creed Syndicate as a true 4th style alongside cane, kukri and knuckles, with its own
icon, built so Heavy and Long need only a new (w, φ) table. Nothing gets installed without the game closed and a rollback.
```

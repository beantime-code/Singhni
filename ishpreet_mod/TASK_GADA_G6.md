# TASK: G6, gada multi-kills without stabs; D0, why the gada stays one-handed

For the session linked to the Mac (it can reach the game files and acs_kit). Written by the cloud session on
2026-10-11 from the user's uploaded game data. Read `TASK_GADA.md`, the last PATCH_LOG entries (H1–G5) and this file.
The user's rules from `TASK_GADA.md` all apply:
- Game closed for every install.
- One change per build, logged in PATCH_LOG.
- Two failed attempts at the same fix → stop and report.
- Kukri, cane, knuckles and talwar don't change.

## 1. What is proven (cloud, from the user's files)
**The impaling finishers are multi-kills and multi-counter-kills, and they don't come from the fight graph.** The game
picks every multi-kill (2–4 enemies) and multi-counter from one record:
- Record: `ACVIFightSystemWrapper`, type `71D6E363`, file `68552934583`, in DataPC.forge pack 114 (Game Bootstrap
  Settings).
- 16 entries: 7 multi-kills, plus 3 each of MultiCounter, MultiCounterAD and MultiCounterKill.
- Each entry has a default clip set (the knife's) plus overrides keyed by weapon definition (`4D7A62BB`):
  ACVI_Kukri, ACVI_Brassknuckle and ACVI_Cane, one set per clip family (xx_ / xy_).
- A weapon with no override plays the default: knife stabs.
- The gada has its own definition (ACVI_Gada, H1) and no overrides. G5's swap table doesn't reach this record.

**Which variants stab is measured, not guessed.** Each victim clip carries its blood effect. "Dagger pierce" blood
means a stab; "punch" blood means a blunt blow. Counts below are victim clips:

| Weapon's multi-kills | stab (pierce) | blunt (punch) | none |
|---|---|---|---|
| Cane | 41 | 4 | 64 |
| Knife (kukri / default) | 45 | 2 | 33 |
| Knuckles | 0 | 42 | 62 |
| CaneHB / KnifeHB / KnuckleHB (hidden-blade variants) | 17 | 1 | 23 |

- The cane's multi-counter-kills stab too (6 pierce); the knuckles' are blunt.
- So copying the cane's multi-kills (G5's choice) can't remove the stabs.
- Per-variant table: `python3 tools/fight/fsw.py show <record>`. Data: `data/graph/kill_clip_blood.json`.

Also checked, not the cause:
- **Weapon attachment bones:** both twins' base skeletons have `RightHand_Weapon_Ref` (`3fb256e5`) and
  `LeftHand_Weapon_Ref` (`a9611103`).
- **Left-arm layers in the graph:** the layers gated by weapon values {4,8} (Unity) and {4,19} (Syndicate) are
  shooting layers. They sit among the musket, blunderbuss and pistol reflex-shot clips, so they aren't the grip.

## 2. G6: give the gada its own blunt multi-kills (one build, pack 114 only)
`tools/fight/fsw.py` (in the repo, `beantime-code/Singhni`, branch `claude/kind-tesla-r52xi7`, `ishpreet_mod/`):
- **Parser:** all 16 entries parse to the byte; tested by `tools/fight/test_fsw.py`.
- **Builder:** for each entry and clip family, it adds an ACVI_Gada override.
  - It uses the cane's variants only where none of the cane's victims stab, and the knuckles' otherwise.
  - It never uses hidden-blade (HB) variants, or a list that doesn't start with an attacker clip. One stock cane
    MultiCounterAD list is broken that way.
- **Result on the stock record:** 23 overrides, +2,231 bytes.
  - Multi-kills: 13 come from the knuckles, plus 1 from the xy set's cane MultiKill Vs2 12-3, which is blunt.
  - The cane supplies 5 multi-counters, because its counters have no blood.
  - The knuckles supply MultiCounterAD 12-9 (the cane's list there is broken) and the 3 multi-counter-kills.
- **Safety:** `--replace` first removes any earlier gada overrides, e.g. if G5 added some. Every existing override is
  checked unchanged, and stripping the new ones gives back the input byte for byte.

Steps:
1. Extract the **installed** record (pack 114 now holds H1/O1/G5 changes), with the same acs_kit extraction as H1.
   Save the original for rollback.
2. `python3 tools/fight/fsw.py show fsw_installed.bin`. Confirm the registered weapon list includes ACVI_Gada, and
   note whether gada overrides already exist.
3. Build:
   ```
   python3 tools/fight/fsw.py add fsw_installed.bin --weapon <ACVI_Gada file id> --first-id <free id> \
       --replace --out fsw_g6.bin --report fsw_g6.json
   ```
   `--first-id`: start of a free object-id range, from the allocator H1/G5 used. It consumes about 50 ids.
4. Put `fsw_g6.bin` into pack 114 with the H1-style builder: the pack grows by about 2 KB, and pack 114 growth has
   worked twice. Read it back and re-run `show`.
5. Ask "game closed?". Install with `forge.install({114: ...}, DataPC.forge)`, verify, and log as G6 with a revert.
6. **User test:** fight 3–4 thugs with the GADA, as Jacob and as Evie:
   - Bring two or three of them to low health together to get a multi-kill.
   - Get attacked by two at once to get a multi-counter.
   - **Expected:** blunt blows (knuckle-style strikes, cane bonks on counters), enemies react in place, no stabs.
   - **Trade-off:** the knuckles' multi-kills are punches thrown with the gada in hand. Unity has no heavy
     multi-kills to use instead.

## 3. D0: why it stays one-handed (one boot, decides the next build)
G4 (handle length) and G5 (own table) were two attempts at the grip, so per the rules: diagnose before building
again. This is `TASK_GADA.md` step 0, which was never run.

**Offline checks first (no boot):**
- **a. Left-arm tracks:** in each converted gada attack clip from H2/G1/G5, list the track bone ids. The Unity
  two-handed swing must have tracks for these bones:
  `LeftClavicle b898b609`, `LeftArm eb830ada`, `LeftForeArm 89b93a80`, `LeftHand b675f36c`,
  `RightHand_Weapon_Ref 3fb256e5`. Compare against the Unity source clip. If the converter dropped them, that alone
  explains the one-handed look.
- **b. Attachment bone:** find which bone the gada's in-hand object (kukri chassis) attaches to. Unity's swings move
  the weapon through `RightHand_Weapon_Ref`. If the kukri rig hangs off another bone, the gada won't follow the
  swing and the left hand closes on air.

**The boot (if a and b are clean):** D0 = the current build, with every gada attack slot playing ONE unmistakable
Unity two-handed clip, e.g. `xx_Fight_Heavy_Windup_Atk_Front_Onspot` (4.3 s overhead). The user does three attacks
and sends one screenshot mid-swing.

| What the user sees | Meaning | Next build |
|---|---|---|
| No overhead; still kukri-like swings | The attack clips don't come from those slots | Find where attacks are picked for the gada's in-hand type before building more |
| Overhead with both hands on the shaft | Clips and grip work | Map the real moves per slot (as G1); the grip is solved |
| Overhead with the left hand near, not on, the shaft | The weapon is offset or rotated in the hand | Re-seat the gada model on `RightHand_Weapon_Ref` using the Unity hammer's grip as the reference |
| Overhead with the left arm hanging | Something overrides the left arm | Stop and report; the cloud session can search the graph for the override |

## 4. Not in this task
- Single-target kills: G3–G5 already map them to Unity heavy kills.
- The talwar: it has its own definition and falls back to the knife multi-kills, which suit a blade.
- Sounds.

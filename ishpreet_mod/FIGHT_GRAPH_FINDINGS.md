# Fight graph and weapon data: verified findings (2026-10-10)

Inputs: the user's fight-data export, 5,421 files, all sha256-verified:
- both games' `NewDemo_DEV` AtomGraph files;
- 2,651 settings records from both games' "Game Bootstrap Settings" packs;
- Syndicate's leftover Sword/Long/Heavy clips.

Decoders: `tools/graph/atomgraph.py`. Background: `SWORD_STYLE_PLAN.md`.

Caveat: Syndicate's graph in this export is the **installed** one, so it contains the katar m1–m4 edits: 271+43
references point at kukri clips instead of knuckle clips. The Studio's **Export original (unmodded) graph** reads the
pre-mod copy, which is still in DataPC_extra.forge at offset 515,572,995, from the relocation log.

## 1. The graph
| | Syndicate | Unity |
|---|---|---|
| File | DataPC_extra pack 6969 `NewDemo_DEV`, 52,770,997 B | DataPC pack `DataAI_GroupBehavior_Couple_TakeAway`, 42,638,736 B |
| File ID | 6426366647 | **6426366647 (same graph lineage)** |
| State machines / playback states / transitions | 6,633 / 12,278 / 9,563 | 5,356 / 9,203 / 6,553 |
| Conditions (variable / markup / group / playback / accumulated) | 45,915 / 16,971 / 46,997 / 709 / 349 | 29,264 / 14,202 / 32,924 / 413 / 135 |
| Animation references | 55,879 refs to 11,488 of 11,690 clips in the pack | 45,932 refs to 8,086 of 8,103 clips |
| Runtime variables (RTCP) | 779 | 541 |

Serialization facts (verified):
- **Objects:** each starts with CRC32(class name), e.g. `AtomCondition` = `76384757`, `AtomRTCPDescriptor` =
  `b3b3ca75`, `AtomStateTransitionTarget` = `46f2710b`, `AtomStateMachineNode` = `34ceaeae`.
- **RTCP descriptors:** u32 name length, name\0, u32 type length, type\0, id = CRC32(name), data offset, then an
  initial value.
- **A condition's variable reference is the variable's index in the RTCP table.** Comparison value: int at
  `wrapper + 12`. Operators: == > >= < <= != (0–5).
- **Animation nodes:** each holds its clip's u64 file ID inline. One node per reference.

## 2. How weapons reach the graph
- **Weapon variables:** `PrimaryWeaponSelf` (Syndicate #573, Unity #391), `PrimaryWeaponAtk`, `PrimaryWeaponVic`,
  `PrimaryEquippedWeaponSelf` and `SecondaryWeaponSelf`. Same names and hashes in both games.
- **Values tested against `PrimaryWeaponSelf`:**
  - Syndicate: 0–12 plus **15, 16 and 19, which appear only in Syndicate**;
  - Unity: 0–12.
- **A naive proximity test doesn't attribute these values to cane/kukri/knuckle clips.** The values are mostly
  used in gun and pistol layers, and the melee branch selection sits higher in the state machines. Next step:
  structural parse (state machine → states → transitions), §4.

## 3. Weapon definitions and the item/UI side (decisive)
**Weapon definition records** (type `4D7A62BB`, 46–47 bytes, in Game Bootstrap Settings):

| Record | Game | first field | class value |
|---|---|---|---|
| `DefaultSword` | Unity | 1 | **1** |
| `DefaultHeavy` | Unity | 2 | **3** |
| `DefaultLong` | Unity | 3 | **4** |
| `DefaultWeapon` | Unity | 0 | 0x1f |
| `ACVI_Kukri` | Syndicate | 0 | **1** |
| `ACVI_Brassknuckle` | Syndicate | 0 | **4** |
| `ACVI_Cane` | Syndicate | 0 | **5** |

- **The class value is the UI WeaponType enum.** Unity: 1 Medium, 2 Small, 3 Heavy, 4 Long, 5 Musket…
  Syndicate's binding: 1 Medium (kukri icon), 2 Heavy, 3 Long, 4 = knuckles (new localised name), 5 Musket
  (cane icon), 6 Hidden blade…
- **The kukri occupies Unity's sword class (1, "Medium").** Syndicate re-used Long's number (4) for knuckles and
  Musket's (5) for the cane.
- **The first field is 1/2/3 for Unity's Sword/Heavy/Long and 0 for every Syndicate weapon.** It's the strongest
  candidate for what selects Unity's melee *style*. Syndicate leaves it 0 and must select its styles differently
  (still to find).
- **Inventory items** (`InventoryItemSettings`, `c69075ab`) hold only menu categories: knuckles (2, 4), cane (2, 5).
- **`UIEnumBinding WeaponType`** (`2e772cd8`) maps each class value to an icon reference and a localised name. Heavy
  (2) and Long (3) still point at Unity-era icons. Retargeting them is a data edit (pack 114, in place).

## 3b. Original (unmodded) graph, received 2026-10-10 12:07 UTC
- **It verifies:** 52,770,997 B, same size as the installed one. The two differ in **1,459 bytes** (the katar
  reference swaps).
- **Clip references:** 55,879, of which **325 are knuckle clips** (11 in the installed graph), plus 1,235 kukri
  (`Knife`) and 229 cane.
- **Even in the original, no weapon-value condition is enriched near any of the three families.** The strongest
  pairs are generic fight states (`AttackState`, `PostHurtAction`, `MainCharacterDescriptorTypeInteraction`). So the
  style is chosen above the clip level (state-machine structure) or by code. The structural parser decides which.

## 3c. Multi-kills and multi-counters come from a settings record, not the graph (2026-10-11)
- **Where:** `ACVIFightSystemWrapper` (type `71D6E363`, file `68552934583`, pack 114). It holds 16 entries:
  - 7 multi-kills (Vs4 ×3, Vs3, Vs2 ×3);
  - 3 each of MultiCounter, MultiCounterAD and MultiCounterKill.
- **Structure:** each entry = name + default clip list (knife) + overrides keyed by weapon definition (kukri,
  knuckles, cane) and clip family (xx/xy). Each override has its own variants (Atk + Dfn clips). A weapon without an
  override gets the knife default. Parser and builder: `tools/fight/fsw.py`.
- **Stabs vs blows (victim blood effect):**
  - Cane multi-kills: 41 pierce, 4 punch.
  - Knife: 45 pierce, 2 punch.
  - Knuckles: 0 pierce, 42 punch.
  - Hidden-blade (HB) variants: mostly pierce.
  - Per-clip data: `data/graph/kill_clip_blood.json`.
- **Bones:** bone masks name bones by CRC32 of the name. Both base skeletons have `RightHand_Weapon_Ref` and
  `LeftHand_Weapon_Ref`.
- **Two-handed weapon tests:**
  - The graph's groups that test weapon values {4,8} (Unity) or {4,19} (Syndicate replaced 8 with 19 in many) gate
    shooting layers: musket/blunderbuss two-armed aim, and the pistol off-hand.
  - Unity's melee values come in pairs: (1,10), (3,12), (5,11), (4,8).

## 4. Next steps (cloud, no game launch)
1. **Structural parser** for state machines and transitions: for each `AtomStateMachineNode`, its states, their
   transitions (target index + condition expression), and its initial-state conditions. Output: the tree path of
   every animation reference, and the conditions on the path.
2. Run it on Syndicate's **original** graph and on Unity's. Answer E0: where cane, kukri and knuckle diverge, and
   on which variable and value. Compare with Unity, where Sword, Long and Heavy diverge.
3. Map the graph's weapon numbers (0–19) to names from those divergence points.
4. Then `graft_style.py`: clone the cane combat sub-tree into the Sword branch.

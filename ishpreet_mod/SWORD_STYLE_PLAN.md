# Sword as a true 4th fighting style (then Heavy and Long), worked out as a dependency problem (2026-10-10)

Sources: `combat_recon.md` (earlier sessions' reverse engineering of ACS.exe and pack 114), the user's bundles 1–4, the
AnvilToolkit wiki. "Verified" means checked on the user's real files. Everything else is a hypothesis with the
experiment that settles it.

## 1. The model: a fighting style is a chain of four lookups

For an equipped weapon item `i`:

```
 i ──(1) item data──▶ w = WeaponType(i) ──(2) fight graph──▶ branch B(w) ──(3) states──▶ clips C(B(w))
                     └──(4) UI──▶ icon(w) via UIEnumBinding "WeaponType";  tab(i) via the gear page's fixed tab slots
```

**A true style `s` exists iff all four links are defined for its `w`**, and equipping it changes nothing for the other
styles (isolation). Today:

| Link | Kukri | Cane | Knuckles | **Sword** | Heavy | Long | Where it lives |
|---|---|---|---|---|---|---|---|
| `w` value in the enum | yes (`DaggerLethal`? unverified) | `Cane` | `Knuckle` | `SwordLethal/NonLethal` **present** | `HeavyLethal/NonLethal` present | `LongLethal/NonLethal` present | ACS.exe (one enum, verified in the dump) |
| (1) item → `w` | yes | yes | yes | **missing** | missing | missing | DataPC.forge pack 114 "Game Bootstrap Settings" (in place only) |
| (2) graph branch `B(w)` | full | full | full | **partial: 19 clips left** (unsheath, exit, dodge, strafe, idle, pistol) | 57 clips left (incl. brute `HeavyCombo` enemy attacks) | 17 clips left (idle, strafe, exit) | DataPC_extra pack 6969 `NewDemo_DEV` (AtomGraph, 52.8 MB) |
| (3) clips | yes | yes | yes | **Unity: 564 player clips; all bones match** (55/55 checked on 4 clips) | Unity: 222 | Unity: 299 | Unity DataPC pack `DataAI_GroupBehavior_Couple_TakeAway` (8,297 clips) |
| (4a) icon(`w`) | value 1 "Medium" = kukri icon | 5 "Musket" = cane icon | 4 = knuckles icon | to check (Unity's sword icon slot is the "Medium" value the kukri now uses) | value 2: Unity-era icon ref | value 3: Unity-era icon ref | pack 114 `UIEnumBinding WeaponType` |
| (4b) gear tab | Kukri | Cane | Knuckles | **none** | none | none | fixed tab slots in `AvatarCustomizationManager_0X19FC4AB39F` and code |

So Sword needs links (1), (2), (3) and (4). The enum value already exists, so **no enum or code change is needed for
the gameplay style itself.** Only the separate *tab* (4b) needs code.

## 2. The minimal construction

Let `D` be the set of combat states in the cane branch (attack chain, combo, counter, kill `_Atk` with its enemy `_Dfn`,
near-death, parry, dodge, stun…), and `φ: D → Unity sword clips` the mapping chosen in the Studio's Sword tab, by
family and direction.

1. **Clips (3):** convert each `φ(d)` to a Syndicate `.Animation`. The bones match, so the conversion is format only:
   AnvilToolkit's XML path, or a direct converter once the header difference is decoded (Syndicate has an extra u32 at
   +21, verified on real clips).
2. **Branch (2):** `B(Sword) := B(Sword)_existing ∪ clone(D, condition w=Cane → w=SwordLethal, clip refs → φ)`. The
   existing sword stance, strafe and draw states are kept, so the combat sub-graph is grafted onto locomotion that
   already exists.
3. **Item (1):** a sword item whose weapon data carries `w = SwordLethal`, cloned from the cane item record, with the
   sword mesh as its visual. The weapon mesh path is already proven (katar M1).
4. **Icon (4a):** point `UIEnumBinding WeaponType[SwordLethal]` (and 2 Heavy, 3 Long) at icons Syndicate loads. This is a
   data edit in pack 114, in place. It also makes **every** style's icon reachable, which is the secondary goal.
5. **Tab (4b), optional:** the gameplay style works without its own tab. The sword item can be listed under an
   existing tab while still fighting as Sword, because `w` comes from the item, not the tab. A separate SWORD tab needs
   a small code patch (proxy DLL, toolchain available) that adds one slot to the gear page. Do it last.

**Heavy and Long for almost no extra work:** steps 2–4 are one tool parameterized by `(w, φ)`. Once it works for
Sword, Heavy is `(HeavyLethal, φ_heavy)` and Long is `(LongLethal, φ_long)`: only new mapping tables (Unity has the
clips) and two icon pointers. Heavy may be cheaper still: Syndicate keeps a brute enemy heavy branch (`HeavyCombo`),
which may only need the player-side states.

## 3. Unknowns, ordered by how much each one decides

| # | Question | How | Cost | If the answer is bad |
|---|---|---|---|---|
| E0 | Do `NewDemo_DEV`'s transitions test `w`, and does a Sword branch still exist (H1)? How big is `D`? | Decode the graph (both games: Unity's has full Sword/Long/Heavy branches to compare against) | 0 boots, cloud, needs **Fight data** export | If `w` isn't in the graph, the branch is picked in code → find it in the unpacked exe instead |
| E1 | Which `w` does each existing weapon carry (is the kukri `DaggerLethal` or `SwordLethal`)? | Weapon and inventory records from pack 114, in the same export | 0 boots | If the kukri already owns `SwordLethal`, Sword takes `LongLethal` or a different free value; the method is unchanged |
| E2 | The exact difference between Unity and Syndicate `.Animation` layouts | Byte diff of real clips (have: 4 Unity, 1 Syndicate cane), then the leftover Sword clips (same names in both games) | 0 boots | Use the ATK XML path |
| E3 | Why m2 (adding 177 clip records to pack 6969) crashed | Bisect: (a) add 1 unreferenced record; (b) referenced; (c) with new-ID range vs reused. Not internal sub-IDs: clips have none (verified). | 1–3 boots | If records can't be added, overwrite unused records in place (Sword/Long/Heavy leftovers and other unused clips), or put the new clips in a separate pack loaded with the graph |
| E4 | Is the style really picked from item data? | Set the cane item's `w` to `SwordLethal` (data only, in place): the stance should change to the leftover sword stance | 1 boot | Then the link is code: find it from E0's references in the exe |

The Studio's **Sword → Export fight data** produces the inputs for E0–E2 (multi-part, under 28 MB each). The cloud
session runs E0–E2. E3 and E4 are single-boot tests for the Desktop session, run with the in-game gate.

## 4. Deliverables in order
1. **Fight data** export → E0–E2 in the cloud. Output: `fight_graph.md` (the decoded branches, `D`, every
   `w`-conditioned transition) and `anim_format.md`.
2. Graph-clone tool `graft_style.py (w, φ)` + verifier: re-parse, every reference resolves, the other branches are
   byte-identical.
3. Sword item + icon bindings for Sword, Heavy and Long (pack 114 in place).
4. One-pair test (one attack + one kill pair) → in-game gate → the full `φ`.
5. Heavy, then Long: new `φ` tables only.
6. Optional: the SWORD gear tab (code patch).

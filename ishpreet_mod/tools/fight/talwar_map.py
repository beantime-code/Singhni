"""Talwar T1 move map: for each knife (kukri) player clip family the talwar still plays, the Unity one-handed sword
clips to put in its place. Input is the two games' clip names, so every clip named here exists in the game files.

    python3 talwar_map.py --syn syn_clip_names.txt --unity acu_fight_clips.tsv --out ../../data/graph/talwar_map.json

syn names: every ACVI_Fight_xx_Knife_*_Atk clip in Syndicate's DataPC_extra.forge (the fight graph's pack).
unity names: column 1 of acu_fight_clips.tsv (Unity clips seen in the fight graph's packs).

Status per family:
    done   already Unity sword in S5b (front kills 1-4 + their deaths, stance, strafe, pistol moves)
    T1     replace in the talwar's own animation table (built like the gada's G5 table)
    keep   stays the knife's: short lead-ins, multi-kills/counters (the knife's suit a blade), box and cart moves
Paired moves (an Atk with an enemy Dfn) are always swapped as a pair: never a sword strike over a knife reaction.
"""
import argparse
import collections
import json
import re
import sys

# family regex (on the Syndicate name without 'ACVI_Fight_xx_Knife_' and the variant number) -> rule
RULES = [
    (r'^Attack01_(Left|Right|BackLeft|BackRight)_N_Atk$', 'T1', 'side', False,
     'Directional strikes. Unity has on-the-spot and 2 m sword strikes per side.'),
    (r'^Attack01_N_Atk$', 'T1', 'front', False, 'Front strikes: Unity on-the-spot and 2 m front sword strikes.'),
    (r'^Attack0[23]_N_Atk$', 'T1', 'combo', True,
     'Combo hits 2 and 3: Unity guard-chain combos (UR->DL, UR->DR, UR->UL), attacker and enemy halves together.'),
    (r'^ComboEnder(H)?_Atk$', 'T1', 'ender', False, 'Combo enders: Unity combo finishers (left / right).'),
    (r'^Counter(_(Left|Right|BackLeft|BackRight))?_N_Atk$', 'T1', 'parry', True,
     'Counters: Unity sword parries for that side, attacker and enemy halves together.'),
    (r'^Counter90_N_Atk$', 'T1', 'parry', True, 'Quarter-turn counter: Unity has no 90-degree parry, so its front parries.'),
    (r'^CounterKill(_(Left|Right|BackLeft|BackRight))?_N_Atk$', 'T1', 'perfect', True,
     'Counter-kills: Unity perfect parries for that side (they end the enemy), both halves.'),
    (r'^ComboStun_Init0[123]_N_Atk$', 'T1', 'stun', False, 'Stuns: Unity sword shoulder charges.'),
    (r'^Wall_Kill_N_Atk$', 'T1', 'wall', True, 'Wall kills: Unity has exactly 3 sword wall kills, both halves.'),
    (r'^(Stun)?NearDeath_(LFlank|RFlank|LShoulder|RShoulder)_Atk$', 'T1', 'sig', True,
     'Finishers on a staggering enemy: Unity signature front kills, both halves.'),
    (r'^ComboNearDeath_.*$', 'T1', 'sig', True, 'Combo into near-death finisher: Unity signature front kills.'),
    (r'^Kill_N_Atk$', 'done', None, True, 'S5b: Unity sword front kills 1-4 with the matching Unity deaths.'),
    (r'^(Kill|Wall_Kill|MultiKill_.*|Attack01)_(InitApp|InitND|Init_.*)_N_Atk$|^.*_Init.*$', 'keep', None, False,
     'Lead-ins (0.3-0.4 s step-ins). Kept: they only bring you into range.'),
    (r'^Multi(Kill|Counter|CounterAD|CounterKill)_.*$', 'keep', None, True,
     'Multi-kills and multi-counters come from the multi-kill table, where the knife sets suit a blade.'),
    (r'^(Box|Cart)_.*$', 'keep', None, False, 'Box and cart fights: contextual, kept as the knife\'s for now.'),
    (r'^(Wall_Attack0[123]|Wall_ComboEnderH_Init)_N_Atk$', 'T1', 'front', False,
     'Attacks with the enemy against a wall: Unity front strikes.'),
    (r'^.*Blocked.*$|^AttackCountered.*$', 'keep', None, True,
     'Blocked / countered attacks: these pair with the enemy\'s block; kept until the strikes are in.'),
]

SIDE = {'Left': 'Left', 'Right': 'Right', 'BackLeft': 'Back', 'BackRight': 'Back'}


def unity_pool(names):
    u = sorted({n.strip() for n in names if n.strip().startswith('xx_Fight_Sword_')})
    s = set(u)

    def grab(rx):
        return [n for n in u if re.match(rx, n)]

    def pairs(rx):
        a = [n for n in grab(rx) if n.endswith('_Atk')]
        return [[n, n[:-4] + '_Dfn'] for n in a if n[:-4] + '_Dfn' in s]
    return {
        'front': grab(r'xx_Fight_Sword_Atk_(OnSpot|2m)_Front_\d+$'),
        'side': {d: grab(rf'xx_Fight_Sword_Atk_(OnSpot|2m)_{d}_\d+$') for d in ('Left', 'Right', 'Back')},
        'combo': [[n, n.replace('_Atk', '_Dfn')] for n in grab(r'xx_Fight_Sword_Combo_0\d_Onspot_UR_to_(DL|DR|UL)_Atk$')
                  if n.replace('_Atk', '_Dfn') in s],
        'ender': grab(r'xx_Fight_Sword_Combo_Finisher_(Left|Right)_\d+$'),
        'parry': {d: pairs(rf'xx_Fight_Sword_Parry_{d}_(UL|UR|DL|DR)_Atk$') for d in ('Front', 'Left', 'Right', 'Back')},
        'perfect': {d: pairs(rf'xx_Fight_Sword_PerfectParry_{d}_(UL|UR|DL|DR)_Atk$')
                    for d in ('Front', 'Left', 'Right', 'Back')},
        'stun': grab(r'xx_Fight_Sword_ShoulderCharge_(Front|Left|Right|BackLeft|RightBack)_Atk$'),
        'wall': pairs(r'xx_Fight_Sword_Kill_Wall_\d+_Atk$'),
        'sig': pairs(r'xx_Fight_Sword_Sig_Kill_Front_\d+_Atk$'),
    }


def side_of(fam):
    m = re.search(r'_(Left|Right|BackLeft|BackRight)_', fam)
    return m.group(1) if m else None


def build(syn_names, unity_names):
    pool = unity_pool(unity_names)
    fams = collections.OrderedDict()
    for n in sorted(syn_names):
        if not (n.startswith('ACVI_Fight_xx_Knife_') and n.endswith('_Atk')):
            continue
        fam = re.sub(r'_V?\d+(_|$)', r'_N\1', n[len('ACVI_Fight_xx_Knife_'):]).replace('_N_N_', '_N_')
        fams.setdefault(fam, []).append(n)
    out, unmatched = [], []
    for fam, clips in fams.items():
        rule = next((r for r in RULES if re.match(r[0], fam)), None)
        if rule is None:
            unmatched.append(fam)
            continue
        _, status, key, paired, note = rule
        cand = []
        if status == 'T1':
            v = pool[key]
            if isinstance(v, dict):
                d = side_of(fam)
                d = SIDE.get(d, 'Front') if key == 'side' or d else ('Front' if key != 'side' else 'Left')
                v = v.get(d) or v.get('Front', [])
            cand = v
        out.append({'family': fam, 'knife_clips': clips, 'status': status, 'paired': paired,
                    'unity': cand, 'note': note})
    return out, unmatched


def markdown(rows):
    lines = ['| Knife family (talwar plays now) | Clips | Status | Unity sword clips | Note |', '|---|---|---|---|---|']
    for r in rows:
        u = r['unity']
        shown = ', '.join((x[0] if isinstance(x, list) else x).replace('xx_Fight_Sword_', '') for x in u[:4])
        if len(u) > 4:
            shown += f' (+{len(u) - 4})'
        lines.append(f'| {r["family"]} | {len(r["knife_clips"])} | {r["status"]} | {shown or "-"} | {r["note"]} |')
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--syn', required=True, help='text file, one Syndicate clip name per line')
    ap.add_argument('--unity', required=True, help='acu_fight_clips.tsv (name in column 1)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--md')
    a = ap.parse_args(argv)
    syn = [l.strip() for l in open(a.syn) if l.strip()]
    uni = [l.split('\t')[0] for l in open(a.unity)]
    rows, unmatched = build(syn, uni)
    if unmatched:
        print('families with no rule (add one):', ', '.join(unmatched))
        return 1
    json.dump(rows, open(a.out, 'w'), indent=1)
    if a.md:
        open(a.md, 'w').write(markdown(rows) + '\n')
    c = collections.Counter(r['status'] for r in rows)
    print(f'{len(rows)} families: ' + ', '.join(f'{k} {v}' for k, v in sorted(c.items())))
    empty = [r['family'] for r in rows if r['status'] == 'T1' and not r['unity']]
    if empty:
        print('T1 families with no Unity candidate:', ', '.join(empty))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

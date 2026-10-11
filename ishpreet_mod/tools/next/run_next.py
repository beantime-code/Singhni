"""One command for the next round: gada G6 + katar K1 (multi-kill table, pack 114) and Ishpreet k29a/k29b (dlc_14
201/200), plus the read-only menu dump (W0) and the optional D0a grip check. Runs in the Mac's Cowork shell.

    cd ~/mnt/Duleep_Files/ishpreet_mod/tools
    python3 next/run_next.py prepare                 # everything offline; writes Duleep_Files/Next/REPORT.md
    python3 next/run_next.py install --game-closed   # only after the user says the game is closed
    python3 next/run_next.py revert  --game-closed   # puts back what was installed before `install`
    python3 next/run_next.py status

    --only gada,katar,ishpreet,menu,d0   limits prepare/install/revert to those parts (to bisect a crash)

prepare never writes into a game folder. It:
  gada     G6: the gada gets its own blunt multi-kills (tools/fight/fsw.py add, ACVI_Gada, --replace).
  katar    K1: the katar's definition (ACVI_Brassknuckle) plays exactly the kukri's multi-kill sets (fsw.py copy):
           stabs instead of punches. Jacob's real brass knuckles share that definition; since katar m1 they already
           fight with the kukri's moves.
  ishpreet k29a = QA of the installed k28 body + k26 coat against stock Elise; k29b = one weight field (costume.
           reweight, dry run + gate). k29b is staged only if the gate passes (joins better, nothing worse).
  menu     W0: the weapon-type bindings and every weapon item with its subcategory, from the live pack 114.
  d0       D0a: left-arm and weapon-ref tracks present in the gada's attack clips (only if next_config.json lists
           the clips).
gada and katar edit the same record, so they become ONE pack 114 file; --only gada / --only katar build one of them.

Settings: Duleep_Files/next_config.json (all optional; see DEFAULTS). Nothing here guesses a game id: anything it
can't find from the game's own data or the index stops that part with a message saying what to put in the config.
"""
import argparse
import csv
import datetime
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, 'fight'))
sys.path.insert(0, os.path.join(TOOLS, 'menu'))

FSW_RID = 68552934583          # ACVIFightSystemWrapper, DataPC.forge pack 114
T_WEAPON_DEF = 0x4D7A62BB
BODY_RID, COAT_RID = 296181347212, 296181347207   # dlc_14 pack 201 body, pack 200 coat (Elise slot)
FEMALE_SKEL, ELISE_SKEL, NAKED_BODY = 101290185321, 306812379500, 401137995317
PARTS = ('gada', 'katar', 'ishpreet', 'menu', 'd0')
DEFAULTS = {
    'gada_definition': None,       # file id of ACVI_Gada; found by name in pack 114 when None
    'first_id': None,              # first free object id for new objects; a free private range is found when None
    'id_base': 987654400000,       # where the free-range search starts
    'coat_band': 0.06,
    'k28_log': None,               # k28 build log (names the pieces in the QA report); optional
    'records': {},                 # {"<record id>": "<forge path relative to the game folder>:<pack index>"}
    'd0': None,                    # {"clips": ["<.data file or forge:index>:<record id>", ...], "reference": same}
    'out_names': {'body': 'Evie/dlc14_201_JaspreetBody_k29b.data', 'coat': 'Evie/dlc14_200_EliseCoat_k29b.data',
                  'p114': 'Next/DataPC_114_{tag}.data'},
}


# ---------------------------------------------------------------------------------------------------- environment
class Env:
    """acs_kit paths and modules. Tests pass a fake."""

    def __init__(self):
        from acs_kit_loader import load
        self.forge, self.paths = load()
        self.WORK, self.GAME = self.paths.WORK, self.paths.GAME
        self.DPF = os.path.join(self.GAME, 'DataPC.forge')
        self.LIVE_DLC14, self.ORIG_DLC14 = self.paths.LIVE_DLC14, self.paths.ORIG_DLC14


def config(env):
    p = os.path.join(env.WORK, 'next_config.json')
    c = json.loads(json.dumps(DEFAULTS))
    if os.path.exists(p):
        with open(p) as f:
            user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(c.get(k), dict):
                c[k].update(v)
            else:
                c[k] = v
    return c


class Stop(Exception):
    """a part can't continue; the message says what is missing"""


def _rname(r):
    n = struct.unpack_from('<I', r, 8)[0] if len(r) > 12 else 0
    return r[12:12 + n].decode('latin-1') if 0 < n < 300 else ''


def _rtype(r):
    return struct.unpack_from('<I', r, 0)[0] if len(r) >= 4 else None


def find_free(blobs, n, base):
    """first id >= base such that no u64 (at any byte offset) in `blobs` falls in [id, id + n)"""
    import numpy as np
    vals = []
    for b in blobs:
        for k in range(8):
            m = (len(b) - k) // 8
            if m > 0:
                vals.append(np.frombuffer(b, '<u8', m, k))
    v = np.concatenate(vals) if vals else np.zeros(0, np.uint64)
    start = base
    while True:
        hit = v[(v >= start) & (v < start + n)]
        if not len(hit):
            return start
        start = int(hit.max()) + 1


def locate(env, cfg, rid):
    """(forge path, pack index) of a record: config 'records' first, else the acs_kit deep index"""
    o = cfg['records'].get(str(rid))
    if o:
        fp, idx = o.rsplit(':', 1)
        return os.path.join(env.GAME, fp), int(idx)
    for name in ('acs_index_deep.csv', 'acs_index.csv'):
        p = os.path.join(env.WORK, name)
        if not os.path.exists(p):
            continue
        with open(p, newline='') as f:
            for row in csv.DictReader(f):
                if row['id'] == str(rid):
                    return os.path.join(env.GAME, row['forge']), int(row['pack_index'])
    raise Stop(f'record {rid} not found in the index; add "records": {{"{rid}": "<forge>:<pack index>"}} '
               f'to next_config.json')


def read_record(env, cfg, rid, prefer_original=True):
    fp, idx = locate(env, cfg, rid)
    if prefer_original and os.path.basename(fp) == os.path.basename(env.LIVE_DLC14):
        fp = env.ORIG_DLC14                     # build from the untouched dlc_14 copy
    return env.forge.Pack.from_forge(idx, fp).get(rid)


def read_ref(env, s):
    """'<file.data>:<rid>' or '<forge relative to the game>:<index>:<rid>' -> record bytes"""
    parts = s.split(':')
    if len(parts) == 3:
        return env.forge.Pack.from_forge(int(parts[1]), os.path.join(env.GAME, parts[0])).get(int(parts[2]))
    path = parts[0] if os.path.isabs(parts[0]) else os.path.join(env.WORK, parts[0])
    return env.forge.Pack.from_file(path).get(int(parts[1]))


# ---------------------------------------------------------------------------------------------------- parts
def part_fight(env, cfg, out, want):
    """gada G6 and/or katar K1 in one pack 114 file"""
    import fsw
    P = env.forge.Pack.from_forge(114, env.DPF)
    raw = P.get(FSW_RID)
    open(os.path.join(out, 'inputs', 'fsw_installed.bin'), 'wb').write(raw)
    defs = {_rname(r): rid for rid, _, r in P.recs if _rtype(r) == T_WEAPON_DEF}
    for nm, rid in (('ACVI_Kukri', fsw.KUKRI), ('ACVI_Brassknuckle', fsw.KNUCKLE), ('ACVI_Cane', fsw.CANE)):
        if defs.get(nm, rid) != rid:
            raise Stop(f'{nm} has id {defs[nm]} in pack 114, expected {rid}: stop and check')
    registered = fsw.weapon_list(raw)[1]
    lines, notes = [], []
    first = cfg['first_id'] or find_free([r for _, _, r in P.recs], 400, cfg['id_base'])
    new, tag = raw, []
    before_k = fsw.stabs(raw, fsw.KNUCKLE)
    if 'gada' in want:
        gada = cfg['gada_definition'] or defs.get('ACVI_Gada')
        if not gada:
            raise Stop('no weapon definition named ACVI_Gada in pack 114; set "gada_definition" in next_config.json')
        if gada not in registered:
            notes.append(f'ACVI_Gada ({gada}) is NOT in the multi-kill record\'s list of registered definitions '
                         f'({len(registered)} entries). The overrides may be ignored in game; the boot test decides.')
        new, rep = fsw.add_weapon(new, gada, first, replace=True)
        first = rep['next_free_id']
        g = fsw.stabs(new, gada)
        lines.append(f'G6 gada: {sum(r["added"] for r in rep["entries"])} overrides added ({rep["removed_first"]} '
                     f'earlier ones replaced), record {rep["grew_by"]:+d} bytes; stabbing variants the gada can play: '
                     f'{g[0]} of {g[1]}')
        json.dump(rep, open(os.path.join(out, 'g6_report.json'), 'w'), indent=1)
        tag.append('G6')
    if 'katar' in want:
        new, rep = fsw.copy_weapon(new, fsw.KUKRI, fsw.KNUCKLE, first)
        first = rep['next_free_id']
        k = fsw.stabs(new, fsw.KNUCKLE)
        lines.append(f'K1 katar: ACVI_Brassknuckle now plays the kukri\'s multi-kill sets; stabbing variants '
                     f'{before_k[0]}/{before_k[1]} -> {k[0]}/{k[1]} (kukri: {"/".join(map(str, fsw.stabs(new, fsw.KUKRI)))})')
        json.dump(rep, open(os.path.join(out, 'k1_report.json'), 'w'), indent=1)
        tag.append('K1')
    tag = '_'.join(tag)
    open(os.path.join(out, f'fsw_{tag}.bin'), 'wb').write(new)
    P.set(FSW_RID, new)
    dest = os.path.join(env.WORK, cfg['out_names']['p114'].format(tag=tag))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    size = P.save(dest)
    Q = env.forge.Pack.from_file(dest)
    assert Q.get(FSW_RID) == new and len(fsw.parse(Q.get(FSW_RID))) == 16
    old = {rid: r for rid, _, r in env.forge.Pack.from_forge(114, env.DPF).recs}
    changed = [rid for rid, _, r in Q.recs if old.get(rid) != r]
    assert changed == [FSW_RID], changed
    lines.append(f'pack 114 rebuilt: {size} bytes (live entry {env.forge.entries(env.DPF)[114][2]}); read back OK, '
                 f'only record {FSW_RID} differs; new object ids end at {first - 1}')
    return {'tag': tag, 'lines': lines, 'notes': notes,
            'install': [{'tag': tag, 'forge': env.DPF, 'index': 114, 'file': dest}]}


def part_ishpreet(env, cfg, out):
    from costume import reweight
    inst = env.forge.installed(env.LIVE_DLC14)
    if 201 not in inst or 200 not in inst:
        raise Stop('dlc_14 packs 201/200 are not in reloc_registry.json; point "records" at the k28 body / k26 coat')
    d = os.path.join(out, 'inputs')
    files = {}
    for key, rid, src in (('body', BODY_RID, inst[201]), ('coat', COAT_RID, inst[200])):
        files[key] = os.path.join(d, f'installed_{key}.bin')
        open(files[key], 'wb').write(env.forge.Pack.from_file(src).get(rid))
    for key, idx, rid in (('orig_body', 201, BODY_RID), ('orig_coat', 200, COAT_RID)):
        files[key] = os.path.join(d, f'{key}.bin')
        open(files[key], 'wb').write(env.forge.Pack.from_forge(idx, env.ORIG_DLC14).get(rid))
    for key, rid in (('female_skel', FEMALE_SKEL), ('elise_skel', ELISE_SKEL), ('naked', NAKED_BODY)):
        files[key] = os.path.join(d, f'{key}.bin')
        open(files[key], 'wb').write(read_record(env, cfg, rid))
    a = argparse.Namespace(body=files['body'], orig=files['orig_body'], coat=files['coat'],
                           coat_band=cfg['coat_band'], source=files['naked'],
                           skeleton=[files['female_skel'], files['elise_skel']],
                           baseline=[f'body={files["orig_body"]}', f'coat={files["orig_coat"]}'],
                           out=os.path.join(out, 'k29b'), write=True)
    res = reweight.run(a)
    ok, why = res['gate']
    before = {r['gate']: r for r in res['before']}
    lines = ['k29a (installed k28 body + k26 coat vs stock Elise): ' + ', '.join(
        f'{g.split()[0]} {"PASS" if r["pass"] else "FAIL"} {reweight._count(r)}' for g, r in before.items())]
    g8 = before.get('G8 materials', {})
    for s in g8.get('issues', [])[:6] + [f'{k}: {v}' for k, v in list(g8.get('info', {}).items())[:6]]:
        lines.append(f'  G8: {s}')
    lines.append(f'k29b re-weight gate: {"PASS" if ok else "FAIL"}' + ('' if ok else ': ' + '; '.join(why)))
    if not ok:
        return {'tag': 'k29b', 'lines': lines + ['k29b NOT staged (gate failed): nothing to install for Ishpreet'],
                'notes': [], 'install': []}
    plan = []
    for key, idx, rid, src in (('body', 201, BODY_RID, inst[201]), ('coat', 200, COAT_RID, inst[200])):
        P = env.forge.Pack.from_file(src)
        rec = open(res['written'][key], 'rb').read()
        assert len(rec) == len(P.get(rid)), 'same-size edit expected'
        P.set(rid, rec)
        dest = os.path.join(env.WORK, cfg['out_names'][key])
        P.save(dest)
        Q = env.forge.Pack.from_file(dest)
        assert Q.get(rid) == rec
        orig = {x: r for x, _, r in env.forge.Pack.from_file(src).recs}
        assert [x for x, _, r in Q.recs if r != orig.get(x)] == [rid]
        plan.append({'tag': 'k29b', 'forge': env.LIVE_DLC14, 'index': idx, 'file': dest})
        lines.append(f'k29b {key}: {os.path.relpath(dest, env.WORK)} (built on {os.path.relpath(src, env.WORK)})')
    return {'tag': 'k29b', 'lines': lines, 'notes': [], 'install': plan}


def part_menu(env, cfg, out):
    import uienum
    P = env.forge.Pack.from_forge(114, env.DPF)
    t = uienum.menu_tables(P.recs)
    json.dump(t, open(os.path.join(out, 'menu_w0.json'), 'w'), indent=1)
    subs = {}
    for w in t['weapons']:
        subs.setdefault(w['subcategory'], []).append(w['name'])
    lines = [f'weapon items by subcategory: ' + ', '.join(f'{k}: {len(v)}' for k, v in sorted(subs.items()))]
    for nm, rows in t['bindings'].items():
        lines.append(f'{nm}: ' + ', '.join(f'{r["value"]}={r["name"] or "?"}' + ('' if r['icon'] else ' (no icon)')
                                           for r in rows))
    return {'tag': 'W0', 'lines': lines, 'notes': [], 'install': []}


D0_BONES = {'LeftClavicle': 0xb898b609, 'LeftArm': 0xeb830ada, 'LeftForeArm': 0x89b93a80, 'LeftHand': 0xb675f36c,
            'RightHand_Weapon_Ref': 0x3fb256e5, 'LeftHand_Weapon_Ref': 0xa9611103}


def part_d0(env, cfg, out):
    d0 = cfg.get('d0')
    if not d0 or not d0.get('clips'):
        raise Stop('D0a skipped: list the gada attack clips as "d0": {"clips": [...]} in next_config.json')
    rows = []
    refs = list(d0['clips']) + ([d0['reference']] if d0.get('reference') else [])
    for s in refs:
        r = read_ref(env, s)
        rows.append((s, {b: r.count(struct.pack('<I', h)) > 0 for b, h in D0_BONES.items()}))
    lines = ['D0a tracks (y = the clip has a track for the bone):']
    for s, h in rows:
        lines.append(f'  {s}: ' + ' '.join(f'{b}={"y" if v else "MISSING"}' for b, v in h.items()))
    return {'tag': 'D0a', 'lines': lines, 'notes': [], 'install': []}


# ---------------------------------------------------------------------------------------------------- commands
def out_dir(env):
    d = os.path.join(env.WORK, 'Next')
    os.makedirs(os.path.join(d, 'inputs'), exist_ok=True)
    return d


BOOT_TEST = """## One boot (game closed before and after)
Launch Syndicate fresh from the launcher, load the save, then:
1. **Gada (G6):** fight 3-4 thugs with the GADA as Jacob, then as Evie. Bring 2-3 to low health together (multi-kill)
   and get attacked by two at once (multi-counter). Expected: blunt blows (punch- or cane-style), no stabs.
2. **Katar (K1):** same with a KATAR. Expected: the multi-kills stab like the kukri's instead of punching.
3. **Ishpreet (k29b):** as Evie in the Ishpreet outfit: stand (front, back), climb a wall with the camera BELOW her,
   hang from a ledge, crouch. Screenshots numbered 2, 3, 6, 7, 9 as in COSTUME_PIPELINE.md stage 7.
Then quit the game completely and report: crash? which test looked wrong? the screenshots.
If it crashes at boot: `python3 next/run_next.py revert --game-closed --only gada,katar` first (pack 114), boot again;
if it still crashes, `--only ishpreet`.
"""


def prepare(env, only):
    cfg = config(env)
    out = out_dir(env)
    sections, plan, notes = [], [], []
    jobs = []
    if {'gada', 'katar'} & only:
        jobs.append(('Gada G6 + katar K1 (pack 114)', lambda: part_fight(env, cfg, out, only)))
    if 'ishpreet' in only:
        jobs.append(('Ishpreet k29a + k29b (dlc_14 201/200)', lambda: part_ishpreet(env, cfg, out)))
    if 'menu' in only:
        jobs.append(('Weapons menu W0 (read only)', lambda: part_menu(env, cfg, out)))
    if 'd0' in only:
        jobs.append(('Gada D0a grip tracks (read only)', lambda: part_d0(env, cfg, out)))
    for title, fn in jobs:
        try:
            r = fn()
            sections.append((title, r['lines'], r['notes']))
            plan += r['install']
        except Stop as e:
            sections.append((title, [f'STOPPED: {e}'], []))
    reg = {}
    for p in plan:
        reg.setdefault(p['forge'], env.forge.installed(p['forge']))
        prev = reg[p['forge']].get(p['index'])
        p['previous'] = prev
    when = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    json.dump({'prepared': when, 'items': plan}, open(os.path.join(out, 'install_plan.json'), 'w'), indent=1)
    md = [f'# Next round: prepared {when}', '', 'Nothing has been installed. Built files and checks:', '']
    for title, lines, nts in sections:
        md += [f'## {title}'] + [f'- {x}' for x in lines] + [f'- **Note:** {n}' for n in nts] + ['']
    md += ['## Install plan (`install --game-closed`)', '| Build | Forge | Pack | File | Revert to |', '|---|---|---|---|---|']
    for p in plan:
        md.append(f'| {p["tag"]} | {os.path.basename(p["forge"])} | {p["index"]} | {os.path.relpath(p["file"], env.WORK)} '
                  f'| {os.path.relpath(p["previous"], env.WORK) if p["previous"] else "the forge without relocation"} |')
    md += ['', 'Ishpreet QA sheets: `Next/k29b/qa_before/` (= k29a) and `Next/k29b/qa_after/`; show the user '
           '`climb_reach_L.png`, `hang_both.png`, `crouch.png` and their `stock_*` versions before installing.', '',
           BOOT_TEST]
    open(os.path.join(out, 'REPORT.md'), 'w').write('\n'.join(md) + '\n')
    print('\n'.join(md))
    return plan


def _patch_log(env, lines):
    p = os.path.join(env.WORK, 'PATCH_LOG.md')
    with open(p, 'a') as f:
        f.write('\n' + '\n'.join(lines) + '\n')


def install(env, only, game_closed):
    if not game_closed:
        raise SystemExit('Ask the user whether the game is closed; rerun with --game-closed only after they say yes.')
    out = out_dir(env)
    plan = json.load(open(os.path.join(out, 'install_plan.json')))
    items = [p for p in plan['items'] if _part_of(p['tag']) & only]
    if not items:
        raise SystemExit('nothing staged for ' + ','.join(sorted(only)))
    ok = True
    for fp in sorted({p['forge'] for p in items}):
        m = {p['index']: p['file'] for p in items if p['forge'] == fp}
        ok &= bool(env.forge.install(m, fp))
    when = datetime.date.today().isoformat()
    for tag in sorted({p['tag'] for p in items}):
        mine = [p for p in items if p['tag'] == tag]
        _patch_log(env, [f'## {when} — {tag} [ishpreet_mod/tools/next/run_next.py; report Next/REPORT.md]'] + [
            f'- {os.path.basename(p["forge"])} {p["index"]} = {os.path.relpath(p["file"], env.WORK)}; revert: '
            + (os.path.relpath(p['previous'], env.WORK) if p['previous'] else 'None (forge without relocation)')
            for p in mine] + [f'- Revert all of it: `python3 next/run_next.py revert --game-closed --only '
                              f'{",".join(sorted(_part_of(tag)))}`'])
    shutil.copy(os.path.join(out, 'install_plan.json'), os.path.join(out, 'installed_plan.json'))
    print('ALL OK' if ok else 'CHECK MISMATCH')
    return ok


def revert(env, only, game_closed):
    if not game_closed:
        raise SystemExit('Ask the user whether the game is closed; rerun with --game-closed only after they say yes.')
    out = out_dir(env)
    plan = json.load(open(os.path.join(out, 'installed_plan.json')))
    items = [p for p in plan['items'] if _part_of(p['tag']) & only]
    ok = True
    for fp in sorted({p['forge'] for p in items}):
        ok &= bool(env.forge.install({p['index']: p['previous'] for p in items if p['forge'] == fp}, fp))
    _patch_log(env, [f'## {datetime.date.today().isoformat()} — reverted {", ".join(sorted({p["tag"] for p in items}))}'
                     f' [run_next.py revert]'])
    print('reverted' if ok else 'CHECK MISMATCH')
    return ok


def _part_of(tag):
    return {'G6': {'gada'}, 'K1': {'katar'}, 'G6_K1': {'gada', 'katar'}, 'k29b': {'ishpreet'}}.get(tag, set())


def main(argv=None, env=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('prepare', 'install', 'revert', 'status'))
    ap.add_argument('--only', default=','.join(PARTS))
    ap.add_argument('--game-closed', action='store_true')
    a = ap.parse_args(argv)
    only = set(a.only.split(','))
    bad = only - set(PARTS)
    if bad:
        raise SystemExit(f'unknown part(s): {", ".join(bad)}')
    env = env or Env()
    if a.cmd == 'prepare':
        return prepare(env, only)
    if a.cmd == 'install':
        return install(env, only, a.game_closed)
    if a.cmd == 'revert':
        return revert(env, only, a.game_closed)
    print(open(os.path.join(out_dir(env), 'REPORT.md')).read())


if __name__ == '__main__':
    main()

"""prepare -> install -> revert with a stand-in for acs_kit (no game files touched). The multi-kill record and the menu
records are the real ones when NEXT_FIXTURES points at a folder holding fsw_syn.bin and WeaponType.*.bin; otherwise
the synthetic record from tools/fight/test_fsw.py is used. The costume re-weight itself is stubbed here (its own
tests are tools/costume/test_costume.py).

    python3 next/test_run_next.py
"""
import glob
import os
import pickle
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'fight'))
import run_next  # noqa: E402
import fsw  # noqa: E402
import test_fsw  # noqa: E402


def _rec(typ, name, body=b''):
    return struct.pack('<III', typ, 0, len(name)) + name.encode() + body


class FakePack:
    def __init__(self, recs):
        self.recs = [list(r) for r in recs]

    @classmethod
    def from_file(cls, p):
        return cls(pickle.load(open(p, 'rb')))

    def get(self, rid):
        return next(r for i, f, r in self.recs if i == rid)

    def set(self, rid, data):
        for e in self.recs:
            if e[0] == rid:
                e[2] = bytes(data)
                return
        raise KeyError(rid)

    def save(self, out):
        b = pickle.dumps(self.recs)
        open(out, 'wb').write(b)
        return len(b)


class FakeForge:
    def __init__(self, packs):
        self.packs, self.reg, self.calls = packs, {}, []
        Fake = self

        class P(FakePack):
            @classmethod
            def from_forge(cls, idx, fp):
                key = (os.path.basename(fp), idx)
                if key in Fake.reg_files():
                    return FakePack.from_file(Fake.reg_files()[key])
                return cls(Fake.packs[key])
        self.Pack = P

    def reg_files(self):
        return {(os.path.basename(fp), i): p for fp, m in self.reg.items() for i, p in m.items()}

    def entries(self, fp):
        return {i: ('x', 0, 1000, 0) for (f, i) in self.packs if f == os.path.basename(fp)}

    def installed(self, fp):
        return dict(self.reg.get(fp, {}))

    def install(self, mapping, fp):
        self.calls.append((fp, dict(mapping)))
        cur = self.reg.setdefault(fp, {})
        for i, p in mapping.items():
            if p is None:
                cur.pop(i, None)
            else:
                cur[i] = p
        return True


class FakeEnv:
    def __init__(self, work, forge):
        self.WORK = work
        self.GAME = os.path.join(work, 'game')
        self.DPF = os.path.join(self.GAME, 'DataPC.forge')
        self.LIVE_DLC14 = os.path.join(self.GAME, 'dlc_14/DataPC_14_dlc.forge')
        self.ORIG_DLC14 = os.path.join(work, 'DataPC_14_dlc.forge.original')
        self.forge = forge


def _fixtures():
    d = os.environ.get('NEXT_FIXTURES')
    if d and os.path.exists(os.path.join(d, 'fsw_syn.bin')):
        import importlib
        importlib.reload(fsw)
        wt = glob.glob(os.path.join(d, 'WeaponType.*.bin'))
        return open(os.path.join(d, 'fsw_syn.bin'), 'rb').read(), (open(wt[0], 'rb').read() if wt else b''), True
    rec, names, blood = test_fsw.synthetic()
    test_fsw._install(names, blood)
    return rec, b'', False


def test_prepare_install_revert():
    fswrec, wt, real = _fixtures()
    gada = 900000000001
    p114 = [(run_next.FSW_RID, 0, fswrec),
            (fsw.KUKRI, 0, _rec(run_next.T_WEAPON_DEF, 'ACVI_Kukri')),
            (fsw.KNUCKLE, 0, _rec(run_next.T_WEAPON_DEF, 'ACVI_Brassknuckle')),
            (fsw.CANE, 0, _rec(run_next.T_WEAPON_DEF, 'ACVI_Cane')),
            (gada, 0, _rec(run_next.T_WEAPON_DEF, 'ACVI_Gada')),
            (60702028383, 0, _rec(0x2E772CD8, 'WeaponType', wt)),
            (280403707645, 0, _rec(0xC69075AB, 'ACVI_Kukri_02', bytes.fromhex(
                '5d04a78155da09000000000000005d04a78156da0900a03da2090200000001000000')))]
    with tempfile.TemporaryDirectory() as work:
        forge = FakeForge({('DataPC.forge', 114): p114})
        env = FakeEnv(work, forge)
        plan = run_next.main(['prepare', '--only', 'gada,katar,menu,d0'], env=env)
        assert len(plan) == 1 and plan[0]['index'] == 114 and plan[0]['previous'] is None
        rep = open(os.path.join(work, 'Next', 'REPORT.md')).read()
        assert 'G6 gada' in rep and 'K1 katar' in rep and 'D0a skipped' in rep and 'subcategory' in rep
        new = FakePack.from_file(plan[0]['file']).get(run_next.FSW_RID)
        assert fsw.stabs(new, fsw.KNUCKLE) == fsw.stabs(new, fsw.KUKRI)
        assert fsw.stabs(new, gada)[0] == 0
        try:
            run_next.main(['install'], env=env)
            raise AssertionError('install must refuse without --game-closed')
        except SystemExit:
            pass
        run_next.main(['install', '--game-closed'], env=env)
        assert forge.calls[-1] == (env.DPF, {114: plan[0]['file']})
        log = open(os.path.join(work, 'PATCH_LOG.md')).read()
        assert 'G6_K1' in log and 'revert' in log
        run_next.main(['revert', '--game-closed'], env=env)
        assert forge.calls[-1] == (env.DPF, {114: None}) and 114 not in forge.reg[env.DPF]
        if real:
            assert 'WeaponType: 0=Unarmed' in rep, rep


def test_ishpreet_gate_stages_only_on_pass():
    from costume import reweight
    with tempfile.TemporaryDirectory() as work:
        env = FakeEnv(work, FakeForge({}))
        live = env.LIVE_DLC14
        os.makedirs(os.path.join(work, 'Evie'))
        body_pack = os.path.join(work, 'Evie', 'k28.data')
        coat_pack = os.path.join(work, 'Evie', 'k26.data')
        FakePack([(run_next.BODY_RID, 0, b'B' * 64), (5, 0, b'x')]).save(body_pack)
        FakePack([(run_next.COAT_RID, 0, b'C' * 64)]).save(coat_pack)
        env.forge.reg[live] = {201: body_pack, 200: coat_pack}
        env.forge.packs.update({('DataPC_14_dlc.forge.original', 201): [(run_next.BODY_RID, 0, b'b' * 64)],
                                ('DataPC_14_dlc.forge.original', 200): [(run_next.COAT_RID, 0, b'c' * 64)],
                                ('London.forge', 7): [(run_next.FEMALE_SKEL, 0, b's'), (run_next.ELISE_SKEL, 0, b'e'),
                                                      (run_next.NAKED_BODY, 0, b'n')]})
        open(os.path.join(work, 'acs_index_deep.csv'), 'w').write(
            'forge,pack_index,name,id,offset,size,record_type\n' + ''.join(
                f'London.forge,7,x,{r},0,0,0\n' for r in (run_next.FEMALE_SKEL, run_next.ELISE_SKEL, run_next.NAKED_BODY)))
        real_run = reweight.run
        rows = lambda n: [{'gate': 'G3 junctions', 'pass': not n, 'count': n}]  # noqa: E731

        def fake_run(a, n_after):
            os.makedirs(a.out, exist_ok=True)
            w = {}
            for k, ch in (('body', b'X'), ('coat', b'Y')):
                w[k] = os.path.join(a.out, k + '.record')
                open(w[k], 'wb').write(ch * 64)
            before, after = rows(4), rows(n_after)
            return {'before': before, 'after': after, 'written': w, 'info': {}, 'gate': reweight.gate(before, after)}
        try:
            reweight.run = lambda a: fake_run(a, 4)          # nothing improves: not staged
            r = run_next.part_ishpreet(env, run_next.config(env), run_next.out_dir(env))
            assert r['install'] == [] and any('NOT staged' in x for x in r['lines'])
            reweight.run = lambda a: fake_run(a, 0)
            r = run_next.part_ishpreet(env, run_next.config(env), run_next.out_dir(env))
            assert [p['index'] for p in r['install']] == [201, 200]
            b = FakePack.from_file(r['install'][0]['file'])
            assert b.get(run_next.BODY_RID) == b'X' * 64 and b.get(5) == b'x'
        finally:
            reweight.run = real_run


def test_find_free():
    blob = struct.pack('<QQ', 1000, 1003) + b'\x00' + struct.pack('<Q', 1010)
    assert run_next.find_free([blob], 5, 1000) == 1004      # 1000 and 1003 taken; 1004..1008 free
    assert run_next.find_free([blob], 8, 1000) == 1011      # 1004..1011 would hold 1010


if __name__ == '__main__':
    for t in [test_find_free, test_prepare_install_revert, test_ishpreet_gate_stages_only_on_pass]:
        t()
        print('ok', t.__name__)

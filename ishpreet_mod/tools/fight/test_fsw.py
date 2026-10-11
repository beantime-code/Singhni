"""Tests for fsw.py on a synthetic ACVIFightSystemWrapper record (same serialization, fake ids), plus the real record
when FSW_RECORD points at it (Syndicate pack 114, file 68552934583).

    python3 -m pytest test_fsw.py      or      python3 test_fsw.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fsw  # noqa: E402

GADA = 900000000001


def _ref(i):
    return b'\x01\x00' + struct.pack('<Q', i)


def _clips(ids):
    return struct.pack('<I', len(ids)) + b''.join(_ref(i) for i in ids)


def _obj(oid, tag):
    return b'\x00' + struct.pack('<Q', oid) + tag


def synthetic():
    """16 entries; knuckle variants blunt, cane variants stab (except entry 0 set 1), kukri knife, one HB variant."""
    names, blood, nid = {}, {}, [5000]

    def clip(nm, b):
        nid[0] += 1
        names[nid[0]] = nm
        blood[nm] = b
        return nid[0]

    def kill(w, k, v, letters):
        return [clip(f'ACVI_Fight_xx_{w}_{k}_V{v}_Atk', '-')] + [
            clip(f'ACVI_Fight_Npc_{w}_{k}_V{v}_Dfn{j + 1:02d}', c) for j, c in enumerate(letters)]

    rec = b'\x01' + struct.pack('<Q', 68552934583) + bytes.fromhex('63e3d671')
    rec += struct.pack('<I', 3) + b''.join(_ref(w) for w in (fsw.KUKRI, fsw.KNUCKLE, fsw.CANE))
    rec += struct.pack('<I', 16)
    oid = 7000
    for k in range(16):
        nm = f'MultiKill_T{k}'
        rec += _obj(oid, fsw.ENTRY) + struct.pack('<I', len(nm)) + nm.encode() + b'\x00' + struct.pack('<I', k)
        oid += 1
        rec += _clips(kill('Knife', nm, 1, 'PP'))
        subs = []
        for y in (0, 1):
            for w, wn, letters in ((fsw.KNUCKLE, 'Knuckle', 'BB'), (fsw.CANE, 'Cane', 'BB' if (k, y) == (0, 1) else 'PP'),
                                   (fsw.KUKRI, 'Knife', 'PP')):
                variants = [kill(wn, nm, 1 + y, letters)]
                if w == fsw.KNUCKLE and k == 5:
                    variants.append(kill('KnuckleHB', nm, 2, 'BB'))
                s = _obj(oid, fsw.SUB) + b'\x00' + struct.pack('<QI', w, y) + _clips([]) + struct.pack('<I', len(variants))
                oid += 1
                for v in variants:
                    s += _obj(oid, fsw.VAR) + _clips(v)
                    oid += 1
                subs.append(s)
        rec += struct.pack('<I', len(subs)) + b''.join(subs) + b'\x00' * 8
    return rec, names, blood


def _install(names, blood):
    fsw.NAMES.clear()
    fsw.NAMES.update(names)
    fsw.BLOOD.clear()
    fsw.BLOOD.update(blood)


def test_parse_synthetic():
    rec, names, blood = synthetic()
    _install(names, blood)
    e = fsw.parse(rec)
    assert len(e) == 16 and all(len(x['subs']) == 6 for x in e)
    assert fsw.weapon_list(rec)[1] == [fsw.KUKRI, fsw.KNUCKLE, fsw.CANE]


def test_add_blunt_only_and_strip_roundtrip():
    rec, names, blood = synthetic()
    _install(names, blood)
    new, rep = fsw.add_weapon(rec, GADA, 10 ** 12)
    entries = fsw.parse(new)
    for e in entries:
        mine = [s for s in e['subs'] if s['weapon'] == GADA]
        assert len(mine) == 2
        for s in mine:
            for v in s['variants']:
                n = [fsw.name(c) for c in v['clips']]
                assert 'P' not in fsw.rating(v['clips']) and not any('HB_' in x for x in n)
    # entry 0, set 1: the cane's variant is blunt there, so the cane is preferred; elsewhere the knuckles
    donors = {(r['entry'], c['y']): c['donor'] for r in rep['entries'] for c in r['characters']}
    assert donors[('MultiKill_T0', 1)] == fsw.name(fsw.CANE) or donors[('MultiKill_T0', 1)] == 'ACVI_Cane'
    assert all(d in ('ACVI_Brassknuckle', f'0x{fsw.KNUCKLE:x}') for (en, y), d in donors.items() if (en, y) != ('MultiKill_T0', 1))
    # the HB knuckle variant in entry 5 is dropped
    t5 = [r for r in rep['entries'] if r['entry'] == 'MultiKill_T5'][0]
    assert all(len(c['variants']) == 1 for c in t5['characters'])
    stripped, n = fsw.strip_weapon(new, GADA)
    assert n == 32 and stripped == rec
    again, rep2 = fsw.add_weapon(new, GADA, 2 * 10 ** 12, replace=True)
    assert rep2['removed_first'] == 32 and len(again) == len(new)


def test_duplicate_refused():
    rec, names, blood = synthetic()
    _install(names, blood)
    new, _ = fsw.add_weapon(rec, GADA, 10 ** 12)
    try:
        fsw.add_weapon(new, GADA, 10 ** 12)
    except ValueError:
        return
    raise AssertionError('second add without replace should fail')


def test_real_record():
    path = os.environ.get('FSW_RECORD')
    if not path or not os.path.exists(path):
        return
    import importlib
    importlib.reload(fsw)
    b = open(path, 'rb').read()
    e = fsw.parse(b)
    assert len(e) == 16
    new, rep = fsw.add_weapon(b, GADA, 10 ** 12, replace=True)
    assert fsw.strip_weapon(new, GADA)[0] == fsw.strip_weapon(b, GADA)[0]


if __name__ == '__main__':
    for t in [test_parse_synthetic, test_add_blunt_only_and_strip_roundtrip, test_duplicate_refused, test_real_record]:
        t()
        print('ok', t.__name__)

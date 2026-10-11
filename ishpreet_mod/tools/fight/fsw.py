"""ACVIFightSystemWrapper (type 71D6E363, Syndicate DataPC.forge pack 114, file 68552934583): multi-kill tables.

The game picks every multi-kill (2-4 enemies) and multi-counter from this record, not from the fight graph:

    entry (b48e5f6f)  name e.g. 'MultiKill_Vs4_12-3-6-9_V01', index, DEFAULT clip list [Atk, Dfn1..n],
                      list of weapon overrides
    override (443c0f4f)  weapon definition ref (4D7A62BB: ACVI_Kukri / ACVI_Brassknuckle / ACVI_Cane),
                      y (clip set: 0 = xx_ clips, 1 = xy_ clips; one per twin, most likely),
                      direct clip list, list of variants
    variant (c36be86f)  clip list [Atk, Dfn1..n]

A weapon whose definition has no override plays the DEFAULT, which is the knife (kukri) set. The gada has its own
definition (ACVI_Gada) and no overrides, so every gada multi-kill and multi-counter is a knife stab.

Serialization (verified on the stock record, all 16 entries parse to the byte):
    object header  = u8 0, u64 object id, u32 class CRC
    clip/item ref  = u8 1, u8 0, u64 file id          (lists: u32 count + refs)
    weapon ref     = u8 0, u64 file id
    name           = u32 length (no NUL), bytes, NUL

    python3 fsw.py show RECORD.bin                    # table + blunt/pierce rating of every variant
    python3 fsw.py add  RECORD.bin --weapon ID --first-id ID --out NEW.bin [--report report.json]
    python3 fsw.py copy RECORD.bin --src ID --dst ID --first-id ID --out NEW.bin   # dst plays src's sets

`add` gives a weapon its own overrides in all 16 entries, built from blunt variants only (see pick_variants).
It inserts objects (the record grows); nothing else changes. Object ids come from --first-id upward, so the
caller must pass the start of a free id range (the same allocator used for the H1/G5 records).
"""
import argparse
import json
import os
import struct
import sys

ENTRY = bytes.fromhex('6f5f8eb4')
SUB = bytes.fromhex('4f0f3c44')
VAR = bytes.fromhex('6fe86bc3')
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', '..', 'data', 'graph')
KUKRI, KNUCKLE, CANE = 212431133686, 212431133687, 212431133688


class _R:
    def __init__(self, b, o):
        self.b, self.o = b, o

    def u8(self):
        self.o += 1
        return self.b[self.o - 1]

    def u32(self):
        self.o += 4
        return struct.unpack_from('<I', self.b, self.o - 4)[0]

    def u64(self):
        self.o += 8
        return struct.unpack_from('<Q', self.b, self.o - 8)[0]

    def hdr(self, tag):
        flag, oid, t = self.u8(), self.u64(), self.b[self.o:self.o + 4]
        self.o += 4
        if flag != 0 or t != tag:
            raise ValueError(f'expected {tag.hex()} object at {self.o - 13}, got flag {flag} tag {t.hex()}')
        return oid

    def clips(self):
        n, out = self.u32(), []
        for _ in range(n):
            a, c = self.u8(), self.u8()
            if (a, c) != (1, 0):
                raise ValueError(f'bad clip ref prefix at {self.o - 2}')
            out.append(self.u64())
        return out


def parse(b):
    """Entries in file order. Every object keeps its byte span (start, end) for rebuilding."""
    starts, i = [], b.find(ENTRY)
    while i != -1:
        starts.append(i - 9)
        i = b.find(ENTRY, i + 4)
    entries = []
    for k, o in enumerate(starts):
        r = _R(b, o)
        eid = r.hdr(ENTRY)
        n = r.u32()
        name = b[r.o:r.o + n].decode('latin1')
        r.o += n
        if b[r.o] != 0:
            raise ValueError(f'name not NUL-terminated at {r.o}')
        r.o += 1
        index = r.u32()
        default = r.clips()
        nsub_at = r.o
        subs = []
        for _ in range(r.u32()):
            s0 = r.o
            sid = r.hdr(SUB)
            if r.u8() != 0:
                raise ValueError(f'bad weapon ref at {r.o - 1}')
            weapon, y = r.u64(), r.u32()
            direct = r.clips()
            variants = []
            for _ in range(r.u32()):
                v0 = r.o
                vid = r.hdr(VAR)
                variants.append({'id': vid, 'clips': r.clips(), 'span': (v0, r.o)})
            subs.append({'id': sid, 'weapon': weapon, 'y': y, 'clips': direct, 'variants': variants,
                         'span': (s0, r.o)})
        nxt = starts[k + 1] if k + 1 < len(starts) else None
        if nxt is not None and r.o > nxt:
            raise ValueError(f'entry {name} overruns the next entry')
        entries.append({'id': eid, 'name': name, 'index': index, 'default': default, 'nsub_at': nsub_at,
                        'subs': subs, 'span': (o, r.o)})
    if len(entries) != 16:
        raise ValueError(f'expected 16 entries, found {len(entries)}')
    return entries


def weapon_list(b):
    """The record's list of registered weapon definitions: (offset of count, [ids])."""
    needle = b'\x01\x00' + struct.pack('<Q', KUKRI)
    i = b.find(needle)
    while i != -1:
        for back in range(0, 40):
            c = i - 10 * back - 4
            if c < 0:
                break
            n = struct.unpack_from('<I', b, c)[0]
            if 0 < n < 64 and back < n and c + 4 + 10 * n <= len(b) and all(
                    b[c + 4 + 10 * j:c + 6 + 10 * j] == b'\x01\x00' for j in range(n)):
                return c, [struct.unpack_from('<Q', b, c + 6 + 10 * j)[0] for j in range(n)]
        i = b.find(needle, i + 1)
    return None, []


def _load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        return json.load(f)


NAMES = {int(k): v for k, v in _load('fsw_names.json').items()}
BLOOD = _load('kill_clip_blood.json')   # clip name -> 'P' pierce blood, 'B' punch blood, '-' none


def name(i):
    return NAMES.get(i, f'0x{i:x}')


def rating(clips):
    """One letter per clip: P = a victim bleeds 'dagger pierce' (a stab), B = punch blood, - = none, ? = unknown."""
    return ''.join(BLOOD.get(name(c), '?') for c in clips)


def is_blunt(clips):
    """No victim bleeds from a stab, no hidden-blade (HB) clip, every clip known, and the list starts with the
    attacker's clip (one stock cane counter list starts with a victim clip instead; it is skipped)."""
    nm = [name(c) for c in clips]
    return (bool(nm) and nm[0].endswith('_Atk') and 'P' not in rating(clips)
            and not any('HB_' in n for n in nm) and all(n in BLOOD for n in nm))


def pick_variants(entry, y):
    """Blunt variants for one entry and character: the cane's where they don't stab, else the knuckles'.
    Returns (donor, [clip lists])."""
    for donor in (CANE, KNUCKLE):
        for s in entry['subs']:
            if s['weapon'] == donor and s['y'] == y:
                lists = [v['clips'] for v in s['variants']] or ([s['clips']] if s['clips'] else [])
                keep = [c for c in lists if is_blunt(c)]
                if keep:
                    return donor, keep
    return None, []


def _clips_bytes(clips):
    return struct.pack('<I', len(clips)) + b''.join(b'\x01\x00' + struct.pack('<Q', c) for c in clips)


def build_override(weapon, y, variant_lists, alloc):
    out = b'\x00' + struct.pack('<Q', alloc()) + SUB + b'\x00' + struct.pack('<QI', weapon, y)
    out += _clips_bytes([]) + struct.pack('<I', len(variant_lists))
    for clips in variant_lists:
        out += b'\x00' + struct.pack('<Q', alloc()) + VAR + _clips_bytes(clips)
    return out


def strip_weapon(b, weapon):
    """Remove every override for `weapon` (e.g. an earlier build's). Returns (new bytes, number removed)."""
    out, last, removed = bytearray(), 0, 0
    for e in parse(b):
        drop = [s for s in e['subs'] if s['weapon'] == weapon]
        if not drop:
            continue
        nsub = struct.unpack_from('<I', b, e['nsub_at'])[0]
        out += b[last:e['nsub_at']] + struct.pack('<I', nsub - len(drop))
        last = e['nsub_at'] + 4
        for s in drop:
            out += b[last:s['span'][0]]
            last = s['span'][1]
        removed += len(drop)
    out += b[last:]
    return bytes(out), removed


def add_weapon(b, weapon, first_id, ys=None, replace=False):
    """Return (new bytes, report). Adds overrides for `weapon` to all 16 entries, for each clip set (y) that the
    entry already has overrides for, inserted after that entry's last override. With replace=True, existing
    overrides for `weapon` are removed first; without it they are an error."""
    removed = 0
    if replace:
        b, removed = strip_weapon(b, weapon)
    entries = parse(b)
    for e in entries:
        if any(s['weapon'] == weapon for s in e['subs']):
            raise ValueError(f'{e["name"]} already has overrides for weapon {weapon} (use --replace)')
    nxt = [first_id]

    def alloc():
        nxt[0] += 1
        return nxt[0] - 1

    out, last, report = bytearray(), 0, []
    for e in entries:
        chars = sorted({s['y'] for s in e['subs']}) if ys is None else ys
        blobs, rows = [], []
        for y in chars:
            donor, lists = pick_variants(e, y)
            if not lists:
                rows.append({'y': y, 'donor': None, 'variants': []})
                continue
            blobs.append(build_override(weapon, y, lists, alloc))
            rows.append({'y': y, 'donor': name(donor), 'variants': [
                {'atk': name(c[0]), 'rating': rating(c), 'clips': [name(x) for x in c]} for c in lists]})
        insert_at = e['subs'][-1]['span'][1] if e['subs'] else e['nsub_at'] + 4
        nsub = struct.unpack_from('<I', b, e['nsub_at'])[0]
        out += b[last:e['nsub_at']] + struct.pack('<I', nsub + len(blobs)) + b[e['nsub_at'] + 4:insert_at]
        out += b''.join(blobs)
        last = insert_at
        report.append({'entry': e['name'], 'added': len(blobs), 'characters': rows})
    out += b[last:]
    new = bytes(out)
    verify(b, new, weapon)
    return new, {'weapon': weapon, 'first_id': first_id, 'next_free_id': nxt[0], 'removed_first': removed,
                 'grew_by': len(new) - len(b), 'entries': report}


def copy_weapon(b, src, dst, first_id):
    """Return (new bytes, report): `dst` plays exactly what `src` plays. Every `dst` override is removed, then each
    `src` override is cloned for `dst` (same clip set, direct clips and variants, new object ids). Where `src` has no
    override, `dst` has none either, so both fall back to the same default."""
    b, removed = strip_weapon(b, dst)
    nxt = [first_id]

    def alloc():
        nxt[0] += 1
        return nxt[0] - 1

    out, last, report = bytearray(), 0, []
    for e in parse(b):
        blobs = []
        for s in e['subs']:
            if s['weapon'] != src:
                continue
            blob = b'\x00' + struct.pack('<Q', alloc()) + SUB + b'\x00' + struct.pack('<QI', dst, s['y'])
            blob += _clips_bytes(s['clips']) + struct.pack('<I', len(s['variants']))
            for v in s['variants']:
                blob += b'\x00' + struct.pack('<Q', alloc()) + VAR + _clips_bytes(v['clips'])
            blobs.append(blob)
        insert_at = e['subs'][-1]['span'][1] if e['subs'] else e['nsub_at'] + 4
        nsub = struct.unpack_from('<I', b, e['nsub_at'])[0]
        out += b[last:e['nsub_at']] + struct.pack('<I', nsub + len(blobs)) + b[e['nsub_at'] + 4:insert_at]
        out += b''.join(blobs)
        last = insert_at
        report.append({'entry': e['name'], 'copied': len(blobs)})
    out += b[last:]
    new = bytes(out)
    for ea, eb in zip(parse(b), parse(new)):
        keep = [(s['weapon'], s['y'], s['clips'], [v['clips'] for v in s['variants']]) for s in ea['subs']]
        got = [(s['weapon'], s['y'], s['clips'], [v['clips'] for v in s['variants']]) for s in eb['subs']]
        assert got[:len(keep)] == keep and ea['default'] == eb['default'], ea['name']
        assert [(y, c, v) for w, y, c, v in got[len(keep):]] == [(y, c, v) for w, y, c, v in keep if w == src]
        assert all(w == dst for w, *_ in got[len(keep):])
    assert weapon_list(b)[1] == weapon_list(new)[1]
    return new, {'src': src, 'dst': dst, 'first_id': first_id, 'next_free_id': nxt[0], 'removed_first': removed,
                 'grew_by': len(new) - len(b), 'entries': report}


def stabs(b, weapon):
    """(variants whose victims bleed from a stab, all variants) that `weapon` plays, default included where it has
    no override."""
    p = t = 0
    for e in parse(b):
        mine = [s for s in e['subs'] if s['weapon'] == weapon]
        lists = [v['clips'] for s in mine for v in s['variants']] + [s['clips'] for s in mine if s['clips']]
        if not mine:
            lists = [e['default']]
        t += len(lists)
        p += sum('P' in rating(c) for c in lists)
    return p, t


def verify(old, new, weapon):
    """Re-parse and check: same entries, old overrides unchanged, new overrides blunt and only for `weapon`."""
    a, b = parse(old), parse(new)
    assert [e['name'] for e in a] == [e['name'] for e in b]
    for ea, eb in zip(a, b):
        assert ea['default'] == eb['default'] and ea['index'] == eb['index']
        old_subs = [(s['weapon'], s['y'], s['clips'], [v['clips'] for v in s['variants']]) for s in ea['subs']]
        new_subs = [(s['weapon'], s['y'], s['clips'], [v['clips'] for v in s['variants']]) for s in eb['subs']]
        assert new_subs[:len(old_subs)] == old_subs, ea['name']
        for w, y, direct, variants in new_subs[len(old_subs):]:
            assert w == weapon and not direct and variants
            assert all(is_blunt(c) for c in variants), (ea['name'], y)
    wa, wb = weapon_list(old)[1], weapon_list(new)[1]
    assert wa == wb


def show(b):
    off, weapons = weapon_list(b)
    print(f'registered weapon definitions ({len(weapons)}) at {off}: ' + ', '.join(name(w) for w in weapons))
    for e in parse(b):
        print(f'\n{e["name"]}  default {rating(e["default"])}  {name(e["default"][0])}')
        for s in e['subs']:
            lists = [v['clips'] for v in s['variants']] or [s['clips']]
            who = f'set {s["y"]}'
            print(f'   {name(s["weapon"]):20s} {who}  ' + '  '.join(
                f'{rating(c)}{"(HB)" if any("HB_" in name(x) for x in c) else ""}' for c in lists))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('show')
    p.add_argument('record')
    p = sub.add_parser('add')
    p.add_argument('record')
    p.add_argument('--weapon', type=int, required=True, help='file id of the weapon definition (e.g. ACVI_Gada)')
    p.add_argument('--first-id', type=int, required=True, help='first free object id for the new objects')
    p.add_argument('--out', required=True)
    p.add_argument('--report')
    p.add_argument('--replace', action='store_true', help='remove existing overrides for this weapon first')
    p = sub.add_parser('copy', help='make one weapon play exactly what another plays (e.g. katar = kukri)')
    p.add_argument('record')
    p.add_argument('--src', type=int, required=True)
    p.add_argument('--dst', type=int, required=True)
    p.add_argument('--first-id', type=int, required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--report')
    a = ap.parse_args()
    with open(a.record, 'rb') as f:
        b = f.read()
    if a.cmd == 'show':
        show(b)
        return
    if a.cmd == 'copy':
        new, rep = copy_weapon(b, a.src, a.dst, a.first_id)
        with open(a.out, 'wb') as f:
            f.write(new)
        if a.report:
            with open(a.report, 'w') as f:
                json.dump(rep, f, indent=1)
        bp, bt = stabs(b, a.dst)
        np_, nt = stabs(new, a.dst)
        print(f'wrote {a.out}: {len(b)} -> {len(new)} bytes ({len(new) - len(b):+d}); {name(a.dst)} now plays '
              f'{name(a.src)}\'s sets: stabbing variants {bp}/{bt} -> {np_}/{nt}')
        return
    new, rep = add_weapon(b, a.weapon, a.first_id, replace=a.replace)
    with open(a.out, 'wb') as f:
        f.write(new)
    if a.report:
        with open(a.report, 'w') as f:
            json.dump(rep, f, indent=1)
    print(f'wrote {a.out}: {len(b)} -> {len(new)} bytes ({len(new) - len(b):+d}), removed {rep["removed_first"]} '
          f'old overrides, added {sum(r["added"] for r in rep["entries"])}, ids {a.first_id}..{rep["next_free_id"] - 1}')
    for r in rep['entries']:
        for c in r['characters']:
            who = f'set {c["y"]}'
            print(f'   {r["entry"]:28s} {who} from {c["donor"]}: ' + ', '.join(
                f'{v["atk"].replace("ACVI_Fight_", "")} [{v["rating"]}]' for v in c['variants']))


if __name__ == '__main__':
    sys.exit(main())

"""Compare bone-name hashes of two Anvil skeleton files (e.g. Unity ACU_BaseSkeleton_Male vs Syndicate ACVI_CHR_SHR_Male).

Input: raw Skeleton files (type 24AECB7C) written by `anvil_forge.py extract` (or ATK unpack).
Bones are serialized objects of type 9EF0E7A1. The bone-name hash follows the type marker at a small fixed
offset. The offset is not documented, so this tool FINDS it: it tries offsets 0..32 and keeps the one with the most
hits in the known list (--known), or else the most bones shared between the two skeletons. Validate once
against a known bone list:

    python3 anvil_bones.py syn.bin --known ../../Evie/elise_skel_bones.json      # expect ~100% of known found
    python3 anvil_bones.py acu.bin syn.bin                                         # Unity vs Syndicate overlap

If validation finds < 95% of the known bones, don't trust the comparison. Use ATK's XML export of both
skeletons instead (handoff S-2).
"""
import argparse
import json
import struct
import sys

BONE = struct.pack('<I', 0x9EF0E7A1)


BONE_MARKERS = [0x95741049, 0x9EF0E7A1]  # Unity bones (seen in the user's ACU_BaseSkeleton_*: hash right after it)


def candidates(path):
    """{offset: [u32 after each bone marker at that offset]} for offsets 0..32."""
    b = open(path, 'rb').read()
    pos = []
    for m in BONE_MARKERS:
        mb = struct.pack('<I', m)
        pos = [i for i in range(len(b) - 4) if b[i:i + 4] == mb]
        if pos:
            break
    if not pos:
        raise ValueError(f'{path}: no bone markers (is this a Skeleton file?)')
    return {off: [struct.unpack_from('<I', b, p + 4 + off)[0] for p in pos if p + 8 + off <= len(b)]
            for off in range(0, 33)}


def load_known(path):
    d = json.load(open(path))
    items = d if isinstance(d, list) else list(d.values()) if isinstance(d, dict) else []
    out = set()
    for x in (list(d.keys()) if isinstance(d, dict) else []) + items:
        try:
            out.add(int(x, 0) if isinstance(x, str) else int(x))
        except (TypeError, ValueError):
            if isinstance(x, dict):
                for k in ('hash', 'id', 'bone_id', 'BoneID'):
                    if k in x:
                        out.add(int(x[k], 0) if isinstance(x[k], str) else int(x[k]))
    return out


def analyze(a_path, b_path=None, known_path=None, offset=None):
    """Returns a dict with the chosen offset, bone counts, validation and overlap figures."""
    ca = candidates(a_path)
    cb = candidates(b_path) if b_path else None
    known = load_known(known_path) if known_path else None
    if offset is not None:
        off = offset
    elif known:
        off = max(ca, key=lambda o: len(known & set(ca[o])))
    elif cb:
        # most shared bones; on a tie prefer the offset with the most distinct values (a misaligned read
        # of the same hashes collapses many of them into the same number)
        # then prefer values that vary in their lowest AND highest byte: name hashes are random 32-bit values,
        # while a read shifted into neighbouring padding keeps one end constant
        off = max(ca, key=lambda o: (len(set(ca[o]) & set(cb[o])),
                                     min(len({v & 0xFF for v in ca[o]}), len({v >> 24 for v in ca[o]})),
                                     len(set(ca[o]) | set(cb[o]))))
    else:
        raise ValueError('give a known bone list or a second skeleton so the hash offset can be determined')
    a = ca[off]
    res = {'offset': off, 'a_bones': len(a), 'a_hashes': [f'{h:08X}' for h in a]}
    if known:
        hit = len(known & set(a))
        res.update(known=len(known), known_found=hit, known_pct=round(100 * hit / max(len(known), 1), 1),
                   trusted=hit >= 0.95 * len(known))
    if cb:
        b = cb[off]
        sa, sb = set(a), set(b)
        res.update(b_bones=len(b), shared=len(sa & sb), only_a=[f'{h:08X}' for h in sorted(sa - sb)],
                   only_b=[f'{h:08X}' for h in sorted(sb - sa)],
                   a_in_b_pct=round(100 * len(sa & sb) / max(len(sa), 1), 1))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b', nargs='?')
    ap.add_argument('--known', help='JSON list/dict of bone hashes known to be in skeleton a')
    ap.add_argument('--offset', type=int)
    args = ap.parse_args()
    try:
        r = analyze(args.a, args.b, args.known, args.offset)
    except ValueError as e:
        sys.exit(str(e))
    print(f"{args.a}: {r['a_bones']} bones (hash offset {r['offset']})")
    if 'known' in r:
        print(f"validation: {r['known_found']}/{r['known']} known bones found ({r['known_pct']}%)")
    if 'shared' in r:
        print(f"{args.b}: {r['b_bones']} bones")
        print(f"shared {r['shared']}; only in A {len(r['only_a'])}; only in B {len(r['only_b'])}")
        print(f"A bones present in B: {r['a_in_b_pct']}%")
        for h in r['only_a']:
            print(f'  only A: {h}')


if __name__ == '__main__':
    main()

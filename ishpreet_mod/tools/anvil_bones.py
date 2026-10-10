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


def candidates(path):
    """{offset: [u32 after each bone marker at that offset]} for offsets 0..32."""
    b = open(path, 'rb').read()
    pos = [i for i in range(len(b) - 4) if b[i:i + 4] == BONE]
    if not pos:
        sys.exit(f'{path}: no bone markers (is this a Skeleton file?)')
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b', nargs='?')
    ap.add_argument('--known', help='JSON list/dict of bone hashes known to be in skeleton a')
    ap.add_argument('--offset', type=int)
    args = ap.parse_args()
    ca = candidates(args.a)
    cb = candidates(args.b) if args.b else None
    known = load_known(args.known) if args.known else None
    if args.offset is not None:
        off = args.offset
    elif known:
        off = max(ca, key=lambda o: len(known & set(ca[o])))
    elif cb:
        off = max(ca, key=lambda o: len(set(ca[o]) & set(cb[o])))
    else:
        sys.exit('give --known or a second skeleton so the hash offset can be determined')
    a = ca[off]
    print(f'{args.a}: {len(a)} bones (hash offset {off})')
    if known:
        hit = len(known & set(a))
        print(f'validation: {hit}/{len(known)} known bones found ({100 * hit / max(len(known), 1):.1f}%)')
    if cb:
        b = cb[off]
        sa, sb = set(a), set(b)
        print(f'{args.b}: {len(b)} bones')
        print(f'shared {len(sa & sb)}; only in A {len(sa - sb)}; only in B {len(sb - sa)}')
        print(f'A bones present in B: {100 * len(sa & sb) / max(len(sa), 1):.1f}%')
        for h in sorted(sa - sb):
            print(f'  only A: {h:08X}')


if __name__ == '__main__':
    main()

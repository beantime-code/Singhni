"""Skeleton record (type 24AECB7C): bones with name hash and parent. Verified on ACVI_CHR_SHR_Female/Male and the
Elise/Aveline outfit skeletons.

    bone object = [u8 0][u64 bone object id][u32 95741049][u32 name hash = CRC32(name)][u8 flag][u64 parent object id] ...
The root's parent field points at no bone in the record. Addon (outfit) skeletons name parents that live in the base
skeleton by object id, so `merge()` resolves parents across records by object id first, then by name hash.
"""
import struct
import zlib

TAG = struct.pack('<I', 0x95741049)

NAMES = ['Reference', 'Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head', 'LeftClavicle', 'LeftArm', 'LeftForeArm',
         'LeftHand', 'RightClavicle', 'RightArm', 'RightForeArm', 'RightHand', 'LeftUpLeg', 'LeftLeg', 'LeftFoot',
         'LeftToeBase', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase', 'LeftHand_Weapon_Ref',
         'RightHand_Weapon_Ref'] + [s + f + str(i) for s in ('LeftHand', 'RightHand')
                                    for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky') for i in (1, 2, 3)]
NAME_OF = {zlib.crc32(n.encode()): n for n in NAMES}


def bone_name(h):
    return NAME_OF.get(h, f'0x{h:08x}')


def parse(raw):
    """[{oid, hash, parent_oid}] in record order"""
    out, i = [], raw.find(TAG)
    while i != -1:
        if i >= 9 and raw[i - 9] == 0:
            oid = struct.unpack_from('<Q', raw, i - 8)[0]
            h = struct.unpack_from('<I', raw, i + 4)[0]
            par = struct.unpack_from('<Q', raw, i + 9)[0] if raw[i + 8] == 2 else None
            out.append({'oid': oid, 'hash': h, 'parent_oid': par})
        i = raw.find(TAG, i + 4)
    return out


def merge(*records):
    """{bone hash: parent bone hash or None} over several skeleton records (base first, addons after)"""
    by_oid, bones = {}, []
    for raw in records:
        for b in parse(raw):
            by_oid[b['oid']] = b['hash']
            bones.append(b)
    parent = {}
    for b in bones:
        p = by_oid.get(b['parent_oid']) if b['parent_oid'] is not None else None
        if p == b['hash']:
            p = None
        parent.setdefault(b['hash'], p)
        if parent[b['hash']] is None and p is not None:
            parent[b['hash']] = p
    return parent


def chain(parent, h):
    out = []
    while h is not None and h not in out:
        out.append(h)
        h = parent.get(h)
    return out


def model_positions(raw):
    """{bone hash: (3,) rest position in the skeleton's model frame}: the first vector after the parent references.
    Mapping to mesh/world space (z up, -y front): world = (m.y, -m.x, m.z) + offset (see world_rest)."""
    out, i = {}, raw.find(TAG)
    while i != -1:
        if i >= 9 and raw[i - 9] == 0 and raw[i + 8] == 2 and raw[i + 17] == 2:
            h = struct.unpack_from('<I', raw, i + 4)[0]
            out[h] = struct.unpack_from('<3f', raw, i + 26)
        i = raw.find(TAG, i + 4)
    return out


def world_rest(records, anchors=None):
    """{bone hash: world rest position} from skeleton records. `anchors` {hash: world position} (e.g. palette pivots)
    calibrate the vertical offset; without anchors the Hips are put at 0.964 m (Evie's base skeleton)."""
    import numpy as np
    mp = {}
    for raw in records:
        for h, v in model_positions(raw).items():
            mp.setdefault(h, np.array([v[1], -v[0], v[2]]))
    off = np.array([0, 0, 0.964])
    if anchors:
        common = [h for h in anchors if h in mp]
        if common:
            off = np.mean([np.asarray(anchors[h]) - mp[h] for h in common], axis=0)
    return {h: v + off for h, v in mp.items()}

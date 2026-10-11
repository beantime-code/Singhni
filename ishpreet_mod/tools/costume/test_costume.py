"""Tests for the costume QA gates on synthetic garments (no game data needed): each gate must FAIL on the defect it
exists for and PASS on the fixed version.   python3 test_costume.py   (or pytest)

Synthetic rig: a skeleton record built here in the game's layout (Reference > Hips > legs, Reference > Spine > Spine1 >
Spine2 > Neck/arms). Garments: a 'kurta' tube on the torso and a 'skirt' tube below it, overlapping 2 cm at the waist,
like Ishpreet's kurta hem tucked over the skirt top.
"""
import os
import struct
import sys
import zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from costume import geom, qa, rom, skel  # noqa: E402

BONES = {  # name: (parent, world rest position)
    'Reference': (None, (0, 0, 0)), 'Hips': ('Reference', (0, 0, 0.964)), 'Spine': ('Reference', (0, 0, 1.036)),
    'Spine1': ('Spine', (0, 0.008, 1.207)), 'Spine2': ('Spine1', (0, 0.01, 1.33)), 'Neck': ('Spine2', (0, 0.02, 1.48)),
    'LeftUpLeg': ('Hips', (0.087, 0, 0.964)), 'LeftLeg': ('LeftUpLeg', (0.10, 0, 0.53)),
    'LeftFoot': ('LeftLeg', (0.11, 0.02, 0.09)), 'RightUpLeg': ('Hips', (-0.087, 0, 0.964)),
    'RightLeg': ('RightUpLeg', (-0.10, 0, 0.53)), 'RightFoot': ('RightLeg', (-0.11, 0.02, 0.09)),
    'LeftClavicle': ('Spine2', (0.03, 0.0, 1.40)), 'LeftArm': ('LeftClavicle', (0.17, 0.05, 1.40)),
    'LeftForeArm': ('LeftArm', (0.40, 0.05, 1.20)), 'LeftHand': ('LeftForeArm', (0.58, 0.05, 1.02)),
    'RightClavicle': ('Spine2', (-0.03, 0.0, 1.40)), 'RightArm': ('RightClavicle', (-0.17, 0.05, 1.40)),
    'RightForeArm': ('RightArm', (-0.40, 0.05, 1.20)), 'RightHand': ('RightForeArm', (-0.58, 0.05, 1.02)),
}
H = {n: zlib.crc32(n.encode()) for n in BONES}


def skeleton_record():
    oid = {n: 1000 + i for i, n in enumerate(BONES)}
    out = bytearray(b'\x01' + struct.pack('<Q', 999) + bytes.fromhex('7ccbae24'))
    for n, (par, w) in BONES.items():
        m = (-w[1], w[0], w[2] - 0.964)
        out += b'\x00' + struct.pack('<Q', oid[n]) + skel.TAG + struct.pack('<I', H[n])
        out += b'\x02' + struct.pack('<Q', oid[par] if par else 77) + b'\x02' + struct.pack('<Q', oid[n])
        out += struct.pack('<3f', *m) + b'\x00' * 40
    return bytes(out)


class FakeMesh:
    def __init__(self, P, T, bones, W, UV=None, material=1):
        self.P, self.T = np.asarray(P, float), np.asarray(T, int)
        self.palette = [H.get(b, b if isinstance(b, int) else 0) for b in bones]
        self.W = np.asarray(W, float)
        self.UV = np.zeros((len(self.P), 2)) if UV is None else np.asarray(UV, float)
        self.maps = [{'material': material}]
        self.subs = [[0, 0, len(self.P), 0, len(self.T), 1]]

    def positions(self):
        return self.P.copy()

    def uvs(self):
        return self.UV.copy()

    def all_tris(self, drop_collapsed=True):
        return self.T.copy(), np.zeros(len(self.T), int)

    def influences(self):
        k = self.W.shape[1]
        return np.tile(np.arange(k), (len(self.P), 1)), self.W.copy()

    def bone_hash_weights(self):
        return {h: self.W[:, i].copy() for i, h in enumerate(self.palette)}

    def bind_matrices(self):
        out = {}
        for h in self.palette:
            name = next((n for n, x in H.items() if x == h), None)
            M = np.eye(4)
            if name:
                M[:3, 3] = BONES[name][1]
            out[h] = M
        return out


def tube(r, z0, z1, na=48, nz=12, yc=0.0):
    a = np.linspace(0, 2 * np.pi, na, endpoint=False)
    z = np.linspace(z0, z1, nz)
    P = np.array([(r * np.cos(t), yc + r * np.sin(t), zz) for zz in z for t in a])
    T = []
    for i in range(nz - 1):
        for j in range(na):
            p, q = i * na + j, i * na + (j + 1) % na
            T += [(p, q, p + na), (q, q + na, p + na)]
    UV = np.array([(j / na, i / nz) for i in range(nz) for j in range(na)])
    return P, np.array(T), UV


def kurta(hem_weights='spine'):
    P, T, UV = tube(0.16, 1.00, 1.30)
    t = np.clip((P[:, 2] - 1.0) / 0.3, 0, 1)
    if hem_weights == 'spine':          # the bug class: the hem rides on the spine, the skirt on the hips
        W = np.c_[np.zeros(len(P)), 1 - t * 0.5, t * 0.5]
    else:                               # fixed: the hem carries the skirt's (hips) weights, blending up the torso
        h = np.clip((P[:, 2] - 1.0) / 0.12, 0, 1)
        W = np.c_[1 - h, h * (1 - t * 0.5), h * t * 0.5]
    return FakeMesh(P, T, ['Hips', 'Spine', 'Spine1'], W, UV * 0.4 + [0.0, 0.5], material=1)


def skirt(uv_shift=(0.6, 0.0)):
    P, T, UV = tube(0.172, 0.60, 1.02)
    W = np.c_[np.ones(len(P))]
    return FakeMesh(P, T, ['Hips'], W, UV * 0.4 + list(uv_shift), material=1)


def layers(*meshes):
    return [qa.Layer(f'm{i}', m) for i, m in enumerate(meshes)]


def rig_for(L):
    return qa.make_rig(L, [skeleton_record()])


def test_skeleton_and_rig():
    sk = skeleton_record()
    par = skel.merge(sk)
    assert skel.chain(par, H['LeftHand'])[-1] == H['Reference']
    pos = skel.world_rest([sk])
    assert np.allclose(pos[H['LeftForeArm']], BONES['LeftForeArm'][1], atol=1e-5)
    _, rig = rig_for(layers(kurta()))
    W = rig.solve(rom.POSES['hang_both'], 1.0)
    arm = BONES['LeftArm'][1]
    fore = W[H['LeftArm']][:3, :3] @ (np.subtract(BONES['LeftForeArm'][1], arm))
    assert fore[2] > 0.15, 'hang_both should point the upper arm up'


def test_g3_junction_opens_then_fixed():
    for hem, should_fail in (('spine', True), ('hips', False)):
        L = layers(kurta(hem), skirt())
        parent, rig = rig_for(L)
        J = qa.find_junctions(L)
        assert J, 'kurta hem should register as a junction with the skirt'
        g3, g4 = qa.g3_g4(L, rig, ['bend_forward', 'twist_L'], (1.0,), J)
        assert g3['pass'] != should_fail, (hem, g3['issues'][:2])


def test_g2_seam_tear():
    P, T, UV = tube(0.16, 1.0, 1.3)
    na = 48
    half = P[:, 0] >= 0
    W = np.c_[np.where(half, 1.0, 0.0), np.where(half, 0.0, 1.0)]
    # split the tube into two pieces along x=0 by duplicating the seam vertices
    m1 = FakeMesh(P, T[np.all(half[T], 1)], ['Spine', 'Spine1'], W)
    m2 = FakeMesh(P, T[np.all(~half[T] | (np.abs(P[T, 0]) < 1e-9), 1)], ['Spine', 'Spine1'], W[:, ::-1])
    res = qa.g2_seams(layers(m1, m2))
    assert not res['pass']
    res_ok = qa.g2_seams(layers(m1, FakeMesh(P, m2.T, ['Spine', 'Spine1'], W)))
    assert res_ok['pass'], res_ok['issues'][:3]


def test_g1_hole():
    m = kurta('hips')
    c = m.P[m.T].mean(1)
    hole = (np.abs(c[:, 2] - 1.15) < 0.03) & (np.abs(np.arctan2(c[:, 1], c[:, 0])) < 0.2)
    holed = FakeMesh(m.P, m.T[~hole], ['Hips', 'Spine', 'Spine1'], m.W)
    _, rig = rig_for(layers(m))
    assert not qa.g1_holes(layers(holed), rig)['pass']
    assert qa.g1_holes(layers(m), rig)['pass']           # neck and hem openings: the neck and legs pass through
    patch = FakeMesh(m.P, m.T[hole], ['Hips', 'Spine', 'Spine1'], m.W)
    assert qa.g1_holes(layers(holed, patch), rig)['pass']   # the same hole covered by a patch is fine


def named(L, *names):
    for lay, n in zip(L, names):
        for c in np.unique(lay.vl[lay.vl >= 0]):
            lay.names[int(c)] = n
    return L


def test_g6_uv_overlap():
    assert qa.g6_atlas(named(layers(kurta('hips'), skirt((0.6, 0.0))), 'kurta', 'skirt'))['pass']
    bad = qa.g6_atlas(named(layers(kurta('hips'), skirt((0.2, 0.3))), 'kurta', 'skirt'))   # skirt reads kurta paint
    assert not bad['pass'] and 'kurta' in bad['issues'][0]
    unnamed = qa.g6_atlas(layers(kurta('hips'), skirt((0.2, 0.3))))
    assert unnamed['pass'] and any(i.startswith('WARN') for i in unnamed['info'])


def test_g7_missing_bone():
    m = kurta('hips')
    bad = FakeMesh(m.P, m.T, ['Hips', 'Spine', 0x12345678], m.W)
    L = layers(bad)
    parent, rig = rig_for(L)
    assert not qa.g7_weights(L, rig, parent)['pass']
    L = layers(m)
    parent, rig = rig_for(L)
    assert qa.g7_weights(L, rig, parent)['pass']


def sash(weights='hips'):
    P, T, UV = tube(0.168, 1.05, 1.16, nz=5)
    if weights == 'hips':               # the bug class: the sash rides on the hips while the kurta under it bends
        W = np.c_[np.ones(len(P)), np.zeros(len(P)), np.zeros(len(P))]
    else:                               # fixed: the sash copies the weights of the kurta right under it
        k = kurta('hips')
        j, _ = geom.nearest(P, k.P)
        W = k.W[j]
    return FakeMesh(P, T, ['Hips', 'Spine', 'Spine1'], W, UV * 0.1 + [0.8, 0.8], material=1)


def test_g4_clipping_then_fixed():
    for w, should_fail in (('hips', True), ('kurta', False)):
        L = layers(kurta('hips'), sash(w))
        parent, rig = rig_for(L)
        g3, g4 = qa.g3_g4(L, rig, ['bend_forward', 'bend_back', 'twist_L'], (1.0,), [])
        assert g4['checked'], 'the sash should register as lying over the kurta'
        assert g4['pass'] != should_fail, (w, g4['issues'][:2])


def test_views_run():
    L = layers(kurta('hips'), skirt())
    parent, rig = rig_for(L)
    rows = qa.g5_views(L, rig, ['crouch'], None)
    assert {r['view'] for r in rows} == set(qa.VIEWS)
    assert qa.g5_compare(rows, rows)['pass']




# ---------------------------------------------------------------- one weight field (weights.py)
def body():
    """torso + two legs, weighted like a real body: Hips -> Spine -> Spine1 -> Spine2 up the torso, UpLeg -> Leg down
    each leg, legs blend into the hips at the top"""
    pieces = []
    P, T, _ = tube(0.15, 0.95, 1.45, nz=26)
    z = P[:, 2]
    w = np.zeros((len(P), 7))
    w[:, 0] = np.clip((1.02 - z) / 0.08, 0, 1)
    w[:, 2] = np.clip((z - 1.25) / 0.1, 0, 1)
    w[:, 3] = np.clip((z - 1.36) / 0.08, 0, 1)
    w[:, 2] *= 1 - w[:, 3]
    w[:, 1] = np.clip(1 - w[:, 0] - w[:, 2] - w[:, 3], 0, 1)
    pieces.append((P, T, w))
    for side, col in ((1, 4), (-1, 5)):
        P, T, _ = tube(0.07, 0.15, 0.97, nz=20)
        P[:, 0] += side * 0.09
        z = P[:, 2]
        w = np.zeros((len(P), 7))
        top = np.clip((z - 0.90) / 0.07, 0, 1)
        w[:, 0] = top
        w[:, col] = 1 - top
        pieces.append((P, T, w))
    off = np.cumsum([0] + [len(p[0]) for p in pieces])
    BP = np.vstack([p[0] for p in pieces])
    BT = np.vstack([p[1] + off[i] for i, p in enumerate(pieces)])
    BW = np.vstack([p[2] for p in pieces])
    return BP, BT, BW, ['Hips', 'Spine', 'Spine1', 'Spine2', 'LeftUpLeg', 'RightUpLeg', 'Neck']


def test_outfit_weights_hold_the_waist():
    from costume import weights
    BP, BT, BW, bones = body()
    k = tube(0.16, 1.00, 1.30)
    s = tube(0.168, 1.05, 1.16, nz=5)
    sk = tube(0.172, 0.62, 1.02)
    sk[0][:, :2] *= (1 + (1.02 - sk[0][:, 2:3]) * 0.9)          # flared skirt: the hem is far from the legs
    # A: per-piece rules, as built k23-k28: kurta from the body, sash on the hips, skirt 50/50 on the thighs
    j, _ = geom.nearest(k[0], BP)
    WA_k = BW[j]
    WA_s = np.zeros((len(s[0]), 7))
    WA_s[:, 0] = 1
    WA_sk = np.zeros((len(sk[0]), 7))
    a = np.clip((1.02 - sk[0][:, 2]) / 0.35, 0, 1)
    WA_sk[:, 0] = 1 - a
    WA_sk[:, 4] = a / 2
    WA_sk[:, 5] = a / 2
    # B: one field over the outfit
    (WB_k, WB_s, WB_sk), info = weights.outfit_weights([k[:2], s[:2], sk[:2]], BP, BT, BW)
    assert 0.2 < info['confident'] < 1.0
    poses = ['bend_forward', 'twist_L', 'crouch', 'sprint_L']
    bad = {}
    for name, (wk, ws, wsk) in (('A', (WA_k, WA_s, WA_sk)), ('B', (WB_k, WB_s, WB_sk))):
        L = layers(FakeMesh(k[0], k[1], bones, wk), FakeMesh(s[0], s[1], bones, ws), FakeMesh(sk[0], sk[1], bones, wsk))
        parent, rig = rig_for(L)
        g3, g4 = qa.g3_g4(L, rig, poses, (1.0,), qa.find_junctions(L))
        bad[name] = (g3['count'], g4['count'], g3['issues'][:1] + g4['issues'][:1])
    assert bad['A'][0] + bad['A'][1] > 0, bad['A']
    assert bad['B'][0] + bad['B'][1] == 0, bad['B']


def test_g8_material_changed():
    stock = layers(skirt())
    built = layers(FakeMesh(*tube(0.172, 0.62, 1.02)[:2], ['Hips'], np.ones((48 * 12, 1)), material=2))
    stock[0].label = built[0].label = 'coat'
    assert not qa.g8_materials(built, stock)['pass']
    assert qa.g8_materials(stock, stock)['pass']


def test_reweight_solve_one_mesh_layers():
    """kurta + sash in ONE mesh (like the body record), skirt in the coat, stock 'boot' piece fixed"""
    from costume import reweight
    BP, BT, BW, bones = body()
    k, s_, sk = tube(0.16, 1.00, 1.30), tube(0.168, 1.05, 1.16, nz=5), tube(0.172, 0.62, 1.02)
    sk[0][:, :2] *= (1 + (1.02 - sk[0][:, 2:3]) * 0.9)
    boot, bT, _ = tube(0.075, 0.1, 0.3, nz=4)
    boot[:, 0] += 0.09
    P = np.vstack([k[0], s_[0], boot])
    T = np.vstack([k[1], s_[1] + len(k[0]), bT + len(k[0]) + len(s_[0])])
    Wsash = np.zeros((len(s_[0]), 7))
    Wsash[:, 0] = 1                                         # the bug: sash on the hips
    j, _ = geom.nearest(k[0], BP)
    Wboot = np.zeros((len(boot), 7))
    Wboot[:, 4] = 1
    Wb = np.vstack([BW[j], Wsash, Wboot])
    bodym = FakeMesh(P, T, bones, Wb)
    orig_like = FakeMesh(boot, bT, bones, Wboot)            # the stock piece the build kept
    Wsk = np.zeros((len(sk[0]), 7))
    a = np.clip((1.02 - sk[0][:, 2]) / 0.35, 0, 1)
    Wsk[:, 0], Wsk[:, 4], Wsk[:, 5] = 1 - a, a / 2, a / 2
    coat = FakeMesh(sk[0], sk[1], bones, Wsk)
    src = FakeMesh(BP, BT, bones, BW)
    parent = skel.merge(skeleton_record())
    keep = reweight.stock_mask
    reweight.stock_mask = lambda b, o: np.r_[np.zeros(len(k[0]) + len(s_[0]), bool), np.ones(len(boot), bool)]
    try:
        res, hashes, info = reweight.solve(bodym, coat, src, parent, orig_like, coat_band=0.06)
    finally:
        reweight.stock_mask = keep
    idx, W = res['body']
    assert not np.isin(np.arange(len(k[0]) + len(s_[0]), len(P)), idx).any(), 'stock piece must stay untouched'
    Wn = bodym.W.copy()
    col = [hashes.index(H[b]) for b in bones]
    Wn[idx] = W[:, col]
    cidx, cW = res['coat']
    Wc = coat.W.copy()
    Wc[cidx] = cW[:, col]
    L = layers(FakeMesh(P, T, bones, Wn), FakeMesh(sk[0], sk[1], bones, Wc))
    _, rig = rig_for(L)
    g3, g4 = qa.g3_g4(L, rig, ['bend_forward', 'twist_L', 'crouch'], (1.0,), qa.find_junctions(L))
    assert g3['pass'] and g4['pass'], (g3['issues'][:2], g4['issues'][:2])


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)

"""Range-of-motion poses and linear blend skinning for built costume meshes: no game clips and no VM needed.

Every pose is a list of limb aims in world space ("point the upper arm straight up", "thigh forward and up, shin
down") plus optional twists. A bone's direction is pivot(child) - pivot(bone). Pivots are the bind positions from the
meshes' own palettes (inverse bind matrices), and parents come from the skeleton records (skel.merge). Aims are applied
parent first, each as the shortest rotation from the bone's current direction to the target, so no knowledge of
Ubisoft's local bone axes is needed.

World axes as stored in the meshes: +x = character's left, -y = front, +z = up (metres).
The poses cover what breaks garments in play: climbing reaches (arms overhead, one knee high), hanging, deep crouch,
sprint stride, straddle, wall-run arms back, spine bend and twist. Each pose is sampled at several fractions of the
way from the bind pose, so a seam that opens half-way is caught too.
"""
import zlib

import numpy as np

from . import skel

H = {n: zlib.crc32(n.encode()) for n in skel.NAMES}
CHILD = {'LeftClavicle': 'LeftArm', 'LeftArm': 'LeftForeArm', 'LeftForeArm': 'LeftHand',
         'RightClavicle': 'RightArm', 'RightArm': 'RightForeArm', 'RightForeArm': 'RightHand',
         'LeftUpLeg': 'LeftLeg', 'LeftLeg': 'LeftFoot', 'RightUpLeg': 'RightLeg', 'RightLeg': 'RightFoot',
         'Spine': 'Spine2', 'Spine2': 'Neck', 'Neck': 'Head'}

UP, DOWN, FWD, BACK, LEFT, RIGHT = (np.array(v, float) for v in
                                    ((0, 0, 1), (0, 0, -1), (0, -1, 0), (0, 1, 0), (1, 0, 0), (-1, 0, 0)))


def _n(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _mirror(d):
    d = np.array(d, float)
    d[0] = -d[0]
    return d


def _side(pose):
    """mirror a pose left <-> right"""
    out = []
    for bone, kind, val in pose:
        b = bone.replace('Left', '\0').replace('Right', 'Left').replace('\0', 'Right')
        out.append((b, kind, _mirror(val) if kind == 'aim' else -val))
    return out


def _arm(side, upper, fore):
    return [(side + 'Arm', 'aim', _n(upper)), (side + 'ForeArm', 'aim', _n(fore))]


def _leg(side, thigh, shin):
    return [(side + 'UpLeg', 'aim', _n(thigh)), (side + 'Leg', 'aim', _n(shin))]


_CLIMB_L = (_arm('Left', UP * 1 + FWD * 0.25 + LEFT * 0.15, UP + FWD * 0.2) +
            _arm('Right', DOWN + FWD * 0.3 + RIGHT * 0.2, DOWN + FWD * 0.5) +
            _leg('Left', FWD + UP * 0.35 + LEFT * 0.25, DOWN + BACK * 0.15) +
            _leg('Right', DOWN + BACK * 0.15 + RIGHT * 0.1, DOWN + BACK * 0.4))
POSES = {
    'climb_reach_L': _CLIMB_L,
    'climb_reach_R': _side(_CLIMB_L),
    'hang_both': (_arm('Left', UP + LEFT * 0.25, UP) + _arm('Right', UP + RIGHT * 0.25, UP) +
                  _leg('Left', DOWN + FWD * 0.3, DOWN + BACK * 0.3) + _leg('Right', DOWN + FWD * 0.2, DOWN + BACK * 0.4)),
    'wall_step_L': (_arm('Left', UP + FWD * 0.6, UP + FWD * 0.6) + _arm('Right', UP + FWD * 0.6, UP + FWD * 0.6) +
                    _leg('Left', FWD + UP * 0.8, DOWN + FWD * 0.2) + _leg('Right', DOWN, DOWN + BACK * 0.2)),
    'crouch': ([('Spine', 'aim', _n(UP + FWD * 0.6))] + _arm('Left', DOWN + FWD, DOWN + FWD * 1.5) +
               _arm('Right', DOWN + FWD, DOWN + FWD * 1.5) +
               _leg('Left', FWD + UP * 0.1 + LEFT * 0.3, DOWN + BACK * 0.9) +
               _leg('Right', FWD + UP * 0.1 + RIGHT * 0.3, DOWN + BACK * 0.9)),
    'sprint_L': (_arm('Left', DOWN + BACK * 0.8, DOWN + FWD * 0.8) + _arm('Right', DOWN + FWD * 0.9, FWD + UP * 0.6) +
                 _leg('Left', FWD + DOWN * 0.6, DOWN + BACK * 0.5) + _leg('Right', DOWN + BACK * 0.6, BACK + DOWN * 0.3)),
    'straddle': _leg('Left', DOWN + LEFT * 0.9, DOWN + LEFT * 0.9) + _leg('Right', DOWN + RIGHT * 0.9, DOWN + RIGHT * 0.9),
    'arms_back': _arm('Left', DOWN + BACK * 1.2 + LEFT * 0.3, DOWN + BACK) + _arm('Right', DOWN + BACK * 1.2 + RIGHT * 0.3, DOWN + BACK),
    'bend_forward': [('Spine', 'aim', _n(UP + FWD * 1.0)), ('Spine2', 'aim', _n(UP + FWD * 1.3))],
    'bend_back': [('Spine', 'aim', _n(UP + BACK * 0.35)), ('Spine2', 'aim', _n(UP + BACK * 0.5))],
    'twist_L': [('Spine1', 'twist', 0.45), ('Spine2', 'twist', 0.35)],
    'twist_R': [('Spine1', 'twist', -0.45), ('Spine2', 'twist', -0.35)],
}
POSES['sprint_R'] = _side(POSES['sprint_L'])
POSES['wall_step_R'] = _side(POSES['wall_step_L'])


def _rot_between(a, b):
    a, b = _n(a), _n(b)
    v, c = np.cross(a, b), float(a @ b)
    if c > 1 - 1e-9:
        return np.eye(3)
    if c < -1 + 1e-9:
        p = np.cross(a, [1, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1, 0])
        p = _n(p)
        return 2 * np.outer(p, p) - np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K / (1 + c)


def _axis_angle(axis, ang):
    axis = _n(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def _log(R):
    ang = np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))
    if ang < 1e-9:
        return np.zeros(3)
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2 * np.sin(ang))
    return w * ang


class Rig:
    """parent: {hash: parent hash}; pivots: {hash: (3,) bind position}"""

    def __init__(self, parent, pivots):
        self.parent, self.pivot = parent, pivots
        order, seen = [], set()

        def visit(h):
            if h in seen:
                return
            seen.add(h)
            p = parent.get(h)
            if p is not None:
                visit(p)
            order.append(h)
        for h in list(pivots):
            visit(h)
        self.order = order

    @classmethod
    def from_meshes(cls, parent, meshes):
        piv = {}
        for m in meshes:
            for h, M in m.bind_matrices().items():
                piv.setdefault(h, M[:3, 3])
        return cls(parent, piv)

    def solve(self, pose, frac=1.0):
        """{hash: 4x4 world transform relative to bind} for a pose applied `frac` of the way"""
        world = {}
        aims = {H[b]: (k, v) for b, k, v in pose if b in H}

        def W(h):
            if h in world:
                return world[h]
            p = self.parent.get(h)
            Mp = W(p) if (p is not None and p in self.pivot) else np.eye(4)
            M = Mp.copy()
            if h in aims and h in self.pivot:
                kind, val = aims[h]
                piv = Mp[:3, :3] @ self.pivot[h] + Mp[:3, 3]
                if kind == 'aim':
                    ch = H.get(CHILD.get(skel.bone_name(h), ''))
                    if ch in self.pivot:
                        cur = Mp[:3, :3] @ (self.pivot[ch] - self.pivot[h])
                        R = _rot_between(cur, val)
                    else:
                        R = np.eye(3)
                else:
                    R = _axis_angle(UP, val)
                R = _axis_angle(_log(R), np.linalg.norm(_log(R)) * frac) if np.linalg.norm(_log(R)) > 0 else R
                D = np.eye(4)
                D[:3, :3] = R
                D[:3, 3] = piv - R @ piv
                M = D @ Mp
            world[h] = M
            return M
        for h in self.order:
            W(h)
        return world


def skin(mesh, world):
    """posed vertex positions of a Mesh under world transforms (bones missing from `world` stay at bind)"""
    P = mesh.positions()
    Ph = np.c_[P, np.ones(len(P))]
    pal, w = mesh.influences()
    mats = np.array([world.get(h, np.eye(4)) for h in mesh.palette])
    out = np.zeros_like(P)
    for k in range(pal.shape[1]):
        Mk = mats[pal[:, k]]
        out += w[:, k:k + 1] * np.einsum('nij,nj->ni', Mk, Ph)[:, :3]
    return out


def frames(rig, fracs=(0.5, 1.0), poses=None):
    """yield (name, frac, world)"""
    for name in (poses or POSES):
        for f in fracs:
            yield name, f, rig.solve(POSES[name], f)

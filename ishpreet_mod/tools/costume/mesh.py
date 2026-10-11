"""Read-only skinned mesh record (type 415D9568, Syndicate 'original Ubisoft layout'), stride 40 (body: 8 influences) and
stride 32 (cloth pieces such as Aveline's skirt: 4 influences). numpy only, so it runs in the Mac's Cowork shell too.

Layout (acs_kit/FORMATS.md, verified there on Elise's body; stride 32 verified here on Aveline's skirt):
    palette: N x 81 bytes [a1e7f09e][u32 bone hash = CRC32(name)][64-byte inverse bind matrix][9 bytes], count u32 at P0-12
    u32 L, vertex buffer (L bytes), u32 M, index buffer (u16, local per sub)
    tail: sub tables (tag ef8773a5: vStart, 0, vCount, idxStart, triCount, 1) x2, bone maps (tag c1341d0b: +9 count u16,
          +11 vCount u16, +14 material id u64, +22 count x u16 palette indices)
    vertex: int16 x,y,z,w (pos = xyz * w/32767 / 16384 m) | normal u8x4 | tangent u8x4 | binormal u8x4 | int16 u,v (/2048) |
            stride 40: 8 slots + 8 weights; stride 32: 4 slots + 4 weights (weights sum to 255). z up, front = -y.
"""
import struct

import numpy as np

TAG_PAL = bytes.fromhex('a1e7f09e')
TAG_SUB = bytes.fromhex('ef8773a5')
TAG_MAP = bytes.fromhex('c1341d0b')


def _find_vb(r):
    best, n = None, len(r)
    for k in range(0, min(n - 8, 400000)):
        L = struct.unpack_from('<I', r, k)[0]
        if 4000 < L < n - k - 8:
            M = struct.unpack_from('<I', r, k + 4 + L)[0]
            if 600 < M < n and k + 8 + L + M <= n and M % 6 == 0:
                for s in (40, 32):
                    if L % s:
                        continue
                    w = np.frombuffer(r, np.uint8, L, k + 4).reshape(-1, s)[:200, 6:8].copy().view(np.int16)
                    if (w == w[0]).all() and w[0, 0] > 0:
                        if best is None or L > best[0]:
                            best = (L, k, M, s)
                        break
    if best is None:
        raise ValueError('vertex buffer not found')
    return best


class Mesh:
    def __init__(self, raw, name=''):
        r = self.raw = bytes(raw)
        self.name = name
        self.p0 = r.find(TAG_PAL)
        self.npal = struct.unpack_from('<I', r, self.p0 - 12)[0]
        if not all(r[self.p0 + 81 * i:self.p0 + 81 * i + 4] == TAG_PAL for i in range(self.npal)):
            raise ValueError('palette walk failed')
        self.palette = [struct.unpack_from('<I', r, self.p0 + 81 * i + 4)[0] for i in range(self.npal)]
        self.inv_bind = np.array([np.array(struct.unpack_from('<16f', r, self.p0 + 81 * i + 8)).reshape(4, 4).T
                                  for i in range(self.npal)])
        L, k, M, s = _find_vb(r)
        self.stride = s
        self.vb_off = k + 4
        self.VB = np.frombuffer(r, np.uint8, L, k + 4).reshape(-1, s).copy()
        self.IB = np.frombuffer(r, np.uint16, M // 2, k + 8 + L).copy()
        tail0 = k + 8 + L + M
        tabs, j = [], r.find(TAG_SUB, tail0)
        while j >= 0:
            tabs.append(struct.unpack_from('<6I', r, j + 4))
            j = r.find(TAG_SUB, j + 4)
        self.subs = [list(e) for e in tabs[:len(tabs) // 2]]          # [vStart, 0, vCount, idxStart, triCount, 1]
        self.maps, j = [], r.find(TAG_MAP, tail0)
        while j >= 0:
            cnt, vc = struct.unpack_from('<HH', r, j + 9)
            self.maps.append({'cnt': cnt, 'vc': vc, 'material': struct.unpack_from('<Q', r, j + 14)[0],
                              'bones': list(struct.unpack_from('<%dH' % cnt, r, j + 22))})
            j = r.find(TAG_MAP, j + 4)
        if [m['vc'] for m in self.maps] != [s_[2] & 0xffff for s_ in self.subs]:
            raise ValueError('bone maps do not line up with sub-meshes')

    # ------------------------------------------------------------------ geometry
    def positions(self):
        raw = self.VB[:, 0:8].copy().view(np.int16).reshape(-1, 4).astype(np.float64)
        return raw[:, :3] * (raw[:, 3:4] / 32767.0) / 16384.0

    def normals(self):
        n = self.VB[:, 8:11].astype(np.float64) / 127.5 - 1.0
        return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)

    def uvs(self):
        return self.VB[:, 20:24].copy().view(np.int16).reshape(-1, 2).astype(np.float64) / 2048.0

    def tris(self, sub, local=False):
        vs, _, vc, ist, tc, _x = self.subs[sub]
        T = self.IB[ist:ist + tc * 3].reshape(-1, 3).astype(np.int64)
        return T if local else T + vs

    def all_tris(self, drop_collapsed=True):
        """(triangles, sub index per triangle). Collapsed triangles (v0,v0,v0 = 'hidden') are dropped."""
        Ts, S = [], []
        for si in range(len(self.subs)):
            T = self.tris(si)
            if drop_collapsed:
                T = T[(T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2])]
            Ts.append(T)
            S.append(np.full(len(T), si))
        return np.vstack(Ts), np.concatenate(S)

    def sub_of_vertex(self):
        out = np.zeros(len(self.VB), int)
        for si, (vs, _, vc, _, _, _) in enumerate(self.subs):
            out[vs:vs + vc] = si
        return out

    # ------------------------------------------------------------------ skinning
    def influences(self):
        """(palette index (n,k), weight (n,k) floats summing to 1). k = 8 (stride 40) or 4 (stride 32)."""
        k = 8 if self.stride == 40 else 4
        slots = self.VB[:, 24:24 + k].astype(int)
        w = self.VB[:, 24 + k:24 + 2 * k].astype(np.float64) / 255.0
        pal = np.zeros_like(slots)
        sov = self.sub_of_vertex()
        for si, m in enumerate(self.maps):
            lut = np.array(m['bones'] + [0] * (256 - m['cnt']))
            sel = sov == si
            pal[sel] = lut[slots[sel]]
        return pal, w

    def bone_hash_weights(self):
        """dense {bone hash: (n,) weight} over all vertices"""
        pal, w = self.influences()
        out = {}
        for k in range(pal.shape[1]):
            for p in np.unique(pal[:, k]):
                h = self.palette[p]
                sel = (pal[:, k] == p) & (w[:, k] > 0)
                if sel.any():
                    out.setdefault(h, np.zeros(len(self.VB)))[sel] += w[sel, k]
        return out

    def bind_matrices(self):
        """{bone hash: 4x4 world bind matrix} from the palette's inverse bind matrices"""
        return {h: np.linalg.inv(M) for h, M in zip(self.palette, self.inv_bind)}

    # ------------------------------------------------------------------ same-size weight patch
    def patch_weights(self, idx, W, hashes, parent):
        """new record bytes with vertices `idx` re-weighted to dense W (len(idx), len(hashes)) over bone `hashes`.
        Same size: only the slot/weight bytes change. A bone missing from a sub-mesh's bone map hands its weight to its
        nearest ancestor that is in the map. Returns (bytes, {bone hash: ancestor used} for the moved bones)."""
        from . import skel
        k = 8 if self.stride == 40 else 4
        out = bytearray(self.raw)
        sov = self.sub_of_vertex()
        moved = {}
        idx = np.asarray(idx)
        for si, m in enumerate(self.maps):
            sel = np.where(sov[idx] == si)[0]
            if not len(sel):
                continue
            slot_of = {self.palette[p]: sl for sl, p in enumerate(m['bones'])}
            col = np.zeros((len(hashes), len(m['bones'])))
            for c, h in enumerate(hashes):
                tgt = next((a for a in skel.chain(parent, h) if a in slot_of), None)
                if tgt is None:
                    tgt = next(iter(slot_of))
                if tgt != h:
                    moved[h] = tgt
                col[c, slot_of[tgt]] = 1
            Ws = np.asarray(W)[sel] @ col                       # (n, slots in this sub)
            top = np.argsort(-Ws, 1)[:, :k]
            tw = np.take_along_axis(Ws, top, 1)
            tw = tw / np.maximum(tw.sum(1, keepdims=True), 1e-12)
            x = tw * 255                                    # largest-remainder rounding: sums to 255, error < 1/255
            q = np.floor(x).astype(int)
            rem = 255 - q.sum(1)
            frac_order = np.argsort(-(x - q), 1)
            for r_ in range(1, k + 1):
                hit = rem >= r_
                q[hit, frac_order[hit, r_ - 1]] += 1
            slots = np.where(q > 0, top, 0).astype(np.uint8)
            for r_, v in enumerate(idx[sel]):
                o = self.vb_off + int(v) * self.stride + 24
                out[o:o + k] = bytes(slots[r_])
                out[o + k:o + 2 * k] = bytes(q[r_].astype(np.uint8))
        return bytes(out), moved

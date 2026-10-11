"""Costume QA gates: run on a BUILT outfit before it is installed. numpy (+ Pillow for the images), no VM, no game clips.

    python3 -m costume.qa --mesh body=Evie/dlc14_201_JaspreetBody_k28.data:296181347212 \
                          --mesh coat=Evie/dlc14_200_EliseCoat_k26.data:296181347207 \
                          --skeleton ACVI_CHR_SHR_Female.bin --skeleton Elise_Body_skeleton.bin \
                          --out qa_k28 [--orig dlc14_201_original.data --log build_k28.log] [--quick]

Gates (each prints PASS/FAIL with the worst cases and where they are on the body):
  G1 holes        open boundary loops that are small and not tucked under another piece (cuffs/hems are big loops)
  G2 seam tears   coincident vertices (across all pieces and meshes) whose bone weights differ: they split in motion
  G3 junctions    edges of a piece that touch another piece at rest and pull away from it in any pose (spine gap, armpit)
  G4 clipping     a piece that lies over another at rest goes through it in a pose (legs through the skirt, sash)
  G5 views        see-through holes and how much of the garment's inside shows, from below/behind/sides per pose (PNGs)
  G6 atlas        UV islands of different pieces overlapping in the same material's texture (leg showing kurta paint)
  G7 weights      weights not summing to 1, bones the skeleton can't drive (vertices vanish/sink), far-away bones
  G8 materials    the material each sub-mesh is drawn with, vs the stock outfit's (painted textures that never show)
Poses: rom.POSES (climb reaches, hang, wall step, crouch, sprint, straddle, arms back, bend, twist) at 50% and 100%.
A FAIL means the build should not reach the game. Thresholds are arguments; defaults are set from what was visible in
the k23-k28 screenshots (a 1 cm gap is visible in game; 3 mm clipping is not).
"""
import argparse
import json
import os
import re
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from costume import geom, rom, skel  # noqa: E402
from costume.mesh import Mesh  # noqa: E402

MESH_TYPE = 0x415D9568


# ---------------------------------------------------------------- loading
def load_record(spec):
    """'path[:record_id]' -> raw mesh record. path is a raw record (.bin) or a pack (.data) holding it."""
    m = re.match(r'(.*):(\d+)$', spec)
    path, rid = (m.group(1), m.group(2)) if m else (spec, None)
    raw = open(path, 'rb').read()
    if raw[:1] == b'\x01' and len(raw) > 13 and raw[9:13] == MESH_TYPE.to_bytes(4, 'little'):
        return raw
    import anvil_forge as af

    class One(af.Forge):
        def __init__(self, data):
            self._d = data

        def raw_pack(self, p):
            return self._d
    files = list(One(raw).pack_files({'id': 0, 'type': 0, 'name': os.path.basename(path), 'size': len(raw)}))
    cand = [f for f in files if (rid is None and f['type'] == MESH_TYPE) or (rid is not None and str(f['id']) == rid)]
    if not cand:
        raise SystemExit(f'{spec}: no mesh record found ({len(files)} files in the pack)')
    return cand[0]['data']


class Layer:
    def __init__(self, label, mesh):
        self.label, self.mesh = label, mesh
        self.P = mesh.positions()
        self.T, self.tsub = mesh.all_tris()
        self.tl, self.vl = geom.components(self.P, self.T)
        self.pal, self.w = mesh.influences()
        self.names = {}

    def comp_name(self, c):
        if c in self.names:
            return self.names[c]
        V = self.P[self.vl == c]
        n = int((self.tl == c).sum())
        return f'{self.label}#{c} ({n} tris, z {V[:, 2].min():.2f}-{V[:, 2].max():.2f})'


def name_from_log(layer, orig_vcount_sub1, log_text):
    """name pieces appended to sub 1 from a kameez build log ('  + name N v M tris' lines, in append order)"""
    vs = layer.mesh.subs[1][0] + orig_vcount_sub1
    for m in re.finditer(r'^  \+ (\w[\w ]*?) (\d+) v', log_text, re.M):
        n = int(m.group(2))
        cs = np.unique(layer.vl[vs:vs + n])
        for c in cs[cs >= 0]:
            layer.names.setdefault(int(c), m.group(1))
        vs += n


def location(p):
    x, y, z = p
    side = 'centre' if abs(x) < 0.04 else ('left' if x > 0 else 'right')
    face = 'front' if y < -0.03 else ('back' if y > 0.03 else 'side')
    part = ('head' if z > 1.55 else 'neck/shoulders' if z > 1.40 else 'chest' if z > 1.20 else 'waist' if z > 1.00
            else 'hips/thighs' if z > 0.70 else 'knees/shins' if z > 0.25 else 'feet')
    return f'{part}, {face}, {side} ({x:+.2f},{y:+.2f},{z:.2f})'


# ---------------------------------------------------------------- gates
def g7_weights(layers, rig, parent):
    issues = []
    for L in layers:
        s = L.w.sum(1)
        bad = np.abs(s - 1) > 0.01
        if bad.any():
            issues.append(f'{L.label}: {int(bad.sum())} vertices whose weights do not sum to 1')
        used = set(np.unique(L.pal[L.w > 0]))
        for p in sorted(used):
            h = L.mesh.palette[p]
            ch = skel.chain(parent, h)
            if h not in parent or ch[-1] != rom.H['Reference']:
                n = int(((L.pal == p) & (L.w > 0)).any(1).sum())
                issues.append(f'{L.label}: bone {skel.bone_name(h)} drives {n} vertices but is not in the skeleton '
                              f'(chain {"/".join(skel.bone_name(x) for x in ch)}): in game they do not move or vanish')
        dom = L.pal[np.arange(len(L.P)), L.w.argmax(1)]
        piv = np.array([rig.pivot.get(L.mesh.palette[p], L.P[i]) for i, p in enumerate(dom)])
        far = np.linalg.norm(piv - L.P, axis=1) > 0.6
        used_v = L.vl >= 0
        if (far & used_v).any():
            issues.append(f'{L.label}: {int((far & used_v).sum())} vertices are driven mostly by a bone over 60 cm away, '
                          f'e.g. at {location(L.P[np.where(far & used_v)[0][0]])}')
    return {'gate': 'G7 weights', 'pass': not issues, 'issues': issues}


def g2_seams(layers, tol=5e-4, max_diff=0.05):
    allP = np.vstack([L.P for L in layers])
    owner = np.concatenate([np.full(len(L.P), i) for i, L in enumerate(layers)])
    local = np.concatenate([np.arange(len(L.P)) for L in layers])
    used = np.concatenate([L.vl >= 0 for L in layers])
    wid = geom.weld_ids(allP, tol)
    _, cnt = np.unique(wid, return_counts=True)
    multi = np.where((cnt[wid] > 1) & used)[0]

    def wvec(i):
        L = layers[owner[i]]
        j = local[i]
        return {L.mesh.palette[p]: w for p, w in zip(L.pal[j], L.w[j]) if w > 0}
    bad, worst = [], 0.0
    order = np.argsort(wid[multi])
    grp = multi[order]
    starts = np.r_[0, np.where(np.diff(wid[grp]) != 0)[0] + 1, len(grp)]
    for a, b in zip(starts[:-1], starts[1:]):
        g = grp[a:b]
        if len(g) < 2:
            continue
        ws = [wvec(i) for i in g]
        keys = set().union(*ws)
        M = np.array([[w.get(k, 0) for k in keys] for w in ws])
        d = np.abs(M - M.mean(0)).sum(1).max()
        if d > max_diff:
            i = g[0]
            L = layers[owner[i]]
            pieces = sorted({layers[owner[x]].comp_name(int(layers[owner[x]].vl[local[x]])) for x in g})
            bad.append((d, allP[i], pieces))
        worst = max(worst, d)
    bad.sort(key=lambda x: -x[0])
    issues = [f'{len(bad)} seam points have different bone weights on each side (worst {worst:.2f}): they split apart in motion']
    issues += [f'  weight difference {d:.2f} at {location(p)} between {", ".join(pc)}' for d, p, pc in bad[:12]]
    return {'gate': 'G2 seam tears', 'pass': not bad, 'issues': issues if bad else [], 'count': len(bad)}


def _boundary(L):
    wid = geom.weld_ids(L.P)
    E = geom.boundary_edges(L.T, wid)
    return wid, E


def _perimeter(L, lp, E, wid):
    s = set(lp.tolist())
    e = E[[x in s for x in E[:, 0]]]
    return float(np.linalg.norm(L.P[e[:, 0]] - L.P[e[:, 1]], axis=1).sum())


OPENING_BONES = [('Hips', 'Spine'), ('Spine', 'Spine1'), ('Spine1', 'Spine2'), ('Spine2', 'Neck'), ('Neck', 'Head'), ('LeftArm', 'LeftForeArm'), ('LeftForeArm', 'LeftHand'),
                 ('RightArm', 'RightForeArm'), ('RightForeArm', 'RightHand'), ('LeftUpLeg', 'LeftLeg'),
                 ('LeftLeg', 'LeftFoot'), ('RightUpLeg', 'RightLeg'), ('RightLeg', 'RightFoot')]
EXTENSIONS = [('Hips', (0, 0, -0.30)), ('Head', (0, 0, 0.30)), ('Head', (0, -0.35, 0.05)), ('LeftHand', (0.25, 0, -0.2)),
              ('RightHand', (-0.25, 0, -0.2)), ('LeftFoot', (0, -0.25, -0.05)), ('RightFoot', (0, -0.25, -0.05))]


def _segments(rig):
    seg = []
    for a, b in OPENING_BONES:
        if rom.H[a] in rig.pivot and rom.H[b] in rig.pivot:
            seg.append((rig.pivot[rom.H[a]], rig.pivot[rom.H[b]]))
    for a, d in EXTENSIONS:
        if rom.H[a] in rig.pivot:
            p = rig.pivot[rom.H[a]]
            seg.append((p, p + np.array(d)))
    return seg


def _is_opening(pts, segments):
    """a limb, the neck or the face passes through the loop: some segment crosses the loop's plane inside it"""
    c = pts.mean(0)
    _, _, Vt = np.linalg.svd(pts - c)
    n, e1, e2 = Vt[2], Vt[0], Vt[1]
    q = np.c_[(pts - c) @ e1, (pts - c) @ e2]
    order = np.argsort(np.arctan2(q[:, 1], q[:, 0]))
    poly = q[order]
    for a, b in segments:
        da, db = (a - c) @ n, (b - c) @ n
        if da * db > 0:
            continue
        t = da / (da - db) if da != db else 0.5
        x = a + t * (b - a) - c
        u, v = x @ e1, x @ e2
        inside = False
        for k in range(len(poly)):
            (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % len(poly)]
            if (y1 > v) != (y2 > v) and u < (x2 - x1) * (v - y1) / (y2 - y1 + 1e-12) + x1:
                inside = not inside
        if inside:
            return True
    return False


def g1_holes(layers, rig=None, cover=0.008):
    """a hole = a boundary loop that no limb/neck/face passes through (so it is not an opening) and that no other piece
    covers. Without a rig, falls back to: small loops beyond each piece's two longest."""
    issues, centres = [], []
    segments = _segments(rig) if rig is not None else None
    for i, L in enumerate(layers):
        wid, E = _boundary(L)
        by_piece = {}
        for lp in geom.loops(E, wid):
            by_piece.setdefault(int(L.vl[lp[0]]), []).append((_perimeter(L, lp, E, wid), lp))
        cands = []
        for c, lps in by_piece.items():
            lps.sort(key=lambda x: -x[0])
            for k, (per, lp) in enumerate(lps):
                if len(lp) < 3 or k == 0:        # the longest loop is the piece's outline (a panel's edge, a hem)
                    continue
                if segments is not None:
                    if not _is_opening(L.P[lp], segments):
                        cands.append((c, per, lp))
                elif k >= 2 and per <= 0.25:
                    cands.append((c, per, lp))
        for c, per, lp in cands:
            pts = L.P[lp]
            covered = False
            found = None
            for j, M in enumerate(layers):
                mask = (M.vl >= 0) & ((M.vl != c) if j == i else True)
                if not mask.any():
                    continue
                _, d = geom.nearest(pts, M.P[mask])
                if (d < cover).mean() > 0.8:
                    covered = True
                    break
            if not covered:
                issues.append(f'hole ~{per * 100:.0f} cm round in {L.comp_name(c)} at {location(pts.mean(0))}')
                centres.append(pts.mean(0))
    return {'gate': 'G1 holes', 'pass': not issues, 'issues': issues[:30], 'count': len(issues), 'centres': centres}


def g1_vs_stock(res, base_res, near=0.03):
    """holes the stock outfit has in the same place are Ubisoft's, not the build's: info, not FAIL"""
    if not base_res or not base_res.get('centres'):
        return res
    B = np.array(base_res['centres'])
    keep, stock = [], []
    for txt, c in zip(res['issues'], res['centres']):
        (stock if np.linalg.norm(B - c, axis=1).min() < near else keep).append(txt)
    out = dict(res, issues=keep, count=len(keep), **{'pass': not keep})
    if stock:
        out['info'] = [f'{len(stock)} openings are also in the stock outfit (not counted)'] + stock[:3]
    return out


def _pieces(layers):
    """[(layer index, component, vertex indices)] for components with at least 20 vertices"""
    out = []
    for i, L in enumerate(layers):
        for c in np.unique(L.vl[L.vl >= 0]):
            v = np.where(L.vl == c)[0]
            if len(v) >= 20:
                out.append((i, int(c), v))
    return out


def find_junctions(layers, d0=0.015):
    """boundary vertices of piece A lying within d0 of piece B at rest -> [(A, B, A boundary verts, rest distance)]"""
    pieces = _pieces(layers)
    out = []
    for ia, ca, va in pieces:
        L = layers[ia]
        wid, E = _boundary(L)
        bv = np.unique(E.ravel())
        bv = bv[L.vl[bv] == ca]
        if not len(bv):
            continue
        for ib, cb, vb in pieces:
            if (ia, ca) == (ib, cb):
                continue
            j, d = geom.nearest(L.P[bv], layers[ib].P[vb])
            sel = d < d0
            if sel.sum() >= 4:
                out.append({'a': (ia, ca), 'b': (ib, cb), 'verts': bv[sel], 'rest': d[sel]})
    return out


def g3_g4(layers, rig, poses, fracs, junctions, open_tol=0.010, clip_tol=0.003, overlap_d=0.025):
    """junction opening and clipping across poses"""
    pieces = _pieces(layers)
    # layering pairs for clipping: A over B where many A vertices sit within overlap_d outside B at rest
    restN = [geom.vnormals(L.P, L.T) for L in layers]
    pairs = []
    for ia, ca, va in pieces:
        for ib, cb, vb in pieces:
            if (ia, ca) == (ib, cb):
                continue
            s, d, j = geom.signed_to_surface(layers[ia].P[va], layers[ib].P[vb], restN[ib][vb])
            near = d < overlap_d
            if near.sum() >= 30 and (s[near] > 0).mean() > 0.8:
                pairs.append({'a': (ia, ca), 'b': (ib, cb), 'verts': va[near & (s > 0)]})
    jres = {k: (0.0, None) for k in range(len(junctions))}
    cres = {k: (0, None, None) for k in range(len(pairs))}
    for name, f, world in rom.frames(rig, fracs, poses):
        PP = [rom.skin(L.mesh, world) for L in layers]
        NN = [geom.vnormals(P_, L.T) for P_, L in zip(PP, layers)]
        for k, J in enumerate(junctions):
            ia, ca = J['a']
            ib, cb = J['b']
            vb = np.where(layers[ib].vl == cb)[0]
            _, d = geom.nearest(PP[ia][J['verts']], PP[ib][vb])
            gap = d - J['rest']
            g = float(gap.max())
            if g > jres[k][0]:
                jres[k] = (g, (name, f, layers[ia].P[J['verts'][gap.argmax()]]))
        for k, C in enumerate(pairs):
            ia, ca = C['a']
            ib, cb = C['b']
            vb = np.where(layers[ib].vl == cb)[0]
            s, d, _ = geom.signed_to_surface(PP[ia][C['verts']], PP[ib][vb], NN[ib][vb])
            inside = (s < -clip_tol) & (d < 0.05)
            n = int(inside.sum())
            if n >= 5 and n > cres[k][0]:
                cres[k] = (n, (name, f), layers[ia].P[C['verts'][np.argmin(s)]])
    ji, ci = [], []
    for k, J in enumerate(junctions):
        g, where = jres[k]
        if g > open_tol:
            ia, ca = J['a']
            ib, cb = J['b']
            ji.append((g, f'{layers[ia].comp_name(ca)} pulls {g * 100:.1f} cm away from {layers[ib].comp_name(cb)} '
                          f'in {where[0]} ({int(where[1] * 100)}%) at {location(where[2])}'))
    for k, C in enumerate(pairs):
        n, where, p = cres[k]
        if n:
            ia, ca = C['a']
            ib, cb = C['b']
            ci.append((n, f'{layers[ia].comp_name(ca)} goes through {layers[ib].comp_name(cb)}: {n} vertices in '
                          f'{where[0]} ({int(where[1] * 100)}%), worst at {location(p)}'))
    ji.sort(key=lambda x: -x[0])
    ci.sort(key=lambda x: -x[0])
    return ({'gate': 'G3 junctions', 'pass': not ji, 'issues': [s for _, s in ji[:25]], 'count': len(ji),
             'checked': len(junctions)},
            {'gate': 'G4 clipping', 'pass': not ci, 'issues': [s for _, s in ci[:25]], 'count': len(ci),
             'checked': len(pairs)})


VIEWS = {'front': (0, 1, 0), 'back': (0, -1, 0), 'left': (-1, 0, 0), 'right': (1, 0, 0),
         'below_back': (0, -0.55, 0.83), 'below_front': (0, 0.55, 0.83)}


def g5_views(layers, rig, poses, out_dir, prefix=''):
    """per key pose and view: see-through pixels (enclosed background) and the fraction of visible surface that is a
    garment's inside (back faces). Returns rows; images go to out_dir/<prefix><pose>.png"""
    from PIL import Image
    rows = []
    key_poses = [p for p in ('climb_reach_L', 'climb_reach_R', 'hang_both', 'crouch', 'wall_step_L') if p in poses] or poses
    frames = [('rest', 0.0, rig.solve([], 0))] + [(p, 1.0, rig.solve(rom.POSES[p], 1.0)) for p in key_poses]
    lab_off = np.cumsum([0] + [int(L.vl.max()) + 1 for L in layers])
    for name, f, world in frames:
        P = np.vstack([rom.skin(L.mesh, world) for L in layers])
        voff = np.cumsum([0] + [len(L.P) for L in layers])
        T = np.vstack([L.T + voff[i] for i, L in enumerate(layers)])
        lab = np.concatenate([L.tl + lab_off[i] for i, L in enumerate(layers)])
        tiles = []
        for vname, v in VIEWS.items():
            Limg, Fimg, _ = geom.splat(P, T, lab, v)
            holes = geom.enclosed_background(Limg < 0)
            filled = (Limg >= 0).sum()
            rows.append({'pose': name, 'view': vname, 'hole_px': int(holes.sum()),
                         'inside_frac': round(float((Fimg < 0).sum() / max(filled, 1)), 4)})
            rgb = np.full(Limg.shape + (3,), 40, np.uint8)
            pal = np.random.default_rng(7).integers(90, 230, size=(int(lab.max()) + 2, 3)).astype(np.uint8)
            m = Limg >= 0
            rgb[m] = pal[Limg[m]]
            rgb[Fimg < 0] = (40, 90, 255)
            rgb[holes] = (255, 0, 0)
            tiles.append(Image.fromarray(rgb))
        if out_dir:
            Hh = max(t.height for t in tiles)
            sheet = Image.new('RGB', (sum(t.width for t in tiles), Hh), (20, 20, 20))
            x = 0
            for t in tiles:
                sheet.paste(t, (x, Hh - t.height))
                x += t.width
            sheet.save(os.path.join(out_dir, f'{prefix}{name}.png'))
    return rows


def g5_compare(rows, base=None, hole_margin=20, inside_margin=0.03):
    """FAIL where the build shows more see-through or more garment inside than the stock outfit (baseline) in the same
    pose and view. Without a baseline only see-through pixels count."""
    issues = []
    b = {(r['pose'], r['view']): r for r in (base or [])}
    for r in rows:
        k = (r['pose'], r['view'])
        ref = b.get(k, {'hole_px': 0, 'inside_frac': None})
        if r['hole_px'] > ref['hole_px'] + (hole_margin if base else 0):
            issues.append(f'{k[0]} / {k[1]}: {r["hole_px"]} see-through pixels (stock: {ref["hole_px"]}) - red in {k[0]}.png')
        if ref['inside_frac'] is not None and r['inside_frac'] > ref['inside_frac'] + inside_margin:
            issues.append(f'{k[0]} / {k[1]}: {r["inside_frac"] * 100:.1f}% of the view is the inside of a garment '
                          f'(stock {ref["inside_frac"] * 100:.1f}%) - blue in {k[0]}.png')
    return {'gate': 'G5 views', 'pass': not issues, 'issues': issues[:30], 'table': rows,
            'info': [] if base else ['no baseline given: garment insides are not judged (pass --baseline)']}


def g6_atlas(layers, size=512, share=0.9):
    """UV overlap inside one material. Pieces named differently by the build log (kurta, sirwal, ...) must not share
    texels: FAIL. Unnamed pieces: WARN (stock assets reuse texture between straps and panels on purpose).
    Near-total overlap (>= share of the smaller piece) is a mirrored or two-sided copy: info."""
    issues, warn, info = [], [], []
    by_mat = {}
    for i, L in enumerate(layers):
        mats = np.array([L.mesh.maps[s_]['material'] for s_ in L.tsub])
        for mat in np.unique(mats):
            by_mat.setdefault(int(mat), []).append((i, mats == mat))
    for mat, parts in by_mat.items():
        UV, T, lab, label_name, named = [], [], [], {}, {}
        off = 0
        for i, sel in parts:
            L = layers[i]
            uv = L.mesh.uvs() % 1.0
            UV.append(uv)
            T.append(L.T[sel] + off)
            lab.append(L.tl[sel] + 100000 * i)
            for c in np.unique(L.tl[sel]):
                label_name[int(c + 100000 * i)] = L.comp_name(int(c))
                named[int(c + 100000 * i)] = L.names.get(int(c))
            off += len(uv)
        UV, T, lab = np.vstack(UV), np.vstack(T), np.concatenate(lab)
        _, _, pairs, area = geom.uv_raster(UV, T, lab, size)
        for (a_, b_), px in sorted(pairs.items(), key=lambda x: -x[1]):
            frac = px / max(min(area.get(a_, 0), area.get(b_, 0)), 1)
            txt = (f'material {mat}: {label_name.get(a_)} and {label_name.get(b_)} share {frac * 100:.0f}% of the '
                   f'smaller one\'s texture ({px} texels at {size}px)')
            na, nb = named.get(a_), named.get(b_)
            if frac >= share and (na == nb or not (na and nb)):
                info.append(txt)
            elif na and nb and na != nb:
                issues.append(txt)
            else:
                warn.append(txt)
    return {'gate': 'G6 atlas', 'pass': not issues, 'issues': issues[:25],
            'info': ([f'WARN {w}' for w in warn[:15]] +
                     [f'{len(info)} pairs share texture on purpose (mirrored or two-sided copies)'] + info[:5])}


def g8_materials(layers, baseline=None):
    """which material each sub-mesh is drawn with (bone map +14). The game shows that material's textures, whatever
    texture the build painted. With a baseline of the same label (stock body/coat), a changed material is a FAIL: the
    offline preview and the game will disagree (Ishpreet's skirt: saffron offline, dark grey-brown in game)."""
    issues, info = [], []
    base = {B.label: B for B in (baseline or [])}
    for L in layers:
        mats = [m['material'] for m in L.mesh.maps]
        vis = sorted({int(L.tsub[i]) for i in range(len(L.tsub))})
        info.append(f'{L.label}: ' + ', '.join(f'sub {si} -> material {mats[si]}' + ('' if si in vis else ' (hidden)')
                                                for si in range(len(mats))))
        if L.label in base:
            bm = [m['material'] for m in base[L.label].mesh.maps]
            for si in vis:
                if si < len(bm) and mats[si] != bm[si]:
                    issues.append(f'{L.label} sub {si} is drawn with material {mats[si]}, the stock one uses {bm[si]}: '
                                  f'textures painted into the stock material\'s atlas will not show on it')
                if si >= len(bm):
                    issues.append(f'{L.label} sub {si} has no stock counterpart (stock has {len(bm)} subs)')
    others = {}
    for L in layers:
        for si in sorted({int(x) for x in L.tsub}):
            others.setdefault(L.mesh.maps[si]['material'], []).append(f'{L.label}/sub{si}')
    lone = [f'{m} ({", ".join(v)})' for m, v in others.items() if len(v) == 1 and len(others) > 1]
    if lone:
        info.append('materials used by one sub only (their textures are separate from the rest of the outfit): ' + '; '.join(lone))
    return {'gate': 'G8 materials', 'pass': not issues, 'issues': issues, 'info': info}


# ---------------------------------------------------------------- driver
def make_rig(layers, skeleton_raws):
    parent = skel.merge(*skeleton_raws)
    pivots = skel.world_rest(skeleton_raws, {h: M[:3, 3] for L in layers for h, M in L.mesh.bind_matrices().items()})
    for L in layers:
        for h, M in L.mesh.bind_matrices().items():
            pivots[h] = M[:3, 3]
    return parent, rom.Rig(parent, pivots)


def unposed(layers, rig, poses):
    """pieces that no pose moves (driven only by cloth/helper bones): G3/G4 cannot judge them"""
    moved = [np.zeros(len(L.P), bool) for L in layers]
    for name, f, world in rom.frames(rig, (1.0,), poses):
        for i, L in enumerate(layers):
            moved[i] |= np.linalg.norm(rom.skin(L.mesh, world) - L.P, axis=1) > 0.005
    out = []
    for i, L in enumerate(layers):
        for c in np.unique(L.vl[L.vl >= 0]):
            v = L.vl == c
            if v.sum() >= 20 and moved[i][v].mean() < 0.05:
                out.append(L.comp_name(int(c)))
    return out


def run(layers, skeleton_raws, out_dir=None, poses=None, fracs=(0.5, 1.0), views=True, baseline=None):
    """baseline: layers of the stock outfit in the same slot (e.g. the original Elise body + coat)"""
    parent, rig = make_rig(layers, skeleton_raws)
    poses = poses or list(rom.POSES)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    g1 = g1_holes(layers, rig)
    if baseline:
        _, brig = make_rig(baseline, skeleton_raws)
        g1 = g1_vs_stock(g1, g1_holes(baseline, brig))
    res = [g7_weights(layers, rig, parent), g2_seams(layers), g1]
    J = find_junctions(layers)
    res += list(g3_g4(layers, rig, poses, fracs, J))
    still = unposed(layers, rig, poses)
    if still:
        res[-2].setdefault('info', []).append('not moved by any pose (cloth-simulated or helper-driven), so not judged: '
                                              + '; '.join(still[:8]))
    if views:
        rows = g5_views(layers, rig, poses, out_dir)
        base_rows = None
        if baseline:
            _, brig = make_rig(baseline, skeleton_raws)
            base_rows = g5_views(baseline, brig, poses, out_dir, prefix='stock_')
        res.append(g5_compare(rows, base_rows))
    res.append(g6_atlas(layers))
    res.append(g8_materials(layers, baseline))
    return res


def report(res):
    lines = []
    for r in res:
        lines.append(f'{"PASS" if r["pass"] else "FAIL"}  {r["gate"]}' +
                     (f'  ({r.get("checked")} checked)' if 'checked' in r else ''))
        for s in r.get('issues', []):
            lines.append('      ' + s)
        for s in r.get('info', [])[:4]:
            lines.append('      info: ' + s)
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mesh', action='append', required=True, help='label=path[:record_id]')
    ap.add_argument('--skeleton', action='append', required=True, help='skeleton record(s): base first, outfit after')
    ap.add_argument('--out')
    ap.add_argument('--orig', help='original body pack/record, to name appended pieces from --log')
    ap.add_argument('--log', help='build log with "  + name N v" lines')
    ap.add_argument('--quick', action='store_true', help='100%% poses only, no images')
    ap.add_argument('--poses', help='comma list (default: all)')
    ap.add_argument('--baseline', action='append', help='label=path[:record_id] of the STOCK outfit meshes (repeat)')
    a = ap.parse_args(argv)
    layers = []
    for spec in a.mesh:
        label, path = spec.split('=', 1)
        layers.append(Layer(label, Mesh(load_record(path), label)))
    if a.orig and a.log:
        name_from_log(layers[0], Mesh(load_record(a.orig)).subs[1][2], open(a.log).read())
    sk = [open(p, 'rb').read() for p in a.skeleton]
    poses = a.poses.split(',') if a.poses else None
    base = [Layer(sp.split('=', 1)[0], Mesh(load_record(sp.split('=', 1)[1]))) for sp in (a.baseline or [])]
    res = run(layers, sk, a.out, poses, (1.0,) if a.quick else (0.5, 1.0), views=not a.quick, baseline=base or None)
    txt = report(res)
    print(txt)
    if a.out:
        open(os.path.join(a.out, 'report.txt'), 'w').write(txt + '\n')
        json.dump(res, open(os.path.join(a.out, 'report.json'), 'w'), indent=1, default=str)
    return 0 if all(r['pass'] for r in res) else 1


if __name__ == '__main__':
    sys.exit(main())

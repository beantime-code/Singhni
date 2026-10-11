"""Re-rig a built outfit with ONE weight field (weights.py) and prove it with the QA gates, before and after.
Same-size edit: only vertex weight bytes change; geometry, UVs, palettes and bone maps stay as built.

    python3 -m costume.reweight \
        --body  Evie/dlc14_201_JaspreetBody_k28.data:296181347212 --orig dlc14_201_original.data:296181347212 \
        --coat  Evie/dlc14_200_EliseCoat_k26.data:296181347207 --coat-band 0.06 \
        --source NakedBody_LOD0.data:401137995317 \
        --skeleton ACVI_CHR_SHR_Female.bin --skeleton Elise_outfit_skeleton.bin \
        --out k29a   [--write]

What changes:
  body: every vertex that is not a stock Elise vertex kept by the build (hands, boots, gauntlet...). Stock vertices are
        fixed constraints, so the garments blend into them.
  coat: only the top band (--coat-band metres below its highest edge): the skirt's pinned top then moves exactly
        like the kurta/sash it sits under. The rest keeps its cloth bones.
Without --write it only reports (QA before -> after, vertices changed, bones redirected). With --write it saves
<out>/body.record and <out>/coat.record for acs_kit to put into packs 201/200 (pack.set(id, bytes), then install).
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from costume import qa, skel, weights  # noqa: E402
from costume.mesh import Mesh  # noqa: E402


def dense(mesh, hashes, idx=None):
    hw = mesh.bone_hash_weights()
    n = len(mesh.positions())
    W = np.zeros((n, len(hashes)))
    col = {h: i for i, h in enumerate(hashes)}
    for h, w in hw.items():
        W[:, col[h]] += w
    return W if idx is None else W[idx]


def stock_mask(body, orig):
    """vertices of the built body identical (position, UV, weights) to a vertex of the original record"""
    def keys(m):
        P = np.round(m.positions() * 1e4).astype(np.int64)
        UV = np.round(m.uvs() * 1e4).astype(np.int64)
        pal, w = m.influences()
        hh = np.array(m.palette)[pal] * (w > 0)
        ws = np.sort(np.c_[hh.astype(np.int64), np.round(w * 255).astype(np.int64)], axis=1)
        return [hash(r.tobytes()) for r in np.c_[P, UV, ws]]
    ok = set(keys(orig))
    return np.array([k in ok for k in keys(body)])


def solve(body, coat, source, parent, orig=None, coat_band=0.06, link=0.012):
    Lb = qa.Layer('body', body)
    used = Lb.vl >= 0
    fixed = stock_mask(body, orig) & used if orig is not None else np.zeros(len(Lb.P), bool)
    S = qa.Layer('source', source)
    hashes = sorted(set(source.bone_hash_weights()) | set(body.bone_hash_weights()) |
                    (set(coat.bone_hash_weights()) if coat is not None else set()))
    hashes = [h for h in hashes if h in parent]
    pieces, known_w, known_m, owners, labels = [], [], [], [], []
    # body: one piece per component (fixed vertices carry their own weights)
    Wbody_own = dense(body, hashes)
    pieces.append((Lb.P, Lb.T))
    labels.append(Lb.vl)
    known_w.append(Wbody_own)
    known_m.append(fixed)
    owners.append(('body', np.arange(len(Lb.P)), used & ~fixed))
    if coat is not None:
        Lc = qa.Layer('coat', coat)
        cu = Lc.vl >= 0
        ztop = Lc.P[cu, 2].max()
        band = cu & (Lc.P[:, 2] > ztop - coat_band)
        pieces.append((Lc.P, Lc.T))
        labels.append(Lc.vl)
        known_w.append(dense(coat, hashes))
        known_m.append(cu & ~band)
        owners.append(('coat', np.arange(len(Lc.P)), band))
    # transfer from the source body for the free vertices
    BW = dense(source, hashes)
    BN = qa.geom.vnormals(S.P, S.T)
    W0, K = [], []
    for (P, T), Wk, Mk in zip(pieces, known_w, known_m):
        N = qa.geom.vnormals(P, T)
        Wt, ok, _ = weights.transfer(P, N, S.P, S.T, BN, BW)
        W0.append(np.where(Mk[:, None], Wk, Wt))
        K.append(Mk | ok)
    W0, K = np.vstack(W0), np.concatenate(K)
    edges, ew, offs = weights.outfit_graph(pieces, link, labels=labels)
    W, iters = weights.inpaint(W0, K, edges, ew)
    W = weights.limit(W, 8)
    out = {}
    for k, (name, idx, change) in enumerate(owners):
        Wk = W[offs[k]:offs[k + 1]]
        out[name] = (idx[change], Wk[change])
    return out, hashes, {'iterations': iters, 'confident': float(K.mean())}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--body', required=True)
    ap.add_argument('--orig', help='original body record (stock vertices stay fixed)')
    ap.add_argument('--coat')
    ap.add_argument('--coat-band', type=float, default=0.06)
    ap.add_argument('--source', required=True, help="Evie's NakedBody LOD0 (London 21687, record 401137995317)")
    ap.add_argument('--skeleton', action='append', required=True)
    ap.add_argument('--baseline', action='append', help='stock outfit meshes for the QA view gate')
    ap.add_argument('--out', required=True)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    sk = [open(p, 'rb').read() for p in a.skeleton]
    parent = skel.merge(*sk)
    body = Mesh(qa.load_record(a.body), 'body')
    coat = Mesh(qa.load_record(a.coat), 'coat') if a.coat else None
    orig = Mesh(qa.load_record(a.orig)) if a.orig else None
    source = Mesh(qa.load_record(a.source), 'source')
    res, hashes, info = solve(body, coat, source, parent, orig, a.coat_band)
    print(f'solved: {info["confident"] * 100:.0f}% of vertices matched the body confidently, '
          f'{info["iterations"]} inpainting iterations')
    new = {}
    for name, m in (('body', body), ('coat', coat)):
        if m is None:
            continue
        idx, W = res[name]
        raw, moved = m.patch_weights(idx, W, hashes, parent)
        new[name] = Mesh(raw, name)
        print(f'{name}: {len(idx)} vertices re-weighted' + (', bones redirected to an ancestor in the bone map: ' +
              ', '.join(f'{skel.bone_name(x)}->{skel.bone_name(y)}' for x, y in list(moved.items())[:12])
              if moved else ''))
        if a.write:
            open(os.path.join(a.out, f'{name}.record'), 'wb').write(raw)
    base = [qa.Layer(sp.split('=', 1)[0], Mesh(qa.load_record(sp.split('=', 1)[1]))) for sp in (a.baseline or [])]
    before = qa.run([qa.Layer(n, m) for n, m in (('body', body), ('coat', coat)) if m is not None], sk,
                    os.path.join(a.out, 'qa_before'), baseline=base or None)
    after = qa.run([qa.Layer(n, m) for n, m in new.items()], sk, os.path.join(a.out, 'qa_after'), baseline=base or None)
    lines = ['gate            before  after']
    for b, c in zip(before, after):
        def cnt(r):
            return r.get('count', len(r.get('issues', [])))
        lines.append(f'{b["gate"]:15s} {("PASS" if b["pass"] else "FAIL") + " " + str(cnt(b)):7s} '
                     f'{("PASS" if c["pass"] else "FAIL") + " " + str(cnt(c))}')
    txt = '\n'.join(lines) + '\n\nAFTER:\n' + qa.report(after)
    print(txt)
    open(os.path.join(a.out, 'reweight_report.txt'), 'w').write(txt + '\n')
    return 0 if all(r['pass'] for r in after) else 1


if __name__ == '__main__':
    sys.exit(main())

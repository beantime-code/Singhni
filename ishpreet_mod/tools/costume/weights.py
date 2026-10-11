"""One weight field for a whole outfit: robust transfer from the body + inpainting across every piece. numpy only.

Method (Abdrashitov et al., "Robust Skin Weights Transfer via Weight Inpainting", SIGGRAPH Asia 2023,
https://www.dgp.toronto.edu/~rinat/projects/RobustSkinWeightsTransfer/):
  1. transfer: each garment vertex takes the body's weights at the closest point on the body surface, but only where
     that match is confident (close enough and the normals agree);
  2. inpaint: every other vertex gets weights by smooth (harmonic) interpolation over the garment surface from the
     confident ones.
Extension for layered outfits (the cause of Ishpreet's joins opening): the interpolation runs on ONE graph over all
pieces. Coincident vertices (UV seams, stitched strips) are merged into one node, and vertices of an overlay (sash,
chunni, skirt top) are linked to the piece right under them, so touching pieces end up with the same weights at the
contact and move together. Confident body transfer keeps the inner layer anchored to the body.

    W, info = outfit_weights(pieces, body_P, body_T, body_W, allowed=None)
      pieces: list of (P (n,3), T (m,3)) in bind pose; body_W: (nb, B) dense weights over a bone list
      returns one (n_i, B) array per piece, and the confident fraction
"""
import numpy as np

from . import geom


def closest_on_surface(Q, P, T, chunk=1024):
    """closest point on triangles near each query -> (triangle index, barycentric (n,3), distance).
    Candidate triangles: those touching the nearest surface vertex and its neighbours."""
    vt = [[] for _ in range(len(P))]
    for t, tri in enumerate(T):
        for v in tri:
            vt[v].append(t)
    width = max(len(x) for x in vt) if len(vt) else 1
    VT = np.full((len(P), width), -1)
    for v, ts in enumerate(vt):
        VT[v, :len(ts)] = ts
    j, _ = geom.nearest(Q, P)
    cand = VT[j]                                            # (n, width)
    best_t = np.zeros(len(Q), int)
    best_b = np.zeros((len(Q), 3))
    best_d = np.full(len(Q), np.inf)
    for c in range(cand.shape[1]):
        t = cand[:, c]
        ok = t >= 0
        if not ok.any():
            continue
        tt = T[np.where(ok, t, 0)]
        b, d = _closest_tri(Q, P[tt[:, 0]], P[tt[:, 1]], P[tt[:, 2]])
        better = ok & (d < best_d)
        best_t[better], best_b[better], best_d[better] = t[better], b[better], d[better]
    return best_t, best_b, best_d


def _closest_tri(p, a, b, c):
    """vectorised closest point on triangles (Ericson, Real-Time Collision Detection 5.1.5) -> (barycentric, distance)"""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp = p - b
    d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    cp = p - c
    d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    den = np.where(np.abs(va + vb + vc) < 1e-18, 1e-18, va + vb + vc)
    v, w = vb / den, vc / den
    bary = np.c_[1 - v - w, v, w]
    # regions
    r = np.zeros(len(p), int)
    r[(d1 <= 0) & (d2 <= 0)] = 1
    r[(r == 0) & (d3 >= 0) & (d4 <= d3)] = 2
    r[(r == 0) & (d6 >= 0) & (d5 <= d6)] = 3
    m = (r == 0) & (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    t = d1 / np.where(d1 - d3 == 0, 1e-18, d1 - d3)
    bary[m] = np.c_[1 - t, t, np.zeros(len(t))][m]
    r[m] = 4
    m = (r == 0) & (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    t = d2 / np.where(d2 - d6 == 0, 1e-18, d2 - d6)
    bary[m] = np.c_[1 - t, np.zeros(len(t)), t][m]
    r[m] = 5
    m = (r == 0) & (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    t = (d4 - d3) / np.where((d4 - d3) + (d5 - d6) == 0, 1e-18, (d4 - d3) + (d5 - d6))
    bary[m] = np.c_[np.zeros(len(t)), 1 - t, t][m]
    bary[r == 1] = (1, 0, 0)
    bary[r == 2] = (0, 1, 0)
    bary[r == 3] = (0, 0, 1)
    q = bary[:, :1] * a + bary[:, 1:2] * b + bary[:, 2:3] * c
    return bary, np.linalg.norm(p - q, axis=1)


def transfer(P, N, body_P, body_T, body_N, body_W, max_dist=0.03, max_angle=35.0):
    """weights at the closest body point and a confidence mask (distance and normal agreement)"""
    t, b, d = closest_on_surface(P, body_P, body_T)
    tri = body_T[t]
    W = (b[:, :, None] * body_W[tri]).sum(1)
    n = (b[:, :, None] * body_N[tri]).sum(1)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    cos = np.abs((n * N).sum(1))                      # garments may be modelled with either winding
    ok = (d < max_dist) & (cos > np.cos(np.radians(max_angle)))
    return W, ok, d


def outfit_graph(pieces, link=0.012, weld=5e-4, labels=None):
    """edges (i, j, weight) over the concatenated vertices of all pieces: mesh edges, welds (coincident vertices) and
    links from every connected component to the nearest vertex of any OTHER component (same mesh or another) when
    closer than `link`. labels: optional component label per vertex for each piece (-1 = unused)."""
    offs = np.cumsum([0] + [len(P) for P, T in pieces])
    allP = np.vstack([P for P, T in pieces])
    E = []
    lab = []
    for k, (P, T) in enumerate(pieces):
        e = np.vstack([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]) + offs[k]
        E.append(np.c_[e, np.ones(len(e))])
        if labels is not None and labels[k] is not None:
            l_ = np.asarray(labels[k]).copy()
        else:
            _, l_ = geom.components(P, T)
        l_ = np.where(l_ >= 0, l_ + 1_000_000 * k, -1)
        lab.append(l_)
    lab = np.concatenate(lab)
    wid = geom.weld_ids(allP, weld)
    order = np.argsort(wid)
    same = np.where(wid[order][1:] == wid[order][:-1])[0]
    if len(same):
        E.append(np.c_[order[same], order[same + 1], np.full(len(same), 20.0)])
    used = lab >= 0
    for c in np.unique(lab[used]):
        mine = np.where(lab == c)[0]
        others = np.where(used & (lab != c))[0]
        if not len(others):
            continue
        j, d = geom.nearest(allP[mine], allP[others])
        sel = d < link
        E.append(np.c_[mine[sel], others[j[sel]], np.full(sel.sum(), 4.0)])
    E = np.vstack(E)
    return E[:, :2].astype(int), E[:, 2], offs


def inpaint(W0, known, edges, ew, iters=2000, tol=1e-5):
    """harmonic interpolation by weighted Jacobi: unknown vertices -> weighted mean of their neighbours.
    Edges are gathered once into a sorted CSR-like layout, so one iteration is a gather + np.add.reduceat."""
    W = W0.copy()
    n = len(W)
    if not known.any():
        raise ValueError('no confident vertex: the garment is too far from the body to transfer weights')
    src = np.r_[edges[:, 1], edges[:, 0]]
    dst = np.r_[edges[:, 0], edges[:, 1]]
    w = np.r_[ew, ew]
    o = np.argsort(dst, kind='stable')
    src, dst, w = src[o], dst[o], w[o]
    starts = np.r_[0, np.where(np.diff(dst) != 0)[0] + 1]
    rows = dst[starts]
    deg = np.add.reduceat(w, starts)
    free = ~known
    upd = free[rows]
    rows, deg, starts_f = rows[upd], deg[upd], starts
    W[free] = W0[known].mean(0)
    it = 0
    for it in range(iters):
        acc = np.add.reduceat(W[src] * w[:, None], starts_f)[upd]
        new = acc / deg[:, None]
        delta = np.abs(new - W[rows]).max() if len(rows) else 0
        W[rows] = new
        if delta < tol:
            break
    return W, it + 1


def limit(W, k=8):
    """keep the k largest influences per vertex and renormalise"""
    if W.shape[1] > k:
        idx = np.argsort(-W, 1)[:, k:]
        np.put_along_axis(W, idx, 0, 1)
    W = np.clip(W, 0, None)
    return W / np.maximum(W.sum(1, keepdims=True), 1e-12)


def outfit_weights(pieces, body_P, body_T, body_W, max_dist=0.03, max_angle=35.0, link=0.012, k=8,
                   keep_confident=True):
    body_N = geom.vnormals(body_P, body_T)
    allW, allK = [], []
    for P, T in pieces:
        N = geom.vnormals(P, T)
        W, ok, _ = transfer(P, N, body_P, body_T, body_N, body_W, max_dist, max_angle)
        allW.append(W)
        allK.append(ok)
    W0, K = np.vstack(allW), np.concatenate(allK)
    edges, ew, offs = outfit_graph(pieces, link)
    if not keep_confident:
        K = np.zeros_like(K)
    W, iters = inpaint(W0, K, edges, ew)
    W = limit(W, k)
    return [W[offs[i]:offs[i + 1]] for i in range(len(pieces))], {'confident': float(K.mean()), 'iterations': iters}

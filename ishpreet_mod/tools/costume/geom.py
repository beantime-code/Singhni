"""Geometry helpers for costume QA (numpy only)."""
import numpy as np


def weld_ids(P, tol=5e-4):
    """id per vertex: vertices closer than ~tol share an id"""
    key = np.round(np.asarray(P) / tol).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    return inv.ravel()


def components(P, T, tol=5e-4):
    """connected pieces through shared or coincident vertices -> (label per triangle, label per vertex (-1 unused))"""
    wid = weld_ids(P, tol)
    par = np.arange(wid.max() + 1)

    def f(x):
        root = x
        while par[root] != root:
            root = par[root]
        while par[x] != root:
            par[x], x = root, par[x]
        return root
    for a, b, c in wid[T]:
        ra, rb, rc = f(a), f(b), f(c)
        par[rb] = ra
        par[f(rc)] = ra
    roots = np.array([f(x) for x in range(len(par))])
    _, lab = np.unique(roots, return_inverse=True)
    tl = lab[wid[T[:, 0]]]
    vl = np.full(len(P), -1)
    vl[T.ravel()] = lab[wid[T.ravel()]]
    return tl, vl


def boundary_edges(T, wid):
    """edges (in welded ids) used by exactly one triangle, as original vertex index pairs"""
    E = np.vstack([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
    W = np.sort(wid[E], axis=1)
    _, inv, cnt = np.unique(W, axis=0, return_inverse=True, return_counts=True)
    return E[cnt[inv.ravel()] == 1]


def loops(edges, wid):
    """group boundary edges into connected loops -> list of arrays of vertex indices"""
    if not len(edges):
        return []
    a, b = wid[edges[:, 0]], wid[edges[:, 1]]
    ids = np.unique(np.r_[a, b])
    par = {int(i): int(i) for i in ids}

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for x, y in zip(a, b):
        par[f(int(x))] = f(int(y))
    groups = {}
    for e, x in zip(edges, a):
        groups.setdefault(f(int(x)), []).append(e)
    return [np.unique(np.array(g).ravel()) for g in groups.values()]


def vnormals(P, T):
    N = np.zeros_like(P)
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    for k in range(3):
        np.add.at(N, T[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def nearest(Q, P, chunk=2048):
    """(index, distance) of the nearest point of P for every point of Q (chunked brute force)"""
    Q, P = np.asarray(Q, float), np.asarray(P, float)
    idx = np.zeros(len(Q), int)
    dist = np.zeros(len(Q))
    if not len(P):
        return idx, np.full(len(Q), np.inf)
    lo, hi = Q.min(0) - 0.1, Q.max(0) + 0.1
    keep = np.where(((P >= lo) & (P <= hi)).all(1))[0]
    if not len(keep):
        keep = np.arange(len(P))
    Pk = P[keep]
    p2 = (Pk ** 2).sum(1)
    for s in range(0, len(Q), chunk):
        q = Q[s:s + chunk]
        d2 = (q ** 2).sum(1)[:, None] - 2 * q @ Pk.T + p2[None, :]
        j = d2.argmin(1)
        idx[s:s + chunk] = keep[j]
        dist[s:s + chunk] = np.sqrt(np.maximum(d2[np.arange(len(q)), j], 0))
    return idx, dist


def signed_to_surface(Q, P, N):
    """signed distance of Q to the surface sampled by points P with normals N (positive = outside / in front)"""
    j, d = nearest(Q, P)
    s = ((Q - P[j]) * N[j]).sum(1)
    return s, d, j


def uv_raster(UV, T, labels, size=512):
    """rasterize UV triangles into a size x size grid -> (owner (size,size) int, conflict mask,
    {label pair: overlapping pixels}, {label: covered pixels})"""
    owner = np.full((size, size), -1, int)
    conflict = np.zeros((size, size), bool)
    pairs, area = {}, {}
    U = np.asarray(UV) * size
    for t, lab in zip(T, labels):
        tri = U[t]
        x0, y0 = np.floor(tri.min(0)).astype(int)
        x1, y1 = np.ceil(tri.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a, b, c = tri
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / den
        l2 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / den
        inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (1 - l1 - l2 >= -1e-6)
        if not inside.any():
            continue
        yy, xx = np.nonzero(inside)
        yy, xx = yy + y0, xx + x0
        area.setdefault(int(lab), set()).update((yy * size + xx).tolist())
        prev = owner[yy, xx]
        clash = (prev >= 0) & (prev != lab)
        if clash.any():
            conflict[yy[clash], xx[clash]] = True
            flat = yy[clash] * size + xx[clash]
            for p in np.unique(prev[clash]):
                k = tuple(sorted((int(p), int(lab))))
                pairs.setdefault(k, set()).update(flat[prev[clash] == p].tolist())
        owner[yy, xx] = lab
    return owner, conflict, {k: len(v) for k, v in pairs.items()}, {k: len(v) for k, v in area.items()}


def splat(P, T, labels, view, res=0.006, pad=0.05):
    """orthographic z-buffer of triangles seen along `view` (unit vector from camera into the scene) by point splats.
    Returns (label image, facing image: +1 front, -1 back, 0 empty, extent)."""
    view = np.asarray(view, float) / np.linalg.norm(view)
    up = np.array([0, 0, 1.0]) if abs(view[2]) < 0.9 else np.array([0, 1.0, 0])
    ax = np.cross(up, view)
    ax /= np.linalg.norm(ax)
    ay = np.cross(view, ax)
    X, Y, Z = P @ ax, P @ ay, P @ view
    lo = np.array([X.min() - pad, Y.min() - pad])
    W = int((X.max() + pad - lo[0]) / res) + 1
    Hh = int((Y.max() + pad - lo[1]) / res) + 1
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    facing = np.where(fn @ view < 0, 1, -1)
    L = np.linalg.norm(np.stack([P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 1]], P[T[:, 0]] - P[T[:, 2]]], 1), axis=2).max(1)
    n = np.clip(np.ceil(L / res * 1.5).astype(int), 1, 40)
    pix, dep, lab, fac = [], [], [], []
    for k in np.unique(n):
        sel = np.where(n == k)[0]
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1))
        m = (i + j) <= k
        b1, b2 = i[m] / k, j[m] / k
        b0 = 1 - b1 - b2
        tt = T[sel]
        sx = b0[None] * X[tt[:, 0], None] + b1[None] * X[tt[:, 1], None] + b2[None] * X[tt[:, 2], None]
        sy = b0[None] * Y[tt[:, 0], None] + b1[None] * Y[tt[:, 1], None] + b2[None] * Y[tt[:, 2], None]
        sz = b0[None] * Z[tt[:, 0], None] + b1[None] * Z[tt[:, 1], None] + b2[None] * Z[tt[:, 2], None]
        px = ((sx - lo[0]) / res).astype(int)
        py = ((sy - lo[1]) / res).astype(int)
        pix.append((py * W + px).ravel())
        dep.append(sz.ravel())
        lab.append(np.repeat(labels[sel], sx.shape[1]))
        fac.append(np.repeat(facing[sel], sx.shape[1]))
    pix, dep, lab, fac = map(np.concatenate, (pix, dep, lab, fac))
    o = np.lexsort((dep, pix))
    pix, lab, fac = pix[o], lab[o], fac[o]
    first = np.r_[True, pix[1:] != pix[:-1]]
    L_img = np.full(W * Hh, -1)
    F_img = np.zeros(W * Hh, int)
    L_img[pix[first]] = lab[first]
    F_img[pix[first]] = fac[first]
    return L_img.reshape(Hh, W)[::-1], F_img.reshape(Hh, W)[::-1], (W, Hh)


def enclosed_background(mask_bg):
    """background pixels not connected to the image border (see-through holes inside the silhouette)"""
    reach = np.zeros_like(mask_bg)
    reach[0], reach[-1], reach[:, 0], reach[:, -1] = mask_bg[0], mask_bg[-1], mask_bg[:, 0], mask_bg[:, -1]
    while True:
        g = reach.copy()
        g[1:] |= reach[:-1]
        g[:-1] |= reach[1:]
        g[:, 1:] |= reach[:, :-1]
        g[:, :-1] |= reach[:, 1:]
        g &= mask_bg
        if (g == reach).all():
            return mask_bg & ~reach
        reach = g

"""Shared LevelView helpers: the layout element model, footprint rasterization, and
walkability/clearance analysis. Pure Python + numpy/scipy, runs outside the editor.

Coordinate convention: Unreal world units (cm). X = front(0) -> back of store, Y = left/right,
Z = up with the floor top at Z=0. All plots draw X to the right and +Y DOWNWARD so they match
the top-down in-editor capture (ue_capture.py 'top' preset, camera yaw -90).

Layout element (dict):
  id      unique label (becomes the actor label in Unreal)
  kind    box | cyl | bp | light | volume | marker
  cat     category: wall, floor, roof, shelf, counter, display, deco, gameplay, socket, spawn, ...
  pos     [x,y,z]  box/cyl: CENTER; bp/marker/light: actor location
  size    [sx,sy,sz] full dimensions in cm (box/cyl/volume); for bp an approximate footprint
  yaw     degrees
  mat     material key (see MATERIALS) for box/cyl
  bp      class path for kind=bp (e.g. /Game/Defense/BP_DefenseSocket)
  props   {property: value}; "@<id>" strings resolve to spawned actors, lists allowed
  block   bool: blocks walking (default True for box/cyl/bp with size, False otherwise)
  tall    bool: blocks line of sight (default: size z >= 150)
"""
import json
import math

try:
    import numpy as np
except ImportError:  # the editor's embedded Python only needs MATERIALS / layout loading
    np = None

# Flat-color greybox palette: key -> (rgb 0..1, roughness, metallic, emissive)
MATERIALS = {
    "floor_concrete": ((0.42, 0.40, 0.37), 0.8, 0.0, 0.0),
    "floor_wood":     ((0.36, 0.22, 0.12), 0.6, 0.0, 0.0),
    "floor_rug":      ((0.30, 0.10, 0.08), 0.95, 0.0, 0.0),
    "wall_log":       ((0.45, 0.30, 0.17), 0.8, 0.0, 0.0),
    "wall_plaster":   ((0.72, 0.68, 0.58), 0.9, 0.0, 0.0),
    "stone":          ((0.38, 0.38, 0.36), 0.9, 0.0, 0.0),
    "timber":         ((0.30, 0.18, 0.09), 0.7, 0.0, 0.0),
    "roof":           ((0.25, 0.20, 0.16), 0.9, 0.0, 0.0),
    "metal_shelf":    ((0.42, 0.45, 0.44), 0.55, 0.15, 0.0),
    "shelf_green":    ((0.14, 0.28, 0.16), 0.6, 0.0, 0.0),
    "counter":        ((0.40, 0.26, 0.13), 0.5, 0.0, 0.0),
    "counter_top":    ((0.15, 0.15, 0.15), 0.3, 0.2, 0.0),
    "water":          ((0.05, 0.25, 0.35), 0.1, 0.0, 0.3),
    "glass":          ((0.55, 0.75, 0.80), 0.1, 0.0, 0.0),
    "foliage":        ((0.15, 0.35, 0.12), 0.9, 0.0, 0.0),
    "canvas":         ((0.55, 0.50, 0.33), 0.9, 0.0, 0.0),
    "boat_hull":      ((0.70, 0.70, 0.72), 0.3, 0.8, 0.0),
    "boat_accent":    ((0.60, 0.10, 0.08), 0.4, 0.0, 0.0),
    "sign":           ((0.85, 0.65, 0.20), 0.5, 0.0, 2.0),
    "light_fixture":  ((1.00, 0.85, 0.60), 0.5, 0.0, 8.0),
    "fire":           ((1.00, 0.40, 0.10), 0.5, 0.0, 20.0),
    "barrier":        ((0.70, 0.55, 0.10), 0.5, 0.0, 0.0),
    "dock_door":      ((0.35, 0.36, 0.40), 0.5, 0.7, 0.0),
    "door_frame":     ((0.20, 0.12, 0.06), 0.6, 0.0, 0.0),
    # product / prop colors used by the Blender placeholder meshes (PlaceholderAssets/)
    "product_red":    ((0.55, 0.08, 0.06), 0.6, 0.0, 0.0),
    "product_blue":   ((0.08, 0.20, 0.45), 0.6, 0.0, 0.0),
    "product_orange": ((0.85, 0.35, 0.05), 0.6, 0.0, 0.0),
    "product_camo":   ((0.26, 0.28, 0.16), 0.9, 0.0, 0.0),
    "product_tan":    ((0.62, 0.50, 0.34), 0.8, 0.0, 0.0),
    "antler":         ((0.80, 0.74, 0.62), 0.7, 0.0, 0.0),
}

# 2D plot colors by category
CAT_COLORS = {
    "wall": "#5a3d22", "floor": "#d9d2c4", "roof": "#00000000", "shelf": "#2f6b3a",
    "counter": "#8a5a2b", "display": "#3a79a8", "deco": "#9a8f7a", "gameplay": "#c23b22",
    "socket": "#e0a100", "spawn": "#7a1fa2", "light": "#ffe28a", "zone": "#00000000",
    "prop": "#6d6d6d", "rack": "#4d7d5a",
}

SOCKET_COLORS = {"FLOOR": "#e0a100", "WALL": "#d45500", "TURRET_BASE": "#d10000", "OTHER": "#7a7a00"}


def load_layout(path):
    with open(path) as f:
        data = json.load(f)
    if "elements" in data:
        return data
    # a ue_dump_level.py dump -> convert to elements (bounds boxes)
    els = []
    for a in data["actors"]:
        ext = a["bounds_extent"]
        if max(ext) > 20000:
            continue
        cat = "gameplay" if a["class"].startswith("BP_") else "prop"
        if a["bounds_origin"][2] + ext[2] <= 25 and max(ext[0], ext[1]) > 300:
            cat = "floor"  # slab whose top sits at/below floor level
        if "Volume" in a["class"] or a["class"] in ("PlayerStart", "TargetPoint", "Note"):
            cat = "spawn" if a["class"] in ("PlayerStart", "TargetPoint") else "zone"
        if a["class"].startswith("BP_DefenseSocket"):
            cat = "socket"
        for t in a.get("tags", []):
            if t.startswith("LV_"):
                cat = t[3:]
        els.append({"id": a["label"], "kind": "box", "cat": cat,
                    "pos": a["bounds_origin"], "size": [2 * e for e in ext], "yaw": 0,
                    "cls": a["class"], "props": a.get("props", {})})
    return {"name": data["map"], "bounds": None, "elements": els}


def footprint_corners(el):
    """4 XY corners of an element's rotated footprint."""
    x, y = el["pos"][0], el["pos"][1]
    sx, sy = el["size"][0] / 2, el["size"][1] / 2
    a = math.radians(el.get("yaw", 0))
    c, s = math.cos(a), math.sin(a)
    pts = []
    for dx, dy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
        pts.append((x + dx * c - dy * s, y + dx * s + dy * c))
    return pts


def blocks(el):
    if "block" in el:
        return el["block"]
    if el["kind"] in ("box", "cyl") and el["cat"] not in ("floor", "roof", "zone", "light"):
        # things hanging above head height (z bottom > 220) don't block walking
        return (el["pos"][2] - el["size"][2] / 2) < 200
    return False


def is_tall(el):
    if "tall" in el:
        return el["tall"]
    return blocks(el) and (el["pos"][2] + el["size"][2] / 2) >= 150


class Grid:
    """Rasterized top-down occupancy grid over the layout bounds."""

    def __init__(self, bounds, res=25.0):
        (self.x0, self.y0), (self.x1, self.y1) = bounds
        self.res = res
        self.nx = int(math.ceil((self.x1 - self.x0) / res))
        self.ny = int(math.ceil((self.y1 - self.y0) / res))
        self.block = np.zeros((self.ny, self.nx), bool)
        self.tall = np.zeros((self.ny, self.nx), bool)
        xs = self.x0 + (np.arange(self.nx) + 0.5) * res
        ys = self.y0 + (np.arange(self.ny) + 0.5) * res
        self.X, self.Y = np.meshgrid(xs, ys)

    def poly_mask(self, pts):
        # point-in-convex-polygon test for the rotated rectangle
        m = np.ones_like(self.block)
        n = len(pts)
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            cross = (bx - ax) * (self.Y - ay) - (by - ay) * (self.X - ax)
            m &= cross >= 0
        if not m.any():  # winding may be reversed
            m = np.ones_like(self.block)
            for i in range(n):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
                cross = (bx - ax) * (self.Y - ay) - (by - ay) * (self.X - ax)
                m &= cross <= 0
        return m

    def stamp(self, el):
        if el["kind"] == "cyl":
            r = el["size"][0] / 2
            m = (self.X - el["pos"][0]) ** 2 + (self.Y - el["pos"][1]) ** 2 <= r * r
        else:
            m = self.poly_mask(footprint_corners(el))
        self.block |= m
        if is_tall(el):
            self.tall |= m

    def cell(self, x, y):
        return (int((y - self.y0) / self.res), int((x - self.x0) / self.res))

    def world(self, r, c):
        return (self.x0 + (c + 0.5) * self.res, self.y0 + (r + 0.5) * self.res)


def build_grid(layout, res=25.0):
    g = Grid(layout["bounds"], res)
    for el in layout["elements"]:
        if el["kind"] in ("box", "cyl", "bp") and "size" in el and blocks(el):
            g.stamp(el)
    return g


def analyze(layout, res=25.0, agent_radius=45.0):
    """Walkability metrics. Returns (grid, clearance_cm, metrics dict, paths)."""
    from scipy import ndimage

    g = build_grid(layout, res)
    free = ~g.block
    clearance = ndimage.distance_transform_edt(free) * res  # cm to nearest obstacle
    walk = clearance >= agent_radius
    lbl, n = ndimage.label(walk)

    els = layout["elements"]
    anchor = next((e for e in els if e.get("id") == "Hub_Center"), None)
    hub = anchor["pos"][:2] if anchor else [(g.x0 + g.x1) / 2, (g.y0 + g.y1) / 2]
    hr, hc = g.cell(*hub)
    main_lbl = lbl[hr, hc] if 0 <= hr < g.ny and 0 <= hc < g.nx else 0

    walk_area = walk.sum() * res * res / 1e4
    comp_sizes = ndimage.sum(walk, lbl, range(1, n + 1)) * res * res / 1e4 if n else []
    if (not main_lbl) and n:
        main_lbl = int(np.argmax(comp_sizes)) + 1  # no/blocked hub anchor: largest region is "main"
    orphan = [round(float(s), 1) for i, s in enumerate(comp_sizes, 1) if i != main_lbl and s > 1.0]
    orphan_at = []
    for i, s in enumerate(comp_sizes, 1):
        if i != main_lbl and s > 1.0:
            rr, cc = np.nonzero(lbl == i)
            orphan_at.append([int(v) for v in g.world(int(rr.mean()), int(cc.mean()))])
    inside = np.ones_like(walk)
    if layout.get("interior"):
        (ix0, iy0), (ix1, iy1) = layout["interior"]
        r0, c0 = g.cell(ix0, iy0)
        r1, c1 = g.cell(ix1, iy1)
        inside = np.zeros_like(walk)
        inside[max(r0, 0):r1, max(c0, 0):c1] = True

    m = {
        "walkable_m2": round(float(walk_area), 1),
        "open_fight_m2(clear>=3m)": round(float((clearance >= 300).sum() * res * res / 1e4), 1),
        "narrow_m2(corridor<2.4m)": round(float(((clearance < 120) & walk).sum() * res * res / 1e4), 1),
        "disconnected_pockets_m2": orphan,
        "pocket_centers": orphan_at,
    }
    if layout.get("interior"):
        a = res * res / 1e4
        m["interior_walkable_m2"] = round(float((walk & inside).sum() * a), 1)
        m["interior_open_fight_m2"] = round(float(((clearance >= 300) & inside).sum() * a), 1)
        m["interior_narrow_m2"] = round(float(((clearance < 120) & walk & inside).sum() * a), 1)

    # BFS path lengths from breach points / entrances to key targets
    paths = {}
    starts = [e for e in els if e.get("tag") in ("breach",)]
    targets = [e for e in els if e.get("tag") in ("checkout",)]
    if starts and targets:
        dist_maps = {}
        for t in targets:
            dist_maps[t["id"]] = _bfs(walk, g, t["pos"][:2])
        for s in starts:
            best = None
            for t in targets:
                d = _lookup(dist_maps[t["id"]], g, s["pos"][:2])
                if d is not None and (best is None or d < best[0]):
                    best = (d, t["id"])
            paths[s["id"]] = best
            if best:
                paths[s["id"] + "_path"] = _trace(dist_maps[best[1]], g, s["pos"][:2])
        m["breach_to_checkout_m"] = {k: (round(v[0] / 100, 1) if v else None) for k, v in paths.items()
                                     if not k.endswith("_path")}

    # turret coverage: walkable cells in LOS within range of any turret socket
    turrets = [e for e in els if e["cat"] == "socket" and "TURRET" in str(e.get("props", {}).get("SocketType", ""))]
    if turrets:
        cov = np.zeros_like(walk)
        for t in turrets:
            cov |= _los_disc(g, t["pos"][:2], 1500.0)
        m["turret_cover_%"] = round(100.0 * (cov & walk).sum() / max(walk.sum(), 1), 1)
        g.turret_cov = cov & walk
        if layout.get("interior"):
            m["interior_turret_cover_%"] = round(100.0 * (cov & walk & inside).sum() / max((walk & inside).sum(), 1), 1)
    return g, clearance, m, paths


def _bfs(walk, g, xy):
    import heapq
    dist = np.full(walk.shape, np.inf)
    r, c = _nearest_walk(walk, g, xy)
    if r is None:
        return dist
    dist[r, c] = 0
    q = [(0.0, r, c)]
    steps = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1), (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]
    h, w_ = walk.shape
    while q:
        d, r, c = heapq.heappop(q)
        if d > dist[r, c]:
            continue
        for dr, dc, w in steps:
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w_ and walk[rr, cc]:
                nd = d + w * g.res
                if nd < dist[rr, cc]:
                    dist[rr, cc] = nd
                    heapq.heappush(q, (nd, rr, cc))
    return dist


def _nearest_walk(walk, g, xy, max_r=40):
    r0, c0 = g.cell(*xy)
    for rad in range(max_r):
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                r, c = r0 + dr, c0 + dc
                if 0 <= r < walk.shape[0] and 0 <= c < walk.shape[1] and walk[r, c]:
                    return r, c
    return None, None


def _lookup(dist, g, xy):
    walk = np.isfinite(dist)
    r, c = _nearest_walk(walk, g, xy)
    return None if r is None else float(dist[r, c])


def _trace(dist, g, xy):
    walk = np.isfinite(dist)
    r, c = _nearest_walk(walk, g, xy)
    if r is None:
        return []
    pts = [g.world(r, c)]
    for _ in range(20000):
        best = (dist[r, c], r, c)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if 0 <= rr < dist.shape[0] and 0 <= cc < dist.shape[1] and dist[rr, cc] < best[0]:
                    best = (dist[rr, cc], rr, cc)
        if best[1:] == (r, c):
            break
        r, c = best[1], best[2]
        pts.append(g.world(r, c))
    return pts


def _los_disc(g, xy, rng):
    """Cells within rng of xy with no tall blocker on the straight line (ray march)."""
    cov = np.zeros_like(g.block)
    r0, c0 = g.cell(*xy)
    nrays = 360
    steps = int(rng / g.res)
    for i in range(nrays):
        a = 2 * math.pi * i / nrays
        dr, dc = math.sin(a), math.cos(a)
        for s in range(steps):
            r = int(round(r0 + dr * s))
            c = int(round(c0 + dc * s))
            if not (0 <= r < g.ny and 0 <= c < g.nx):
                break
            if g.tall[r, c] and s > 2:
                break
            cov[r, c] = True
    return cov

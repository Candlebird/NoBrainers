"""Render a layout (store_layout.py export, or a ue_dump_level.py dump) as a 2D plan and/or
3D matplotlib view, plus walkability/defense metrics.

Usage:
  python plan.py <layout.json> [--out PNG] [--mode plan|clearance|defense|3d|all]
                 [--labels] [--width PX] [--region x0,y0,x1,y1]

Outputs PNGs next to --out (default Saved/LevelView/<name>_<mode>.png) and prints metrics
as a single compact JSON line (LEVELVIEW_METRICS {...}).
"""
import argparse
import json
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon

import lvlib

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))


def setup_axes(layout, width_px, region=None):
    (x0, y0), (x1, y1) = region or layout["bounds"]
    aspect = (y1 - y0) / (x1 - x0)
    w_in = width_px / 100
    fig, ax = plt.subplots(figsize=(w_in, w_in * aspect + 0.6), dpi=100)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)  # +Y down, matches the top-down capture
    ax.set_aspect("equal")
    step = 500 if (x1 - x0) <= 12000 else 1000
    ax.set_xticks(np.arange(math.floor(x0 / step) * step, x1 + 1, step))
    ax.set_yticks(np.arange(math.floor(y0 / step) * step, y1 + 1, step))
    ax.tick_params(labelsize=6)
    ax.grid(True, lw=0.3, color="#888", alpha=0.5)
    ax.set_xlabel("X (cm)  front -> back", fontsize=7)
    return fig, ax


def draw_elements(ax, layout, labels=False, alpha=1.0):
    els = sorted(layout["elements"], key=lambda e: (e["pos"][2] + e.get("size", [0, 0, 0])[2] / 2))
    for el in els:
        cat = el["cat"]
        if cat in ("roof", "zone", "light") or el["kind"] == "volume":
            continue
        top = el["pos"][2] + el.get("size", [0, 0, 0])[2] / 2
        if el["kind"] in ("box", "cyl") and top > 1200 and cat != "wall":
            continue  # skip high ceiling stuff (beams, clerestory)
        col = lvlib.CAT_COLORS.get(cat, "#999")
        if el.get("mat") in lvlib.MATERIALS and cat not in ("floor",):
            rgb = lvlib.MATERIALS[el["mat"]][0]
            col = tuple(min(1, c * 1.4) for c in rgb)
        if cat == "socket":
            st = str(el.get("props", {}).get("SocketType", "")).split(".")[-1].split(":")[0].strip(" <>")
            ax.add_patch(Circle(el["pos"][:2], 45, color=lvlib.SOCKET_COLORS.get(st, "#e0a100"), zorder=6))
            ax.text(el["pos"][0], el["pos"][1], st[:1], fontsize=4, ha="center", va="center", color="k", zorder=7, clip_on=True)
            continue
        if cat == "spawn" or el["kind"] == "marker" or (el["kind"] == "bp" and "size" not in el):
            mk = {"spawn": ("x", "#7a1fa2"), "gameplay": ("D", "#c23b22")}.get(cat, ("o", "#444"))
            ax.plot(*el["pos"][:2], marker=mk[0], color=mk[1], ms=4, zorder=6)
            if labels:
                ax.text(el["pos"][0] + 40, el["pos"][1], el["id"], fontsize=4, zorder=7, clip_on=True)
            continue
        if el["kind"] == "cyl":
            ax.add_patch(Circle(el["pos"][:2], el["size"][0] / 2, fc=col, ec="k", lw=0.3, alpha=alpha, zorder=3))
        else:
            z = 1 if cat == "floor" else (4 if cat == "gameplay" else 3)
            ax.add_patch(Polygon(lvlib.footprint_corners(el), closed=True, fc=col, ec="k", lw=0.3,
                                 alpha=alpha if cat != "floor" else 0.6, zorder=z))
        if labels and (el.get("label2d") or cat in ("counter", "display", "gameplay")):
            ax.text(el["pos"][0], el["pos"][1], el.get("label2d", el["id"]), fontsize=4.5, ha="center",
                    va="center", zorder=8, color="k",
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.6), clip_on=True)
    for el in layout["elements"]:
        if el.get("tag") == "breach":
            ax.plot(*el["pos"][:2], marker="*", color="red", ms=9, zorder=9, clip_on=True)
            ax.text(el["pos"][0], el["pos"][1] - 120, el["id"], fontsize=5, color="red", ha="center", zorder=9, clip_on=True)


def render(layout, mode, out, labels, width, region):
    g, clr, metrics, paths = lvlib.analyze(layout)
    fig, ax = setup_axes(layout, width, region)
    ext = [g.x0, g.x1, g.y1, g.y0]
    if mode == "clearance":
        img = np.where(clr > 0, np.minimum(clr, 600), np.nan)
        im = ax.imshow(img, extent=ext, cmap="RdYlGn", vmin=0, vmax=600, alpha=0.85, zorder=2, origin="upper")
        cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
        cb.set_label("clearance to nearest obstacle (cm)", fontsize=6)
        cb.ax.tick_params(labelsize=5)
        draw_elements(ax, layout, labels, alpha=0.9)
    elif mode == "defense":
        draw_elements(ax, layout, labels)
        if hasattr(g, "turret_cov"):
            ax.imshow(np.where(g.turret_cov, 1.0, np.nan), extent=ext, cmap="autumn", alpha=0.25, zorder=5,
                      origin="upper")
        for k, v in paths.items():
            if k.endswith("_path") and v:
                p = np.array(v)
                ax.plot(p[:, 0], p[:, 1], "r--", lw=0.8, zorder=8)
    else:
        draw_elements(ax, layout, labels)
    ax.set_title(f"{layout.get('name', '')}  [{mode}]", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=100)
    plt.close(fig)
    return metrics


def render_3d(layout, out, width, elev=35, azim=-60):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(width / 100, width / 100 * 0.7), dpi=100)
    ax = fig.add_subplot(111, projection="3d")
    faces, colors = [], []
    for el in layout["elements"]:
        if el["kind"] not in ("box", "cyl") or el["cat"] in ("roof",) or el.get("hide3d"):
            continue
        cs = lvlib.footprint_corners(el) if el["kind"] == "box" else _circle_pts(el)
        zb = el["pos"][2] - el["size"][2] / 2
        zt = el["pos"][2] + el["size"][2] / 2
        rgb = lvlib.MATERIALS.get(el.get("mat"), ((0.6, 0.6, 0.6),))[0]
        a = 0.25 if el["cat"] == "wall" else 0.9
        bot = [(x, y, zb) for x, y in cs]
        top = [(x, y, zt) for x, y in cs]
        faces.append(top)
        colors.append((*rgb, a))
        for i in range(len(cs)):
            j = (i + 1) % len(cs)
            faces.append([bot[i], bot[j], top[j], top[i]])
            colors.append((*[c * 0.8 for c in rgb], a))
    pc = Poly3DCollection(faces, facecolors=colors, edgecolors=(0, 0, 0, 0.15), linewidths=0.2)
    ax.add_collection3d(pc)
    (x0, y0), (x1, y1) = layout["bounds"]
    zmax = max((e["pos"][2] + e["size"][2] / 2) for e in layout["elements"] if e["kind"] in ("box", "cyl")
               and e["cat"] != "roof")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.set_zlim(0, max(zmax, 100))
    ax.set_box_aspect((x1 - x0, y1 - y0, max(zmax, 100)))
    ax.view_init(elev=elev, azim=azim)
    ax.tick_params(labelsize=5)
    fig.tight_layout()
    fig.savefig(out, dpi=100)
    plt.close(fig)


def _circle_pts(el, n=12):
    r = el["size"][0] / 2
    return [(el["pos"][0] + r * math.cos(2 * math.pi * i / n), el["pos"][1] + r * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("layout")
    ap.add_argument("--out")
    ap.add_argument("--mode", default="plan")
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--width", type=int, default=1100)
    ap.add_argument("--region")
    ap.add_argument("--elev", type=float, default=35)
    ap.add_argument("--azim", type=float, default=-60)
    a = ap.parse_args()
    layout = lvlib.load_layout(a.layout)
    if not layout.get("bounds"):
        xs = [e["pos"][0] for e in layout["elements"]]
        ys = [e["pos"][1] for e in layout["elements"]]
        layout["bounds"] = [[min(xs) - 500, min(ys) - 500], [max(xs) + 500, max(ys) + 500]]
    region = None
    if a.region:
        v = [float(t) for t in a.region.split(",")]
        region = [[v[0], v[1]], [v[2], v[3]]]
    base = a.out or os.path.join(PROJ, "Saved", "LevelView", os.path.basename(a.layout).rsplit(".", 1)[0])
    base = base[:-4] if base.endswith(".png") else base
    os.makedirs(os.path.dirname(base), exist_ok=True)
    modes = ["plan", "clearance", "defense", "3d"] if a.mode == "all" else [a.mode]
    metrics = None
    for m in modes:
        out = f"{base}_{m}.png"
        if m == "3d":
            render_3d(layout, out, a.width, a.elev, a.azim)
        else:
            metrics = render(layout, m, out, a.labels, a.width, region)
        print("wrote", out)
    if metrics:
        print("LEVELVIEW_METRICS " + json.dumps(metrics))


if __name__ == "__main__":
    main()

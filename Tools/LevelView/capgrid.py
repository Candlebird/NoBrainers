"""Offline: draw a world-coordinate grid (and optional layout ids) over an ortho 'top' capture.

Usage: python capgrid.py <cap_name.png> [--step 500] [--layout layout.json] [--width 1100]
Reads the cap_<name>.json sidecar written by ue_capture.py. Writes <cap_name>_grid.png.
"""
import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import lvlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png")
    ap.add_argument("--step", type=float, default=500)
    ap.add_argument("--layout")
    ap.add_argument("--width", type=int, default=1100)
    a = ap.parse_args()
    cam = json.load(open(a.png[:-4] + ".json"))
    if not cam.get("ortho"):
        raise SystemExit("grid overlay only works for ortho (top) captures")
    img = plt.imread(a.png)
    h, w = img.shape[:2]
    cx, cy = cam["center"]
    ow = cam["ortho_width"]
    oh = ow * h / w
    ext = [cx - ow / 2, cx + ow / 2, cy + oh / 2, cy - oh / 2]
    fig, ax = plt.subplots(figsize=(a.width / 100, a.width / 100 * h / w + 0.4), dpi=100)
    ax.imshow(img, extent=ext)
    ax.set_xticks(np.arange(np.ceil(ext[0] / a.step) * a.step, ext[1], a.step))
    ax.set_yticks(np.arange(np.ceil(ext[3] / a.step) * a.step, ext[2], a.step))
    ax.grid(True, color="cyan", lw=0.3, alpha=0.6)
    ax.tick_params(labelsize=6)
    if a.layout:
        for el in lvlib.load_layout(a.layout)["elements"]:
            if el.get("label2d") or el.get("tag") in ("breach", "checkout"):
                ax.text(el["pos"][0], el["pos"][1], el.get("label2d", el["id"]), fontsize=5, color="yellow",
                        ha="center", va="center")
    fig.tight_layout()
    out = a.png[:-4] + "_grid.png"
    fig.savefig(out, dpi=100)
    print("wrote", out)


if __name__ == "__main__":
    main()

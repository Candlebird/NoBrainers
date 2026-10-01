"""Headless Blender: Sledgehammer + Katana (same pipeline/conventions as Tools/LevelView/blender_gear.py FireAxe).
blender --background --factory-startup --python PlaceholderAssets/Weapons/blender_sledge_katana.py
Outputs here: Sledgehammer.blend, Katana.blend, SK_/SM_Wpn_*.fbx. Grip bone at origin, blade/head along UE +Y, up +Z, real size.
Imported by ue_import_sledge_katana.py (reuses Tools/LevelView/ue_import_gear.py logic).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "Tools", "LevelView"))
import blender_gear as g
from blender_placeholders import reset

g.dirs = lambda: (HERE, HERE)
WD, GM, BS, GOLD = "wood_stock", "gunmetal", "blade_steel", "gold"


def w_sledgehammer():
    g.wtube(WD, -10, 80, 0, 1.8)          # handle, 90 cm total
    g.wtube(GM, -10, 16, 0, 2.2)          # darker grip wrap
    g.wbox(BS, 68, 80, -12.5, 12.5, 12)   # 12 x 12 x 25 head
    return (74, 0), "Tip"


def w_katana():
    g.wtube(GM, -10, 15, 0, 1.6)          # wrapped handle (25 cm)
    g.wbox(GOLD, 15, 16.5, -3, 3, 6)      # small guard
    n = 6
    a0, a1 = 16.5, 90.0
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        c0, c1 = 4 * t0 * t0, 4 * t1 * t1
        zc = (c0 + c1) / 2
        hh = 1.5 if i < n - 1 else 0.8
        g.wbox(BS, a0 + (a1 - a0) * t0, a0 + (a1 - a0) * t1 + 0.2, zc - hh, zc + hh, 0.6)
    return (88, 0), "Tip"


for wid, fn in (("Sledgehammer", w_sledgehammer), ("Katana", w_katana)):
    reset()
    end, nm = fn()
    g.finish_weapon(wid, end, nm)
    import bpy
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, f"{wid}.blend"))
    old = os.path.join(HERE, f"Wpn_{wid}.blend")
    for ext in ("", "1"):
        if os.path.exists(old + ext):
            os.remove(old + ext)
print("DONE")

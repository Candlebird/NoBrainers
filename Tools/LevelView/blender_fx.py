"""Headless Blender: small cosmetic FX meshes.

blender --background --factory-startup --python blender_fx.py

Writes <project>/PlaceholderAssets/Blender/SM_FX_<Name>.blend and FBX/SM_FX_<Name>.fbx.
Authored in cm at final size so the Unreal actor can spawn at scale 1:
  ProjectileStreak: 25 cm long along UE +X, 3 cm thick, centred on the pivot (BP_FauxProjectile's root).
Material slot "laser" gets M_LaserProjectile in Unreal (ue_import_fx.py).
"""
import os
import sys

import bmesh
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from blender_gear import dirs, fbx, join_all  # noqa: E402
from blender_placeholders import new_obj, reset  # noqa: E402


def projectile_streak():
    """UV sphere stretched into a 25 x 3 x 3 cm streak along +X."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.5)
    for v in bm.verts:
        v.co.x *= 25.0
        v.co.y *= 3.0
        v.co.z *= 3.0
    new_obj("streak", bm, "laser")


MODELS = {"ProjectileStreak": projectile_streak}


def main():
    bdir, fdir = dirs()
    for name, fn in MODELS.items():
        reset()
        fn()
        full = f"SM_FX_{name}"
        _, slots, lo, hi = join_all(full)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(bdir, full + ".blend"))
        fbx(os.path.join(fdir, full + ".fbx"), {"MESH"})
        print(f"FX {full} min=({lo.x:.1f},{lo.y:.1f},{lo.z:.1f}) max=({hi.x:.1f},{hi.y:.1f},{hi.z:.1f}) slots={slots}")


if __name__ == "__main__":
    main()

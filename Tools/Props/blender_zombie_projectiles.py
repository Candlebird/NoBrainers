"""Headless Blender: Spitter acid projectile + puddle placeholder meshes.

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --factory-startup \
    --python Tools/Props/blender_zombie_projectiles.py

Output: PlaceholderAssets/FBX/Props/SM_SpitterGlob.fbx, SM_AcidPuddle.fbx (mesh only)
        PlaceholderAssets/Blender/SM_SpitterGlob.blend, SM_AcidPuddle.blend

Authored directly in Blender meters at final real-world size (same convention as
Tools/Characters/blender_zombie_anims.py), exported with apply_unit_scale + FBX_SCALE_UNITS so the FBX lands
at the intended cm size in Unreal at import scale 1:1:1. Both meshes use material slot "acid"
(ue_import_zombie_projectiles.py assigns /Game/Props/Zombie/M_Acid to it).
"""
import math
import os
import random

import bmesh
import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BDIR = os.path.join(ROOT, "PlaceholderAssets", "Blender")
FDIR = os.path.join(ROOT, "PlaceholderAssets", "FBX", "Props")


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    return m


def new_obj(name, bm, material):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat(material))
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    return ob


def spitter_glob(diameter=0.30, subdiv=2):
    """Icosphere, 30 cm diameter, origin at center."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=diameter / 2.0)
    return new_obj("SM_SpitterGlob", bm, "acid")


def acid_puddle(diameter=4.0, thickness=0.02, segs=16, jitter=0.18, seed=7):
    """Irregular flat disc, 400 cm diameter, 2 cm thick, origin at bottom center."""
    random.seed(seed)
    radius = diameter / 2.0
    bm = bmesh.new()
    angles = [2.0 * math.pi * i / segs for i in range(segs)]
    radii = [radius * (1.0 + random.uniform(-jitter, jitter)) for _ in range(segs)]
    bottom = [bm.verts.new((radii[i] * math.cos(a), radii[i] * math.sin(a), 0.0)) for i, a in enumerate(angles)]
    top = [bm.verts.new((radii[i] * math.cos(a), radii[i] * math.sin(a), thickness)) for i, a in enumerate(angles)]
    bc = bm.verts.new((0.0, 0.0, 0.0))
    tc = bm.verts.new((0.0, 0.0, thickness))
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
        bm.faces.new((bc, bottom[j], bottom[i]))
        bm.faces.new((tc, top[i], top[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj("SM_AcidPuddle", bm, "acid")


def finish(ob, name):
    os.makedirs(BDIR, exist_ok=True)
    os.makedirs(FDIR, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BDIR, f"{name}.blend"))
    bpy.ops.export_scene.fbx(filepath=os.path.join(FDIR, f"{name}.fbx"), use_selection=True,
                             object_types={"MESH"}, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False)
    b = ob.bound_box
    xs = [v[0] for v in b]
    ys = [v[1] for v in b]
    zs = [v[2] for v in b]
    print(f"PROP {name} size_m=({max(xs)-min(xs):.3f},{max(ys)-min(ys):.3f},{max(zs)-min(zs):.3f})")


def main():
    reset()
    finish(spitter_glob(), "SM_SpitterGlob")
    reset()
    finish(acid_puddle(), "SM_AcidPuddle")
    print("PROJECTILES_DONE")


main()

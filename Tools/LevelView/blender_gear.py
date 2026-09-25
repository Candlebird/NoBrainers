"""Headless Blender: weapon + sellable item placeholder models at real-world size.

blender --background --factory-startup --python blender_gear.py -- [only=Pistol,CannedBeans,...] [axis=y|x]

Writes to <project>/PlaceholderAssets:
  Blender/Wpn_<ID>.blend, FBX/SK_Wpn_<ID>.fbx (2-bone skeletal: Grip root -> Muzzle/Tip), FBX/SM_Wpn_<ID>.fbx
  Blender/SM_Item_<ID>.blend, FBX/SM_Item_<ID>.fbx
Unlike blender_placeholders.py, nothing is normalized: models are authored in cm at real size.
  Weapons: pivot = grip, barrel/blade along UE +Y (axis=y, default) or UE +X (axis=x), up +Z.
           Note Blender->UE FBX import flips Y, so UE +Y is authored along Blender -Y.
  Items:   pivot = bottom centre, front faces +X.
Material slot names are lvlib.MATERIALS keys; ue_import_gear.py maps them to MI_LV_<key>.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from blender_placeholders import mat, new_obj, reset  # noqa: E402

PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(PROJ, "PlaceholderAssets")
AXIS = "y"


# ---------------------------------------------------------------- primitives (cm, final UE-ish frame)
def _xform(ob, loc, rot=None):
    if rot:
        ob.rotation_euler = rot
    ob.location = loc
    return ob


def cube(material, x0, x1, y0, y1, z0, z1):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((v.co.x + 0.5) * (x1 - x0) + x0, (v.co.y + 0.5) * (y1 - y0) + y0,
                       (v.co.z + 0.5) * (z1 - z0) + z0))
    return new_obj("cube", bm, material)


def tube(material, base, h, r0, r1=None, rot=None, segs=12):
    """Cylinder/cone of height h along local +Z from `base`, optionally rotated about its base."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r0, radius2=r0 if r1 is None else r1, depth=h)
    for v in bm.verts:
        v.co.z += h / 2
    return _xform(new_obj("tube", bm, material), base, rot)


def ball(material, c, r):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=r)
    return _xform(new_obj("ball", bm, material), c)


def ring(material, c, major, minor, rot=None):
    bm = bmesh.new()
    n, m = 14, 6
    rings = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rings.append([bm.verts.new(((major + minor * math.cos(b)) * math.cos(a),
                                    (major + minor * math.cos(b)) * math.sin(a), minor * math.sin(b)))
                      for b in (2 * math.pi * j / m for j in range(m))])
    for i in range(n):
        a, b = rings[i], rings[(i + 1) % n]
        for j in range(m):
            bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _xform(new_obj("ring", bm, material), c, rot)


# ---------------------------------------------------------------- weapon frame: L = forward along the weapon
def _pos(L, z, w=0.0):
    """Weapon-local (width, length, height) cm -> Blender coords."""
    if AXIS == "x":
        return (L, w, z)
    return (w, -L, z)


def wbox(material, L0, L1, z0, z1, w, off=0.0):
    a, b = _pos(L0, z0, off - w / 2), _pos(L1, z1, off + w / 2)
    return cube(material, min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]), z0, z1)


def wtube(material, L0, L1, z, r0, r1=None, off=0.0, segs=12):
    rot = (0.0, math.pi / 2, 0.0) if AXIS == "x" else (math.pi / 2, 0.0, 0.0)  # local +Z -> forward
    return tube(material, _pos(L0, z, off), L1 - L0, r0, r1, rot, segs)


# ---------------------------------------------------------------- join / export
def join_all(name):
    obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me = ob.data
    for v in me.vertices:  # authored in cm, Blender units are m
        v.co *= 0.01
    uniq, remap = [], {}
    for i, m in enumerate(me.materials):
        if m.name not in uniq:
            uniq.append(m.name)
        remap[i] = uniq.index(m.name)
    new_idx = [remap[p.material_index] for p in me.polygons]
    me.materials.clear()  # clear() resets every polygon's material_index to 0
    for nm in uniq:
        me.materials.append(bpy.data.materials[nm])
    for p, i in zip(me.polygons, new_idx):
        p.material_index = i
        p.use_smooth = False
    me.update()
    ob.name = me.name = name
    lo = Vector((min(v.co[i] for v in me.vertices) for i in range(3))) * 100
    hi = Vector((max(v.co[i] for v in me.vertices) for i in range(3))) * 100
    return ob, uniq, lo, hi


def fbx(path, types):
    bpy.ops.export_scene.fbx(filepath=path, use_selection=False, object_types=types, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE", add_leaf_bones=False,
                             bake_anim=False, use_armature_deform_only=False, armature_nodetype="NULL")


def dirs():
    b, f = os.path.join(OUT, "Blender"), os.path.join(OUT, "FBX")
    os.makedirs(b, exist_ok=True)
    os.makedirs(f, exist_ok=True)
    return b, f


def finish_item(item_id):
    ob, slots, lo, hi = join_all(f"SM_Item_{item_id}")
    bdir, fdir = dirs()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(bdir, f"SM_Item_{item_id}.blend"))
    fbx(os.path.join(fdir, f"SM_Item_{item_id}.fbx"), {"MESH"})
    print(f"GEAR SM_Item_{item_id} cm=({hi.x - lo.x:.1f},{hi.y - lo.y:.1f},{hi.z - lo.z:.1f}) "
          f"zmin={lo.z:.1f} slots={slots}")


def finish_weapon(wid, end, end_name):
    ob, slots, lo, hi = join_all(f"SM_Wpn_{wid}")
    bdir, fdir = dirs()
    fbx(os.path.join(fdir, f"SM_Wpn_{wid}.fbx"), {"MESH"})
    # skeletal: armature object named "Armature" so UE drops it and Grip becomes the root bone
    arm = bpy.data.armatures.new("Armature")
    arm_ob = bpy.data.objects.new("Armature", arm)
    bpy.context.scene.collection.objects.link(arm_ob)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm_ob
    arm_ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    grip = arm.edit_bones.new("Grip")
    grip.head = (0, 0, 0)
    grip.tail = Vector(_pos(5, 0)) * 0.01
    tip = arm.edit_bones.new(end_name)
    tip.head = Vector(_pos(end[0], end[1])) * 0.01
    tip.tail = Vector(_pos(end[0] + 5, end[1])) * 0.01
    tip.parent = grip
    bpy.ops.object.mode_set(mode="OBJECT")
    vg = ob.vertex_groups.new(name="Grip")
    vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
    ob.parent = arm_ob
    ob.modifiers.new("Armature", "ARMATURE").object = arm_ob
    ob.name = ob.data.name = f"SK_Wpn_{wid}"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(bdir, f"Wpn_{wid}.blend"))
    fbx(os.path.join(fdir, f"SK_Wpn_{wid}.fbx"), {"ARMATURE", "MESH"})
    print(f"GEAR Wpn_{wid} cm=({hi.x - lo.x:.1f},{hi.y - lo.y:.1f},{hi.z - lo.z:.1f}) "
          f"min=({lo.x:.0f},{lo.y:.0f},{lo.z:.0f}) max=({hi.x:.0f},{hi.y:.0f},{hi.z:.0f}) slots={slots}")


# ---------------------------------------------------------------- weapons (cm; L forward, z up, grip at 0)
GM, WD, BS, RED, CAMO = "gunmetal", "wood_stock", "blade_steel", "product_red", "product_camo"


def w_pistol():
    wbox(GM, -4, 18, 3, 8, 3)
    wbox(GM, -3, 12, 0, 3, 3.2)
    wbox(GM, -4, 1, -7, 1, 3.4)
    wbox(GM, 1, 5, -2, -1, 1)
    return (18, 6), "Muzzle"


def w_magnum():
    wtube(GM, 7, 28, 7, 1.2)
    wbox(GM, -3, 8, 2, 9, 3)
    wtube(GM, 1, 7, 5.5, 2.6, segs=8)
    wbox(WD, -5, 0, -7, 3, 3.4)
    return (26, 7), "Muzzle"


def w_sawedoff():
    wtube(GM, 2, 38, 5, 1.5, off=-1.6)
    wtube(GM, 2, 38, 5, 1.5, off=1.6)
    wbox(GM, -6, 3, 2, 7, 5)
    wbox(WD, 6, 20, 1.5, 4, 4.5)
    wbox(WD, -12, -5, -6, 5, 3.5)
    return (38, 5), "Muzzle"


def w_smg():
    wbox(GM, -12, 20, 2, 9, 4)
    wtube(GM, 20, 30, 6, 1)
    wbox(GM, 3, 7, -12, 2, 2.5)
    wbox(GM, -5, 0, -8, 2, 3)
    return (30, 6), "Muzzle"


def w_rifle():
    wbox(CAMO, -10, 30, 1, 9, 5)
    wtube(GM, 30, 62, 6, 1)
    wbox(GM, 8, 14, -11, 1, 3)
    wbox(GM, -3, 2, -8, 1, 3)
    wbox(CAMO, -28, -10, -3, 7, 4)
    return (62, 6), "Muzzle"


def w_shotgun():
    wbox(GM, -6, 12, 1, 8, 5)
    wtube(GM, 12, 70, 6, 1.4)
    wtube(GM, 12, 60, 3, 1.2)
    wbox(WD, 25, 42, 0.5, 5, 4.5)
    wbox(WD, -30, -6, -8, 6, 4)
    return (70, 5), "Muzzle"


def w_leveraction():
    wbox(GM, -6, 10, 1, 8, 4.5)
    wtube(GM, 10, 68, 6, 1.1)
    wtube(GM, 10, 55, 3.5, 0.9)
    wbox(WD, 12, 35, 1.5, 5, 4)
    wbox(GM, -4, 6, -5, -4, 1)
    wbox(GM, -4, -3, -5, 1, 1)
    wbox(GM, 5, 6, -5, 1, 1)
    wbox(WD, -27, -6, -8, 6, 4)
    return (68, 5), "Muzzle"


def w_longrifle():
    wbox(CAMO, -10, 30, 1, 8, 5)
    wtube(GM, 30, 82, 5.5, 1.1)
    wtube(GM, -4, 22, 11, 2)
    wbox(GM, 0, 2, 8, 10, 1.5)
    wbox(GM, 16, 18, 8, 10, 1.5)
    wbox(CAMO, -32, -10, -8, 7, 4)
    wbox(GM, -3, 2, -6, 1, 3)
    return (82, 6), "Muzzle"


def w_bat():
    wtube(WD, -15, 70, 0, 1.6, 3.5)
    wtube(WD, -16, -15, 0, 2.2)
    return (70, 0), "Tip"


def w_pipewrench():
    wbox(GM, -8, 30, -1.5, 1.5, 3)
    wbox(RED, 26, 34, -2, 8, 4)
    wbox(GM, 30, 38, 6, 10, 4)
    return (32, 0), "Tip"


def w_machete():
    wbox("counter_top", -6, 6, -1.5, 1.5, 2.2)
    wbox("counter_top", 6, 7, -2, 2.5, 2)
    wbox(BS, 7, 50, -2, 5, 0.5)
    wbox(BS, 50, 54, 0, 4, 0.5)
    return (48, 0), "Tip"


def w_fireaxe():
    wtube(WD, -12, 70, 0, 1.8)
    wbox(RED, 60, 70, -3, 5, 4)
    wbox(BS, 61, 69, -13, -3, 1.2)
    wbox(RED, 62, 68, 5, 12, 2)
    return (68, 0), "Tip"


def w_canoepaddle():
    wbox(WD, -22, -19, -5, 5, 3)
    wtube(WD, -19, 92, 0, 1.5)
    wbox(WD, 90, 118, -9, 9, 1.5)
    return (120, 0), "Tip"


WEAPONS = {"Pistol": w_pistol, "Magnum": w_magnum, "SawedOff": w_sawedoff, "SMG": w_smg, "Rifle": w_rifle,
           "Shotgun": w_shotgun, "LeverAction": w_leveraction, "LongRifle": w_longrifle, "Bat": w_bat,
           "PipeWrench": w_pipewrench, "Machete": w_machete, "FireAxe": w_fireaxe, "CanoePaddle": w_canoepaddle}


# ---------------------------------------------------------------- items (cm; bottom-centre pivot, front +X)
def bx(material, sx, sy, sz, z0=0.0, cx=0.0, cy=0.0):
    return cube(material, cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z0, z0 + sz)


def up(material, r, z0, z1, r1=None, cx=0.0, cy=0.0, segs=12):
    return tube(material, (cx, cy, z0), z1 - z0, r, r1, None, segs)


FRONT = (0.0, math.pi / 2, 0.0)  # local +Z -> +X (disc faces the front)


def i_cannedbeans():
    up("metal_shelf", 4, 0, 11)
    up(RED, 4.05, 1.5, 9.5)


def i_energybar():
    bx("product_yellow", 8, 14, 6)


def i_spoiledmeat():
    bx("product_white", 14, 18, 1.5)
    bx("spoiled", 10, 13, 3.5, 1.5)


def i_bag(material):
    bx(material, 5, 14, 16)
    bx(material, 3, 14, 2, 16)


def i_campcoffee():
    up("timber", 5, 0, 13)
    up("timber", 4.6, 13, 14)


def i_bandage():
    up("product_white", 3.5, 0, 7)


def i_medkit():
    bx("product_white", 10, 24, 16)
    bx(RED, 0.4, 3, 10, 3, cx=5.2)
    bx(RED, 0.4, 10, 3, 6.5, cx=5.2)


def i_painkillers():
    up("product_orange", 2.5, 0, 8)
    up("product_white", 2.6, 8, 10)


def i_insectrepellent():
    up("product_yellow", 3, 0, 15)
    up("product_green", 2.6, 15, 18)


def i_nails():
    bx("product_tan", 6, 10, 5)


def i_scrapmetal():
    cube("metal_shelf", -8, 4, -10, 6, 1, 2.2).rotation_euler = (0.1, 0.0, 0.2)
    cube("metal_shelf", -3, 8, -6, 10, 3.5, 4.7).rotation_euler = (-0.25, 0.1, -0.3)
    cube("metal_shelf", -6, 6, -9, 3, 5.5, 6.7).rotation_euler = (0.2, -0.2, 0.5)


def i_ducttape():
    ring("metal_shelf", (0, 0, 2.5), 3, 2.5)


def i_flashlight():
    rot = (math.pi / 2, 0.0, 0.0)  # local +Z -> -Y
    tube("product_yellow", (0, 10, 3), 15, 2.3, rot=rot)
    tube(GM, (0, -5, 3), 5, 2.3, 3, rot=rot)


def i_paracord():
    ring("product_orange", (0, 0, 2.5), 4.5, 2.5)


def i_goldwatch():
    bx("counter_top", 6, 8, 1.5)
    tube("gold", (-0.5, 0, 4), 1, 2.5, rot=FRONT)


def i_vintagecoin():
    bx("counter_top", 5, 6, 1)
    tube("gold", (-0.2, 0, 3), 0.4, 2, rot=FRONT)


def i_luckycharm():
    up("product_white", 1.2, 0, 5.5, segs=8)
    ring("gold", (0, 0, 6.3), 0.7, 0.2, rot=FRONT)


def i_bigfoot():
    up("timber", 4, 0, 2)
    up("product_green", 2.8, 2, 15, 2.4)
    ball("product_green", (0, 0, 17.5), 2.5)


def i_antlertrophy():
    bx("counter_top", 1.5, 16, 20, cx=-0.75)
    for s in (-1, 1):
        tube("antler", (0, s * 2, 12), 12, 1.0, 0.5, rot=(-s * 0.9, 0.4, 0.0), segs=6)
        tube("antler", (0, s * 7, 17), 4, 0.5, 0.25, rot=(-s * 0.3, 0.3, 0.0), segs=6)


def i_ammo(material, sx, sy, sz):
    bx(material, sx, sy, sz)
    bx("product_white", sx + 0.2, sy * 0.5, sz * 0.4, sz * 0.3)


ITEMS = {
    "CannedBeans": i_cannedbeans, "EnergyBar": i_energybar, "SpoiledMeat": i_spoiledmeat,
    "BeefJerky": lambda: i_bag("product_tan"), "TrailMix": lambda: i_bag("product_green"),
    "CampCoffee": i_campcoffee, "Bandage": i_bandage, "MedKit": i_medkit, "Painkillers": i_painkillers,
    "InsectRepellent": i_insectrepellent, "Nails": i_nails, "ScrapMetal": i_scrapmetal, "DuctTape": i_ducttape,
    "Flashlight": i_flashlight, "ParacordBundle": i_paracord, "GoldWatch": i_goldwatch,
    "VintageCoin": i_vintagecoin, "LuckyCharm": i_luckycharm, "BigfootFigurine": i_bigfoot,
    "AntlerTrophy": i_antlertrophy, "PistolAmmo": lambda: i_ammo("product_blue", 8, 12, 6),
    "RifleAmmo": lambda: i_ammo("product_green", 8, 14, 7), "ShotgunShells": lambda: i_ammo(RED, 9, 15, 8),
}


def main():
    global AXIS
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = dict(a.split("=", 1) for a in argv if "=" in a)
    only = set(flags["only"].split(",")) if "only" in flags else None
    AXIS = flags.get("axis", "y")
    for wid, fn in WEAPONS.items():
        if only and wid not in only:
            continue
        reset()
        end, end_name = fn()
        finish_weapon(wid, end, end_name)
    for iid, fn in ITEMS.items():
        if only and iid not in only:
            continue
        reset()
        fn()
        finish_item(iid)
    print("GEAR_DONE")


main()

"""Headless Blender: generate low-poly placeholder props for Map_Store_Outdoors.

blender --background --factory-startup --python blender_placeholders.py -- [out_dir] [only=Name1,Name2]

Default out_dir: <project>/PlaceholderAssets. Writes Blender/SM_PH_<Name>.blend and FBX/SM_PH_<Name>.fbx.

Convention (so a model can replace a greybox Cube/Cylinder with no layout math):
every model is normalized to fill exactly a 1 m cube centered on the origin (pivot at bbox center),
same as /Engine/BasicShapes/Cube. The layout's element "size" then scales it, so author each model at
roughly its in-game proportions to avoid visible stretching. The long axis is Blender +X.
Material slot names are lvlib.MATERIALS keys; ue_import_placeholders.py maps them to MI_LV_<key>.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))

PRODUCTS = ["product_red", "product_blue", "product_orange", "product_camo", "canvas", "product_tan"]


# ---------------------------------------------------------------- scene helpers
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
    ob["ph_mat"] = material  # survives curve<->mesh conversion, which drops material slots
    return ob


def box(material, cx, cy, cz, sx, sy, sz, rz=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
        x, y = v.co.x, v.co.y
        c, s = math.cos(rz), math.sin(rz)
        v.co.x, v.co.y = x * c - y * s + cx, x * s + y * c + cy
        v.co.z += cz
    return new_obj("box", bm, material)


def cyl(material, cx, cy, z0, z1, r0, r1=None, segs=12, rot=None):
    """Cylinder/cone along +Z from z0 to z1 (optionally rotated by euler `rot` around its base)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r0, radius2=r0 if r1 is None else r1,
                          depth=z1 - z0)
    for v in bm.verts:
        v.co.z += (z1 - z0) / 2
    ob = new_obj("cyl", bm, material)
    if rot:
        ob.rotation_euler = rot
    ob.location = (cx, cy, z0)
    return ob


def loft(material_for_seg, sections, name="loft"):
    """Hull loft. sections: list of (x, [(y, z), ...]) with the same point count, ordered around the profile.
    material_for_seg(i) -> slot name for the faces between profile points i and i+1. Ends are capped."""
    bm = bmesh.new()
    rings = [[bm.verts.new((x, y, z)) for (y, z) in pts] for x, pts in sections]
    names = []
    n = len(rings[0])

    def slot(nm):
        if nm not in names:
            names.append(nm)
        return names.index(nm)

    for a, b in zip(rings, rings[1:]):
        for i in range(n - 1):
            f = bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
            f.material_index = slot(material_for_seg(i))
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        try:
            f = bm.faces.new(list(reversed(ring)) if rev else ring)
            f.material_index = slot(material_for_seg(-1))
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for nm in names:
        ob.data.materials.append(mat(nm))
    return ob


def finish(name, out_dir):
    """Join all meshes, normalize to a centered 1 m cube, save .blend + FBX."""
    obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in obs:
        if (not o.data.materials or any(m is None for m in o.data.materials)) and o.get("ph_mat"):
            o.data.materials.clear()
            o.data.materials.append(mat(o["ph_mat"]))
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me = ob.data
    lo = Vector((min(v.co[i] for v in me.vertices) for i in range(3)))
    hi = Vector((max(v.co[i] for v in me.vertices) for i in range(3)))
    size = hi - lo
    ctr = (lo + hi) / 2
    for v in me.vertices:
        v.co = Vector(((v.co[i] - ctr[i]) / size[i] for i in range(3)))
    # merge duplicate material slots (join keeps one slot per source object)
    uniq = []
    remap = {}
    for i, m in enumerate(me.materials):
        if m.name not in uniq:
            uniq.append(m.name)
        remap[i] = uniq.index(m.name)
    new_idx = [remap[p.material_index] for p in me.polygons]
    me.materials.clear()  # note: clear() resets every polygon's material_index to 0
    for nm in uniq:
        me.materials.append(bpy.data.materials[nm])
    for p, i in zip(me.polygons, new_idx):
        p.material_index = i
    me.update()
    for p in me.polygons:
        p.use_smooth = False
    ob.name = me.name = f"SM_PH_{name}"
    bdir, fdir = os.path.join(out_dir, "Blender"), os.path.join(out_dir, "FBX")
    os.makedirs(bdir, exist_ok=True)
    os.makedirs(fdir, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(bdir, f"SM_PH_{name}.blend"))
    bpy.ops.export_scene.fbx(filepath=os.path.join(fdir, f"SM_PH_{name}.fbx"), use_selection=False,
                             object_types={"MESH"}, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False)
    print(f"PH_MODEL SM_PH_{name} tris={sum(len(p.vertices) - 2 for p in me.polygons)} "
          f"authored_size_m=({size.x:.2f},{size.y:.2f},{size.z:.2f}) slots={uniq}")


# ---------------------------------------------------------------- models
def m_pine():
    """Foliage only (the layout keeps a separate collidable trunk). ~0.58 : 1 width:height."""
    rnd = random.Random(1)
    tiers = [(0.0, 2.10), (1.5, 1.70), (3.0, 1.30), (4.4, 0.85)]
    for z, r in tiers:
        c = cyl("foliage", 0, 0, z, z + 2.8, r, 0.0, segs=9)
        c.rotation_euler = (0, 0, rnd.uniform(0, 1))
        me = c.data
        for v in me.vertices:  # ragged, slightly drooping skirt
            if v.co.z < 0.05 and (v.co.x or v.co.y):
                v.co.z -= rnd.uniform(0.0, 0.25)
                v.co.x *= rnd.uniform(0.9, 1.05)
                v.co.y *= rnd.uniform(0.9, 1.05)
    cyl("timber", 0, 0, -0.25, 0.4, 0.18, 0.15, segs=6)  # bit of trunk under the skirt


def m_log_column():
    """Peeled log column with vertical flutes and timber collars. 0.6 x 0.6 x 10."""
    rnd = random.Random(2)
    bm = bmesh.new()
    segs, rings, h = 20, 12, 10.0
    grid = []
    for j in range(rings + 1):
        z = h * j / rings
        row = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            r = 0.27 + 0.012 * math.sin(7 * a + j * 0.4) + rnd.uniform(-0.006, 0.006)
            row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        grid.append(row)
    for j in range(rings):
        for i in range(segs):
            bm.faces.new((grid[j][i], grid[j][(i + 1) % segs], grid[j + 1][(i + 1) % segs], grid[j + 1][i]))
    bm.faces.new(list(reversed(grid[0])))
    bm.faces.new(grid[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    new_obj("log", bm, "wall_log")
    cyl("timber", 0, 0, 0.0, 0.35, 0.30, 0.29, segs=12)
    cyl("timber", 0, 0, 9.65, 10.0, 0.29, 0.30, segs=12)


def _stock_shelf(rnd, x0, x1, y0, y1, z, zmax, flip):
    """Fill a shelf strip with product boxes (y0..y1 depth band, flush to the aisle-side edge)."""
    x = x0 + 0.03
    while x < x1 - 0.12:
        w = rnd.uniform(0.12, 0.34)
        if x + w > x1 - 0.03:
            break
        if rnd.random() < 0.12:  # gap / sold out
            x += w
            continue
        d = rnd.uniform(0.6, 0.95) * (y1 - y0)
        hgt = rnd.uniform(0.35, 0.9) * (zmax - z)
        yc = (y1 - d / 2) if not flip else (y0 + d / 2)
        box(rnd.choice(PRODUCTS), x + w / 2, yc, z + hgt / 2, w * 0.95, d, hgt)
        x += w


def m_gondola(length=7.0, depth=1.2, h=1.8, double=True, seed=3):
    """Double-sided store gondola with stocked shelves, long axis +X."""
    rnd = random.Random(seed)
    half = depth / 2
    box("metal_shelf", 0, 0, 0.07, length, depth, 0.14)                    # kick base
    box("metal_shelf", 0, 0 if double else half - 0.03, h / 2, length, 0.05, h)  # spine / pegboard
    box("shelf_green", 0, 0 if double else half - 0.03, h - 0.08, length, 0.07, 0.16)  # header strip
    n_up = max(2, round(length / 1.2))
    for k in range(n_up + 1):
        x = -length / 2 + length * k / n_up
        box("metal_shelf", x, 0, h / 2, 0.04, depth if double else 0.1, h)
    levels = [0.14, 0.55, 0.95, 1.35] if h >= 1.7 else [0.14, 0.55, 0.95]
    sides = (-1, 1) if double else (-1,)
    for s in sides:
        y0, y1 = (0.03, half) if s > 0 else (-half, -0.03)
        if not double:
            y0, y1 = -half, half - 0.06
        for li, z in enumerate(levels):
            if li:
                box("metal_shelf", 0, (y0 + y1) / 2, z, length, y1 - y0, 0.025)
            ztop = (levels[li + 1] if li + 1 < len(levels) else h - 0.2) - 0.03
            for k in range(n_up):
                bx0 = -length / 2 + length * k / n_up + 0.03
                bx1 = -length / 2 + length * (k + 1) / n_up - 0.03
                _stock_shelf(rnd, bx0, bx1, y0, y1, z + 0.013, ztop, flip=(s > 0))


def m_wall_shelf():
    m_gondola(length=16.0, depth=0.8, h=2.4, double=True, seed=4)


def m_bass_boat():
    """Bass boat with red stripe, console, seats and outboard. 6 x 2 x 2.2."""
    secs = []
    n = 14
    for k in range(n + 1):
        t = k / n
        x = -2.6 + 5.1 * t
        bow = max(0.0, (t - 0.55) / 0.45)
        hw = 1.0 * (1 - 0.92 * bow ** 1.8)
        keel = 0.05 + 0.45 * bow ** 2
        chine = 0.35 + 0.3 * bow ** 2
        top = 1.2
        secs.append((x, [(0.0, top), (-hw, top), (-hw, 0.95), (-hw, 0.85), (-hw * 0.95, chine), (0.0, keel),
                         (hw * 0.95, chine), (hw, 0.85), (hw, 0.95), (hw, top), (0.0, top)]))
    loft(lambda i: "boat_accent" if i in (2, 7) else ("boat_hull" if i >= 0 else "boat_hull"), secs, "hull")
    box("counter_top", 0.2, 0, 1.22, 4.0, 1.6, 0.04)                 # carpeted deck
    box("boat_accent", 0.6, 0.45, 1.6, 0.6, 0.6, 0.8)               # console
    box("glass", 0.85, 0.45, 2.1, 0.08, 0.6, 0.3, rz=0.0)
    for x in (-0.3, -1.3):
        box("counter_top", x, 0.35, 1.45, 0.45, 0.45, 0.45)
        box("counter_top", x, -0.35, 1.45, 0.45, 0.45, 0.45)
    box("counter_top", -2.85, 0, 1.25, 0.4, 0.35, 0.9)              # outboard
    box("counter_top", -2.9, 0, 0.55, 0.12, 0.1, 0.6)


def m_canoe():
    """Open-look canoe (closed hull + timber gunwales and thwarts). 5 x 0.9 x 0.6."""
    secs = []
    n = 16
    for k in range(n + 1):
        t = k / n
        x = -2.5 + 5.0 * t
        e = abs(2 * t - 1)
        hw = 0.45 * math.sqrt(max(0.0, 1 - e ** 2.4)) + 0.004
        sheer = 0.45 + 0.15 * e ** 3
        keel = 0.0 + 0.2 * e ** 4
        secs.append((x, [(0.0, sheer - 0.05), (-hw, sheer), (-hw * 0.9, 0.18 + keel * 0.5), (0.0, keel),
                         (hw * 0.9, 0.18 + keel * 0.5), (hw, sheer), (0.0, sheer - 0.05)]))
    loft(lambda i: "counter_top" if i in (0, 5, -1) else "boat_accent", secs, "canoe")
    for x in (-1.0, 0.0, 1.0):
        box("timber", x, 0, 0.44, 0.08, 0.85, 0.04)


def m_tent():
    """Dome tent with rainfly door and poles. 3.5 x 3.5 x 2.2."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.75)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    for v in bm.verts:
        v.co.z *= 2.2 / 1.75
    # fill the base hole so the mesh is closed
    edges = [e for e in bm.edges if e.is_boundary]
    bmesh.ops.edgeloop_fill(bm, edges=edges)
    new_obj("tent", bm, "canvas")
    box("door_frame", 1.62, 0, 0.6, 0.25, 0.9, 1.2)                  # door / vestibule
    for a in (math.pi / 4, -math.pi / 4):
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=False, segments=24, radius=1.78)
        for v in bm.verts:
            x, y = v.co.x, v.co.y
            v.co.x, v.co.y, v.co.z = x * math.cos(a), x * math.sin(a), max(0.0, y) * 2.2 / 1.75
        new_obj("pole_path", bm, "metal_shelf")
    # poles are edges only; turn them into thin tubes
    for o in [o for o in bpy.context.scene.objects if o.name.startswith("pole_path")]:
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.convert(target="CURVE")
        o.data.bevel_depth = 0.02
        o.data.bevel_resolution = 1
        bpy.ops.object.convert(target="MESH")
        o.select_set(False)
    box("shelf_green", 0, 0, 0.02, 3.5, 3.5, 0.04)                   # footprint tarp


def m_boulder(seed):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    off = Vector((seed * 3.1, seed * 1.7, seed * 0.9))
    for v in bm.verts:
        n = noise.noise(v.co * 1.3 + off) * 0.28 + noise.noise(v.co * 3.2 + off) * 0.08
        v.co *= 1.0 + n
        v.co.z = max(v.co.z, -0.55)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    new_obj("rock", bm, "stone")


def m_chandelier():
    """Antler chandelier: timber ring, bone tines, warm bulbs. 2.2 x 2.2 x ~0.45."""
    rnd = random.Random(5)
    bm = bmesh.new()
    ring_r = 1.0
    bmesh.ops.create_circle(bm, cap_ends=False, segments=24, radius=ring_r)
    new_obj("ring", bm, "timber")
    o = bpy.context.scene.objects[-1]
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="CURVE")
    o.data.bevel_depth = 0.07
    o.data.bevel_resolution = 1
    bpy.ops.object.convert(target="MESH")
    o.select_set(False)
    for k in range(12):
        a = 2 * math.pi * k / 12 + rnd.uniform(-0.1, 0.1)
        x, y = ring_r * math.cos(a), ring_r * math.sin(a)
        c = cyl("antler", 0, 0, 0, rnd.uniform(0.25, 0.38), 0.035, 0.008, segs=5)
        c.location = (x, y, 0.02)
        c.rotation_euler = (0, rnd.uniform(0.35, 0.7), a)  # lean outward
        if k % 2 == 0:
            cyl("light_fixture", x * 0.93, y * 0.93, 0.05, 0.2, 0.05, 0.045, segs=6)
    cyl("timber", 0, 0, -0.08, -0.02, 0.14, 0.14, segs=8)             # hub
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        box("timber", 0.5 * math.cos(a), 0.5 * math.sin(a), -0.05, 1.0, 0.05, 0.05, rz=a)


def m_display_table():
    """Timber display table with a product pyramid. 3.0 x 1.4 x 0.9."""
    rnd = random.Random(6)
    box("timber", 0, 0, 0.72, 3.0, 1.4, 0.08)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box("timber", sx * 1.35, sy * 0.6, 0.34, 0.12, 0.12, 0.68)
    box("timber", 0, 0, 0.15, 2.8, 1.2, 0.04)
    x = -1.35
    while x < 1.2:
        w = rnd.uniform(0.2, 0.4)
        box(rnd.choice(PRODUCTS), x + w / 2, rnd.uniform(-0.3, 0.3), 0.76 + 0.07, w * 0.9, rnd.uniform(0.3, 0.6), 0.14)
        x += w
    box(rnd.choice(PRODUCTS), 0, 0, 0.9 + 0.03, 1.0, 0.5, 0.2)  # top tier (sets max height ~1.0 -> normalized)


def m_apparel_round():
    """Round clothing rack with hanging garments. 1.4 x 1.4 x 1.3."""
    rnd = random.Random(7)
    cyl("metal_shelf", 0, 0, 0, 0.05, 0.35, 0.35, segs=10)
    cyl("metal_shelf", 0, 0, 0.05, 1.25, 0.025, segs=6)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, segments=20, radius=0.6)
    new_obj("rail", bm, "metal_shelf")
    o = bpy.context.scene.objects[-1]
    o.location.z = 1.25
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="CURVE")
    o.data.bevel_depth = 0.015
    bpy.ops.object.convert(target="MESH")
    o.select_set(False)
    colors = ["product_camo", "product_orange", "shelf_green", "product_blue", "product_tan"]
    n = 22
    for k in range(n):
        a = 2 * math.pi * k / n
        box(colors[(k // 4) % len(colors)], 0.6 * math.cos(a), 0.6 * math.sin(a), 0.93, 0.05, 0.42,
            rnd.uniform(0.55, 0.7), rz=a)
    cyl("metal_shelf", 0, 0, 1.25, 1.3, 0.7, 0.7, segs=4)  # keeps bbox square to the rack diameter


def m_pallet():
    """Wood pallet with a stretch-wrapped box stack. 1.2 x 1.0 x 1.4."""
    rnd = random.Random(8)
    for y in (-0.45, 0, 0.45):
        box("timber", 0, y, 0.05, 1.2, 0.1, 0.1)
    for x in range(7):
        box("floor_wood", -0.54 + x * 0.18, 0, 0.12, 0.14, 1.0, 0.04)
    for lvl in range(3):
        for i in range(2):
            for j in range(2):
                box(rnd.choice(["canvas", "product_tan"]), -0.3 + i * 0.6, -0.25 + j * 0.5, 0.14 + 0.2 + lvl * 0.42,
                    0.58, 0.48, 0.4)


def m_elk():
    """Blocky low-poly bull elk statue facing +X. 1.6 x 0.5 x 1.6 (antlers included)."""
    box("wall_log", 0, 0, 0.9, 1.1, 0.42, 0.45)                       # body
    box("wall_log", 0.52, 0, 1.12, 0.35, 0.4, 0.5)                    # shoulders
    for x in (-0.42, 0.4):
        for y in (-0.13, 0.13):
            box("timber", x, y, 0.35, 0.1, 0.1, 0.7)                   # legs
    box("timber", 0.7, 0, 1.35, 0.2, 0.2, 0.45, rz=0)                 # neck
    o = bpy.context.scene.objects[-1]
    o.rotation_euler = (0, math.radians(-35), 0)
    box("wall_log", 0.85, 0, 1.52, 0.3, 0.16, 0.14)                   # head
    box("timber", -0.58, 0, 1.0, 0.08, 0.1, 0.12)                     # tail
    for y in (-1, 1):                                                 # antlers: beam + 4 tines
        beam = cyl("antler", 0.75, y * 0.06, 1.58, 1.98, 0.025, 0.015, segs=5)
        beam.rotation_euler = (math.radians(-y * 30), math.radians(-25), 0)
        for k in range(4):
            t = cyl("antler", 0.75 - 0.05 * k, y * (0.1 + 0.05 * k), 1.66 + 0.08 * k, 1.66 + 0.08 * k + 0.14,
                    0.012, 0.005, segs=4)
            t.rotation_euler = (math.radians(-y * 20), math.radians(35), 0)


MODELS = {
    "Pine": m_pine,
    "LogColumn": m_log_column,
    "Gondola": m_gondola,
    "WallShelf": m_wall_shelf,
    "BassBoat": m_bass_boat,
    "Canoe": m_canoe,
    "Tent": m_tent,
    "BoulderA": lambda: m_boulder(1),
    "BoulderB": lambda: m_boulder(2),
    "Chandelier": m_chandelier,
    "DisplayTable": m_display_table,
    "ApparelRound": m_apparel_round,
    "Pallet": m_pallet,
    "Elk": m_elk,
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = None
    out_dir = os.path.join(PROJ, "PlaceholderAssets")
    for a in argv:
        if a.startswith("only="):
            only = set(a[5:].split(","))
        else:
            out_dir = os.path.abspath(a)
    for name, fn in MODELS.items():
        if only and name not in only:
            continue
        reset()
        fn()
        finish(name, out_dir)


if __name__ == "__main__":
    main()

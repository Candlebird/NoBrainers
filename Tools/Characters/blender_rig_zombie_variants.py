r"""Headless Blender: rig new zombie body meshes onto SK_Zombie's skeleton (same bone names/hierarchy).

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --factory-startup \
    PlaceholderAssets/Blender/SK_Zombie.blend --python Tools/Characters/blender_rig_zombie_variants.py

Input : PlaceholderAssets/Blender/SK_Zombie.blend (read only, never saved over)
        Assets/Female_Zombie_MESH.fbx, Assets/SwampCreature-MESH.fbx (unrigged meshes)
Output: PlaceholderAssets/Blender/Zombie/SK_Zombie_<Variant>.blend
        PlaceholderAssets/FBX/Zombie/SK_Zombie_<Variant>.fbx (armature + mesh, no animation)

Each body has different proportions, so the rig is fitted per mesh rather than scaled:
  - the mesh is centered on the pelvis in X/Y and dropped so its lowest point is on the floor (Z=0),
  - s = target height / SK_Zombie height sets the base scale,
  - torso joints keep their relative front/back position inside the body cross-section at the scaled height,
  - arm joints follow a line fitted through the arm's cross-section centroids (legs: same, by height),
  - every bone keeps SK_Zombie's local roll, rotated by the change in its chain direction,
  - automatic (bone heat) weights; any vertex heat leaves unweighted copies its nearest weighted neighbor.
SK_Zombie_Skeleton uses Skeleton translation retargeting (pelvis AnimationScaled), so the shared animations
play on each mesh's own bind pose.
"""
import os
import sys

import bpy
import bmesh
from mathutils import Vector, kdtree

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC_DIR = os.path.join(ROOT, "Assets")
BDIR = os.path.join(ROOT, "PlaceholderAssets", "Blender", "Zombie")
FDIR = os.path.join(ROOT, "PlaceholderAssets", "FBX", "Zombie")

# variant name -> (source fbx, material name)
VARIANTS = {
    "Female": ("Female_Zombie_MESH.fbx", "M_Zombie_Female"),
    "Swamp": ("SwampCreature-MESH.fbx", "M_Zombie_Swamp"),
}

TORSO = ["pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head", "clavicle_l", "clavicle_r"]
CHAIN_CHILD = {
    "pelvis": "spine_01", "spine_01": "spine_02", "spine_02": "spine_03", "spine_03": "neck_01",
    "neck_01": "head",
}
for s in ("l", "r"):
    CHAIN_CHILD.update({
        f"clavicle_{s}": f"upperarm_{s}", f"upperarm_{s}": f"lowerarm_{s}", f"lowerarm_{s}": f"hand_{s}",
        f"thigh_{s}": f"calf_{s}", f"calf_{s}": f"foot_{s}", f"foot_{s}": f"ball_{s}",
    })
    for f in ("index", "middle", "ring", "pinky", "thumb"):
        CHAIN_CHILD[f"{f}_01_{s}"] = f"{f}_02_{s}"
        CHAIN_CHILD[f"{f}_02_{s}"] = f"{f}_03_{s}"


def fail(reason):
    print(f"VARIANT_FAIL {reason}")
    sys.stdout.flush()
    sys.exit(1)


def world_verts(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def side_of(name):
    return 1.0 if name.endswith("_l") else -1.0 if name.endswith("_r") else 0.0


def region(name):
    if name in TORSO:
        return "torso"
    if any(name.startswith(p) for p in ("thigh", "calf", "foot", "ball")):
        return "leg"
    return "arm"


class Body:
    """Cross-section queries on one mesh's world-space vertices."""

    def __init__(self, verts):
        self.v = verts
        self.zmin = min(p.z for p in verts)
        self.zmax = max(p.z for p in verts)
        self.height = self.zmax - self.zmin

    def torso_y_range(self, z, half_w=8.0, dz=2.0):
        ys = [p.y for p in self.v if abs(p.x) < half_w and abs(p.z - z) < dz]
        while len(ys) < 6 and dz < 20:
            dz *= 1.5
            ys = [p.y for p in self.v if abs(p.x) < half_w and abs(p.z - z) < dz]
        return (min(ys), max(ys)) if ys else None

    def fit_line(self, pts, axis):
        """Least-squares line of the two other coords as functions of `axis` ('x' or 'z')."""
        others = ("y", "z") if axis == "x" else ("x", "y")
        t = [getattr(p, axis) for p in pts]
        n = len(t)
        mt = sum(t) / n
        var = sum((a - mt) ** 2 for a in t) or 1e-6
        coefs = {}
        for o in others:
            vals = [getattr(p, o) for p in pts]
            mv = sum(vals) / n
            k = sum((a - mt) * (b - mv) for a, b in zip(t, vals)) / var
            coefs[o] = (mv - k * mt, k)
        return axis, coefs

    def slice_centroids(self, axis, lo, hi, side, step=2.0, keep=None):
        out = []
        a = lo
        while a <= hi:
            pts = [p for p in self.v if abs(getattr(p, axis) - a) < step / 2 and p.x * side > 0
                   and (keep is None or keep(p))]
            if len(pts) >= 4:
                c = sum(pts, Vector()) / len(pts)
                out.append(c)
            a += step
        return out


def line_at(line, value):
    axis, coefs = line
    p = Vector((0, 0, 0))
    setattr(p, axis, value)
    for o, (b, k) in coefs.items():
        setattr(p, o, b + k * value)
    return p


def arm_line(body, side, s_extent):
    """Line through arm slice centroids, x from just outside the chest to 75% of the reach."""
    reach = max(p.x * side for p in body.v)
    lo, hi = max(0.35 * reach, 30.0 * s_extent), 0.75 * reach
    pts = []
    x = lo
    while x <= hi:
        sl = [p for p in body.v if abs(p.x - side * x) < 1.0 and p.z > body.zmin + 0.55 * body.height]
        if len(sl) >= 4:
            pts.append(sum(sl, Vector()) / len(sl))
        x += 2.0
    if len(pts) < 5:
        fail(f"arm fit found only {len(pts)} slices (side {side})")
    return body.fit_line(pts, "x")


def leg_line(body, side):
    lo, hi = body.zmin + 0.12 * body.height, body.zmin + 0.40 * body.height
    pts = body.slice_centroids("z", lo, hi, side)
    if len(pts) < 5:
        fail(f"leg fit found only {len(pts)} slices (side {side})")
    return body.fit_line(pts, "z")


def import_mesh(fbx):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(SRC_DIR, fbx))
    new = set(bpy.data.objects) - before
    meshes = [o for o in new if o.type == "MESH"]
    if len(meshes) != 1:
        fail(f"{fbx}: expected 1 mesh, got {len(meshes)}")
    mesh = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    for o in new:
        if o is not mesh:
            bpy.data.objects.remove(o)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return mesh


def pelvis_center_y(body, z):
    r = body.torso_y_range(z, half_w=20.0, dz=3.0)
    return (r[0] + r[1]) / 2


def fit_rig(ref_arm, ref_body, tgt_body, s):
    """Return {bone: (new_head, delta_quat)} for every deform bone of the reference rig."""
    mw = ref_arm.matrix_world
    old = {b.name: mw @ b.head_local for b in ref_arm.data.bones}
    lines = {}
    for side in (1.0, -1.0):
        lines[("arm", side)] = (arm_line(ref_body, side, 1.0), arm_line(tgt_body, side, s))
        lines[("leg", side)] = (leg_line(ref_body, side), leg_line(tgt_body, side))

    new = {}
    for name, p in old.items():
        if name == "root" or name.startswith("ik_"):
            continue
        reg = region(name)
        if reg == "torso":
            z_new = p.z * s
            rr = ref_body.torso_y_range(p.z)
            tr = tgt_body.torso_y_range(z_new)
            if rr and tr and rr[1] - rr[0] > 1e-3:
                f = (p.y - rr[0]) / (rr[1] - rr[0])
                y_new = tr[0] + f * (tr[1] - tr[0])
            else:
                y_new = p.y * s
            new[name] = Vector((p.x * s, y_new, z_new))
        else:
            side = side_of(name)
            lr, lt = lines[(reg, side)]
            key = p.x if reg == "arm" else p.z
            base_r = line_at(lr, key)
            base_t = line_at(lt, key * s)
            new[name] = base_t + (p - base_r) * s
    return old, new


def heat_proxy_weights(mesh, arm, voxel=1.5):
    proxy = mesh.copy()
    proxy.data = mesh.data.copy()
    proxy.name = "HeatProxy"
    bpy.context.collection.objects.link(proxy)
    proxy.parent = None
    proxy.matrix_world = mesh.matrix_world
    proxy.modifiers.clear()
    proxy.vertex_groups.clear()
    rm = proxy.modifiers.new("Remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = proxy
    proxy.select_set(True)
    bpy.ops.object.modifier_apply(modifier=rm.name)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    for g in proxy.vertex_groups:
        if g.name not in mesh.vertex_groups:
            mesh.vertex_groups.new(name=g.name)
    dt = mesh.modifiers.new("WeightXfer", "DATA_TRANSFER")
    dt.object = proxy
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"
    dt.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    bpy.ops.object.modifier_move_to_index(modifier=dt.name, index=0)
    bpy.ops.object.modifier_apply(modifier=dt.name)
    bpy.data.objects.remove(proxy)


def build_variant(variant, fbx, mat_name, ref_blend):
    bpy.ops.wm.open_mainfile(filepath=ref_blend)
    ref_arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    ref_mesh = next((o for o in bpy.data.objects if o.type == "MESH"), None)
    if ref_arm is None or ref_mesh is None:
        fail("SK_Zombie.blend missing armature or mesh")
    ref_arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    ref_body = Body(world_verts(ref_mesh))

    mesh = import_mesh(fbx)
    body = Body(world_verts(mesh))
    s = body.height / ref_body.height

    # Center: X on the bbox middle (bodies are symmetric), Y on the hip section, feet on the floor.
    pz_ref = ref_arm.matrix_world @ ref_arm.data.bones["pelvis"].head_local
    dy = pelvis_center_y(ref_body, pz_ref.z) * s - pelvis_center_y(body, pz_ref.z * s + body.zmin)
    xs = [p.x for p in body.v]
    dx = -(min(xs) + max(xs)) / 2
    mesh.location = (dx, dy, -body.zmin)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    body = Body(world_verts(mesh))

    old, new = fit_rig(ref_arm, ref_body, body, s)

    # Reuse the reference armature (bone names, hierarchy, deform flags, IK bones) and move its joints.
    bpy.data.objects.remove(ref_mesh)
    arm = ref_arm
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    frames = {b.name: (b.head.copy(), b.tail.copy(), b.z_axis.copy(), b.length) for b in eb}
    for b in eb:
        b.use_connect = False

    deltas = {}

    def delta_for(name):
        if name in deltas:
            return deltas[name]
        child = CHAIN_CHILD.get(name)
        if child and name in new and child in new:
            d = (old[child] - old[name]).rotation_difference(new[child] - new[name])
        else:
            parent = eb[name].parent
            d = delta_for(parent.name) if parent and parent.name in new else Vector((0, 0, 1)).rotation_difference(Vector((0, 0, 1)))
        deltas[name] = d
        return d

    for name, head in new.items():
        b = eb[name]
        h0, t0, z0, length = frames[name]
        d = delta_for(name)
        b.head = head
        b.tail = head + (d @ (t0 - h0).normalized()) * length * s
        b.align_roll(d @ z0)

    # Rebuild IK bones on the fitted feet/hands, same layout as blender_rig_zombie.py.
    def place(name, target):
        b = eb[name]
        vec = b.tail - b.head
        b.head = target
        b.tail = target + vec
    for side in ("l", "r"):
        place(f"ik_foot_{side}", eb[f"foot_{side}"].head.copy())
    place("ik_hand_gun", eb["hand_r"].head.copy())
    for side in ("l", "r"):
        place(f"ik_hand_{side}", eb[f"hand_{side}"].head.copy())
    bpy.ops.object.mode_set(mode="OBJECT")

    # Skin with bone heat, then patch any vertices heat left unweighted (separate eye/teeth shells).
    name = f"SK_Zombie_{variant}"
    mesh.name = mesh.data.name = name
    for mat in mesh.data.materials:
        if mat:
            mat.name = mat_name
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    groups = {g.index: g.name for g in mesh.vertex_groups}
    deform = {b.name for b in arm.data.bones if b.use_deform}

    def weights(v):
        return [(g.group, g.weight) for g in v.groups if g.weight > 1e-4 and groups.get(g.group) in deform]

    verts = mesh.data.vertices
    if not any(weights(v) for v in verts):
        # Bone heat has no solution on this mesh (overlapping shells/fins): solve it on a watertight voxel
        # remesh instead and transfer the weights back by nearest face.
        heat_proxy_weights(mesh, arm)
        groups = {g.index: g.name for g in mesh.vertex_groups}
    weighted = [v.index for v in verts if weights(v)]
    missing = [v.index for v in verts if not weights(v)]
    if not weighted:
        fail(f"{name}: automatic weights produced no weights")
    if missing:
        tree = kdtree.KDTree(len(weighted))
        for i, idx in enumerate(weighted):
            tree.insert(verts[idx].co, i)
        tree.balance()
        for idx in missing:
            _, i, _ = tree.find(verts[idx].co)
            for gi, w in weights(verts[weighted[i]]):
                mesh.vertex_groups[gi].add([idx], w, "REPLACE")
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)

    empty = sum(1 for v in verts if not weights(v))
    for ob in (arm, mesh):
        if any(abs(c - 1.0) > 1e-4 for c in ob.scale):
            fail(f"{ob.name} scale not (1,1,1): {tuple(ob.scale)}")

    os.makedirs(BDIR, exist_ok=True)
    os.makedirs(FDIR, exist_ok=True)
    arm.data.pose_position = "POSE"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BDIR, f"{name}.blend"), copy=True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(FDIR, f"{name}.fbx"), use_selection=False,
                             object_types={"ARMATURE", "MESH"}, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_UNITS", add_leaf_bones=False, bake_anim=False,
                             use_armature_deform_only=False, mesh_smooth_type="FACE")
    print(f"VARIANT {name} scale={s:.3f} height={body.height:.1f} verts={len(verts)} "
          f"heat_missing={len(missing)} still_empty={empty} bones={len(arm.data.bones)} "
          f"mats={[m.name for m in mesh.data.materials if m]}")


def main():
    ref_blend = bpy.data.filepath
    if not ref_blend.endswith("SK_Zombie.blend"):
        fail(f"open PlaceholderAssets/Blender/SK_Zombie.blend first (got {ref_blend})")
    only = [a for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else []
    for variant, (fbx, mat) in VARIANTS.items():
        if not only or variant in only:
            build_variant(variant, fbx, mat, ref_blend)


if __name__ == "__main__":
    main()

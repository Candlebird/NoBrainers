"""Headless Blender: key a two-handed melee swing on the UE4 mannequin skeleton and export it as an FBX animation.

"C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background --factory-startup --python Tools/Characters/blender_melee_anim.py

Input : PlaceholderAssets/FBX/SK_Mannequin_Ref.fbx (read-only, exported from UE4_Mannequin_Skeleton)
Output: PlaceholderAssets/Blender/A_MeleeSwing.blend, PlaceholderAssets/FBX/A_MeleeSwing.fbx

Upper body only: spine_01..03 + neck_01 are FK-keyed, both arms are posed by a two-bone IK solve toward a keyed
right-hand target (left hand = right target + GRIP_OFFSET_L). Pelvis, root and legs are never keyed.
Works in centimeters (1 BU = 1 cm), every object at scale 1.

Notes on Blender 5.2 / mannequin quirks handled here:
  - import_scene.fbx has no apply_unit_scale option any more (unit scale is always applied).
  - The FBX "root" node is type Root, which Blender turns into the armature OBJECT, so the "root" bone is rebuilt
    (at the origin, pelvis + ik roots parented to it) exactly like Tools/Characters/blender_rig_zombie.py does.
  - ignore_leaf_bones must stay False: the mannequin has no *_end bones, so that flag would drop 13 real bones.
  - With automatic_bone_orientation off, bone tails don't point at the child bone, so Blender's IK constraint
    (which drives the lowerarm TAIL) can't place the hand. The arms are therefore solved analytically per frame
    (shoulder -> elbow -> hand head) against the keyed IK_Target empties and keyed every frame (same result as a
    visual-keying bake). The pole empties set the elbow bend plane directly, so no pole-angle search is needed.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BDIR = os.path.join(ROOT, "PlaceholderAssets", "Blender")
FDIR = os.path.join(ROOT, "PlaceholderAssets", "FBX")
SRC_FBX = os.path.join(FDIR, "SK_Mannequin_Ref.fbx")
OUT_BLEND = os.path.join(BDIR, "A_MeleeSwing.blend")
OUT_FBX = os.path.join(FDIR, "A_MeleeSwing.fbx")

# ---------------------------------------------------------------------------------------------------------------
# Tunables (re-tune and re-run)
# ---------------------------------------------------------------------------------------------------------------
FPS = 30
FRAME_START = 0
FRAME_END = 21          # 0.7 s at 1.0x
HIT_FRAME = 10

# frame: ((F, R, U) hand_r target in cm relative to chest point C, spine yaw total deg (+ = torso to its left),
#         spine pitch total deg (+ = lean back))
KEYS = {
    0: ((30.0, 15.0, 5.0), -10.0, 0.0),      # guard
    7: ((-5.0, 28.0, 30.0), -40.0, 5.0),     # full wind-up, behind right shoulder
    10: ((40.0, 0.0, 0.0), 0.0, -8.0),       # half-arc, straight out front (hit)
    13: ((15.0, -30.0, -15.0), 50.0, -10.0),  # follow-through, low left
    21: ((30.0, 15.0, 5.0), -10.0, 0.0),     # recover (= guard)
}
INTERP = {0: "BEZIER", 7: "LINEAR", 10: "LINEAR", 13: "BEZIER", 21: "BEZIER"}
GRIP_OFFSET_L = (0.0, 0.0, -10.0)    # left-hand target relative to right-hand target (F, R, U)
POLE_R = (-20.0, 50.0, -30.0)        # (F, R, U) relative to C
POLE_L = (-20.0, -50.0, -30.0)
NECK_COUNTER = 0.5                   # neck_01 yaw = -NECK_COUNTER * spine yaw total

SPINE = ("spine_01", "spine_02", "spine_03")
REACH_TOL = 3.0
MAX_PULL = 0.20


def fail(reason):
    print(f"MELEE_ANIM FAIL {reason}")
    sys.stdout.flush()
    sys.exit(1)


def fcurves_of(obj):
    ad = obj.animation_data
    act = ad.action
    try:
        return list(act.fcurves)
    except AttributeError:  # Blender 5.x slotted actions
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
        return list(cb.fcurves) if cb else []


def set_interp(obj, data_path_prefix=None):
    for fc in fcurves_of(obj):
        if data_path_prefix and not fc.data_path.startswith(data_path_prefix):
            continue
        for kp in fc.keyframe_points:
            k = int(round(kp.co.x))
            if k in INTERP:
                kp.interpolation = INTERP[k]
        fc.update()


def count_fbx_bones(path):
    from io_scene_fbx import parse_fbx
    root, _ver = parse_fbx.parse(path)
    objs = [e for e in root.elems if e.id == b"Objects"][0]
    return sum(1 for e in objs.elems if e.id == b"Model" and e.props[2] in (b"LimbNode", b"Root"))


def main():
    scene = bpy.context.scene
    vl = bpy.context.view_layer
    for ob in list(bpy.data.objects):  # factory scene (cube/camera/light) must not reach the export
        bpy.data.objects.remove(ob)

    # ---------------------------------------------------------------- import (cm units BEFORE import)
    scene.unit_settings.scale_length = 0.01
    bpy.ops.import_scene.fbx(filepath=SRC_FBX, use_manual_orientation=False, global_scale=1.0,
                             automatic_bone_orientation=False, primary_bone_axis="Y", secondary_bone_axis="X",
                             ignore_leaf_bones=False, force_connect_children=False, use_anim=False)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if len(arms) != 1 or len(meshes) != 1:
        fail(f"import produced {len(arms)} armatures / {len(meshes)} meshes")
    arm, mesh = arms[0], meshes[0]

    # Drop the FBX's wrapper empty, keep world transforms.
    for ob in (arm, mesh):
        if ob.parent and ob.parent.type == "EMPTY":
            mw = ob.matrix_world.copy()
            if ob is mesh:
                continue
            ob.parent = None
            ob.matrix_world = mw
    for ob in list(bpy.data.objects):
        if ob.type == "EMPTY":
            bpy.data.objects.remove(ob)
    arm.name = arm.data.name = "Armature"
    mesh.name = "SK_Mannequin"
    mesh.data.name = "SK_Mannequin"

    bpy.ops.object.select_all(action="DESELECT")
    vl.objects.active = arm
    arm.select_set(True)
    if tuple(round(s, 6) for s in arm.scale) != (1.0, 1.0, 1.0):
        mesh.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        mesh.select_set(False)

    # Rebuild the "root" bone the Root node was folded into (same as the zombie rig).
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    if "root" not in eb:
        r = eb.new("root")
        r.head, r.tail, r.roll = Vector((0, 0, 0)), Vector((0, 20, 0)), 0.0
        r.use_deform = False
        for b in eb:
            if b.parent is None and b is not r:
                b.parent = r
    bpy.ops.object.mode_set(mode="OBJECT")
    vl.update()

    bones = arm.data.bones
    if "root" not in bones:
        fail("no bone 'root'")
    n_fbx = count_fbx_bones(SRC_FBX)
    if len(bones) != n_fbx:
        fail(f"bone count {len(bones)} != fbx {n_fbx}")
    pelvis_z = bones["pelvis"].head_local.z
    if not (85.0 <= pelvis_z <= 110.0):
        fail(f"pelvis rest head Z {pelvis_z:.2f} outside 85-110")
    if arm.matrix_world != Matrix.Identity(4):
        fail("armature object transform is not identity")
    print(f"MELEE_ANIM import bones={len(bones)} fbx={n_fbx} pelvisZ={pelvis_z:.2f} "
          f"arm_scale={tuple(arm.scale)} mesh_scale={tuple(mesh.scale)}")

    # ---------------------------------------------------------------- character axes from rest
    U = Vector((0, 0, 1))
    Rv = bones["clavicle_r"].head_local - bones["clavicle_l"].head_local
    Rv.z = 0.0
    Rv.normalize()
    Fv = U.cross(Rv)
    C = bones["spine_03"].head_local.copy()

    def to_arm(t):
        return C + Fv * t[0] + Rv * t[1] + U * t[2]

    def to_off(t):
        return Fv * t[0] + Rv * t[1] + U * t[2]

    def to_fru(p):
        d = p - C
        return (d.dot(Fv), d.dot(Rv), d.dot(U))

    print(f"MELEE_ANIM axes F={tuple(round(x, 3) for x in Fv)} R={tuple(round(x, 3) for x in Rv)} "
          f"C={tuple(round(x, 2) for x in C)}")

    # ---------------------------------------------------------------- spine FK keys
    bpy.ops.object.select_all(action="DESELECT")
    vl.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    pbs = arm.pose.bones
    for pb in pbs:
        pb.rotation_mode = "QUATERNION"
    scene.render.fps = FPS
    scene.render.fps_base = 1.0
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END

    fk = SPINE + ("neck_01",)

    def rot_about_head(pb, rot):
        h = pb.head.copy()
        pb.matrix = Matrix.Translation(h) @ rot @ Matrix.Translation(-h) @ pb.matrix
        vl.update()

    for f, (_t, yaw, pitch) in sorted(KEYS.items()):
        scene.frame_set(f)
        for n in fk:
            pbs[n].rotation_quaternion = (1, 0, 0, 0)
            pbs[n].location = (0, 0, 0)
        vl.update()
        for n in SPINE:
            rot = Matrix.Rotation(math.radians(yaw / 3.0), 4, U)
            if n == "spine_03":
                rot = Matrix.Rotation(math.radians(pitch), 4, Rv) @ rot
            rot_about_head(pbs[n], rot)
        rot_about_head(pbs["neck_01"], Matrix.Rotation(math.radians(-NECK_COUNTER * yaw), 4, U))
        for n in fk:
            pbs[n].keyframe_insert("rotation_quaternion", frame=f, group=n)
    set_interp(arm)
    arm.animation_data.action.name = "A_MeleeSwing"

    # ---------------------------------------------------------------- two-bone IK helpers
    def arm_chain(s):
        return pbs[f"upperarm_{s}"], pbs[f"lowerarm_{s}"], pbs[f"hand_{s}"]

    def lengths(s):
        ua, la, hd = (bones[f"upperarm_{s}"], bones[f"lowerarm_{s}"], bones[f"hand_{s}"])
        return (la.head_local - ua.head_local).length, (hd.head_local - la.head_local).length

    LEN = {s: lengths(s) for s in ("l", "r")}

    def reset_arm(s):
        for pb in arm_chain(s):
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
        vl.update()

    def basis(d, n):
        d = d.normalized()
        n = (n - d * n.dot(d)).normalized()
        return Matrix((d, n, d.cross(n))).transposed()  # columns d, n, d x n

    def solve_arm(s, T, P):
        """Pose upperarm/lowerarm so hand_<s> head reaches T with the elbow bent toward P. Returns reach error."""
        ua, la, hd = arm_chain(s)
        a, b = LEN[s]
        S = ua.head.copy()
        E0, H0 = la.head.copy(), hd.head.copy()
        dv = T - S
        d = min(max(dv.length, abs(a - b) + 1e-3), a + b - 1e-3)
        u = dv.normalized()
        p = (P - S)
        p = (p - u * p.dot(u)).normalized()
        ca = (a * a + d * d - b * b) / (2 * a * d)
        sa = math.sqrt(max(0.0, 1 - ca * ca))
        E = S + (u * ca + p * sa) * a
        Tc = S + u * d
        # upperarm: align (shoulder->elbow, bend-plane normal) frames
        n0 = (E0 - S).cross(H0 - S)
        n1 = (E - S).cross(Tc - S)
        rot = (basis(E - S, n1) @ basis(E0 - S, n0).transposed()).to_4x4()
        rot_about_head(ua, rot)
        # lowerarm: swing elbow->hand onto elbow->target
        Ec, Hc = la.head.copy(), hd.head.copy()
        rot = (Hc - Ec).rotation_difference(Tc - Ec).to_matrix().to_4x4()
        rot_about_head(la, rot)
        return (hd.head - T).length

    def reach_ok(s, T):
        a, b = LEN[s]
        return (T - arm_chain(s)[0].head).length <= a + b - 0.5

    # ---------------------------------------------------------------- reach pre-pass (check d, pull toward C)
    grip = to_off(GRIP_OFFSET_L)
    targets, pulls = {}, {}
    for f, (t, _y, _p) in sorted(KEYS.items()):
        scene.frame_set(f)
        reset_arm("l")
        reset_arm("r")
        base = to_arm(t)
        chosen = None
        for i in range(0, 11):
            k = MAX_PULL * i / 10.0
            T = C + (base - C) * (1.0 - k)
            if reach_ok("r", T) and reach_ok("l", T + grip):
                chosen = (T, k)
                break
        if chosen is None:
            chosen = (C + (base - C) * (1.0 - MAX_PULL), MAX_PULL)
        targets[f] = chosen[0]
        if chosen[1] > 0:
            pulls[f] = (round(chosen[1] * 100), tuple(round(x, 1) for x in to_fru(chosen[0])))

    # ---------------------------------------------------------------- IK target / pole empties
    def empty(name, loc, parent=None):
        e = bpy.data.objects.new(name, None)
        scene.collection.objects.link(e)
        e.parent = parent
        e.location = loc
        return e

    bpy.ops.object.mode_set(mode="OBJECT")
    tgt_r = empty("IK_Target_R", targets[FRAME_START])
    tgt_l = empty("IK_Target_L", grip, tgt_r)  # parent at identity rotation -> local offset == armature offset
    pole_r = empty("Pole_R", to_arm(POLE_R))
    pole_l = empty("Pole_L", to_arm(POLE_L))
    for f, T in targets.items():
        tgt_r.location = T
        tgt_r.keyframe_insert("location", frame=f)
    set_interp(tgt_r)
    vl.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")

    # ---------------------------------------------------------------- per-frame solve + key (visual bake)
    reach_err = {}
    for f in range(FRAME_START, FRAME_END + 1):
        scene.frame_set(f)
        reset_arm("r")
        reset_arm("l")
        Tr = tgt_r.matrix_world.translation.copy()
        Tl = tgt_l.matrix_world.translation.copy()
        er = solve_arm("r", Tr, pole_r.matrix_world.translation)
        el = solve_arm("l", Tl, pole_l.matrix_world.translation)
        if f in KEYS:
            reach_err[f] = (round(er, 2), round(el, 2))
        for s in ("l", "r"):
            for pb in arm_chain(s)[:2]:
                pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)

    # Pole sanity at frame 0: elbow >= 5 cm below shoulder-hand midpoint and on its own side.
    scene.frame_set(FRAME_START)
    pole_info = {}
    for s, sign in (("r", 1), ("l", -1)):
        ua, la, hd = arm_chain(s)
        mid = (ua.head + hd.head) * 0.5
        below = (mid - la.head).dot(U)
        side = to_fru(la.head)[1] * sign
        pole_info[s] = (round(below, 2), round(side, 2))

    for e in (tgt_l, tgt_r, pole_r, pole_l):
        bpy.data.objects.remove(e)
    act = arm.animation_data.action
    act.name = "A_MeleeSwing"

    # ---------------------------------------------------------------- checks
    fails = []
    max_gap, gap_frame = 0.0, 0
    pelvis_bad = []
    hand_r_at = {}
    for f in range(FRAME_START, FRAME_END + 1):
        scene.frame_set(f)
        hr, hl = pbs["hand_r"].head.copy(), pbs["hand_l"].head.copy()
        g = (hl - hr).length
        if g > max_gap:
            max_gap, gap_frame = g, f
        hand_r_at[f] = to_fru(hr)
        if pbs["pelvis"].location.length > 1e-4:
            pelvis_bad.append(f)
    print(f"MELEE_ANIM pole_check (below_mid, own_side) r={pole_info['r']} l={pole_info['l']}")
    if not all(v[0] >= 5.0 and v[1] > 0 for v in pole_info.values()):
        fails.append("pole")
    print(f"MELEE_ANIM (a) max |hand_l-hand_r| = {max_gap:.2f} @f{gap_frame}")
    if max_gap > 20.0:
        fails.append("a")
    h = hand_r_at[HIT_FRAME]
    print(f"MELEE_ANIM (b) f{HIT_FRAME} hand_r FRU = ({h[0]:.2f}, {h[1]:.2f}, {h[2]:.2f})")
    if not (h[0] >= 30.0 and abs(h[1]) <= 12.0):
        fails.append("b")
    h7, h13 = hand_r_at[7], hand_r_at[13]
    print(f"MELEE_ANIM (c) f7 hand_r FRU = ({h7[0]:.2f}, {h7[1]:.2f}, {h7[2]:.2f}); "
          f"f13 hand_r FRU = ({h13[0]:.2f}, {h13[1]:.2f}, {h13[2]:.2f})")
    if not (h7[1] >= 15.0 and h7[2] >= 15.0 and h13[1] <= -15.0):
        fails.append("c")
    print(f"MELEE_ANIM (d) reach err (r, l) per key = {reach_err}; pulls toward C = {pulls or 'none'}")
    if any(max(v) > REACH_TOL for v in reach_err.values()):
        fails.append("d")
    print(f"MELEE_ANIM (e) pelvis nonzero loc frames = {pelvis_bad or 'none'}")
    if pelvis_bad:
        fails.append("e")
    if fails:
        fail(",".join(fails))

    # ---------------------------------------------------------------- save + export
    bpy.ops.object.mode_set(mode="OBJECT")
    scene.frame_set(FRAME_START)
    os.makedirs(BDIR, exist_ok=True)
    os.makedirs(FDIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.export_scene.fbx(filepath=OUT_FBX, object_types={"ARMATURE", "MESH"}, use_selection=False,
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Z", axis_up="Y", primary_bone_axis="Y", secondary_bone_axis="X",
                             add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype="NULL",
                             bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                             bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
                             bake_anim_step=1.0, bake_anim_simplify_factor=0.0)
    if not (os.path.isfile(OUT_BLEND) and os.path.isfile(OUT_FBX)):
        fail("outputs missing")
    print(f"MELEE_ANIM action={act.name} frames={FRAME_START}-{FRAME_END}@{FPS} "
          f"blend={os.path.getsize(OUT_BLEND)} fbx={os.path.getsize(OUT_FBX)}")
    print("MELEE_ANIM OK")


if __name__ == "__main__":
    main()

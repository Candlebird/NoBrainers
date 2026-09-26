"""Headless Blender: key placeholder zombie animations on SK_Zombie's UE4-mannequin-style skeleton and export one
FBX per clip.

"C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background --factory-startup \
    PlaceholderAssets/Blender/SK_Zombie.blend --python Tools/Characters/blender_zombie_anims.py \
    [-- --type Runner] [-- --clip Walk]

Input : PlaceholderAssets/Blender/SK_Zombie.blend (read only, never saved over).
Output: PlaceholderAssets/FBX/Zombie/A_Z_<Type>_<Clip>.fbx (armature only, no mesh, bake_anim, one action each)
        PlaceholderAssets/Blender/Zombie/A_Z_Anims.blend (all actions, fake-user'd)

Technique: every pose is authored as an *armature-space* rotation about a bone's own head, using the three
character axes (U = world up, Rv = character "right" pointed axis, Fv = forward = U x Rv, both derived from the
clavicle_l/clavicle_r rest offset exactly like Tools/Characters/blender_melee_anim.py). This sidesteps needing each
bone's local roll/axis convention: rotating any bone by a signed "P" (pitch, swing fwd/back, about Rv), "B" (bank,
raise/lower sideways, about Fv) or "Y" (yaw/twist, about U) degree amount behaves the same regardless of which side
of the body it is on or how its rest roll is set, and a pose dict is just {bone_name: [(axis_letter, degrees), ...]}
applied in order on top of the bone's rest transform. Pelvis root motion (spawn climb, lying deaths) is done the
same way plus a direct world-space translation of the pelvis bone.

Every clip is its own Action (Blender 5.x slotted actions handled the same way as blender_melee_anim.py), keyed at
a handful of named "pose" keyframes (not baked per-frame) and left for Blender's own interpolation in between --
placeholder quality, not a hand-tuned bake. Locomotion loops are 9 keys sampling one full gait cycle (phase 0..1,
last key duplicates the first). Never keys root or pelvis translation for in-place loops.
"""
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BDIR = os.path.join(ROOT, "PlaceholderAssets", "Blender", "Zombie")
FDIR = os.path.join(ROOT, "PlaceholderAssets", "FBX", "Zombie")
OUT_BLEND = os.path.join(BDIR, "A_Z_Anims.blend")
FPS = 30

# ---------------------------------------------------------------------------------------------------------------
# CLI (after "--")
# ---------------------------------------------------------------------------------------------------------------
argv = sys.argv
ARGS_TYPE = None
ARGS_CLIP = None
if "--" in argv:
    tail = argv[argv.index("--") + 1:]
    i = 0
    while i < len(tail):
        if tail[i] == "--type" and i + 1 < len(tail):
            ARGS_TYPE = tail[i + 1]
            i += 2
        elif tail[i] == "--clip" and i + 1 < len(tail):
            ARGS_CLIP = tail[i + 1]
            i += 2
        else:
            i += 1


def fail(reason):
    print(f"ZOMBIE_ANIM FAIL {reason}")
    sys.stdout.flush()
    sys.exit(1)


# ---------------------------------------------------------------------------------------------------------------
# Type tuning. tone in {"floppy","twitchy","heavy","between"} drives amplitude/overshoot/jitter of the shared
# pose shapes below (see TONE below).
# ---------------------------------------------------------------------------------------------------------------
TYPE_PARAMS = {
    "Shambler": dict(tone="floppy", hunch=16, arm_reach=False, speed_walk=0.75, speed_run=1.05,
                     stride=1.0, bounce=1.35, sway=1.4, arm_swing=0.7, jitter=0.0),
    "Runner":   dict(tone="twitchy", hunch=10, arm_reach=False, speed_walk=1.1, speed_run=2.1,
                     stride=1.1, bounce=0.75, sway=0.55, arm_swing=1.1, jitter=2.5),
    "Brute":    dict(tone="heavy", hunch=8, arm_reach=False, speed_walk=0.65, speed_run=1.15,
                     stride=1.25, bounce=1.6, sway=1.7, arm_swing=0.6, jitter=0.0),
    "Spitter":  dict(tone="between", hunch=24, arm_reach=True, speed_walk=0.85, speed_run=1.35,
                     stride=0.9, bounce=1.0, sway=1.0, arm_swing=0.8, jitter=1.0),
    "Screamer": dict(tone="twitchy", hunch=26, arm_reach=False, speed_walk=0.95, speed_run=1.7,
                     stride=1.0, bounce=0.9, sway=0.8, arm_swing=1.2, jitter=3.5),
    "Bloater":  dict(tone="floppy", hunch=14, arm_reach=True, speed_walk=0.7, speed_run=0.95,
                     stride=0.9, bounce=1.5, sway=1.6, arm_swing=0.65, jitter=0.0),
}
TYPES = list(TYPE_PARAMS.keys())

CLIPS_COMMON = ["Idle", "Walk", "Run", "Spawn", "Attack1", "Attack2", "Attack3", "HitReact",
                "Death1", "Death2", "Death3"]
CLIPS_EXTRA = {
    "Runner": ["Sprint", "Lunge"],
    "Brute": ["ChargeWindup", "Charge", "Stun"],
    "Spitter": ["Lob"],
    "Screamer": ["Shriek", "FleeRun"],
    "Bloater": ["Swell"],
}
SPAWN_LEN = {"Shambler": 2.2, "Runner": 1.5, "Brute": 3.0, "Spitter": 2.0, "Screamer": 1.8, "Bloater": 2.5}


def clip_list(type_name):
    return CLIPS_COMMON + CLIPS_EXTRA.get(type_name, [])


# ---------------------------------------------------------------------------------------------------------------
# Rig access
# ---------------------------------------------------------------------------------------------------------------
def get_rig():
    arm = mesh = None
    for ob in bpy.data.objects:
        if ob.type == "ARMATURE":
            arm = ob
        elif ob.type == "MESH":
            mesh = ob
    if arm is None:
        fail("no armature object in SK_Zombie.blend")
    return arm, mesh


LEG = lambda s: [f"thigh_{s}", f"calf_{s}", f"foot_{s}", f"ball_{s}"]
ARM = lambda s: [f"clavicle_{s}", f"upperarm_{s}", f"lowerarm_{s}", f"hand_{s}"]
SPINE = ["spine_01", "spine_02", "spine_03"]
HEAD_CHAIN = ["neck_01", "head"]
ORDER = (["pelvis"] + SPINE + HEAD_CHAIN + ARM("l") + ARM("r") + LEG("l") + LEG("r"))


def fcurves_of(obj):
    ad = obj.animation_data
    act = ad.action
    try:
        return list(act.fcurves)
    except AttributeError:
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
        return list(cb.fcurves) if cb else []


def main():
    scene = bpy.context.scene
    vl = bpy.context.view_layer
    arm, mesh = get_rig()
    if mesh is not None:
        mesh.hide_set(True)
    bones = arm.data.bones
    for req in ("pelvis", "clavicle_l", "clavicle_r", "spine_03"):
        if req not in bones:
            fail(f"missing bone {req}")

    U = Vector((0.0, 0.0, 1.0))
    Rv = (bones["clavicle_r"].head_local - bones["clavicle_l"].head_local)
    Rv.z = 0.0
    Rv.normalize()
    Fv = U.cross(Rv)
    FORWARD_SIGN = 1.0  # flip to -1.0 if the preview shows the rig walking/reaching backward
    Fv = Fv * FORWARD_SIGN
    PELVIS_REST_Z = bones["pelvis"].head_local.z
    AXIS = {"P": Rv, "B": Fv, "Y": U}
    print(f"ZOMBIE_ANIM axes U={tuple(U)} Rv={tuple(round(x,3) for x in Rv)} "
          f"Fv={tuple(round(x,3) for x in Fv)} pelvisZ={round(PELVIS_REST_Z,2)}")

    bpy.ops.object.select_all(action="DESELECT")
    vl.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    pbs = arm.pose.bones
    for pb in pbs:
        pb.rotation_mode = "QUATERNION"
    scene.render.fps = FPS
    scene.render.fps_base = 1.0

    def reset_bone(name):
        pb = pbs[name]
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)  # matrix-based rot_world() can leave decomposition noise in scale; must
        # be re-zeroed every frame or it compounds across the many pb.matrix round-trips in a clip (root
        # cause of the "spike" mesh artifact seen in QA previews -- non-keyed child bones like fingers then
        # inherit a huge stray scale from an ancestor whose matrix_basis never got cleaned up).
        if name == "pelvis":
            pb.location = (0.0, 0.0, 0.0)

    def reset_all():
        for n in ORDER:
            reset_bone(n)
        vl.update()

    def rot_world(name, axis_letter, deg):
        if abs(deg) < 1e-6:
            return
        pb = pbs[name]
        h = pb.head.copy()
        R = Matrix.Rotation(math.radians(deg), 4, AXIS[axis_letter])
        pb.matrix = Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ pb.matrix
        vl.update()

    def apply_ops(name, ops):
        for axis_letter, deg in ops:
            rot_world(name, axis_letter, deg)

    def set_pelvis_world(pos):
        pb = pbs["pelvis"]
        m = pb.matrix.copy()
        m.translation = pos
        pb.matrix = m
        vl.update()

    def apply_pose(pose, pelvis_pos=None):
        """pose: {bone_name: [(axis,deg), ...]}. Bones in ORDER not present in pose stay at rest for this frame."""
        for name in ORDER:
            if name in pose:
                apply_ops(name, pose[name])
        if pelvis_pos is not None:
            set_pelvis_world(pelvis_pos)

    rng_cache = {}

    def jitter(seed_key, amp):
        if amp <= 0:
            return 0.0
        r = rng_cache.get(seed_key)
        if r is None:
            r = random.Random(hash(seed_key) & 0xFFFFFFFF)
            rng_cache[seed_key] = r
        return r.uniform(-amp, amp)

    # ------------------------------------------------------------------------------------------------------- pose
    # library: base arm carry, gait generator, attack/death/special shapes.
    def base_arms(p):
        if p["arm_reach"]:
            b, elbow, wrist = -42.0, 55.0, 10.0
        else:
            b, elbow, wrist = -68.0, 30.0, 5.0
        ops = {}
        for s in ("l", "r"):
            ops[f"upperarm_{s}"] = [("B", b), ("P", -8.0 if p["arm_reach"] else 0.0)]
            ops[f"lowerarm_{s}"] = [("P", elbow)]
            ops[f"hand_{s}"] = [("P", wrist)]
        return ops

    def gait_pose(phase, p, kind, tone):
        """One instant of a locomotion loop. kind in walk/run/sprint/charge/fleerun."""
        amp = {"walk": (18, 10), "run": (32, 45), "sprint": (40, 55),
               "charge": (26, 30), "fleerun": (30, 40)}[kind]
        thigh_amp = amp[0] * p["stride"]
        calf_amp = amp[1] * p["stride"]
        bounce_amp = 4.0 * p["bounce"] * (1.4 if kind in ("run", "sprint", "fleerun") else 1.0)
        sway_amp = 6.0 * p["sway"]
        arm_amp = amp[0] * 0.9 * p["arm_swing"]
        hunch = p["hunch"] * (1.15 if kind in ("run", "sprint", "charge", "fleerun") else 1.0)
        two_pi = 2.0 * math.pi
        pose = dict(base_arms(p))

        def add(name, axis, deg):
            pose.setdefault(name, []).append((axis, deg))

        for s, ph_off in (("l", 0.0), ("r", 0.5)):
            ph = phase + ph_off
            thigh = thigh_amp * math.sin(two_pi * ph)
            calf = calf_amp * max(0.0, math.sin(two_pi * ph))
            add(f"thigh_{s}", "P", thigh)
            add(f"calf_{s}", "P", calf)
            add(f"foot_{s}", "P", -0.4 * calf - 6.0 * max(0.0, -math.sin(two_pi * ph)))
            # contralateral arm swing on top of the carry pose
            add(f"upperarm_{s}", "P", -arm_amp * math.sin(two_pi * ph + math.pi))
            add(f"lowerarm_{s}", "P", 6.0 * max(0.0, math.sin(two_pi * ph)))
        add("spine_01", "P", -hunch * 0.4)
        add("spine_02", "P", -hunch * 0.35)
        add("spine_03", "P", -hunch * 0.25)
        add("spine_03", "Y", sway_amp * math.sin(two_pi * phase))
        add("neck_01", "P", hunch * 0.3)
        add("head", "P", hunch * 0.15 + jitter(("head", kind, round(phase % 1.0, 3)), p["jitter"] * 0.6))
        pelvis_bounce = bounce_amp * abs(math.sin(two_pi * phase * 2.0)) - bounce_amp * 0.5
        pelvis_pos = Vector((0.0, 0.0, PELVIS_REST_Z + pelvis_bounce))
        return pose, pelvis_pos

    def build_locomotion(kind, p, tone, n_keys=9, loop=True, speed=1.0):
        base_len = {"walk": 1.15, "run": 0.75, "sprint": 0.55, "charge": 0.95, "fleerun": 0.6}[kind]
        length_s = base_len / max(speed, 0.05)
        n_frames = max(8, round(length_s * FPS))
        frames = {}
        for i in range(n_keys):
            phase = i / (n_keys - 1)
            f = round(phase * n_frames)
            pose, ppos = gait_pose(phase, p, kind, tone)
            frames[f] = (pose, ppos)
        return frames, loop, n_frames

    def build_idle(p, tone):
        pose = dict(base_arms(p))
        h = p["hunch"]
        pose["spine_01"] = pose.get("spine_01", []) + [("P", -h * 0.3)]
        pose["spine_02"] = pose.get("spine_02", []) + [("P", -h * 0.25)]
        pose["spine_03"] = pose.get("spine_03", []) + [("P", -h * 0.2)]
        pose["neck_01"] = pose.get("neck_01", []) + [("P", h * 0.25)]
        pose["head"] = pose.get("head", []) + [("P", h * 0.1)]
        breathe = dict(pose)
        breathe = {k: list(v) for k, v in pose.items()}
        breathe.setdefault("spine_02", []).append(("P", -1.5))
        frames = {0: (pose, None), 45: (breathe, None), 90: (pose, None)}
        return frames, True, 90

    def build_hitreact(p, tone, side_sign=1.0):
        idle_frames, _, _ = build_idle(p, tone)
        neutral = idle_frames[0][0]
        peak = {k: list(v) for k, v in neutral.items()}
        snap = 26.0 * (1.4 if tone == "twitchy" else 1.0)
        peak.setdefault("spine_03", []).append(("P", -snap))
        peak.setdefault("spine_02", []).append(("Y", 10.0 * side_sign))
        peak.setdefault("neck_01", []).append(("P", -snap * 0.5))
        peak.setdefault("head", []).append(("Y", 14.0 * side_sign))
        n = 12 if tone != "twitchy" else 9
        frames = {0: (neutral, None), max(3, n // 3): (peak, None), n: (neutral, None)}
        return frames, False, n

    def _claw(side, p, big):
        wind = dict(base_arms(p))
        wind[f"upperarm_{side}"] = [("B", -20.0), ("P", -40.0 * big)]
        wind[f"lowerarm_{side}"] = [("P", 70.0 * big)]
        wind["spine_03"] = [("Y", 14.0 if side == "r" else -14.0), ("P", -10.0)]
        strike = dict(base_arms(p))
        strike[f"upperarm_{side}"] = [("B", -10.0), ("P", 60.0 * big)]
        strike[f"lowerarm_{side}"] = [("P", 15.0)]
        strike["spine_03"] = [("Y", -18.0 if side == "r" else 18.0), ("P", 8.0)]
        return wind, strike

    def build_attack(variant, p, tone):
        heavy = tone == "heavy"
        floppy = tone == "floppy"
        big = 1.25 if heavy else (1.1 if floppy else 1.0)
        length_s = (1.4 if heavy else (0.9 if tone == "twitchy" else 1.1))
        n = max(20, round(length_s * FPS))
        neutral = dict(base_arms(p))
        if variant == "right_claw":
            wind, strike = _claw("r", p, big)
        elif variant == "left_claw":
            wind, strike = _claw("l", p, big)
        else:  # overhead_bite: two-hand overhead smash / bite lunge
            wind = dict(base_arms(p))
            for s in ("l", "r"):
                wind[f"upperarm_{s}"] = [("B", 40.0), ("P", -55.0 * big)]
                wind[f"lowerarm_{s}"] = [("P", 90.0)]
            wind["spine_03"] = [("P", -22.0 * big)]
            wind["neck_01"] = [("P", -18.0)]
            strike = dict(base_arms(p))
            for s in ("l", "r"):
                strike[f"upperarm_{s}"] = [("B", -30.0), ("P", 45.0 * big)]
                strike[f"lowerarm_{s}"] = [("P", 20.0)]
            strike["spine_03"] = [("P", 30.0 * big)]
            strike["neck_01"] = [("P", 22.0)]
        recover = {k: [(a, d * (0.35 if floppy else 0.15)) for a, d in v] for k, v in strike.items()}
        f_wind = round(n * 0.32)
        f_hit = round(n * 0.55)
        f_recover = round(n * (0.85 if not floppy else 0.95))
        frames = {0: (neutral, None), f_wind: (wind, None), f_hit: (strike, None),
                  f_recover: (recover, None), n: (neutral, None)}
        return frames, False, n, f_hit

    def build_spawn(p, tone, length_s):
        n = round(length_s * FPS)
        buried = Vector((0.0, 0.0, PELVIS_REST_Z - 110.0))
        rising = Vector((0.0, 0.0, PELVIS_REST_Z - 45.0))
        cresting = Vector((0.0, 0.0, PELVIS_REST_Z - 8.0))
        standing = Vector((0.0, 0.0, PELVIS_REST_Z))
        claw_up = dict(base_arms(p))
        for s in ("l", "r"):
            claw_up[f"upperarm_{s}"] = [("B", 60.0), ("P", -70.0)]
            claw_up[f"lowerarm_{s}"] = [("P", 20.0)]
        claw_up["spine_01"] = [("P", 20.0)]
        claw_up["spine_03"] = [("P", 15.0)]
        pull = dict(base_arms(p))
        for s in ("l", "r"):
            pull[f"upperarm_{s}"] = [("B", 10.0), ("P", 55.0)]
            pull[f"lowerarm_{s}"] = [("P", 80.0)]
        pull["spine_02"] = [("P", -25.0)]
        idle_frames, _, _ = build_idle(p, tone)
        neutral = idle_frames[0][0]
        frames = {
            0: (claw_up, buried),
            round(n * 0.35): (claw_up, rising),
            round(n * 0.6): (pull, cresting),
            round(n * 0.85): ({k: [(a, d * 0.4) for a, d in v] for k, v in pull.items()}, standing),
            n: (neutral, standing),
        }
        return frames, False, n

    def _death_shape(variant, p, big):
        if variant == "fall_back":
            spine = [("P", 70.0 * big)]
            arms = [("B", 20.0), ("P", -40.0)]
            pelvis_z = PELVIS_REST_Z - (85.0 if big > 1.0 else 78.0)
            yaw = 0.0
        elif variant == "crumple_forward":
            spine = [("P", -95.0 * big)]
            arms = [("B", -10.0), ("P", 45.0)]
            pelvis_z = PELVIS_REST_Z - 82.0
            yaw = 0.0
        else:  # spin_side
            spine = [("Y", 60.0), ("B", 55.0 * big)]
            arms = [("B", -5.0), ("P", 20.0)]
            pelvis_z = PELVIS_REST_Z - 80.0
            yaw = 70.0
        pose = {"spine_02": spine, "spine_03": [(a, d * 0.6) for a, d in spine]}
        for s in ("l", "r"):
            pose[f"upperarm_{s}"] = arms
            pose[f"lowerarm_{s}"] = [("P", 40.0)]
        if yaw:
            pose["pelvis"] = [("Y", yaw)]
        return pose, pelvis_z

    def build_death(variant, p, tone):
        heavy = tone == "heavy"
        floppy = tone == "floppy"
        big = 1.2 if heavy else (1.1 if floppy else 1.0)
        length_s = 1.6 if heavy else (2.0 if floppy else 1.4)
        n = round(length_s * FPS)
        neutral = dict(base_arms(p))
        hit = {k: [(a, d * 0.5) for a, d in v] for k, v in neutral.items()}
        hit["spine_03"] = [("P", -18.0)]
        landed, pelvis_z = _death_shape(variant, p, big)
        settle = {k: [(a, d * 1.08) for a, d in v] for k, v in landed.items()}
        rest_pos = Vector((0.0, 0.0, PELVIS_REST_Z))
        land_pos = Vector((0.0, 0.0, pelvis_z))
        frames = {
            0: (neutral, rest_pos),
            round(n * 0.15): (hit, rest_pos),
            round(n * 0.55): (landed, land_pos),
            n: (settle, land_pos),
        }
        return frames, False, n

    def build_special(clip_name, p, tone):
        heavy = tone == "heavy"
        if clip_name == "ChargeWindup":
            n = round(1.0 * FPS)
            wind = dict(base_arms(p))
            wind["spine_02"] = [("P", -30.0)]
            wind["spine_03"] = [("P", -20.0)]
            wind["neck_01"] = [("P", -20.0)]
            wind["thigh_r"] = [("P", -14.0)]
            paw = {k: list(v) for k, v in wind.items()}
            paw["thigh_r"] = [("P", 10.0)]
            paw["calf_r"] = [("P", 20.0)]
            neutral = dict(base_arms(p))
            frames = {0: (neutral, None), round(n * 0.4): (wind, None),
                      round(n * 0.7): (paw, None), n: (wind, None)}
            return frames, False, n, None
        if clip_name == "Charge":
            return build_locomotion("charge", p, tone, n_keys=7, loop=True, speed=1.3) + (None,)
        if clip_name == "Stun":
            n = round(1.5 * FPS)
            frames = {}
            for i, ph in enumerate((0.0, 0.25, 0.5, 0.75, 1.0)):
                f = round(ph * n)
                pose = dict(base_arms(p))
                pose["spine_02"] = [("B", 18.0 * math.sin(2 * math.pi * ph))]
                pose["spine_03"] = [("B", 14.0 * math.sin(2 * math.pi * ph + 0.6))]
                pose["head"] = [("Y", 20.0 * math.sin(2 * math.pi * ph + 1.2)),
                                ("P", 8.0 * math.sin(2 * math.pi * ph))]
                for s in ("l", "r"):
                    pose[f"upperarm_{s}"] = [("B", 6.0 * math.sin(2 * math.pi * ph + (0.0 if s == "l" else 3.0)))]
                frames[f] = (pose, None)
            return frames, True, n, None
        if clip_name == "Lunge":
            n = round(1.1 * FPS)
            crouch = dict(base_arms(p))
            crouch["spine_02"] = [("P", -25.0)]
            crouch["thigh_l"] = crouch["thigh_r"] = [("P", -35.0)]
            crouch["calf_l"] = crouch["calf_r"] = [("P", 55.0)]
            thrust = dict(base_arms(p))
            for s in ("l", "r"):
                thrust[f"upperarm_{s}"] = [("B", -35.0), ("P", 70.0)]
                thrust[f"lowerarm_{s}"] = [("P", 10.0)]
            thrust["spine_02"] = [("P", 45.0)]
            thrust["spine_03"] = [("P", 20.0)]
            thrust["thigh_l"] = thrust["thigh_r"] = [("P", 45.0)]
            thrust["calf_l"] = thrust["calf_r"] = [("P", 10.0)]
            recover = dict(base_arms(p))
            neutral = dict(base_arms(p))
            f_hit = round(n * 0.55)
            frames = {0: (neutral, None), round(n * 0.3): (crouch, None), f_hit: (thrust, None),
                      round(n * 0.8): (recover, None), n: (neutral, None)}
            return frames, False, n, f_hit
        if clip_name == "Lob":
            n = round(1.0 * FPS)
            rear = dict(base_arms(p))
            for s in ("l", "r"):
                rear[f"upperarm_{s}"] = [("B", 30.0), ("P", -60.0)]
                rear[f"lowerarm_{s}"] = [("P", 100.0)]
            rear["spine_02"] = [("P", -30.0)]
            rear["neck_01"] = [("P", -15.0)]
            release = dict(base_arms(p))
            for s in ("l", "r"):
                release[f"upperarm_{s}"] = [("B", -25.0), ("P", 55.0)]
                release[f"lowerarm_{s}"] = [("P", 10.0)]
            release["spine_02"] = [("P", 35.0)]
            recover = {k: [(a, d * 0.3) for a, d in v] for k, v in release.items()}
            neutral = dict(base_arms(p))
            f_release = round(n * 0.55)
            frames = {0: (neutral, None), round(n * 0.35): (rear, None), f_release: (release, None),
                      round(n * 0.8): (recover, None), n: (neutral, None)}
            return frames, False, n, f_release
        if clip_name == "Shriek":
            n = round(1.5 * FPS)
            arch = dict(base_arms(p))
            for s in ("l", "r"):
                arch[f"upperarm_{s}"] = [("B", 80.0), ("P", -20.0)]
                arch[f"lowerarm_{s}"] = [("P", 5.0)]
            arch["spine_02"] = [("P", -35.0)]
            arch["spine_03"] = [("P", -30.0)]
            arch["neck_01"] = [("P", -35.0)]
            arch["head"] = [("P", -20.0)]
            neutral = dict(base_arms(p))
            settle = {k: [(a, d * 0.7) for a, d in v] for k, v in arch.items()}
            frames = {0: (neutral, None), round(n * 0.45): (arch, None),
                      round(n * 0.75): (settle, None), n: (neutral, None)}
            return frames, False, n, None
        if clip_name == "FleeRun":
            return build_locomotion("fleerun", p, tone, n_keys=9, loop=True, speed=1.5) + (None,)
        if clip_name == "Swell":
            n = round(1.5 * FPS)
            frames = {}
            steps = 7
            for i in range(steps + 1):
                t = i / steps
                f = round(t * n)
                amp = 3.0 + 22.0 * t
                freq = 1.0 + 5.0 * t
                pose = dict(base_arms(p))
                spread = 25.0 * t
                for s in ("l", "r"):
                    pose[f"upperarm_{s}"] = [("B", 20.0 + spread)]
                shake = amp * math.sin(freq * t * 10.0 + (0 if i % 2 == 0 else math.pi))
                pose["spine_01"] = [("B", shake * 0.5)]
                pose["spine_02"] = [("B", -shake)]
                pose["spine_03"] = [("B", shake * 0.7)]
                frames[f] = (pose, None)
            return frames, False, n, None
        fail(f"unknown special clip {clip_name}")

    # ------------------------------------------------------------------------------------------------------- key + export
    def key_and_export(type_name, clip_name, frames, loop, n_frames, hit_frame=None):
        act = bpy.data.actions.new(f"A_Z_{type_name}_{clip_name}")
        act.use_fake_user = True
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = act
        scene.frame_start, scene.frame_end = 0, n_frames
        for f in sorted(frames):
            scene.frame_set(f)
            pose, ppos = frames[f]
            reset_all()
            apply_pose(pose, ppos)
            for name in ORDER:
                pbs[name].keyframe_insert("rotation_quaternion", frame=f, group=name)
            if ppos is not None:
                pbs["pelvis"].keyframe_insert("location", frame=f, group="pelvis")
        for fc in fcurves_of(arm):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER" if not loop else "LINEAR" if False else "BEZIER"
            fc.update()
        # loop safety: verify first/last keyed pose match
        keys = sorted(frames)
        if loop and len(keys) >= 2:
            f0, f1 = keys[0], keys[-1]
            if frames[f0][0] != frames[f1][0]:
                print(f"ZOMBIE_ANIM WARN {type_name} {clip_name} loop endpoints differ")
        bpy.ops.object.mode_set(mode="OBJECT")
        scene.frame_set(0)
        bpy.ops.object.mode_set(mode="POSE")
        bpy.ops.object.mode_set(mode="OBJECT")
        os.makedirs(FDIR, exist_ok=True)
        out = os.path.join(FDIR, f"A_Z_{type_name}_{clip_name}.fbx")
        bpy.ops.object.select_all(action="DESELECT")
        arm.select_set(True)
        vl.objects.active = arm
        bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={"ARMATURE"},
                                 apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                                 add_leaf_bones=False, bake_anim=True, bake_anim_use_all_bones=True,
                                 bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
                                 bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                                 bake_anim_simplify_factor=0.0)
        bpy.ops.object.mode_set(mode="POSE")
        if not os.path.isfile(out):
            fail(f"export missing for {type_name} {clip_name}")
        note = f" hit={hit_frame}" if hit_frame is not None else ""
        print(f"ZOMBIE_ANIM OK {type_name} {clip_name} frames={n_frames}{note}")
        return n_frames, hit_frame

    def dispatch(type_name, clip_name):
        p = TYPE_PARAMS[type_name]
        tone = p["tone"]
        if clip_name == "Idle":
            frames, loop, n = build_idle(p, tone)
            return key_and_export(type_name, clip_name, frames, loop, n)
        if clip_name in ("Walk", "Run", "Sprint"):
            kind = {"Walk": "walk", "Run": "run", "Sprint": "sprint"}[clip_name]
            speed = {"Walk": p["speed_walk"], "Run": p["speed_run"], "Sprint": p["speed_run"] * 1.35}[clip_name]
            frames, loop, n = build_locomotion(kind, p, tone, speed=speed)
            return key_and_export(type_name, clip_name, frames, loop, n)
        if clip_name == "Spawn":
            frames, loop, n = build_spawn(p, tone, SPAWN_LEN[type_name])
            return key_and_export(type_name, clip_name, frames, loop, n)
        if clip_name in ("Attack1", "Attack2", "Attack3"):
            variant = {"Attack1": "right_claw", "Attack2": "left_claw", "Attack3": "overhead_bite"}[clip_name]
            frames, loop, n, hit = build_attack(variant, p, tone)
            return key_and_export(type_name, clip_name, frames, loop, n, hit)
        if clip_name == "HitReact":
            frames, loop, n = build_hitreact(p, tone)
            return key_and_export(type_name, clip_name, frames, loop, n)
        if clip_name in ("Death1", "Death2", "Death3"):
            variant = {"Death1": "fall_back", "Death2": "crumple_forward", "Death3": "spin_side"}[clip_name]
            frames, loop, n = build_death(variant, p, tone)
            return key_and_export(type_name, clip_name, frames, loop, n)
        # type-specific extras
        frames, loop, n, hit = build_special(clip_name, p, tone)
        return key_and_export(type_name, clip_name, frames, loop, n, hit)

    types = [ARGS_TYPE] if ARGS_TYPE else TYPES
    for t in types:
        if t not in TYPE_PARAMS:
            fail(f"unknown type {t}")
    summary = {}
    total = 0
    for t in types:
        clips = [ARGS_CLIP] if ARGS_CLIP else clip_list(t)
        for c in clips:
            if c not in clip_list(t):
                fail(f"clip {c} not valid for type {t}")
            n, hit = dispatch(t, c)
            summary[(t, c)] = (n, hit)
            total += 1

    bpy.ops.object.mode_set(mode="OBJECT")
    os.makedirs(BDIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"ZOMBIE_ANIM SUMMARY types={len(types)} clips={total} blend={os.path.getsize(OUT_BLEND)}")
    print("ZOMBIE_ANIM ALL_OK")


if __name__ == "__main__":
    main()

"""Re-author the Shambler clips on the IK rig, in the style of the hand-animated idle.

Every clip is built as deltas on top of A_Z_Shambler_Idle frame 0 (the hand-made base
pose). Legs are driven by ik_foot_l/r + ik_knee_l/r; arms stay FK. Keys are sparse
Bezier with per-group timing offsets (hips lead, spine/arms/head/hands trail), which is
how the idle is keyed.

Only the 10 non-idle A_Z_Shambler_* actions are replaced. The idle and every other
zombie type are left untouched.

Run inside Blender (Scripting tab) to apply to the open file, or headless:
  blender --background --factory-startup A_Z_Anims.blend --python blender_shambler_ik_anims.py -- --out <copy.blend>
Headless runs never overwrite the source file unless --out points at it.
"""
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

IDLE = "A_Z_Shambler_Idle"
PREFIX = "A_Z_Shambler_"

# Character frame -> world: character faces -Y, x = character right = world -X.
RV = Vector((-1.0, 0.0, 0.0))   # right  (+P about it: forward limbs swing up, spine tilts back, toe lifts)
FV = Vector((0.0, -1.0, 0.0))   # forward (+B about it: top tips to character right)
UV = Vector((0.0, 0.0, 1.0))    # up     (+Y about it: facing turns to character left)

# Tunables
WALK_HALF_STRIDE = 20.0
RUN_HALF_STRIDE = 30.0

GROUPS = {
    "legs": ["ik_foot_l", "ik_foot_r", "ik_knee_l", "ik_knee_r", "foot_l", "foot_r", "ball_l", "ball_r"],
    "pelvis": ["pelvis"],
    "spine": ["spine_01", "spine_02", "spine_03"],
    "shoulders": ["clavicle_l", "clavicle_r", "upperarm_l", "upperarm_r"],
    "headgrp": ["neck_01", "head"],
    "forearms": ["lowerarm_l", "lowerarm_r"],
    "hands": ["hand_l", "hand_r"],
    "fingers": [],  # filled from the rig
}
LAG = {"legs": 0, "pelvis": 0, "spine": 1, "shoulders": 2, "headgrp": 3, "forearms": 4, "hands": 5, "fingers": 6}
FINGERS = ["index", "middle", "ring", "pinky"]

LOC_BONES = {"pelvis", "ik_foot_l", "ik_foot_r", "ik_knee_l", "ik_knee_r"}


def side_of(name):
    if name.endswith("_l"):
        return "l"
    if name.endswith("_r"):
        return "r"
    return ""


SIGN_B = {"l": 1.0, "r": -1.0, "": 1.0}
SIGN_Y = {"l": -1.0, "r": 1.0, "": 1.0}


def world_rot(pby, side=""):
    p, b, y = pby
    rq = (Quaternion(UV, math.radians(y * SIGN_Y[side])) @
          Quaternion(RV, math.radians(p)) @
          Quaternion(FV, math.radians(b * SIGN_B[side])))
    return rq


def c2w(v):
    """character-frame vector (x right, y forward, z up) -> world."""
    return Vector((-v[0], -v[1], v[2]))


def smooth(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


def lerp(a, b, u):
    return a + (b - a) * u


# ---------------------------------------------------------------- rig / base

class Rig:
    def __init__(self):
        self.arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        self.pb = self.arm.pose.bones
        self.idle = bpy.data.actions[IDLE]
        ad = self.arm.animation_data or self.arm.animation_data_create()
        ad.action = self.idle
        self.slot = ad.action_slot
        bpy.context.scene.frame_set(0)
        self.vl = bpy.context.view_layer
        self.vl.update()
        self.base_loc = {p.name: p.location.copy() for p in self.pb}
        self.base_rot = {p.name: p.rotation_quaternion.copy() for p in self.pb}
        self.base_scl = {p.name: p.scale.copy() for p in self.pb}
        self.qB = {p.name: p.matrix.to_quaternion() for p in self.pb}
        self.head = {p.name: p.head.copy() for p in self.pb}
        for n in ("root", "ik_foot_root"):
            if n in self.pb:
                d = (self.pb[n].matrix - self.arm.data.bones[n].matrix_local)
                assert max(abs(x) for row in d for x in row) < 1e-3, f"{n} not at rest in idle"
        fingers = [p.name for p in self.pb if any(p.name.startswith(f + "_0") for f in FINGERS + ["thumb"])]
        GROUPS["fingers"] = fingers
        self.group_of = {b: g for g, bl in GROUPS.items() for b in bl}
        # finger curl axis per side, taken from the idle's own finger rotation
        self.curl_axis = {}
        for s in "lr":
            q = self.base_rot[f"index_01_{s}"]
            ax = Vector((q.x, q.y, q.z))
            self.curl_axis[s] = ax.normalized() if ax.length > 1e-4 else Vector((1, 0, 0))

    def ankle_char(self, s):
        h = self.head[f"foot_{s}"]
        return Vector((-h.x, -h.y, h.z))

    def ball_char(self, s):
        h = self.head[f"ball_{s}"]
        return Vector((-h.x, -h.y, h.z))

    def reset(self):
        for p in self.pb:
            p.location = self.base_loc[p.name]
            p.rotation_quaternion = self.base_rot[p.name]
            p.scale = self.base_scl[p.name]

    def apply(self, pose):
        """pose: dict channel -> value. Returns dict bone -> (loc, quat) locals."""
        self.reset()
        for name, v in pose.items():
            if name in self.pb and name not in ("foot_l", "foot_r"):
                if name in LOC_BONES and not isinstance(v, tuple):
                    continue
                if name in LOC_BONES and name != "pelvis":
                    continue
                s = side_of(name)
                R = world_rot(v, s)
                qb = self.qB[name]
                self.pb[name].rotation_quaternion = self.base_rot[name] @ (qb.inverted() @ R @ qb)
        for name in LOC_BONES:
            key = name + "_loc" if name == "pelvis" else name
            if key in pose:
                wd = c2w(pose[key])
                ml = self.arm.data.bones[name].matrix_local.to_3x3()
                self.pb[name].location = self.base_loc[name] + ml.inverted() @ wd
        for s in "lr":
            c = pose.get(f"curl_{s}", 0.0)
            if c:
                for f in FINGERS:
                    for i, k in ((1, 0.7), (2, 1.0), (3, 0.8)):
                        n = f"{f}_0{i}_{s}"
                        if n in self.pb:
                            self.pb[n].rotation_quaternion = self.base_rot[n] @ Quaternion(self.curl_axis[s], math.radians(c * k))
                tn = f"thumb_02_{s}"
                if tn in self.pb:
                    self.pb[tn].rotation_quaternion = self.base_rot[tn] @ Quaternion(self.curl_axis[s], math.radians(c * 0.4))
        self.vl.update()
        # feet: absolute world orientation = R_foot @ base orientation, independent of the IK'd calf
        for s in "lr":
            fb = self.pb[f"foot_{s}"]
            R = world_rot(pose.get(f"foot_{s}", (0.0, 0.0, 0.0)), s)
            head = fb.matrix.to_translation()
            m = (R @ self.qB[fb.name]).to_matrix().to_4x4()
            m.translation = head
            fb.matrix = m
        self.vl.update()


# ---------------------------------------------------------------- pose helpers

def add(pose, name, v):
    if name in pose:
        a = pose[name]
        pose[name] = tuple(x + y for x, y in zip(a, v))
    else:
        pose[name] = tuple(v)


def blend(a, b, u):
    out = {}
    for k in set(a) | set(b):
        va = a.get(k)
        vb = b.get(k)
        if isinstance(va, tuple) or isinstance(vb, tuple):
            n = len(va if va is not None else vb)
            va = va or (0.0,) * n
            vb = vb or (0.0,) * n
            out[k] = tuple(lerp(x, y, u) for x, y in zip(va, vb))
        else:
            out[k] = lerp(va or 0.0, vb or 0.0, u)
    return out


def mirror(pose):
    """Swap sides. Sided channels already mirror B/Y through SIGN_*, so only swap names;
    center rotations negate B and Y; character-frame x flips."""
    out = {}
    for k, v in pose.items():
        if k.endswith("_l"):
            nk = k[:-2] + "_r"
        elif k.endswith("_r"):
            nk = k[:-2] + "_l"
        else:
            nk = k
        if k == "pelvis_loc" or k.startswith("ik_"):
            v = (-v[0], v[1], v[2])
        elif isinstance(v, tuple) and not side_of(k):
            v = (v[0], -v[1], -v[2])
        out[nk] = v
    return out


def plant(s, pitch, rig, fwd=0.0, side=0.0, up=0.0, yaw=0.0):
    """IK foot target + foot rotation for a foot pitched about heel (pitch>0) or ball (pitch<0),
    in character cm relative to its idle spot. Returns partial pose."""
    ank = rig.ankle_char(s)
    ball = rig.ball_char(s)
    if pitch >= 0:
        piv = Vector((ank.x, ank.y - 4.0, 0.0))
    else:
        piv = Vector((ank.x, ball.y, 0.0))
    th = math.radians(pitch)
    dy, dz = ank.y - piv.y, ank.z - piv.z
    ny = piv.y + dy * math.cos(th) - dz * math.sin(th)
    nz = piv.z + dy * math.sin(th) + dz * math.cos(th)
    off = Vector((0.0, ny - ank.y, nz - ank.z))
    if yaw:
        off = Quaternion(Vector((0, 0, 1)), math.radians(yaw)).to_matrix() @ off
    pose = {
        f"ik_foot_{s}": (side + off.x, fwd + off.y, up + off.z),
        f"foot_{s}": (pitch, 0.0, yaw * SIGN_Y[s]),  # yaw given in character frame
        f"ball_{s}": (max(0.0, -pitch) * 0.9, 0.0, 0.0),
    }
    return pose


def knee(s, fwd=0.0, side_in=0.0, up=0.0, xs=0.0):
    """Knee pole offset: side_in>0 = toward the midline (knock-kneed)."""
    inward = 1.0 if s == "l" else -1.0  # left leg sits at char -x, inward is +x
    return {f"ik_knee_{s}": (xs + side_in * inward, fwd, up)}


def merge(*ps):
    out = {}
    for p in ps:
        for k, v in p.items():
            if isinstance(v, tuple):
                add(out, k, v)
            else:
                out[k] = out.get(k, 0.0) + v
    return out


# ---------------------------------------------------------------- keying

def fcurves_for(act, arm):
    ad = arm.animation_data
    try:
        from bpy_extras import anim_utils
        bag = anim_utils.action_ensure_channelbag_for_slot(act, ad.action_slot)
        return bag.fcurves
    except Exception:
        return act.fcurves


def new_action(rig, name):
    old = bpy.data.actions.get(name)
    if old is not None:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ad = rig.arm.animation_data
    ad.action = act
    if ad.action_slot is None:
        slots = [s for s in act.slots]
        if slots:
            ad.action_slot = slots[0]
    return act


def key_bone(rig, name, frame, act_name):
    p = rig.pb[name]
    p.keyframe_insert("location", frame=frame, group=name)
    p.keyframe_insert("rotation_quaternion", frame=frame, group=name)
    p.keyframe_insert("scale", frame=frame, group=name)


ALL_BONES = None


def build(rig, name, length, pose_at, key_times):
    """pose_at(t) -> pose dict. key_times: dict group -> list of (frame, t)."""
    act = new_action(rig, name)
    for g, bones in GROUPS.items():
        for frame, t in key_times[g]:
            rig.apply(pose_at(t))
            for b in bones:
                key_bone(rig, b, frame, name)
    # every other bone: hold the idle base at start and end so the clip is fully keyed
    others = [p.name for p in rig.pb if p.name not in rig.group_of]
    rig.reset()
    for frame in (0, length):
        for b in others:
            key_bone(rig, b, frame, name)
    for fc in fcurves_for(act, rig.arm):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
        fc.update()
    act.frame_range = (0, length)
    act.use_frame_range = True
    return act


def loop_keys(length, n_legs, n_upper, lag_scale=1.0):
    kt = {}
    for g in GROUPS:
        n = n_legs if g in ("legs", "pelvis") else n_upper
        lag = LAG[g] * lag_scale
        frames = sorted({round(length * i / n) for i in range(n)} | {length})
        kt[g] = [(f, (f - lag) % length) for f in frames]
        kt[g][-1] = (length, kt[g][0][1])  # last == first for a clean loop
    return kt


def beat_keys(length, beats, lag_scale=1.0):
    """beats: sorted list of frames that have authored poses (must include 0 and length)."""
    kt = {}
    for g in GROUPS:
        lag = LAG[g] * lag_scale
        keys = [(0, 0.0)]
        for b in beats[1:-1]:
            f = round(b + lag)
            if 0 < f < length and f > keys[-1][0]:
                keys.append((f, float(b)))
        keys.append((length, float(length)))
        kt[g] = keys
    return kt


def beat_sampler(beats_poses):
    frames = [f for f, _ in beats_poses]

    def pose_at(t):
        for i in range(len(frames) - 1):
            if frames[i] <= t <= frames[i + 1]:
                u = (t - frames[i]) / max(1e-6, frames[i + 1] - frames[i])
                return blend(beats_poses[i][1], beats_poses[i + 1][1], smooth(u))
        return beats_poses[-1][1]
    return pose_at, frames


# ---------------------------------------------------------------- clips: locomotion

def gait_foot(rig, s, ph, stance, S, lift, drag):
    """ph in [0,1). Returns (pose, is_stance)."""
    if ph < stance:
        u = ph / stance
        fwd = S - 2.0 * S * u
        if u < 0.12:
            pitch = 12.0 * (1.0 - u / 0.12)
        elif u > 0.78:
            pitch = -20.0 * smooth((u - 0.78) / 0.22)
        else:
            pitch = 0.0
        p = plant(s, pitch, rig, fwd=fwd)
        return p, True
    u = (ph - stance) / (1.0 - stance)
    fwd = -S + 2.0 * S * smooth(u)
    z = lift * math.sin(math.pi * (u ** 0.75))
    toe0 = -30.0 if drag else -20.0
    pitch = lerp(toe0, 8.0 if not drag else -5.0, smooth(u * 1.2))
    p = plant(s, 0.0, rig, fwd=fwd, up=z)
    ank = rig.ankle_char(s)
    p[f"ik_foot_{s}"] = (0.0, fwd, z + max(0.0, -pitch) * 0.25)
    p[f"foot_{s}"] = (pitch, 0.0, 0.0)
    p[f"ball_{s}"] = (0.0, 0.0, 0.0)
    return p, False


def walk_pose_factory(rig, run=False):
    if run:
        stance, S, lift_l, lift_r, drop = 0.5, RUN_HALF_STRIDE, 14.0, 7.0, 11.0
        bob_a, sway_a, yaw_a, roll_a, lean = 4.0, 3.0, 9.0, 5.0, -12.0
    else:
        stance, S, lift_l, lift_r, drop = 0.62, WALK_HALF_STRIDE, 7.0, 3.0, 6.0
        bob_a, sway_a, yaw_a, roll_a, lean = 2.5, 3.0, 5.0, 4.0, -4.0

    def pose_at_norm(p):
        tw = 2 * math.pi * p
        pose = {}
        fl, st_l = gait_foot(rig, "l", p % 1.0, stance, S, lift_l, drag=False)
        fr, st_r = gait_foot(rig, "r", (p + 0.5) % 1.0, stance, S, lift_r, drag=True)
        pose.update(fl)
        pose.update(fr)
        for s, f in (("l", fl), ("r", fr)):
            fy = f[f"ik_foot_{s}"][1]
            pose.update(knee(s, fwd=fy * 0.8, side_in=4.0 + (2.0 if run else 0.0)))
        # pelvis: low, bobbing twice per cycle, limp dip on the right (dragging) leg's stance
        right_stance = 0.5 <= p < 0.5 + stance
        limp = -1.5 * math.sin(math.pi * ((p - 0.5) % 1.0) / stance) if right_stance else 0.0
        bob = -bob_a * 0.5 * (1 + math.cos(4 * math.pi * (p - 0.08))) - drop + limp
        sway = -sway_a * math.sin(tw)
        pose["pelvis_loc"] = (sway, 0.0, bob)
        pose["pelvis"] = (lean - 2.0 * math.sin(4 * math.pi * p), roll_a * math.sin(tw), -yaw_a * math.cos(tw))
        # spine counters the hips, with extra hunch
        for i, n in enumerate(("spine_01", "spine_02", "spine_03")):
            k = (i + 1) / 3.0
            pose[n] = (-2.0 - (3.0 if run else 0.0) + 1.5 * math.sin(4 * math.pi * p + 0.6),
                       -roll_a * 0.45 * math.sin(tw),
                       yaw_a * 0.5 * k * math.cos(tw))
        # head lolls to the right side and bobs late
        pose["neck_01"] = (2.5 * math.sin(4 * math.pi * p + 1.2), 3.0 + 3.0 * math.sin(tw + 0.8), 2.0 * math.cos(tw))
        pose["head"] = (3.5 * math.sin(4 * math.pi * p + 1.8), 2.0 + 3.0 * math.sin(tw + 1.2), 2.0 * math.cos(tw + 0.5))
        # arms: held out like the idle, bouncing with each step; floppy forearms and hands
        amp = 1.8 if run else 1.0
        for s, ph in (("l", 0.0), ("r", math.pi)):
            step = math.sin(4 * math.pi * p + 0.4)
            pose[f"clavicle_{s}"] = (1.5 * amp * step, 0.0, 0.0)
            pose[f"upperarm_{s}"] = (3.0 * amp * step + (-6.0 if run else 0.0) + 3.0 * math.sin(tw + ph),
                                     0.0, 3.0 * amp * math.sin(tw + ph))
            pose[f"lowerarm_{s}"] = (4.0 * amp * math.sin(4 * math.pi * p + 1.0) + (10.0 if run else 0.0), 0.0,
                                     2.0 * math.sin(tw + ph))
            pose[f"hand_{s}"] = (-7.0 * amp * math.sin(4 * math.pi * p + 1.6), 0.0, 3.0 * math.sin(tw + ph + 0.5))
            pose[f"curl_{s}"] = 6.0 + 4.0 * math.sin(tw + ph)
        return pose
    return pose_at_norm


def make_walk(rig, name, length, run):
    f = walk_pose_factory(rig, run)
    kt = loop_keys(length, 16 if not run else 8, 8 if not run else 7, lag_scale=1.0 if not run else 0.6)
    return build(rig, name, length, lambda t: f(t / length), kt)


# ---------------------------------------------------------------- clips: one-shots

def base():
    return {}


def spawn_beats(rig):
    B = []
    B.append((0, merge(
        {"pelvis_loc": (0, 8, -112), "pelvis": (-20, 0, 0)},
        plant("l", 0, rig, up=-112, fwd=5), plant("r", 0, rig, up=-112, fwd=-3),
        knee("l", up=-100), knee("r", up=-100),
        {"spine_01": (-8, 0, 0), "spine_02": (-8, 0, 0), "spine_03": (-5, 0, 0),
         "neck_01": (20, 0, 0), "head": (15, 0, 0),
         "upperarm_l": (60, 0, -15), "upperarm_r": (70, 0, -10),
         "lowerarm_l": (25, 0, 0), "lowerarm_r": (35, 0, 0),
         "hand_l": (-20, 0, 0), "hand_r": (-25, 0, 0), "curl_l": 30, "curl_r": 35})))
    B.append((16, merge(
        {"pelvis_loc": (2, 6, -82), "pelvis": (-30, 5, 5)},
        plant("l", 0, rig, up=-84, fwd=4), plant("r", 0, rig, up=-86, fwd=-3),
        knee("l", up=-72), knee("r", up=-74),
        {"spine_01": (-12, 3, 0), "spine_02": (-10, 3, 3), "spine_03": (-8, 0, 3),
         "neck_01": (15, 5, 0), "head": (10, 5, 0),
         "upperarm_l": (40, 0, -5), "upperarm_r": (15, 0, 5),
         "lowerarm_l": (20, 0, 0), "lowerarm_r": (5, 0, 0),
         "hand_l": (-30, 0, 0), "hand_r": (-40, 0, 0), "curl_l": 40, "curl_r": 45})))
    B.append((30, merge(
        {"pelvis_loc": (-3, 4, -46), "pelvis": (-35, -5, -5)},
        plant("l", 0, rig, up=-24, fwd=10), plant("r", 0, rig, up=-44, fwd=-4),
        knee("l", up=-20, fwd=10), knee("r", up=-40),
        {"spine_01": (-14, -3, 0), "spine_02": (-10, -3, 0), "spine_03": (-6, 0, 0),
         "neck_01": (12, 0, 0), "head": (8, -4, 0),
         "upperarm_l": (-20, 0, 0), "upperarm_r": (-35, 0, 5),
         "lowerarm_l": (5, 0, 0), "lowerarm_r": (0, 0, 0),
         "hand_l": (-35, 0, 0), "hand_r": (-45, 0, 0), "curl_l": 50, "curl_r": 55})))
    B.append((41, merge(
        {"pelvis_loc": (-4, 2, -26), "pelvis": (-24, -4, -4)},
        plant("l", 0, rig, fwd=14), plant("r", 0, rig, up=-12, fwd=-8),
        knee("l", fwd=14, side_in=3), knee("r", up=-10),
        {"spine_01": (-10, -3, 0), "spine_02": (-8, 0, 0), "spine_03": (-4, 0, 0),
         "neck_01": (8, 0, 0), "head": (4, -3, 0),
         "upperarm_l": (-10, 0, 0), "upperarm_r": (-15, 0, 0),
         "lowerarm_l": (0, 0, 0), "lowerarm_r": (-5, 0, 0),
         "hand_l": (-15, 0, 0), "hand_r": (-20, 0, 0), "curl_l": 25, "curl_r": 25})))
    B.append((53, merge(
        {"pelvis_loc": (2, 0, -10), "pelvis": (-10, 2, 2)},
        plant("l", 0, rig, fwd=6), plant("r", 0, rig, fwd=-2),
        knee("l", fwd=6, side_in=3), knee("r", side_in=3),
        {"spine_01": (-5, 2, 0), "spine_02": (-4, 0, 0), "spine_03": (-2, 0, 0),
         "neck_01": (-6, 3, 0), "head": (-4, 2, 0),
         "upperarm_l": (4, 0, 0), "upperarm_r": (2, 0, 0),
         "lowerarm_l": (6, 0, 0), "lowerarm_r": (4, 0, 0),
         "hand_l": (-8, 0, 0), "hand_r": (-10, 0, 0), "curl_l": 10, "curl_r": 12})))
    B.append((61, merge(
        {"pelvis_loc": (0, 0, -3), "pelvis": (2, 0, 0)},
        plant("l", 0, rig, fwd=2), plant("r", 0, rig),
        {"spine_01": (2, 0, 0), "spine_02": (2, 0, 0),
         "neck_01": (-4, 0, 0), "head": (-3, 0, 0),
         "upperarm_l": (5, 0, 0), "upperarm_r": (6, 0, 0),
         "hand_l": (6, 0, 0), "hand_r": (6, 0, 0)})))
    B.append((66, base()))
    return B


def claw_beats(rig):
    """Right-hand claw swipe. Hit at 18."""
    wind = merge(
        {"pelvis_loc": (1, -3, -3), "pelvis": (4, 0, -8)},
        plant("l", 0, rig), plant("r", 0, rig),
        {"spine_01": (3, 0, -6), "spine_02": (3, -3, -8), "spine_03": (2, -3, -6),
         "neck_01": (-6, 0, 6), "head": (-4, 0, 6),
         "clavicle_r": (10, 0, -8), "upperarm_r": (45, 0, -45), "lowerarm_r": (55, 0, 10), "hand_r": (25, 0, 0),
         "upperarm_l": (-10, 0, 8), "lowerarm_l": (5, 0, 0), "hand_l": (-10, 0, 0),
         "curl_r": -5, "curl_l": 20})
    strike = merge(
        {"pelvis_loc": (-2, 9, -9), "pelvis": (-10, -4, 14)},
        plant("l", 0, rig, fwd=18, side=1), plant("r", -15, rig, fwd=-4),
        knee("l", fwd=18, side_in=3),
        {"spine_01": (-8, 0, 8), "spine_02": (-8, 3, 12), "spine_03": (-8, 3, 10),
         "neck_01": (6, 0, -4), "head": (4, -4, -6),
         "clavicle_r": (-6, 0, 12), "upperarm_r": (-15, 0, 55), "lowerarm_r": (-5, 0, 10), "hand_r": (-30, 0, 10),
         "upperarm_l": (-12, 0, -10), "lowerarm_l": (8, 0, 0), "hand_l": (-5, 0, 0),
         "curl_r": 45, "curl_l": 20})
    follow = merge(
        {"pelvis_loc": (-3, 8, -9), "pelvis": (-12, -4, 18)},
        plant("l", 0, rig, fwd=18, side=1), plant("r", -15, rig, fwd=-4),
        knee("l", fwd=18, side_in=3),
        {"spine_01": (-9, 0, 10), "spine_02": (-9, 3, 14), "spine_03": (-9, 4, 10),
         "neck_01": (8, 3, -2), "head": (6, -2, -4),
         "clavicle_r": (-8, 0, 14), "upperarm_r": (-30, 0, 60), "lowerarm_r": (10, 0, 15), "hand_r": (-20, 0, 15),
         "upperarm_l": (-10, 0, -8), "hand_l": (-5, 0, 0),
         "curl_r": 55, "curl_l": 15})
    lift = merge(
        {"pelvis_loc": (-1, 4, -5), "pelvis": (-6, -2, 8)},
        plant("l", 0, rig, fwd=8, up=5), plant("r", 0, rig, fwd=-2),
        knee("l", fwd=8, side_in=3),
        {"spine_01": (-5, 0, 5), "spine_02": (-5, 2, 6), "spine_03": (-4, 2, 4),
         "neck_01": (4, 2, 0), "head": (3, 0, -2),
         "upperarm_r": (-15, 0, 30), "lowerarm_r": (15, 0, 8), "hand_r": (-15, 0, 5),
         "curl_r": 30, "curl_l": 10})
    recover = merge(
        {"pelvis_loc": (0, 1, -1), "pelvis": (-1, 0, 2)},
        plant("l", 0, rig, fwd=1), plant("r", 0, rig),
        {"spine_02": (-1, 0, 1), "upperarm_r": (-4, 0, 6), "lowerarm_r": (4, 0, 0), "hand_r": (-5, 0, 0),
         "curl_r": 8})
    return [(0, base()), (9, wind), (18, strike), (24, follow), (27, lift), (31, recover), (33, base())]


def bite_beats(rig):
    """Two-hand overhead grab and bite. Hit at 18."""
    wind = merge(
        {"pelvis_loc": (0, -4, -4), "pelvis": (8, 0, 0)},
        plant("l", 0, rig), plant("r", 0, rig),
        {"spine_01": (5, 0, 0), "spine_02": (6, 0, 0), "spine_03": (5, 0, 0),
         "neck_01": (12, 0, 0), "head": (14, 0, 0),
         "clavicle_l": (12, 0, 0), "clavicle_r": (12, 0, 0),
         "upperarm_l": (70, 0, -10), "upperarm_r": (72, 0, -10),
         "lowerarm_l": (30, 0, 0), "lowerarm_r": (30, 0, 0),
         "hand_l": (20, 0, 0), "hand_r": (20, 0, 0), "curl_l": -5, "curl_r": -5})
    strike = merge(
        {"pelvis_loc": (0, 12, -12), "pelvis": (-14, 0, 0)},
        plant("r", 0, rig, fwd=22, side=-1), plant("l", -18, rig, fwd=-5),
        knee("r", fwd=22, side_in=3),
        {"spine_01": (-10, 0, 0), "spine_02": (-12, 0, 0), "spine_03": (-12, 0, 0),
         "neck_01": (-6, 0, 0), "head": (-12, 0, 0),
         "clavicle_l": (-6, 0, 4), "clavicle_r": (-6, 0, 4),
         "upperarm_l": (-10, 0, 15), "upperarm_r": (-12, 0, 15),
         "lowerarm_l": (-8, 0, 0), "lowerarm_r": (-8, 0, 0),
         "hand_l": (-25, 0, 0), "hand_r": (-25, 0, 0), "curl_l": 50, "curl_r": 50})
    follow = merge(
        {"pelvis_loc": (0, 10, -13), "pelvis": (-16, 0, 3)},
        plant("r", 0, rig, fwd=22, side=-1), plant("l", -18, rig, fwd=-5),
        knee("r", fwd=22, side_in=3),
        {"spine_01": (-11, 0, 0), "spine_02": (-13, 0, 2), "spine_03": (-12, 0, 2),
         "neck_01": (-2, 0, 4), "head": (6, 4, 8),  # tearing shake
         "upperarm_l": (-18, 0, 18), "upperarm_r": (-18, 0, 18),
         "lowerarm_l": (10, 0, 0), "lowerarm_r": (10, 0, 0),
         "hand_l": (-30, 0, 0), "hand_r": (-30, 0, 0), "curl_l": 60, "curl_r": 60})
    lift = merge(
        {"pelvis_loc": (0, 4, -6), "pelvis": (-7, 0, 0)},
        plant("r", 0, rig, fwd=9, up=5), plant("l", 0, rig, fwd=-2),
        knee("r", fwd=9, side_in=3),
        {"spine_01": (-5, 0, 0), "spine_02": (-6, 0, 0), "spine_03": (-5, 0, 0),
         "neck_01": (2, 0, -4), "head": (-4, -4, -6),
         "upperarm_l": (-10, 0, 8), "upperarm_r": (-10, 0, 8),
         "lowerarm_l": (8, 0, 0), "lowerarm_r": (8, 0, 0),
         "hand_l": (-15, 0, 0), "hand_r": (-15, 0, 0), "curl_l": 30, "curl_r": 30})
    recover = merge(
        {"pelvis_loc": (0, 1, -1), "pelvis": (-1, 0, 0)},
        plant("r", 0, rig, fwd=1), plant("l", 0, rig),
        {"spine_02": (-1, 0, 0), "head": (2, 0, 0), "hand_l": (-4, 0, 0), "hand_r": (-4, 0, 0),
         "curl_l": 6, "curl_r": 6})
    return [(0, base()), (9, wind), (18, strike), (24, follow), (27, lift), (31, recover), (33, base())]


def hitreact_beats(rig):
    snap = merge(
        {"pelvis_loc": (0, -5, -3), "pelvis": (10, -3, 4)},
        plant("l", 0, rig), plant("r", 12, rig, fwd=2),
        {"spine_01": (6, 0, 0), "spine_02": (8, -3, 3), "spine_03": (8, -3, 3),
         "neck_01": (14, -4, 0), "head": (16, -6, 6),
         "upperarm_l": (18, 0, -12), "upperarm_r": (14, 0, -10),
         "lowerarm_l": (15, 0, 0), "lowerarm_r": (12, 0, 0),
         "hand_l": (25, 0, 0), "hand_r": (20, 0, 0), "curl_l": -5, "curl_r": -5})
    over = merge(
        {"pelvis_loc": (0, 2, -3), "pelvis": (-4, 1, -1)},
        plant("l", 0, rig), plant("r", 0, rig),
        {"spine_01": (-3, 0, 0), "spine_02": (-4, 1, 0), "spine_03": (-4, 1, 0),
         "neck_01": (-6, 2, 0), "head": (-7, 3, -2),
         "upperarm_l": (-6, 0, 4), "upperarm_r": (-5, 0, 3),
         "lowerarm_l": (-4, 0, 0), "lowerarm_r": (-4, 0, 0),
         "hand_l": (-12, 0, 0), "hand_r": (-10, 0, 0), "curl_l": 12, "curl_r": 12})
    return [(0, base()), (3, snap), (7, over), (12, base())]


def death1_beats(rig):
    """Falls backward."""
    hit = merge(
        {"pelvis_loc": (0, -6, -3), "pelvis": (12, 0, 0)},
        plant("l", 0, rig), plant("r", 10, rig, fwd=2),
        {"spine_01": (8, 0, 0), "spine_02": (10, 0, 0), "spine_03": (10, 0, 0),
         "neck_01": (15, 0, 0), "head": (18, 4, 0),
         "upperarm_l": (25, 0, -20), "upperarm_r": (22, 0, -20),
         "lowerarm_l": (20, 0, 0), "lowerarm_r": (20, 0, 0),
         "hand_l": (20, 0, 0), "hand_r": (20, 0, 0), "curl_l": -5, "curl_r": -5})
    stagger = merge(
        {"pelvis_loc": (1, -14, -9), "pelvis": (16, -3, -4)},
        plant("l", 0, rig), plant("r", 0, rig, fwd=-20, side=-2),
        knee("r", fwd=-10),
        {"spine_01": (8, -3, 0), "spine_02": (10, -3, 0), "spine_03": (8, 0, 0),
         "neck_01": (10, 0, 0), "head": (12, 6, 4),
         "upperarm_l": (35, 0, -35), "upperarm_r": (30, 0, -35),
         "lowerarm_l": (15, 0, 0), "lowerarm_r": (20, 0, 0),
         "hand_l": (10, 0, 0), "hand_r": (15, 0, 0), "curl_l": 5, "curl_r": 5})
    give = merge(
        {"pelvis_loc": (0, -24, -40), "pelvis": (28, -2, -4)},
        plant("l", 0, rig, fwd=4), plant("r", 0, rig, fwd=-18, side=-2),
        knee("l", fwd=10, up=10), knee("r", fwd=0, up=10),
        {"spine_01": (10, 0, 0), "spine_02": (10, 0, 0), "spine_03": (8, 0, 0),
         "neck_01": (-8, 0, 0), "head": (-10, 6, 4),
         "upperarm_l": (50, 0, -45), "upperarm_r": (45, 0, -45),
         "lowerarm_l": (5, 0, 0), "lowerarm_r": (8, 0, 0),
         "hand_l": (0, 0, 0), "hand_r": (0, 0, 0), "curl_l": 10, "curl_r": 10})
    impact = merge(
        {"pelvis_loc": (0, -38, -84), "pelvis": (75, -2, -4)},
        plant("l", 25, rig, fwd=10, up=-3), plant("r", 20, rig, fwd=-4, side=-3, up=-3),
        knee("l", fwd=10, up=25), knee("r", fwd=0, up=20),
        {"spine_01": (6, 0, 0), "spine_02": (5, 0, 0), "spine_03": (2, 0, 0),
         "neck_01": (-15, 0, 0), "head": (-15, 8, 10),
         "upperarm_l": (70, 0, -60), "upperarm_r": (65, 0, -60),
         "lowerarm_l": (-5, 0, 0), "lowerarm_r": (-5, 0, 0),
         "hand_l": (-10, 0, 0), "hand_r": (-10, 0, 0), "curl_l": 15, "curl_r": 15})
    bounce = merge(impact, {"pelvis_loc": (0, 0, 3), "pelvis": (-4, 0, 0), "neck_01": (6, 0, 0), "head": (6, 0, 0),
                            "upperarm_l": (8, 0, 0), "upperarm_r": (6, 0, 0)})
    settle = merge(
        {"pelvis_loc": (0, -40, -85), "pelvis": (79, -3, -6)},
        plant("l", 55, rig, fwd=20, up=-5, side=-6), plant("r", 50, rig, fwd=0, side=-4, up=-5),
        knee("l", fwd=20, up=20, side_in=-30), knee("r", fwd=0, up=16),
        {"spine_01": (6, 0, 0), "spine_02": (4, 0, 0), "spine_03": (2, 0, 0),
         "neck_01": (-12, 5, 10), "head": (-10, 12, 25),
         "upperarm_l": (78, 0, -75), "upperarm_r": (72, 0, -70),
         "lowerarm_l": (-8, 0, -10), "lowerarm_r": (-6, 0, -12),
         "hand_l": (-15, 0, 0), "hand_r": (-12, 0, 0), "curl_l": 25, "curl_r": 22})
    return [(0, base()), (7, hit), (16, stagger), (26, give), (34, impact), (38, bounce), (44, settle), (60, settle)]


def death2_beats(rig):
    """Knees buckle, then collapses face-down."""
    hit = merge(
        {"pelvis_loc": (0, -3, -4), "pelvis": (-10, 0, 0)},
        plant("l", 0, rig), plant("r", 0, rig),
        {"spine_01": (-10, 0, 0), "spine_02": (-12, 0, 0), "spine_03": (-10, 0, 0),
         "neck_01": (-8, 0, 0), "head": (-10, -4, 0),
         "upperarm_l": (-20, 0, 8), "upperarm_r": (-18, 0, 8),
         "lowerarm_l": (-5, 0, 0), "lowerarm_r": (-5, 0, 0),
         "hand_l": (-20, 0, 0), "hand_r": (-20, 0, 0), "curl_l": 25, "curl_r": 25})
    kneel = merge(
        {"pelvis_loc": (0, -6, -44), "pelvis": (-8, 3, 3)},
        plant("l", -60, rig, fwd=-38), plant("r", -60, rig, fwd=-42),
        knee("l", fwd=-10, up=-40), knee("r", fwd=-12, up=-40),
        {"spine_01": (-12, 0, 0), "spine_02": (-12, 0, 0), "spine_03": (-10, 0, 0),
         "neck_01": (-10, 3, 0), "head": (-10, 3, 4),
         "upperarm_l": (-40, 0, -5), "upperarm_r": (-38, 0, -5),
         "lowerarm_l": (0, 0, 0), "lowerarm_r": (0, 0, 0),
         "hand_l": (-15, 0, 0), "hand_r": (-15, 0, 0), "curl_l": 20, "curl_r": 20})
    tip = merge(
        {"pelvis_loc": (0, 12, -58), "pelvis": (-40, 3, 3)},
        plant("l", -75, rig, fwd=-45, up=-2), plant("r", -75, rig, fwd=-48, up=-2),
        knee("l", fwd=-10, up=-48), knee("r", fwd=-12, up=-48),
        {"spine_01": (-15, 0, 0), "spine_02": (-15, 0, 0), "spine_03": (-12, 0, 0),
         "neck_01": (10, 3, 0), "head": (12, 3, 4),
         "upperarm_l": (50, 0, -20), "upperarm_r": (45, 0, -20),
         "lowerarm_l": (0, 0, 0), "lowerarm_r": (0, 0, 0),
         "hand_l": (35, 0, 0), "hand_r": (35, 0, 0), "curl_l": -5, "curl_r": -5})
    flat = merge(
        {"pelvis_loc": (0, 50, -80), "pelvis": (-80, 4, 5)},
        plant("l", -85, rig, fwd=-58, up=-6), plant("r", -85, rig, fwd=-62, up=-6),
        knee("l", fwd=-25, up=-70), knee("r", fwd=-25, up=-70),
        {"spine_01": (-4, 0, 0), "spine_02": (-3, 0, 0), "spine_03": (-2, 0, 0),
         "neck_01": (20, 0, 10), "head": (15, 5, 30),
         "upperarm_l": (95, 0, -30), "upperarm_r": (85, 0, -40),
         "lowerarm_l": (15, 0, 0), "lowerarm_r": (20, 0, 0),
         "hand_l": (10, 0, 0), "hand_r": (10, 0, 0), "curl_l": 10, "curl_r": 12})
    bounce = merge(flat, {"pelvis_loc": (0, 0, 3), "pelvis": (4, 0, 0), "neck_01": (-6, 0, 0)})
    settle = merge(flat, {"pelvis_loc": (0, 1, -1), "neck_01": (2, 0, 3), "head": (2, 0, 5),
                          "curl_l": 12, "curl_r": 10})
    return [(0, base()), (6, hit), (20, kneel), (32, tip), (40, flat), (44, bounce), (50, settle), (60, settle)]


def death3_beats(rig):
    """Spins toward its right and falls on its side."""
    twist = merge(
        {"pelvis_loc": (4, 2, -6), "pelvis": (0, 8, -20)},
        plant("l", 0, rig, yaw=-15), plant("r", 0, rig),
        {"spine_01": (0, 5, -10), "spine_02": (2, 5, -12), "spine_03": (2, 5, -10),
         "neck_01": (6, 8, -8), "head": (8, 10, -10),
         "upperarm_l": (20, 0, -25), "upperarm_r": (30, 0, -40),
         "lowerarm_l": (10, 0, 0), "lowerarm_r": (15, 0, 0),
         "hand_l": (10, 0, 0), "hand_r": (15, 0, 0), "curl_l": 5, "curl_r": 5})
    spin = merge(
        {"pelvis_loc": (12, 4, -18), "pelvis": (-5, 12, -35)},
        plant("l", -20, rig, fwd=10, side=10, yaw=-35), plant("r", 0, rig, side=6, yaw=-20),
        knee("l", fwd=4, side_in=10), knee("r", side_in=-5),
        {"spine_01": (0, 5, -10), "spine_02": (0, 6, -10), "spine_03": (0, 6, -8),
         "neck_01": (-4, 10, -8), "head": (-6, 12, -10),
         "upperarm_l": (30, 0, -40), "upperarm_r": (40, 0, -55),
         "lowerarm_l": (5, 0, 0), "lowerarm_r": (5, 0, 0),
         "hand_l": (0, 0, 0), "hand_r": (5, 0, 0), "curl_l": 10, "curl_r": 10})
    fall = merge(
        {"pelvis_loc": (35, 8, -55), "pelvis": (-5, 55, -38)},
        plant("l", -30, rig, fwd=10, side=8, up=-2, yaw=-35), plant("r", 20, rig, side=2, up=-2, yaw=-30),
        knee("l", fwd=10, up=-20, xs=15), knee("r", fwd=10, up=-20, xs=15),
        {"spine_01": (0, 8, -5), "spine_02": (0, 8, -5), "spine_03": (0, 5, -4),
         "neck_01": (-6, -10, -5), "head": (-8, -12, -8),
         "upperarm_l": (50, 0, -50), "upperarm_r": (30, 0, -10),
         "lowerarm_l": (0, 0, 0), "lowerarm_r": (0, 0, 0),
         "hand_l": (-5, 0, 0), "hand_r": (0, 0, 0), "curl_l": 15, "curl_r": 12})
    impact = merge(
        {"pelvis_loc": (58, 10, -73), "pelvis": (-8, 82, -38)},
        plant("l", -20, rig, fwd=14, side=-4, up=6, yaw=-35), plant("r", 10, rig, fwd=4, side=-10, up=-2, yaw=-35),
        knee("l", fwd=20, up=-38, xs=25), knee("r", fwd=20, up=-45, xs=25),
        {"spine_01": (0, 4, 0), "spine_02": (0, 3, 0), "spine_03": (0, 2, 0),
         "neck_01": (-4, -18, 0), "head": (-5, -20, 0),
         "upperarm_l": (70, 0, -40), "upperarm_r": (40, 0, 0),
         "lowerarm_l": (-10, 0, 0), "lowerarm_r": (30, 0, 0),
         "hand_l": (-10, 0, 0), "hand_r": (25, 0, 0), "curl_l": 20, "curl_r": 18})
    bounce = merge(impact, {"pelvis_loc": (0, 0, 3), "pelvis": (0, -5, 0), "neck_01": (0, 6, 0), "head": (0, 6, 0)})
    settle = merge(impact, {"pelvis_loc": (1, 0, -1), "pelvis": (0, 2, 0), "neck_01": (0, -4, 5), "head": (5, -6, 8),
                            "upperarm_l": (5, 0, 5), "curl_l": 5, "curl_r": 6})
    return [(0, base()), (6, twist), (15, spin), (26, fall), (34, impact), (38, bounce), (46, settle), (60, settle)]


def make_beats(rig, name, beats_poses, lag_scale=1.0):
    pose_at, frames = beat_sampler(beats_poses)
    length = frames[-1]
    return build(rig, name, length, pose_at, beat_keys(length, frames, lag_scale))


# ---------------------------------------------------------------- hand tweaks

# Hand edits made in Blender on top of the procedural output (2026-09-29). Each entry
# replaces that bone's keys in the clip outright: (frame, local location, local quaternion
# wxyz), scale 1, Bezier with auto-clamped handles. Keeps re-runs identical to the tweaked
# file. Run's knee poles are held still on purpose (the user removed their motion).
USER_TWEAKS = {
    "Attack1": {
        "upperarm_l": [
            (0, (0.0, 0.0, 0.0), (0.58447, 0.45136, -0.52757, -0.41992)),
            (11, (0.0, 0.0, 0.0), (0.61846, 0.44674, -0.43737, -0.47606)),
            (20, (0.0, 0.0, 0.0), (0.67896, 0.29864, -0.61029, -0.27817)),
            (26, (0.0, 0.0, 0.0), (0.64226, 0.35606, -0.52803, -0.42651)),
            (29, (0.0, 0.0, 0.0), (0.58447, 0.45136, -0.52757, -0.41992)),
            (33, (0.0, 0.0, 0.0), (0.58447, 0.45136, -0.52757, -0.41992)),
        ],
        "lowerarm_l": [
            (0, (0.0, 0.0, 0.0), (0.98195, 0.08195, -0.02695, -0.16831)),
            (12, (0.0, 0.0, 0.0), (0.97734, 0.12458, -0.03495, -0.16754)),
            (20, (0.0, 0.0, 0.0), (0.86925, 0.41046, 0.06999, -0.2665)),
            (27, (0.0, 0.0, 0.0), (0.98195, 0.08195, -0.02695, -0.16831)),
            (30, (0.0, 0.0, 0.0), (0.98195, 0.08195, -0.02695, -0.16831)),
            (33, (0.0, 0.0, 0.0), (0.98195, 0.08195, -0.02695, -0.16831)),
        ],
        "lowerarm_r": [
            (0, (0.0, 0.0, 0.0), (0.98833, 0.07181, 0.017, 0.13326)),
            (12, (0.0, 0.0, 0.0), (0.82584, 0.49614, 0.15456, 0.21898)),
            (16, (0.0, 0.0, 0.0), (0.95647, 0.0445, -0.1116, -0.07471)),
            (21, (0.0, 0.0, 0.0), (0.97606, 0.02241, 0.00981, 0.21611)),
            (27, (0.0, 0.0, 0.0), (0.9525, 0.14142, 0.05415, 0.26421)),
            (30, (0.0, 0.0, 0.0), (0.95799, 0.18986, 0.05712, 0.20725)),
            (33, (0.0, 0.0, 0.0), (0.98833, 0.07181, 0.017, 0.13326)),
        ],
    },
    "Attack2": {
        "upperarm_l": [
            (0, (0.0, 0.0, 0.0), (0.58447, 0.45136, -0.52757, -0.41992)),
            (11, (0.0, 0.0, 0.0), (0.45292, 0.40623, -0.79303, 0.03073)),
            (20, (0.0, 0.0, 0.0), (0.65311, 0.58877, -0.1352, -0.45664)),
            (26, (0.0, 0.0, 0.0), (0.58055, 0.60063, 0.00893, -0.54966)),
            (29, (0.0, 0.0, 0.0), (0.59368, 0.53515, -0.27391, -0.53491)),
            (33, (0.0, 0.0, 0.0), (0.58447, 0.45136, -0.52757, -0.41992)),
        ],
        "lowerarm_l": [
            (0, (0.0, 0.0, 0.0), (0.98195, 0.08195, -0.02695, -0.16831)),
            (12, (0.0, 0.0, 0.0), (0.81602, 0.51394, -0.15531, -0.21414)),
            (16, (0.0, 0.0, 0.0), (0.96529, -0.01648, -0.04141, 0.00529)),
            (21, (0.0, 0.0, 0.0), (0.9662, 0.03806, -0.02356, -0.25387)),
            (27, (0.0, 0.0, 0.0), (0.94062, 0.16099, -0.06627, -0.29141)),
            (30, (0.0, 0.0, 0.0), (0.94854, 0.20556, -0.06623, -0.23157)),
            (33, (0.0, 0.0, 0.0), (0.98195, 0.08195, -0.02695, -0.16831)),
        ],
    },
    "Attack3": {
        "upperarm_l": [
            (0, (0.0, 0.0, 0.0), (0.58447, 0.45136, -0.52757, -0.41992)),
            (11, (0.0, 0.0, 0.0), (0.19376, 0.65056, -0.73231, -0.0543)),
            (20, (0.0, 0.0, 0.0), (0.64562, 0.45929, -0.43555, -0.42724)),
            (26, (0.0, 0.0, 0.0), (0.63759, 0.46105, -0.33646, -0.5174)),
            (29, (0.0, 0.0, 0.0), (0.61846, 0.44674, -0.43737, -0.47606)),
            (33, (0.0, 0.0, 0.0), (0.58447, 0.45136, -0.52757, -0.41992)),
        ],
        "upperarm_r": [
            (0, (0.0, 0.0, 0.0), (0.5589, 0.44982, 0.52369, 0.45939)),
            (11, (0.0, 0.0, 0.0), (0.15444, 0.67057, 0.72012, 0.08897)),
            (20, (0.0, 0.0, 0.0), (0.62201, 0.44165, 0.39379, 0.51281)),
            (26, (0.0, 0.0, 0.0), (0.61633, 0.45146, 0.33182, 0.55337)),
            (29, (0.0, 0.0, 0.0), (0.59477, 0.44107, 0.43339, 0.5137)),
            (33, (0.0, 0.0, 0.0), (0.5589, 0.44982, 0.52369, 0.45939)),
        ],
    },
    "Death3": {
        "upperarm_l": [
            (0, (0.0, 0.0, 0.0), (0.58447, 0.45136, -0.52757, -0.41992)),
            (8, (0.0, 0.0, 0.0), (0.53196, 0.40581, -0.7093, -0.22189)),
            (17, (0.0, 0.0, 0.0), (0.51136, 0.36569, -0.77295, -0.08562)),
            (28, (0.0, 0.0, 0.0), (0.44097, 0.4002, -0.79822, 0.09072)),
            (36, (0.0, 0.0, 0.0), (0.21579, 0.57757, -0.37588, -0.69178)),
            (48, (0.0, 0.0, 0.0), (0.21579, 0.57757, -0.37588, -0.69178)),
            (60, (0.0, 0.0, 0.0), (0.21579, 0.57757, -0.37588, -0.69178)),
        ],
    },
    "Run": {
        "ik_knee_l": [
            (0, (10.4155, 3.1268, 21.9996), (1.0, 0.0, 0.0, 0.0)),
            (21, (10.4155, 3.1268, 21.9996), (1.0, 0.0, 0.0, 0.0)),
        ],
        "ik_knee_r": [
            (0, (-5.7253, -8.2077, 19.4991), (1.0, 0.0, 0.0, 0.0)),
            (21, (-5.7253, -8.2077, 19.4991), (1.0, 0.0, 0.0, 0.0)),
        ],
        # 2026-09-29 pass: pelvis height held flat (no bob), sway/twist reshaped by hand.
        "pelvis": [
            (0, (0.0, -3.5406, -4.2993), (0.99621, 0.03743, -0.0784, 0.00295)),
            (3, (2.3455, -1.8357, -4.2993), (0.99642, 0.05281, -0.05524, 0.03613)),
            (5, (2.9916, -1.4438, -4.2993), (0.99819, 0.03986, -0.01341, 0.04307)),
            (8, (2.0405, -3.5467, -4.2993), (0.99796, 0.02179, 0.05295, 0.02811)),
            (10, (0.4471, -4.602, -4.2993), (0.99652, 0.0328, 0.07647, 0.00388)),
            (13, (-2.0405, -3.8961, -4.2993), (0.99608, 0.05314, 0.063, -0.03225)),
            (16, (-2.9916, -0.938, -4.2993), (0.99847, 0.03516, 0.00147, -0.04267)),
            (18, (-2.3455, -3.8197, -4.2993), (0.99827, 0.02215, -0.04366, -0.03265)),
            (21, (0.0, -3.5406, -4.2993), (0.99621, 0.03743, -0.0784, 0.00295)),
        ],
    },
}


def apply_tweaks(rig, act, clip):
    for bone, keys in USER_TWEAKS.get(clip, {}).items():
        fcs = fcurves_for(act, rig.arm)
        for prop in ("location", "rotation_quaternion", "scale"):
            path = f'pose.bones["{bone}"].{prop}'
            for fc in [fc for fc in fcs if fc.data_path == path]:
                fcs.remove(fc)
        rig.reset()
        p = rig.pb[bone]
        for frame, loc, rot in keys:
            p.location = loc
            p.rotation_quaternion = rot
            p.scale = (1.0, 1.0, 1.0)
            key_bone(rig, bone, frame, act.name)
        for fc in fcs:
            if fc.data_path.startswith(f'pose.bones["{bone}"].'):
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
                fc.update()
        rig.reset()


# ---------------------------------------------------------------- QA

def qa(rig, act):
    """Worst IK reach error (cm) and lowest bone height across the clip."""
    ad = rig.arm.animation_data
    ad.action = act
    f0, f1 = map(int, act.frame_range)
    worst, low = 0.0, 1e9
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        for s in "lr":
            calf = rig.pb[f"calf_{s}"]
            tgt = rig.pb[f"ik_foot_{s}"].head
            worst = max(worst, (calf.tail - tgt).length)
        for p in rig.pb:
            if rig.arm.data.bones[p.name].use_deform:
                low = min(low, p.head.z, p.tail.z)
    return worst, low


# ---------------------------------------------------------------- main

def main(out_path=None):
    rig = Rig()
    clips = [
        ("Walk", lambda: make_walk(rig, PREFIX + "Walk", 46, run=False)),
        ("Run", lambda: make_walk(rig, PREFIX + "Run", 21, run=True)),
        ("Spawn", lambda: make_beats(rig, PREFIX + "Spawn", spawn_beats(rig))),
        ("Attack1", lambda: make_beats(rig, PREFIX + "Attack1", claw_beats(rig), 0.8)),
        ("Attack2", lambda: make_beats(rig, PREFIX + "Attack2",
                                       [(f, mirror(p)) for f, p in claw_beats(rig)], 0.8)),
        ("Attack3", lambda: make_beats(rig, PREFIX + "Attack3", bite_beats(rig), 0.8)),
        ("HitReact", lambda: make_beats(rig, PREFIX + "HitReact", hitreact_beats(rig), 0.5)),
        ("Death1", lambda: make_beats(rig, PREFIX + "Death1", death1_beats(rig))),
        ("Death2", lambda: make_beats(rig, PREFIX + "Death2", death2_beats(rig))),
        ("Death3", lambda: make_beats(rig, PREFIX + "Death3", death3_beats(rig))),
    ]
    for label, fn in clips:
        act = fn()
        apply_tweaks(rig, act, label)
        err, low = qa(rig, act)
        print(f"SHAMBLER_IK {label}: frames={tuple(map(int, act.frame_range))} ik_reach_err={err:.2f}cm min_z={low:.1f}")
    rig.arm.animation_data.action = rig.idle
    bpy.context.scene.frame_set(0)
    if out_path:
        bpy.ops.wm.save_as_mainfile(filepath=out_path, copy=True)
        print(f"SHAMBLER_IK saved copy -> {out_path}")


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = None
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    return out


if __name__ == "__main__":
    main(_args() if bpy.app.background else None)

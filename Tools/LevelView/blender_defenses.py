"""Headless Blender: placeholder meshes for the placeable defenses (/Game/Defense/BP_*).

blender --background --factory-startup --python blender_defenses.py -- [only=Spike,Turret,...]

Writes <project>/PlaceholderAssets/Blender/SM_Def_<Name>.blend and FBX/SM_Def_<Name>.fbx.
Authored in cm at real size, in the UE frame of the BP_DefenseSocket the defense spawns on
(pivot = socket origin, +X = socket forward, +Z up):
  FLOOR / TURRET_BASE / OTHER sockets sit 5 cm above the floor, so floor meshes start at z = -5.
  WALL sockets sit 40 cm out from the wall (wall face at x = -40) and 150 cm up (floor at z = -150).
Parts that should move later are separate meshes with their own pivot:
  TurretHead pivot = yaw axis on top of TurretBase (z = 85 in socket space);
  SwingBlade pivot = hinge at the end of SwingMount's arm (x = 0, z = +70 in socket space), hangs down -Z.
Models are Y-symmetric, so Blender->UE's Y flip doesn't matter.
Material slot names are lvlib.MATERIALS keys; ue_import_defenses.py maps them to MI_LV_<key>.
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from blender_gear import ball, cube, dirs, fbx, join_all, tube  # noqa: E402
from blender_placeholders import reset  # noqa: E402

STEEL, DARK, WOOD, YELLOW, BLACK = "blade_steel", "gunmetal", "timber", "product_yellow", "counter_top"
X_AXIS = (0.0, math.pi / 2, 0.0)  # tube local +Z -> +X
Y_AXIS = (-math.pi / 2, 0.0, 0.0)  # tube local +Z -> +Y


def spike():
    """FLOOR: 90 x 90 steel plate with a 4 x 4 grid of 25 cm spikes and hazard-yellow edge rails."""
    cube(DARK, -45, 45, -45, 45, -5, -1)
    for s in (-1, 1):
        cube(YELLOW, -45, 45, s * 45 - 3, s * 45 + 3, -5, 1)
        cube(YELLOW, s * 45 - 3, s * 45 + 3, -45, 45, -5, 1)
    for i in range(4):
        for j in range(4):
            x, y = -30 + i * 20, -30 + j * 20
            tube(DARK, (x, y, -1), 3, 5)
            tube(STEEL, (x, y, 2), 23, 3.2, 0.2, segs=6)


def slow_strip():
    """FLOOR: 90 x 90 black glue mat framed by yellow/black striped boards, with nail studs."""
    cube(BLACK, -40, 40, -40, 40, -5, -2)
    for k in range(9):  # striped frame, 10 cm bands
        c = YELLOW if k % 2 == 0 else BLACK
        a, b = -45 + k * 10, -35 + k * 10
        cube(c, a, b, -45, -38, -5, 0)
        cube(c, a, b, 38, 45, -5, 0)
        cube(c, -45, -38, a, b, -5, 0)
        cube(c, 38, 45, a, b, -5, 0)
    for i in range(5):
        for j in range(5):
            if (i + j) % 2 == 0:
                tube(STEEL, (-28 + i * 14, -28 + j * 14, -2), 5, 1.2, 0.1, segs=5)


def swing_mount():
    """WALL: backplate on the wall (x = -40) plus an arm out to the hinge at (0, 0, 70)."""
    cube(DARK, -40, -36, -30, 30, 30, 100)                            # backplate
    for y in (-22, 22):
        for z in (40, 90):
            tube(STEEL, (-36, y, z), 2, 2.5, rot=X_AXIS, segs=6)     # bolts
    cube(DARK, -36, 4, -5, 5, 64, 76)                                 # arm
    cube(DARK, -36, -14, -5, 5, 40, 64)                               # gusset
    tube(STEEL, (0, -10, 70), 20, 5, rot=Y_AXIS)                      # hinge barrel


def swing_blade():
    """WALL: pendulum hung from its hinge (pivot, origin) — rod down to a curved axe blade, swings along Y."""
    tube(STEEL, (0, -7, 0), 14, 3.5, rot=Y_AXIS)                      # hinge sleeve
    cube(DARK, -2.5, 2.5, -2.5, 2.5, -95, 0)                          # rod
    cube(DARK, -5, 5, -8, 8, -110, -95)                               # blade clamp
    n = 7                                                             # blade: fan of wedges, 70 cm wide
    for k in range(n):
        t = -1 + 2 * k / (n - 1)
        depth = 32 - 10 * t * t
        cube(STEEL, -1.5, 1.5, t * 30 - 6, t * 30 + 6, -100 - depth, -104)


def turret_base():
    """TURRET_BASE: steel tripod with a center post, top plate at z = 85 (the head's yaw pivot)."""
    cube(DARK, -20, 20, -20, 20, -5, 3)                               # foot plate
    tube(DARK, (0, 0, 3), 80, 7)                                      # post
    for k in range(3):
        a = 2 * math.pi * k / 3
        dx, dy, dz = -40 * math.cos(a), -40 * math.sin(a), 60        # foot -> post at z = 55
        tube(DARK, (-dx, -dy, -5), math.sqrt(dx * dx + dy * dy + dz * dz), 3, 2.5, segs=8,
             rot=(math.atan2(-dy, math.hypot(dx, dz)), math.atan2(dx, dz), 0))
        ball(BLACK, (40 * math.cos(a), 40 * math.sin(a), 0), 5)      # rubber feet
    tube(YELLOW, (0, 0, 78), 7, 14)                                   # slew ring


def turret_head():
    """TURRET_BASE: gun head, pivot on the yaw axis at its base, barrel along +X."""
    cube(DARK, -22, 18, -15, 15, 0, 26)                               # receiver
    cube(YELLOW, -22, 18, -15.5, 15.5, 20, 23)                        # stripe
    cube(DARK, -8, 8, -24, -15, 4, 22)                                # ammo box (left)
    cube("product_camo", -7, 7, 15, 22, 6, 20)                        # sensor box (right)
    tube("glass", (7, 22, 13), 3, 4, rot=(-math.pi / 2, 0, 0), segs=10)  # sensor lens
    tube(DARK, (18, 0, 13), 20, 5, rot=X_AXIS)                        # barrel shroud
    tube(STEEL, (38, 0, 13), 22, 2.2, rot=X_AXIS, segs=8)             # barrel
    tube(DARK, (58, 0, 13), 5, 3.5, rot=X_AXIS, segs=8)               # muzzle
    cube(BLACK, -26, -22, -10, 10, 4, 22)                             # back cap


def barricade():
    """OTHER: wooden plank barricade, 130 wide (Y) x 50 deep x 105 tall, on two sawhorse frames."""
    for y in (-50, 50):
        for s in (-1, 1):
            leg = cube(WOOD, -3, 3, y - 3, y + 3, -5, 100)
            leg.rotation_euler = (0, s * math.radians(12), 0)
            leg.location = (-s * 10, 0, 0)
        cube(WOOD, -18, 18, y - 3, y + 3, 30, 36)                     # cross brace
    for z in (35, 62, 89):
        cube(WOOD, 10, 16, -65, 65, z, z + 16)                        # planks on the front
    for y in (-35, 0, 35):
        for z in (43, 70, 97):
            tube(STEEL, (16, y, z), 1.2, 1.2, rot=X_AXIS, segs=5)    # nail heads
    cube(YELLOW, 16, 17, -65, 65, 60, 64)                             # hazard tape


def gas():
    """OTHER: propane-style gas tank on a stand with a valve and a vent nozzle, ~50 x 50 x 105."""
    cube(DARK, -25, 25, -25, 25, -5, 0)                               # base plate
    tube("product_green", (0, 0, 0), 12, 20, segs=16)                 # foot ring
    tube("product_green", (0, 0, 12), 60, 22, segs=16)                # tank body
    ball("product_green", (0, 0, 72), 22)                             # dome
    for z in (25, 55):
        tube(YELLOW, (0, 0, z), 6, 22.4, segs=16)                     # hazard bands
    tube(STEEL, (0, 0, 92), 10, 3)                                    # valve stem
    tube("product_red", (0, 0, 100), 3, 8, segs=10)                   # valve wheel
    tube(STEEL, (0, 0, 97), 20, 2, rot=X_AXIS, segs=8)                # vent pipe
    tube(DARK, (20, 0, 97), 8, 2, 5, rot=X_AXIS, segs=10)             # vent nozzle


MODELS = {
    "Spike": spike,
    "SlowStrip": slow_strip,
    "SwingMount": swing_mount,
    "SwingBlade": swing_blade,
    "TurretBase": turret_base,
    "TurretHead": turret_head,
    "Barricade": barricade,
    "Gas": gas,
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = None
    for a in argv:
        if a.startswith("only="):
            only = set(a[5:].split(","))
    bdir, fdir = dirs()
    for name, fn in MODELS.items():
        if only and name not in only:
            continue
        reset()
        fn()
        full = f"SM_Def_{name}"
        _, slots, lo, hi = join_all(full)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(bdir, full + ".blend"))
        fbx(os.path.join(fdir, full + ".fbx"), {"MESH"})
        print(f"DEF {full} min=({lo.x:.0f},{lo.y:.0f},{lo.z:.0f}) max=({hi.x:.0f},{hi.y:.0f},{hi.z:.0f}) "
              f"slots={slots}")


if __name__ == "__main__":
    main()

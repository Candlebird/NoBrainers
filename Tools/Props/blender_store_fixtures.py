"""Headless Blender: interactable store-fixture placeholder meshes (stock shelf, checkout, kiosks, close-shop
station, ammo pickup).

"C:/Program Files/Blender Foundation/Blender 4.5/blender.exe" --background --factory-startup \
    --python Tools/Props/blender_store_fixtures.py -- [only=StockShelf,AmmoKiosk,...] [preview=<dir>] [verify=1]

Writes <project>/PlaceholderAssets/Blender/SM_<Name>.blend and FBX/SM_<Name>.fbx (mesh only).
Same convention as Tools/LevelView/blender_defenses.py (helpers reused from blender_gear.py):
  authored in cm at true in-game size, join_all() bakes cm -> Blender m, FBX exported with
  apply_unit_scale + FBX_SCALE_UNITS so the mesh imports into UE at 1x1x1 with no import scale.
  Pivot = bottom centre (floor contact, z = 0). Front faces +X (Blender +X == UE +X).
  Blender -> UE flips Y (Blender +Y == UE -Y); coordinates reported by this script are in UE space.
Material slot names are lvlib.MATERIALS keys; the importer maps them to MI_LV_<key>.
  preview=<dir>  also renders a 512x512 Workbench 3/4-front PNG per model (<dir>/SM_<Name>.png)
  verify=1       re-imports every written FBX into an empty scene and prints its world bounding box (cm)
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
LV = os.path.join(HERE, "..", "LevelView")
sys.path.insert(0, os.path.abspath(LV))
import lvlib  # noqa: E402
from blender_gear import ball, cube, dirs, fbx, join_all, ring, tube  # noqa: E402
from blender_placeholders import new_obj, reset  # noqa: E402

# material keys (lvlib.MATERIALS)
DARK, BLACK, STEEL, WHITE = "gunmetal", "counter_top", "blade_steel", "product_white"
YELLOW, ORANGE, BLUE, RED, TAN = "product_yellow", "product_orange", "product_blue", "product_red", "product_tan"
OLIVE, BRASS, WOOD = "product_camo", "gold", "timber"
SCREEN, ALERT, LAMP, STOCK, AMBER = "screen_glow", "alert_red", "light_fixture", "stock_sign", "sign"

X_AXIS = (0.0, math.pi / 2, 0.0)   # tube local +Z -> +X
Y_AXIS = (-math.pi / 2, 0.0, 0.0)  # tube local +Z -> +Y

REPORT = []  # extra lines printed per model (slot / sign positions, UE space)


UE_K = [(1.0, 1.0, 1.0)]  # current model's SCALE, applied to reported coordinates


def ue(p):
    """Blender cm -> UE local cm (flip Y), scaled by the model's SCALE."""
    k = UE_K[0]
    return (round(p[0] * k[0], 1), round(-p[1] * k[1], 1) + 0.0, round(p[2] * k[2], 1))


def obox(material, center, size, rot=(0.0, 0.0, 0.0)):
    """Box of `size` (sx, sy, sz) rotated by Euler `rot` about its own centre, placed at `center`."""
    sx, sy, sz = size
    ob = cube(material, -sx / 2, sx / 2, -sy / 2, sy / 2, -sz / 2, sz / 2)
    ob.rotation_euler = rot
    ob.location = center
    return ob


def along(center, rot, local):
    """World point = center + rot * local offset."""
    return tuple(Vector(center) + Euler(rot).to_matrix() @ Vector(local))


def prism_xz(material, pts, y0, y1):
    """Polygon given in the XZ plane, extruded along Y from y0 to y1."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in pts]
    b = [bm.verts.new((x, y1, z)) for x, z in pts]
    n = len(pts)
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj("prism", bm, material)


def prism_yz(material, pts, x0, x1):
    """Polygon given in the YZ plane, extruded along X from x0 to x1."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in pts]
    b = [bm.verts.new((x1, y, z)) for y, z in pts]
    n = len(pts)
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj("prism", bm, material)


def open_box(material, x0, x1, y0, y1, z0, z1, t=1.0, flap=8.0, flare=math.radians(35)):
    """Open-top cardboard box: 4 walls + floor, with the 4 top flaps flared outward."""
    cube(material, x0, x1, y0, y1, z0, z0 + t)
    cube(material, x0, x0 + t, y0, y1, z0, z1)
    cube(material, x1 - t, x1, y0, y1, z0, z1)
    cube(material, x0, x1, y0, y0 + t, z0, z1)
    cube(material, x0, x1, y1 - t, y1, z0, z1)
    cube(BLACK, x0 + t, x1 - t, y0 + t, y1 - t, z0 + t, z0 + t + 0.3)  # dark inside floor reads "empty"
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s, c = math.sin(flare), math.cos(flare)
    for sgn in (-1, 1):  # flaps on the X walls (hinge along Y), tilt outward about Y
        x = x1 if sgn > 0 else x0
        obox(material, (x + sgn * s * flap / 2, cy, z1 + c * flap / 2), (t, (y1 - y0) * 0.95, flap),
             (0.0, sgn * flare, 0.0))
    for sgn in (-1, 1):  # flaps on the Y walls (hinge along X), tilt outward about X
        y = y1 if sgn > 0 else y0
        obox(material, (cx, y + sgn * s * flap / 2, z1 + c * flap / 2), ((x1 - x0) * 0.95, t, flap),
             (-sgn * flare, 0.0, 0.0))


# ---------------------------------------------------------------- 1. stock shelf
SHELF_LEVELS = (30.0, 58.0, 86.0, 114.0)   # top surface of each shelf board (z, cm)
SHELF_SLOTS_Y = (-87.0, -29.0, 29.0, 87.0)  # 4 evenly spaced slots across the 232 cm interior
SHELF_SLOT_X = 0.0


def stock_shelf():
    """240 W (Y) x 70 D (X) x ~164 H single-sided gondola, open front on +X. Orange ends, blue back,
    white boards, yellow price rails with red tags, glowing green header frame with a blank white face,
    two empty open cardboard boxes on the plinth under the bottom shelf."""
    cube(BLACK, -35, 35, -120, 120, 0, 4)                          # plinth
    cube(ORANGE, -35, 36, -120, -116, 0, 138)                      # end panels
    cube(ORANGE, -35, 36, 116, 120, 0, 138)
    cube(BLUE, -35, -32, -116, 116, 4, 138)                        # back panel
    for yy in range(-100, 101, 25):                                # pegboard-ish vertical ribs
        cube(DARK, -32, -31, yy - 1, yy + 1, 4, 138)
    cube(ORANGE, 33, 36, -116, 116, 0, 8)                          # front kick rail
    for zt in SHELF_LEVELS:
        cube(WHITE, -32, 33, -116, 116, zt - 2.5, zt)              # board
        cube(YELLOW, 33, 36.5, -116, 116, zt - 6, zt + 1.5)        # price-tag rail on the lip
        for yy in SHELF_SLOTS_Y:
            cube(RED, 36.5, 37.2, yy - 6, yy + 6, zt - 5, zt + 0.5)  # price tag per slot
    # header: glowing green frame across the top, flat blank white face toward +X
    cube(STOCK, -35, -29, -120, 120, 138, 166)
    cube(STOCK, -35, -29, -120, -112, 128, 138)                    # frame ears down the uprights
    cube(STOCK, -35, -29, 112, 120, 128, 138)
    cube(WHITE, -29, -28, -114, 114, 141, 163)                     # blank sign face (TextRender goes here)
    # empty open cardboard boxes on the plinth, under the bottom shelf ("needs restocking")
    open_box(TAN, -12, 22, -100, -58, 4, 21)
    open_box(TAN, -18, 14, 45, 83, 4, 19)
    REPORT.append("  slots (UE local, x,y,z = centre of item footprint on the board top):")
    for i, zt in enumerate(SHELF_LEVELS):
        REPORT.append("    level %d: %s" % (i + 1, "  ".join(str(ue((SHELF_SLOT_X, yy, zt))) for yy in SHELF_SLOTS_Y)))
    REPORT.append("  header sign face: centre %s, facing +X, size %g W (Y) x %g H (Z)" % (ue((-28, 0, 152)), 228 * UE_K[0][1], 22 * UE_K[0][2]))


# ---------------------------------------------------------------- 1b. stock shelf tiers (T0-T4)
T_W = 700.0                     # overall width (Y)
T_D = 60.0                      # overall depth (X)
T_INNER = 346.0                 # inner half-width (Y half-extent of usable bay)
# Row board tops. MUST match BP_ShelfActor.GetSlotTransform: z = 45 + row * 95, y = 346 - (col + 0.5) * 692 / cols.
# Rows are 95 apart because carried items are 3x real size (tallest ~62 cm, widest ~72 cm, deepest 60 cm).
T_ROW_TOPS = (45.0, 140.0)
T_TOP = 218.0                   # top of uprights / bottom of the header
T_TIERS = {                     # (rows, cols) -> 2 / 4 / 6 / 8 / 12 slots, matching DT_ShelfTiers
    "StockShelf_T0": (1, 2),
    "StockShelf_T1": (1, 4),
    "StockShelf_T2": (1, 6),
    "StockShelf_T3": (2, 4),
    "StockShelf_T4": (2, 6),
}


def stock_shelf_tier(rows, cols):
    """700 W (Y) x 60 D (X) tiered stock shelf; rows x cols slots, identical frame across all tier variants.
    Closed orange base cabinet, steel-lipped boards with lit undersides, pegboard back, low wire slot dividers,
    end panels with a yellow stripe, glowing header with a blank white sign face."""
    H = T_TOP
    # base cabinet: recessed black toe kick + orange front panel up to the bottom board
    cube(BLACK, -28.57, 25, -348.23, 348.23, 0, 8)                 # plinth, inset so it doesn't z-fight the ends
    cube(ORANGE, 25, 29, -346, 346, 8, T_ROW_TOPS[0] - 7)          # base front panel
    cube(WHITE, 29, 29.4, -330, 330, 18, 22)                       # pinstripe on the base panel
    # end panels with a front steel edge and an aisle-facing stripe
    cube(ORANGE, -30, 29, -350, -346, 0, H)                        # end panels
    cube(ORANGE, -30, 29, 346, 350, 0, H)
    cube(STEEL, 29, 31, -350, -345, 0, H)                          # front edge caps
    cube(STEEL, 29, 31, 345, 350, 0, H)
    cube(YELLOW, -12, 12, -350.6, -350, 25, H - 25)                # aisle-facing stripes on the outer faces
    cube(YELLOW, -12, 12, 350, 350.6, 25, H - 25)
    # pegboard back with a dot grid
    cube(BLUE, -30, -27, -346, 346, 8, H)
    for yy in range(-330, 331, 22):
        for zz in range(int(T_ROW_TOPS[0]) + 12, int(H) - 6, 22):
            cube(DARK, -27, -26.7, yy - 1.5, yy + 1.5, zz - 1.5, zz + 1.5)
    bays = [-346 + c * 692.0 / cols for c in range(1, cols)]       # divider positions; uprights frame each bay
    for yy in bays:
        cube(STEEL, -27, -25, yy - 2, yy + 2, 8, H)
    # header: glowing frame, blank sign face (TextRender goes here), down-lighting strip under it
    cube(STOCK, -30, -22, -349.5, 349.5, H, H + 36)                # inset so it doesn't z-fight the end panels
    cube(STOCK, -29.5, -22, -349.5, -342, H - 10, H)               # header ears
    cube(STOCK, -29.5, -22, 342, 349.5, H - 10, H)
    cube(WHITE, -22, -21, -338, 338, H + 4, H + 32)                # blank sign face
    cube(LAMP, -22, -6, -338, 338, H - 2, H)                       # light strip under the header

    for r in range(rows):
        zt = T_ROW_TOPS[r]
        pitch = 692.0 / cols
        cube(WHITE, -27, 27, -346, 346, zt - 3, zt)                # board
        cube(STEEL, 27, 29, -346, 346, zt - 7, zt + 2)             # steel front lip
        cube(YELLOW, 29, 30.2, -346, 346, zt - 7, zt - 1)          # price-tag rail
        if r > 0:
            cube(LAMP, 10, 24, -338, 338, zt - 4.5, zt - 3)        # light strip under the board, lights the row below
            for yy in bays:
                cube(DARK, -25, -8, yy - 1.5, yy + 1.5, zt - 12, zt - 3)  # board brackets
        for c in range(cols):
            yc = -346 + (c + 0.5) * pitch
            cube(WHITE, 30.2, 30.8, yc - 9, yc + 9, zt - 7, zt - 1)   # price tag
            cube(RED, 30.8, 31.1, yc - 9, yc + 9, zt - 3, zt - 1)     # tag header band
            w = min(pitch - 16, 90)
            cube(TAN, -22, 22, yc - w / 2, yc + w / 2, zt, zt + 0.6)  # slot pad
        for c in range(1, cols):                                   # low wire divider: base bar, front post, top rail
            yb = -346 + c * pitch
            cube(STEEL, -25, 25, yb - 0.6, yb + 0.6, zt, zt + 1)
            cube(STEEL, 23.5, 25, yb - 0.6, yb + 0.6, zt, zt + 18)
            cube(STEEL, -25, 25, yb - 0.6, yb + 0.6, zt + 17, zt + 18)

    for i in range(rows * cols):
        row, col = i // cols, i % cols
        pitch = 692.0 / cols
        REPORT.append("slot %d: UE %s" % (i, ue((0, -346 + (col + 0.5) * pitch, T_ROW_TOPS[row]))))
    REPORT.append("sign face: UE centre (-21, 0, %g) facing +X, 676 W x 28 H" % (H + 18))


# ---------------------------------------------------------------- 2. checkout counter
def checkout_counter():
    """220 L (Y) x 80 D (X) x 91 H counter (lane pole to ~203). Customer side = +X (front), cashier = -X.
    Belt at Blender -Y end (UE +Y), scanner + register mid, bagging at Blender +Y end (UE -Y)."""
    cube(BLACK, -36, 36, -108, 108, 0, 8)                          # recessed kick
    cube("counter", -38, 38, -110, 110, 8, 88)                     # body
    cube(RED, 38, 39, -110, 110, 62, 74)                           # customer-side accent stripe
    cube(YELLOW, 38, 39, -110, 110, 58, 62)
    cube(BLACK, -40, 40, -110, 110, 88, 91)                        # top slab
    # conveyor belt
    cube(BLACK, -22, 22, -108, 16, 91, 94)                         # belt
    for yy in range(-100, 16, 12):
        cube(DARK, -22, 22, yy, yy + 1, 94, 94.3)                  # belt seams
    cube(STEEL, -26, -22, -108, 18, 91, 97)                        # side rails
    cube(STEEL, 22, 26, -108, 18, 91, 97)
    tube(STEEL, (-22, -106, 94), 44, 3, rot=X_AXIS, segs=10)       # end rollers
    tube(STEEL, (-22, 16, 94), 44, 3, rot=X_AXIS, segs=10)
    cube(YELLOW, -18, 18, -45, -41, 94, 98)                        # order divider bar
    # scanner window
    cube(STEEL, -18, 18, 22, 48, 91, 92)
    cube("glass", -15, 15, 25, 45, 92, 92.5)
    cube(ALERT, -15, 15, 34, 36, 92.5, 92.8)                       # scan line
    # register (cashier side): base, drawer, keypad, screen facing the cashier (-X), small customer display (+X)
    cube(DARK, -38, -10, 52, 80, 91, 105)
    cube(BLACK, -39, -37, 55, 77, 93, 102)                         # cash drawer front
    obox(WHITE, (-30, 66, 107), (10, 18, 4), (0, math.radians(10), 0))  # keypad
    tube(DARK, (-18, 60, 105), 14, 2.5)                            # screen post
    scr_c, scr_r = (-18, 60, 130), (0, math.radians(15), 0)        # housing tilted, face toward -X
    obox(BLACK, scr_c, (5, 30, 22), scr_r)
    obox(SCREEN, along(scr_c, scr_r, (-2.7, 0, 0)), (0.6, 26, 18), scr_r)   # cashier screen
    obox(SCREEN, along(scr_c, scr_r, (2.7, 0, -3)), (0.6, 18, 9), scr_r)    # customer display
    # card reader on the customer side
    tube(DARK, (32, 42, 91), 10, 2)
    rd_c, rd_r = (32, 42, 106), (0, math.radians(-25), 0)          # tilted toward the customer (+X)
    obox(BLACK, rd_c, (4, 10, 15), rd_r)
    obox(SCREEN, along(rd_c, rd_r, (2.2, 0, 3.5)), (0.5, 7, 5), rd_r)
    obox(WHITE, along(rd_c, rd_r, (2.2, 0, -3.5)), (0.5, 7, 5), rd_r)
    # bagging area at the far end: steel platform, bag rack, two white bags
    cube(STEEL, -30, 30, 84, 108, 91, 93)
    for xx in (-26, 26):
        tube(STEEL, (xx, 104, 93), 30, 1.2, segs=6)
    cube(STEEL, -27, 27, 103, 105, 121, 123)                       # rack bar
    cube(WHITE, -24, -4, 88, 104, 93, 117)                         # bags
    cube(WHITE, 4, 24, 88, 104, 93, 113)
    # lane-light pole at the cashier-side back corner, numbered lamp on top
    tube(DARK, (-34, 104, 91), 92, 2.5, segs=8)
    cube(BLACK, -44, -24, 92, 116, 180, 183)
    cube(LAMP, -43, -25, 93, 115, 183, 200)                        # lit lamp box
    cube(RED, -44, -24, 92, 116, 200, 203)                         # cap
    for sx in (-1, 1):                                             # lane number "1" on both faces
        x = -25 if sx > 0 else -43.5
        cube(BLACK, x, x + 0.5, 102.5, 105.5, 185, 198)
        cube(BLACK, x, x + 0.5, 102.5, 108, 194, 198)
        cube(BLACK, x, x + 0.5, 100, 108, 185, 187.5)
    REPORT.append("  cashier (player) side = -X (back, register screen faces -X); customer queue side = +X "
                  "(front, card reader + red stripe); belt loads from the UE +Y end, register/bagging/lane "
                  "pole at the UE -Y end")


# ---------------------------------------------------------------- 3. ammo kiosk
def ammo_kiosk():
    """110 W x 80 D x 210 H olive ammo-crate vending station, front +X: yellow stencil band,
    glowing screen, dispensing tray, big brass bullet topper."""
    cube(BLACK, -38, 38, -53, 53, 0, 6)                            # plinth
    cube(OLIVE, -37, 37, -52, 52, 6, 150)                          # crate body
    for z0 in (6, 142):                                            # khaki rims
        cube(TAN, -39, 39, -54, 54, z0, z0 + 8)
    for sx in (-1, 1):                                             # khaki corner protectors
        for sy in (-1, 1):
            cube(TAN, sx * 34 - 6 if sx > 0 else -40, sx * 34 + 6 if sx > 0 else -34,
                 sy * 49 - 6 if sy > 0 else -55, sy * 49 + 6 if sy > 0 else -49, 6, 150)
    cube(YELLOW, -38, 38, -53, 53, 64, 76)                         # stenciled accent band (wraps)
    for k in range(6):                                             # stencil marks on the band front
        y = -38 + k * 15
        cube(BLACK, 38, 38.6, y, y + 8, 66.5, 73.5)
    # screen
    cube(BLACK, 37, 39, -32, 26, 96, 136)
    cube(SCREEN, 39, 40, -28, 22, 100, 132)
    for k, m in enumerate((ALERT, YELLOW, "product_green")):       # buttons
        tube(m, (37, 38, 126 - k * 12), 3, 3.5, rot=X_AXIS, segs=10)
    # dispensing tray
    cube(BLACK, 37, 38, -26, 26, 20, 52)                           # dark opening
    cube(DARK, 38, 39, -22, 22, 32, 50)                            # flap
    cube(STEEL, 37, 47, -26, 26, 20, 24)                           # tray floor lip
    for sy in (-1, 1):
        cube(STEEL, 37, 47, sy * 26 - 2 if sy > 0 else -26, sy * 26 if sy > 0 else -24, 20, 30)
    cube(STEEL, 45, 47, -26, 26, 20, 30)
    # crate latches on the sides
    for sy in (-1, 1):
        y = 52 if sy > 0 else -54
        cube(DARK, -10, 10, y, y + 2, 112, 122)
    # topper: brass bullet on a base plate
    cube(DARK, -30, 30, -30, 30, 150, 155)
    tube(BRASS, (0, 0, 155), 4, 25, segs=16)                       # rim
    tube(BRASS, (0, 0, 159), 25, 23, segs=16)                      # case
    tube(ORANGE, (0, 0, 184), 10, 23, 19, segs=16)                 # copper ogive
    tube(ORANGE, (0, 0, 194), 16, 19, 3, segs=16)


# ---------------------------------------------------------------- 4. discount kiosk
def discount_kiosk():
    """100 W x 70 D x 200 H touch-screen pedestal, front +X: big tilted glowing screen, glowing red
    price-tag topper with a white "%"."""
    cube(BLACK, -30, 30, -40, 40, 0, 6)                            # base
    cube(RED, -31, 31, -41, 41, 1, 4)                              # base accent
    cube(WHITE, -14, 8, -16, 16, 6, 100)                           # column
    cube(RED, 8, 9, -16, 16, 14, 92)                               # red stripe on the column front
    cube(YELLOW, 8.5, 9.5, -12, 12, 60, 70)
    hd_c, hd_r = (-4, 0, 125), (0, math.radians(-22), 0)           # head tilted: screen faces +X and up
    obox(WHITE, hd_c, (10, 96, 58), hd_r)
    obox(BLACK, along(hd_c, hd_r, (5.2, 0, 0)), (0.5, 90, 52), hd_r)  # bezel
    obox(SCREEN, along(hd_c, hd_r, (5.6, 0, 0)), (0.5, 84, 46), hd_r)  # screen
    obox(DARK, along(hd_c, hd_r, (0, 0, -30)), (14, 30, 6), hd_r)  # neck clamp
    # price-tag topper: tag points toward UE -Y (Blender +Y), hole near the point
    tube(DARK, (-6, 0, 152), 10, 2.5, segs=8)
    tag = [(-32, 160), (18, 160), (32, 177), (18, 194), (-32, 194)]
    prism_yz(ALERT, tag, -9, -3)
    ring(BRASS, (-2.5, 20, 177), 3.2, 0.9, rot=X_AXIS)              # tag hole grommet
    # "%" in white on the front face (x = -3)
    ring(WHITE, (-2.5, -17, 185), 3.2, 1.2, rot=X_AXIS)
    ring(WHITE, (-2.5, -3, 169), 3.2, 1.2, rot=X_AXIS)
    obox(WHITE, (-2.3, -10, 177), (1.5, 3, 30), (math.radians(-40), 0, 0))


# ---------------------------------------------------------------- 5. close-shop station
CLOSE_SLOPE = math.atan2(12, 50)


def close_shop_station():
    """~90 W x 60 D x 142 H podium with a big glowing red push button on a sloped top, plus a blank
    OPEN/CLOSED sign board hanging from a post-and-arm behind it. Front +X."""
    cube(BLACK, -28, 28, -43, 43, 0, 6)                            # base
    prism_xz(BLUE, [(-25, 6), (25, 6), (25, 88), (-25, 100)], -40, 40)  # podium, top slopes up to the back
    prism_xz(BLACK, [(-25, 100), (25, 88), (26, 88), (26, 90), (-25, 102)], -41, 41)  # top plate
    for k in range(10):                                            # hazard stripes on the front
        cube(YELLOW if k % 2 == 0 else BLACK, 25, 26, -40 + k * 8, -32 + k * 8, 68, 78)
    # big red mushroom button, perpendicular to the sloped top
    rot = (0.0, CLOSE_SLOPE, 0.0)
    p0 = (2.0, 0.0, 88 + (25 - 2.0) / 50 * 12 + 2)                 # top-plate surface point
    tube(YELLOW, p0, 3, 16, rot=rot, segs=16)                      # hazard collar
    tube(DARK, along(p0, rot, (0, 0, 3)), 4, 7, rot=rot, segs=12)   # stem
    tube(ALERT, along(p0, rot, (0, 0, 7)), 5, 12, rot=rot, segs=16)  # cap
    dome = ball(ALERT, along(p0, rot, (0, 0, 12)), 11.5)
    dome.rotation_euler = rot
    dome.scale = (1, 1, 0.45)
    # sign post + arm + hanging board (board face toward +X)
    tube(DARK, (-27, 42, 0), 142, 2.5, segs=8)
    cube(DARK, -29, -25, 42, 46, 0, 3)                             # post foot
    cube(DARK, -29, -25, -36, 44, 138, 142)                        # arm
    for yy in (-24, 24):
        tube(STEEL, (-27, yy, 132), 6, 0.6, segs=6)                # chains
    cube(WOOD, -28.5, -25.5, -33, 33, 105, 132)                    # board frame
    cube(WHITE, -25.5, -25, -30, 30, 108, 129)                     # blank front face
    cube(WHITE, -29, -28.5, -30, 30, 108, 129)                     # blank back face
    REPORT.append("  sign front face: centre %s, facing +X, size 60 W (Y) x 21 H (Z) "
                  "(back face mirrored at x=-29)" % (ue((-25, 0, 118.5)),))
    REPORT.append("  red button: top-plate centre %s, tilted %.1f deg toward +X"
                  % (ue(p0), math.degrees(CLOSE_SLOPE)))


# ---------------------------------------------------------------- 6. ammo pickup
def ammo_pickup():
    """~40 L (X) x 22 W x 25 H olive ammo can with a glowing amber band, lid propped open (hinged on the
    Blender +Y edge) and oversized brass rounds poking out of the gap."""
    cube(BLACK, -19, 19, -10.5, 10.5, 0, 1.5)                      # skid
    cube(OLIVE, -18, 18, -10, 10, 1.5, 14)                         # can body
    cube(AMBER, -18.5, 18.5, -10.5, 10.5, 5, 9.5)                  # glowing band (wraps)
    cube(BLACK, -9.5, 9.5, 9.5, 10.6, 10, 13)                      # hinge strip
    cube(YELLOW, 17.8, 18.8, -4, 4, 9.5, 13.5)                     # end latch
    cube(YELLOW, -18.8, -17.8, -4, 4, 9.5, 13.5)
    cube(BLACK, -17, 17, -9, 9, 13.5, 14)                          # dark interior
    # rounds leaning out toward -Y, under the lid
    for x, lean, h0 in ((-12, 26, 7), (-5, 30, 6), (2, 24, 7.5), (9, 28, 6), (14.5, 22, 7)):
        rot = (math.radians(lean), 0, 0)
        base = (x, -2.5, h0)
        tube(BRASS, base, 11, 2.3, rot=rot, segs=10)
        tube(ORANGE, along(base, rot, (0, 0, 11)), 5, 2.3, 0.5, rot=rot, segs=10)
    # lid: hinged along the +Y top edge, opened 32 deg
    lid_open = math.radians(32)
    hinge = (0, 10, 14)
    lid_r = (-lid_open, 0, 0)   # negative about X lifts the free (-Y) edge
    obox(OLIVE, along(hinge, lid_r, (0, -10.5, 1.2)), (38, 21, 2.4), lid_r)
    obox(AMBER, along(hinge, lid_r, (0, -10.5, 2.5)), (26, 6, 0.5), lid_r)     # glowing stripe on the lid
    obox(DARK, along(hinge, lid_r, (0, -8, 3.6)), (16, 2.5, 2.5), lid_r)       # carry handle


MODELS = {
    "StockShelf": stock_shelf,
    "CheckoutCounter": checkout_counter,
    "AmmoKiosk": ammo_kiosk,
    "DiscountKiosk": discount_kiosk,
    "CloseShopStation": close_shop_station,
    "AmmoPickup": ammo_pickup,
}
for _name, (_rows, _cols) in T_TIERS.items():
    MODELS[_name] = (lambda rows=_rows, cols=_cols: stock_shelf_tier(rows, cols))
# per-axis (X depth, Y width, Z height) size multiplier baked into the mesh at join time (UE import stays
# 1x1x1). The stock shelf is authored at the 240 W base; after playtest feedback it is ~2x (432 W x 332 H)
# but keeps its 70 cm depth so it still fits against the gondolas it backs onto in Map_Store_Outdoors, and
# 432 W fits the 450 cm spacing of the Hardware shelves. Slots/sign scale with it.
SCALE = {"StockShelf": (1.0, 1.8, 2.0)}


# ---------------------------------------------------------------- preview / verify
def preview(ob, path):
    """512x512 Workbench render, 3/4 view from front (+X), slightly to UE -Y side, from above."""
    sc = bpy.context.scene
    for m in bpy.data.materials:
        rgb, _, _, em = lvlib.MATERIALS.get(m.name, ((1, 0, 1), 0, 0, 0))
        k = 1.6 if em > 0 else 1.0
        m.diffuse_color = (min(rgb[0] * k, 1), min(rgb[1] * k, 1), min(rgb[2] * k, 1), 1)
    lo = Vector([min(v.co[i] for v in ob.data.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in ob.data.vertices) for i in range(3)])
    c, size = (lo + hi) / 2, max(hi - lo)
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = size * 1.25
    cam = bpy.data.objects.new("cam", cam_d)
    sc.collection.objects.link(cam)
    d = Vector((1.0, 0.55, 0.45)).normalized()   # Blender +Y == UE -Y
    cam.location = c + d * size * 4
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam_d.clip_end = size * 10
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_cavity = True
    sc.display.shading.show_object_outline = True
    sc.display.shading.show_backface_culling = True   # flipped faces show up as holes
    sc.render.resolution_x = sc.render.resolution_y = 512
    sc.render.film_transparent = False
    sc.world = sc.world or bpy.data.worlds.new("w")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def verify(paths):
    for p in paths:
        reset()
        bpy.ops.import_scene.fbx(filepath=p)
        obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        pts = [o.matrix_world @ v.co for o in obs for v in o.data.vertices]
        lo = [min(q[i] for q in pts) * 100 for i in range(3)]
        hi = [max(q[i] for q in pts) * 100 for i in range(3)]
        slots = sorted({s.material.name for o in obs for s in o.material_slots if s.material})
        print("VERIFY %s objs=%d bbox_cm min=(%.1f,%.1f,%.1f) max=(%.1f,%.1f,%.1f) size=(%.1f,%.1f,%.1f) slots=%s"
              % (os.path.basename(p), len(obs), *lo, *hi, *(h - l for h, l in zip(hi, lo)), slots))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = dict(a.split("=", 1) for a in argv if "=" in a)
    only = set(flags["only"].split(",")) if "only" in flags else None
    pdir = flags.get("preview")
    bdir, fdir = dirs()
    written = []
    for name, fn in MODELS.items():
        if only and name not in only:
            continue
        reset()
        REPORT.clear()
        UE_K[0] = SCALE.get(name, (1.0, 1.0, 1.0))
        fn()
        full = f"SM_{name}"
        ob, slots, lo, hi = join_all(full, Vector(SCALE.get(name, (1.0, 1.0, 1.0))))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(bdir, full + ".blend"))
        fp = os.path.join(fdir, full + ".fbx")
        fbx(fp, {"MESH"})
        written.append(fp)
        print(f"FIXTURE {full} min=({lo.x:.1f},{lo.y:.1f},{lo.z:.1f}) max=({hi.x:.1f},{hi.y:.1f},{hi.z:.1f}) "
              f"size=({hi.x - lo.x:.1f},{hi.y - lo.y:.1f},{hi.z - lo.z:.1f}) tris~{len(ob.data.polygons)} slots={slots}")
        for line in REPORT:
            print(line)
        if pdir:
            os.makedirs(pdir, exist_ok=True)
            preview(ob, os.path.join(pdir, full + ".png"))
    if flags.get("verify") == "1":
        verify(written)
    print("FIXTURES_DONE", len(written))


if __name__ == "__main__":
    main()

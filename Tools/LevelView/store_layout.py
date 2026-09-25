"""Map_Store_Outdoors layout spec: a Bass Pro-inspired hunting & outdoor superstore (greybox).

python store_layout.py [out.json]    -> writes Saved/LevelView/store_layout.json (default)

Frame: X = 0 at the front wall, increasing toward the back wall (X = L). Y spans -W/2..W/2
(-Y = left side when walking in the front door looking toward +X). Floor top Z = 0.

Building: ~70 x 50 m. Side aisles have a 7 m flat ceiling; a central timber-trussed nave (|Y| < NAVE)
rises on log columns to a clerestory (10 m) and a gabled roof peaking at ~13.5 m.
Every entry is sealed by BP_BreachPoint panels (zombies must break in; breached = nav opens).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Saved", "LevelView", "store_layout.json")

# ---------------------------------------------------------------- dimensions (cm)
L, W = 7000, 5000          # interior length (X) / width (Y)
HW = W / 2
WALL_T = 40
EAVE = 700                 # side-aisle ceiling / outer wall height
NAVE = 1000                # nave half-width (log columns at Y = +-NAVE)
CLER = 1000                # clerestory top
RIDGE = 1350               # roof peak
BAY = 700                  # column / truss spacing along X

BP = {
    "breach": "/Game/Interactable/BP_BreachPoint",
    "socket": "/Game/Defense/BP_DefenseSocket",
    "shelf": "/Game/Interactable/BP_ShelfActor",
    "checkout": "/Game/Interactable/BP_CheckoutCounter",
    "exit": "/Game/Interactable/BP_CustomerExitPoint",
    "crate": "/Game/Interactable/BP_ShippingCrate",
    "kiosk_discount": "/Game/Interactable/BP_DiscountKiosk",
    "kiosk_ammo": "/Game/Interactable/BP_AmmoKiosk",
    "close_shop": "/Game/Interactable/BP_CloseShopStation",
    "shop_station": "/Game/Interactable/BP_ShopStation_Base",
    "pickup": "/Game/Interactable/BP_ItemPickup",
    "cust_spawner": "/Game/AI/Customer/BP_CustomerSpawner",
    "cust_spawn": "/Game/AI/Customer/BP_CustomerSpawnPoint",
    "zombie_mgr": "/Game/Characters/AI/BP_ZombieSpawnerManager",
}

E = []  # elements
_ids = set()


def _add(el):
    assert el["id"] not in _ids, el["id"]
    _ids.add(el["id"])
    E.append(el)
    return el


def box(id, cat, x0, y0, x1, y1, z0, z1, mat, **kw):
    """Axis-aligned box from min/max extents."""
    return _add(dict(id=id, kind="box", cat=cat, pos=[(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2],
                     size=[abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)], mat=mat, **kw))


PH = "/Game/Environment/Placeholder/SM_PH_"  # + name; see Tools/LevelView/blender_placeholders.py


def cbox(id, cat, x, y, sx, sy, z0, z1, mat, yaw=0, **kw):
    """Box from center XY + size, optional yaw."""
    return _add(dict(id=id, kind="box", cat=cat, pos=[x, y, (z0 + z1) / 2], size=[sx, sy, z1 - z0], yaw=yaw,
                     mat=mat, **kw))


def cyl(id, cat, x, y, d, z0, z1, mat, **kw):
    return _add(dict(id=id, kind="cyl", cat=cat, pos=[x, y, (z0 + z1) / 2], size=[d, d, z1 - z0], mat=mat, **kw))


def pine(id, x, y, h, z0=0, block_trunk=True):
    """Stylized pine: collidable trunk + one non-colliding foliage mesh (SM_PH_Pine)."""
    cyl(f"{id}_Trunk", "display" if block_trunk else "deco", x, y, max(30, h * 0.05), z0, z0 + h * 0.35, "timber")
    cyl(f"{id}_Foliage", "deco", x, y, h * 0.42, z0 + h * 0.25, z0 + h * 0.99, "foliage", block=False,
        nocollide=True, mesh=PH + "Pine")


def bp(id, cat, key, x, y, z=50, yaw=0, props=None, size=(100, 100, 100), **kw):
    el = dict(id=id, kind="bp", cat=cat, bp=BP[key], pos=[x, y, z], yaw=yaw, size=list(size), **kw)
    if props:
        el["props"] = props
    return _add(el)


def light(id, x, y, z, intensity, radius=2500, color=(1.0, 0.85, 0.65), kind="point", **kw):
    return _add(dict(id=id, kind="light", cat="light", light=kind, pos=[x, y, z], intensity=intensity,
                     radius=radius, color=list(color), **kw))


def marker(id, cat, cls, x, y, z=0, yaw=0, **kw):
    return _add(dict(id=id, kind="marker", cat=cat, cls=cls, pos=[x, y, z], yaw=yaw, **kw))


def socket(id, stype, x, y, z=5, yaw=0):
    # BP_DefenseSocket: 100cm cylinder marker; floor sockets sit flush-ish, wall sockets hang at 150
    return bp(id, "socket", "socket", x, y, z, yaw, props={"SocketType": stype}, block=False, tall=False)


# ---------------------------------------------------------------- shell
def build_shell(doors):
    """doors: list of (wall, center, width, height) with wall in front/back/left/right."""
    # floors / ground
    box("Ground_Lot", "floor", -3500, -HW - 3000, L + 3000, HW + 3000, -40, -1, "floor_concrete")
    box("Floor_Store", "floor", 0, -HW, L, HW, -20, 0, "floor_wood")
    box("Floor_NaveRug", "floor", 900, -NAVE + 150, L - 900, NAVE - 150, 0, 1, "floor_rug", nocollide=True)

    # outer walls with door gaps
    def wall_run(prefix, axis, fixed, lo, hi, gaps):
        cuts = sorted((c - w / 2, c + w / 2, h) for c, w, h in gaps)
        cur = lo
        i = 0
        segs = []
        for a, b, h in cuts:
            segs.append((cur, a, 0, EAVE))
            segs.append((a, b, h, EAVE))  # lintel above the gap
            cur = b
        segs.append((cur, hi, 0, EAVE))
        for s0, s1, z0, z1 in segs:
            if s1 - s0 < 1 or z1 - z0 < 1:
                continue
            i += 1
            mat = "wall_log"
            if axis == "x":  # wall runs along X at y = fixed
                box(f"{prefix}_{i}", "wall", s0, fixed - WALL_T / 2, s1, fixed + WALL_T / 2, z0, z1, mat)
            else:
                box(f"{prefix}_{i}", "wall", fixed - WALL_T / 2, s0, fixed + WALL_T / 2, s1, z0, z1, mat)

    g = {k: [(c, w, h) for wl, c, w, h in doors if wl == k] for k in ("front", "back", "left", "right")}
    wall_run("Wall_Front", "y", -WALL_T / 2, -HW - WALL_T, HW + WALL_T, g["front"])
    wall_run("Wall_Back", "y", L + WALL_T / 2, -HW - WALL_T, HW + WALL_T, g["back"])
    wall_run("Wall_Left", "x", -HW - WALL_T / 2, 0, L, g["left"])
    wall_run("Wall_Right", "x", HW + WALL_T / 2, 0, L, g["right"])
    # stone wainscot band along the outside of the front facade
    box("Facade_StoneBase_L", "wall", -WALL_T - 30, -HW - WALL_T, -WALL_T, -700, 0, 150, "stone")
    box("Facade_StoneBase_R", "wall", -WALL_T - 30, 700, -WALL_T, HW + WALL_T, 0, 150, "stone")

    # gable end walls above the eave line: stepped timber-clad tiers (greybox triangle)
    steps = 7
    for end, xw in (("Front", -WALL_T / 2), ("Back", L + WALL_T / 2)):
        # clerestory band over the nave
        box(f"Gable_{end}_Cler", "wall", xw - WALL_T / 2, -NAVE - 20, xw + WALL_T / 2, NAVE + 20, EAVE, CLER, "wall_plaster")
        for s in range(steps):
            z0 = CLER + s * (RIDGE - CLER) / steps
            z1 = z0 + (RIDGE - CLER) / steps
            half = NAVE * (1 - (s + 0.5) / steps)
            box(f"Gable_{end}_T{s}", "wall", xw - WALL_T / 2, -half, xw + WALL_T / 2, half, z0, z1, "wall_plaster")

    # side-aisle flat roofs + nave gabled roof (tag roof; hidden in top captures)
    box("Roof_Left", "roof", -WALL_T, -HW - WALL_T, L + WALL_T, -NAVE, EAVE, EAVE + 40, "roof")
    box("Roof_Right", "roof", -WALL_T, NAVE, L + WALL_T, HW + WALL_T, EAVE, EAVE + 40, "roof")
    box("Ceil_Left", "ceiling", 0, -HW, L, -NAVE - 30, EAVE - 20, EAVE, "wall_plaster", noshadow=True)
    box("Ceil_Right", "ceiling", 0, NAVE + 30, L, HW, EAVE - 20, EAVE, "wall_plaster", noshadow=True)
    slope = math.degrees(math.atan2(RIDGE - CLER, NAVE))
    span = math.hypot(NAVE, RIDGE - CLER) + 60
    for side, sgn in (("L", -1), ("R", 1)):
        _add(dict(id=f"Roof_Nave_{side}", kind="box", cat="roof", mat="roof",
                  pos=[L / 2, sgn * NAVE / 2, (CLER + RIDGE) / 2 + 20], size=[L + 2 * WALL_T + 200, span, 30],
                  roll=sgn * slope, yaw=0))
    # clerestory walls on the columns (glass strip), timber columns, trusses
    for side, sgn in (("L", -1), ("R", 1)):
        y = sgn * NAVE
        box(f"Cler_{side}_Beam", "ceiling", 0, y - 25, L, y + 25, EAVE - 60, EAVE, "timber")
        box(f"Cler_{side}_Glass", "ceiling", 0, y - 8, L, y + 8, EAVE, CLER - 60, "glass", noshadow=True)
        box(f"Cler_{side}_Plate", "ceiling", 0, y - 25, L, y + 25, CLER - 60, CLER, "timber")
    n = int(L / BAY)
    for i in range(1, n):
        x = i * BAY
        for side, sgn in (("L", -1), ("R", 1)):
            cyl(f"Col_{side}{i}", "structure", x, sgn * NAVE, 60, 0, CLER, "wall_log", mesh=PH + "LogColumn")
        # tie beam + king post truss across the nave
        box(f"Truss_{i}_Tie", "ceiling", x - 20, -NAVE, x + 20, NAVE, CLER - 60, CLER - 20, "timber")
        box(f"Truss_{i}_King", "ceiling", x - 15, -15, x + 15, 15, CLER - 20, RIDGE - 20, "timber")
        for side, sgn in (("L", -1), ("R", 1)):
            _add(dict(id=f"Truss_{i}_Rafter{side}", kind="box", cat="ceiling", mat="timber",
                      pos=[x, sgn * NAVE / 2, (CLER + RIDGE) / 2 - 30], size=[30, span - 60, 30],
                      roll=sgn * slope, yaw=0))


# ---------------------------------------------------------------- entrances + breach panels
def breach_panel(id, wall, c, width, height=280, props=None):
    """A BP_BreachPoint scaled to fill a door gap. Faces outward (+X local toward outside)."""
    t = 30
    if wall == "front":
        pos, yaw, scale = [-WALL_T / 2, c, height / 2], 180, [t / 100, width / 100, height / 100]
    elif wall == "back":
        pos, yaw, scale = [L + WALL_T / 2, c, height / 2], 0, [t / 100, width / 100, height / 100]
    elif wall == "left":
        pos, yaw, scale = [c, -HW - WALL_T / 2, height / 2], -90, [t / 100, width / 100, height / 100]
    else:
        pos, yaw, scale = [c, HW + WALL_T / 2, height / 2], 90, [t / 100, width / 100, height / 100]
    fp = [width, t] if wall in ("left", "right") else [t, width]
    return bp(id, "gameplay", "breach", pos[0], pos[1], pos[2], yaw, props=props,
              size=[fp[0], fp[1], height], scale=scale, tag="breach", label2d=id.replace("Breach_", "B:"))


def build_entrances():
    # front: 3 glass doors (each its own breach panel), centered
    doors = [("front", 0, 720, 300), ("left", 4200, 240, 280), ("right", 4200, 240, 280), ("back", 1750, 450, 400)]
    build_shell(doors)
    for i, y in enumerate((-240, 0, 240)):
        breach_panel(f"Breach_Front{i + 1}", "front", y, 240, 300)
    breach_panel("Breach_SideL", "left", 4200, 240, 280)
    breach_panel("Breach_SideR", "right", 4200, 240, 280)
    breach_panel("Breach_Dock", "back", 1750, 450, 400)

    # grand entrance portico: stone piers + timber gable canopy outside the front doors
    for s, y in (("L", -560), ("R", 560)):
        box(f"Portico_Pier{s}", "wall", -700, y - 120, -460, y + 120, 0, 450, "stone")
        cyl(f"Portico_Log{s}", "structure", -580, y, 70, 450, 800, "wall_log")
    box("Portico_Beam", "structure", -680, -700, -480, 700, 800, 860, "timber")
    for side, sgn in (("L", -1), ("R", 1)):
        _add(dict(id=f"Portico_Roof{side}", kind="box", cat="roof", mat="roof",
                  pos=[-350, sgn * 390, 950], size=[760, 850, 25], roll=sgn * 22, yaw=0))
    box("Sign_StoreName", "deco", -60, -700, -45, 700, 720, 1000, "sign", label2d="SIGN")
    # side exit + dock exterior details
    box("Dock_Apron", "floor", L, 1250, L + 900, 2250, -1, 5, "floor_concrete", block=False)
    box("Dock_BumperL", "prop", L + 40, 1480, L + 70, 1520, 60, 140, "door_frame")
    box("Dock_BumperR", "prop", L + 40, 1980, L + 70, 2020, 60, 140, "door_frame")
    for s, sgn in (("L", -1), ("R", 1)):
        box(f"ExitSign_{s}", "deco", 4050, sgn * (HW - 25), 4350, sgn * (HW - 5), 300, 360, "light_fixture",
            block=False)


# ---------------------------------------------------------------- interior pieces
def gondola(id, x, y, length, along="x", cat="shelf", h=180, depth=120, mat="metal_shelf"):
    """A double-sided gondola run centered at (x,y). Uses the stocked placeholder mesh (long axis local +X)."""
    return cbox(id, cat, x, y, length, depth, 0, h, mat, yaw=0 if along == "x" else 90, mesh=PH + "Gondola")


def shelf_bp(id, x, y, yaw, cat):
    """Interactive BP_ShelfActor (1m cube) — +X local faces the customer side."""
    return bp(id, "gameplay", "shelf", x, y, 50, yaw, props={"ShelfCategory": cat}, label2d=cat[:4])


def build_front():
    # ---- checkout bank (front right): 3 lanes, queues run back into the store (+X)
    for i, y in enumerate((900, 1400, 1900)):
        n = i + 1
        bp(f"Checkout_{n}", "gameplay", "checkout", 650, y, 50, 0, tag="checkout", label2d=f"CHK{n}")
        box(f"Checkout_{n}_Belt", "counter", 350, y + 60, 600, y + 160, 0, 95, "counter")
        box(f"Checkout_{n}_Top", "counter", 340, y + 50, 610, y + 170, 95, 105, "counter_top", block=False)
        box(f"Checkout_{n}_Rail", "prop", 750, y + 180, 1300, y + 200, 0, 100, "metal_shelf")
        box(f"Checkout_{n}_Sign", "deco", 600, y - 10, 700, y + 10, 250, 330, "sign", block=False)
    box("Checkout_EndRail", "prop", 750, 2380, 1300, 2400, 0, 100, "metal_shelf")
    bp("CloseShop_Station", "gameplay", "close_shop", 80, 2250, 160, 0, size=(30, 180, 160), label2d="CLOSE")

    # ---- lodge / fireplace (front left) with trophy mounts and log benches
    box("Fireplace_Hearth", "display", 60, -1950, 360, -1150, 0, 50, "stone")
    box("Fireplace_Chimney", "display", 0, -1850, 250, -1250, 0, EAVE, "stone")
    box("Fireplace_Fire", "deco", 250, -1700, 280, -1400, 60, 160, "fire", block=False, nocollide=True)
    box("Fireplace_Mantel", "deco", 250, -1900, 300, -1200, 260, 290, "timber", block=False)
    box("Trophy_Moose", "deco", 250, -1650, 330, -1450, 380, 520, "wall_log", block=False)
    for i, y in enumerate((-2000, -1100)):
        cbox(f"Lodge_Bench{i}", "prop", 700, y, 60, 220, 0, 45, "timber", yaw=90 - 60 * (i * 2 - 1))
    cbox("Lodge_Rug", "floor", 650, -1550, 500, 700, 1, 2, "floor_rug", nocollide=True)
    # service desk: kiosks + legacy shop station
    box("ServiceDesk", "counter", 1100, -2450, 1800, -2150, 0, 105, "counter")
    bp("Kiosk_Discount", "gameplay", "kiosk_discount", 1250, -2000, 50, 90, label2d="DISC")
    bp("ShopStation", "gameplay", "shop_station", 1650, -2000, 50, 90, label2d="SHOP")

    # ---- customer flow: spawn inside the doors, exit just inside the doors
    for i, y in enumerate((-400, 0, 400)):
        bp(f"CustSpawn_{i + 1}", "spawn", "cust_spawn", 300, y, 90, 0, size=(0, 0, 0), block=False)
    bp("CustomerExit", "gameplay", "exit", 250, 700, 50, 180, block=False, label2d="EXIT")
    bp("CustomerSpawner", "spawn", "cust_spawner", 150, -900, 100, 0, size=(0, 0, 0), block=False)
    marker("PlayerStart_1", "spawn", "PlayerStart", 1200, -300, 100, 0)
    marker("PlayerStart_2", "spawn", "PlayerStart", 1200, 300, 100, 0)


def build_hub():
    """Central display: rock 'mountain' with waterfall pond, trophy ledges, pine tree."""
    cx, cy = 3500, 0
    _add(dict(id="Hub_Center", kind="marker", cat="zone", cls="Note", pos=[cx, cy, 0], skip_ue=True))
    cyl("Hub_PondWall", "display", cx, cy, 900, 0, 60, "stone")
    cyl("Hub_Water", "display", cx, cy, 820, 60, 62, "water", block=False, nocollide=True)
    cbox("Hub_RockBase", "display", cx + 60, cy, 480, 440, 0, 270, "stone", yaw=10, mesh=PH + "BoulderA")
    cbox("Hub_RockMid", "display", cx + 100, cy + 40, 320, 280, 240, 460, "stone", yaw=25, mesh=PH + "BoulderB")
    cbox("Hub_RockTop", "display", cx + 140, cy - 20, 200, 180, 440, 610, "stone", yaw=-15, mesh=PH + "BoulderA")
    cyl("Hub_Falls", "deco", cx - 150, cy + 10, 120, 62, 450, "water", block=False, nocollide=True)
    cbox("Hub_Elk", "deco", cx + 120, cy + 100, 160, 60, 590, 790, "wall_log", yaw=30, block=False, mesh=PH + "Elk")
    pine("Hub_Pine", cx + 250, cy - 200, 750, z0=250, block_trunk=True)
    # low plinths around the pond for turrets (the 'rock ledges')
    for i, (dx, dy) in enumerate(((-600, -600), (-600, 600), (600, -600), (600, 600))):
        cbox(f"Hub_Ledge{i}", "display", cx + dx, cy + dy, 160, 160, 0, 60, "stone", yaw=45)


def build_departments():
    # ---- HUNTING (left, front-mid): gun counter along the left wall + ammo gondolas
    box("GunCounter", "counter", 2100, -2450, 3900, -2150, 0, 105, "counter", label2d="GUN COUNTER")
    box("GunRack_Wall", "shelf", 2100, -2480, 3900, -2440, 105, 350, "timber", block=False)
    bp("Kiosk_Ammo", "gameplay", "kiosk_ammo", 3000, -2000, 50, 90, label2d="AMMO")
    for i, x in enumerate((2300, 3700)):
        gondola(f"Hunt_Gond{i}", x, -1500, 700, along="y")
        shelf_bp(f"Shelf_Ammo{i + 1}", x, -1100, 90, "AMMO")  # endcap toward nave
    gondola("Hunt_Gond2", 3000, -1500, 700, along="y", h=150)
    shelf_bp("Shelf_Trinkets3", 3000, -1100, 90, "TRINKETS")
    # archery lanes (left, back): open lane with targets at the back wall
    box("Archery_Divider", "prop", 4600, -1650, 6300, -1620, 0, 120, "timber")
    for i, y in enumerate((-2300, -1950)):
        cbox(f"Archery_Target{i}", "prop", 6500, y, 60, 120, 0, 160, "canvas")
    box("Archery_Counter", "counter", 4600, -1600, 4700, -1100, 0, 105, "counter")

    # ---- CAMPING (left, back of nave side): tent display + food/medical gondolas
    cbox("Camp_Tent1", "display", 5200, -800, 350, 350, 0, 220, "canvas", yaw=15, mesh=PH + "Tent")
    cyl("Camp_Firepit", "display", 5700, -700, 140, 0, 40, "stone")
    gondola("Camp_Gond0", 5000, -2200, 800, along="x")
    shelf_bp("Shelf_Food1", 4500, -2200, 180, "FOOD")
    shelf_bp("Shelf_Food2", 5500, -2200, 0, "FOOD")
    gondola("Camp_Gond1", 6000, -1300, 600, along="y")
    shelf_bp("Shelf_Med1", 6000, -900, 90, "MEDICAL")

    # ---- FISHING (right, mid): rod racks along right wall + tackle gondolas
    box("RodRack_Wall", "shelf", 1800, 2420, 3700, 2480, 0, 260, "timber")
    for i, x in enumerate((2200, 3100)):
        gondola(f"Fish_Gond{i}", x, 1650, 700, along="y")
        shelf_bp(f"Shelf_Hardware{i + 1}", x, 1200, -90, "HARDWARE")
    shelf_bp("Shelf_Med2", 3700, 2250, 180, "MEDICAL")
    gondola("Fish_Gond2", 2650, 1650, 700, along="y", h=150)
    shelf_bp("Shelf_Hardware3", 2650, 1200, -90, "HARDWARE")
    # boat-accessory wall bay along the right wall behind the boats
    box("BoatWall_Shelf", "shelf", 4300, 2400, 5900, 2480, 0, 240, "metal_shelf", mesh=PH + "WallShelf")
    # camping wall bay along the left wall
    box("CampWall_Shelf", "shelf", 4300, -2480, 5800, -2400, 0, 240, "metal_shelf", mesh=PH + "WallShelf")

    # ---- BOATS (right, back): two boats on trailers, open floor
    for i, x in enumerate((4600, 5700)):
        cbox(f"Boat_{i}_Hull", "display", x, 1650, 600, 200, 0, 220, "boat_hull", mesh=PH + "BassBoat")

    # ---- AQUARIUM (back center) with rock frame
    box("Aquarium_Tank", "display", 6450, -700, 6990, 700, 0, 300, "glass", label2d="AQUARIUM")
    box("Aquarium_Water", "display", 6480, -670, 6770, 670, 20, 280, "water", block=False, nocollide=True)
    box("Aquarium_RockL", "display", 6350, -1000, 6990, -700, 0, 420, "stone")
    box("Aquarium_RockR", "display", 6350, 700, 6990, 1000, 0, 420, "stone")
    box("Aquarium_RockTop", "display", 6400, -1000, 6950, 1000, 300, 420, "stone", block=False)

    # ---- NAVE islands: low display tables / canoe plinths (waist-high cover, shoot over them)
    for i, (x, y, yaw) in enumerate(((2000, -500, 0), (2000, 500, 0), (5000, -450, 20), (5000, 450, -20))):
        cbox(f"Nave_Table{i}", "display", x, y, 300, 140, 0, 100, "timber", yaw=yaw, mesh=PH + "DisplayTable")
    for dx in (-150, 150):  # sawhorse stands under the canoe
        cbox(f"Nave_CanoeStand{'L' if dx < 0 else 'R'}", "display", 2000 + dx, 0, 20, 80, 0, 90, "timber")
    cbox("Nave_Canoe", "display", 2000, 0, 500, 90, 90, 150, "boat_accent", block=False, mesh=PH + "Canoe")

    # ---- APPAREL / gifts (front, flanking the main aisle)
    for i, y in enumerate((-1600, 1600)):
        cyl(f"Apparel_Round{i}a", "shelf", 1700, y - 200, 140, 0, 130, "shelf_green", mesh=PH + "ApparelRound")
        cyl(f"Apparel_Round{i}b", "shelf", 1700, y + 250, 140, 0, 130, "shelf_green", mesh=PH + "ApparelRound")
    shelf_bp("Shelf_Trinkets1", 1500, -700, 0, "TRINKETS")
    shelf_bp("Shelf_Trinkets2", 1500, 700, 0, "TRINKETS")

    # ---- RECEIVING / stock room behind the dock (back right), with shipping crate
    box("Stock_WallX", "wall", 6000, 1100, 6040, 2500, 0, 400, "wall_plaster")      # partition along Y=
    box("Stock_WallY", "wall", 6000, 1060, 7000, 1100, 0, 400, "wall_plaster")
    # opening into the store floor (gap in Stock_WallX handled as two segments)
    E[-2]["size"][1] = 700; E[-2]["pos"][1] = 1100 + 350 + 700   # upper segment 1800..2500
    box("Stock_WallX2", "wall", 6000, 1100, 6040, 1400, 0, 400, "wall_plaster")    # 1100..1400 ; gap 1400..1800
    bp("ShippingCrate", "gameplay", "crate", 6500, 1300, 50, 90, label2d="CRATE")
    for i, y in enumerate((2200, 2350)):
        cbox(f"Stock_Pallet{i}", "prop", 6300, y, 120, 100, 0, 140, "canvas", mesh=PH + "Pallet")


def build_defense():
    """Defense sockets: FLOOR (traps/barricades), WALL (wall traps), TURRET_BASE, OTHER."""
    # front vestibule: barricade line + wall traps flanking the doors
    for i, y in enumerate((-450, 0, 450)):
        socket(f"Sock_FrontFloor{i + 1}", "FLOOR", 450, y)
    for s, y in (("L", -520), ("R", 520)):
        socket(f"Sock_FrontWall{s}", "WALL", 40, y, 150, 0)
    socket("Sock_FrontTurret", "TURRET_BASE", 1300, 0)
    # side exits: floor choke + wall trap + turret covering the approach
    for s, sgn in (("L", -1), ("R", 1)):
        socket(f"Sock_Side{s}_Floor", "FLOOR", 4200, sgn * (HW - 350))
        socket(f"Sock_Side{s}_Wall", "WALL", 3900, sgn * (HW - 40), 150, 0)
        socket(f"Sock_Side{s}_Turret", "TURRET_BASE", 4800, sgn * (HW - 700))
    # dock: receiving-room choke (the gap in the stock partition) + turret inside
    socket("Sock_Dock_Floor1", "FLOOR", 6600, 1750)
    socket("Sock_Dock_Floor2", "FLOOR", 5850, 1600)
    socket("Sock_Dock_Wall", "WALL", 6040, 1950, 150, 0)
    socket("Sock_Dock_Turret", "TURRET_BASE", 5400, 1100)
    # hub ledges: turrets that cover the whole nave
    for i, (dx, dy) in enumerate(((-600, -600), (-600, 600), (600, -600), (600, 600))):
        socket(f"Sock_Hub_Turret{i + 1}", "TURRET_BASE", 3500 + dx, dy, 65)
    # checkout protection + OTHER sockets at aisle mouths
    socket("Sock_Checkout_Floor", "FLOOR", 1400, 1400)
    socket("Sock_Checkout_Turret", "TURRET_BASE", 300, 2300)
    for i, (x, y) in enumerate(((2800, -900), (2800, 900), (5200, 0), (4300, -1850))):
        socket(f"Sock_Other{i + 1}", "OTHER", x, y)


def build_outside_and_spawns():
    # parking-lot obstacles (trucks) that break up the approach
    for i, (x, y, yaw) in enumerate(((-1800, -2200, 0), (-1800, 2000, 0), (-2400, -800, 90), (3000, -HW - 1300, 90),
                                     (5200, HW + 1400, 90), (L + 1600, -1500, 0))):
        cbox(f"Lot_Truck{i}", "prop", x, y, 520, 210, 0, 190, "boat_accent" if i % 2 else "dock_door", yaw=yaw)
    for i, (x, y) in enumerate(((-3000, -4500), (-3000, 4500), (L + 2500, -4500), (L + 2500, 4500), (1500, -5000),
                                (5500, -5000), (1500, 5000), (5500, 5000))):
        pine(f"Lot_Pine{i}", x, y, 1000)
    # zombie spawn points outside every entry
    spawns = [(-2600, -1200), (-2600, 0), (-2600, 1200), (4200, -HW - 2200), (3000, -HW - 2600),
              (4200, HW + 2200), (5400, HW + 2600), (L + 2200, 1750), (L + 2200, -500)]
    ids = []
    for i, (x, y) in enumerate(spawns):
        sid = f"ZSpawn_{i + 1}"
        yaw = math.degrees(math.atan2(-y, L / 2 - x))
        marker(sid, "spawn", "TargetPoint", x, y, 50, round(yaw))
        ids.append("@" + sid)
    bp("ZombieSpawnerManager", "spawn", "zombie_mgr", -1500, 0, 100, 0, size=(0, 0, 0), block=False,
       props={"SpawnPoints": ids})


def build_lighting():
    light("Sun", 0, 0, 3000, 6.0, kind="directional", pitch=-50, yaw=35)
    light("Sky", 0, 0, 2500, 1.6, kind="sky")
    marker("SkyAtmos", "light", "SkyAtmosphere", 0, 0, 0)
    marker("Fog", "light", "ExponentialHeightFog", 0, 0, -100)
    _add(dict(id="PPV_Global", kind="volume", cat="light", cls="PostProcessVolume", pos=[L / 2, 0, 500],
              pp={"auto_exposure_min_brightness": 0.8, "auto_exposure_max_brightness": 3.0}))
    # nave chandeliers (antler-style rings) + warm points
    for i in range(1, int(L / BAY)):
        x = i * BAY
        if i % 2 == 0:
            cyl(f"Chandelier_{i}", "ceiling", x, 0, 240, 755, 800, "light_fixture", noshadow=True, nocollide=True,
                mesh=PH + "Chandelier")
            light(f"L_Nave_{i}", x, 0, 720, 150, radius=3000)
    # side aisle cans
    for x in range(700, L, 1000):
        for s, y in (("L", -1750), ("R", 1750)):
            light(f"L_Aisle{s}_{x}", x, y, 650, 110, radius=2000, color=(1.0, 0.92, 0.8))
            cbox(f"Can_{s}_{x}", "ceiling", x, y, 120, 120, 670, 680, "light_fixture", noshadow=True, nocollide=True)
    light("L_Fire", 400, -1550, 150, 30, radius=900, color=(1.0, 0.5, 0.2))
    light("L_Aquarium", 6300, 0, 450, 30, radius=1200, color=(0.5, 0.8, 1.0))
    for i, y in enumerate((900, 1400, 1900)):
        light(f"L_Checkout{i + 1}", 750, y, 500, 120, radius=1400, color=(1.0, 0.95, 0.85))
        cbox(f"CheckoutSign_{i + 1}", "deco", 650, y, 30, 160, 420, 480, "light_fixture", noshadow=True, nocollide=True)
    # wash lights along the front wall so the checkout/fireplace backdrop reads
    for y in (-1800, -900, 900, 1800):
        light(f"L_FrontWash_{y}", 250, y, 550, 60, radius=1300, color=(1.0, 0.9, 0.75))
    light("L_Porch", -500, 0, 750, 40, radius=1400)


def build():
    E.clear()
    _ids.clear()
    build_entrances()
    build_front()
    build_hub()
    build_departments()
    build_defense()
    build_outside_and_spawns()
    build_lighting()
    return {"name": "Map_Store_Outdoors", "bounds": [[-3500, -HW - 3000], [L + 3000, HW + 3000]], "elements": E, "interior": [[0, -HW], [L, HW]],
            "nav_bounds": {"center": [L / 2 - 250, 0, 200], "extent": [L / 2 + 3200, HW + 3000, 600]}}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    lay = build()
    with open(out, "w") as f:
        json.dump(lay, f, indent=0)
    print(f"wrote {out}: {len(lay['elements'])} elements")

"""
Generate 128x128 RGBA defense build-menu icon PNGs for No Brainers.

Outputs to PlaceholderAssets/UI/DefenseIcons/. Re-run any time the
glyphs need to change; the icons are then re-imported into
/Game/UI/Icons/Defense/ via Monolith (editor.run_python or
material.import_texture with replace_existing=true).

Run: py Tools/UI/make_defense_icons.py
"""
import math
import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "PlaceholderAssets", "UI", "DefenseIcons",
)
os.makedirs(OUT_DIR, exist_ok=True)

SIZE = 128
CENTER = SIZE / 2
OUTLINE_WIDTH = 6
OUTLINE_COLOR = (20, 20, 20, 255)


def new_canvas():
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def draw_outlined_polygon(draw, points, fill):
    draw.polygon(points, fill=OUTLINE_COLOR)
    inset = _inset_polygon(points, OUTLINE_WIDTH)
    draw.polygon(inset, fill=fill)


def _inset_polygon(points, amount):
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    result = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy) or 1.0
        scale = max(0.0, (dist - amount) / dist)
        result.append((cx + dx * scale, cy + dy * scale))
    return result


def draw_outlined_ellipse(draw, bbox, fill):
    x0, y0, x1, y1 = bbox
    draw.ellipse(bbox, fill=OUTLINE_COLOR)
    draw.ellipse((x0 + OUTLINE_WIDTH, y0 + OUTLINE_WIDTH, x1 - OUTLINE_WIDTH, y1 - OUTLINE_WIDTH), fill=fill)


def save(img, name):
    path = os.path.join(OUT_DIR, name + ".png")
    img.save(path, "PNG")
    print("Wrote", path)


# --- SpikeTrap: three grey upward triangles on a dark base bar ---
def make_spike_trap():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    grey = (170, 170, 180, 255)
    dark = (60, 60, 65, 255)
    base = [(18, 96), (110, 96), (110, 114), (18, 114)]
    draw_outlined_polygon(d, base, dark)
    for cx in (40, 64, 88):
        spike = [(cx, 18), (cx + 18, 96), (cx - 18, 96)]
        draw_outlined_polygon(d, spike, grey)
    save(img, "T_DefIcon_SpikeTrap")


# --- SwingingTrap: brown mallet head on a diagonal handle ---
def make_swinging_trap():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    brown = (150, 100, 50, 255)
    handle = [(24, 106), (34, 116), (92, 40), (82, 30)]
    draw_outlined_polygon(d, handle, brown)
    head = [(70, 14), (114, 30), (100, 66), (56, 50)]
    draw_outlined_polygon(d, head, brown)
    save(img, "T_DefIcon_SwingingTrap")


# --- Turret: teal box body + horizontal barrel ---
def make_turret():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    teal = (40, 170, 190, 255)
    body = [(30, 54), (98, 54), (98, 108), (30, 108)]
    draw_outlined_polygon(d, body, teal)
    barrel = [(78, 40), (116, 46), (116, 62), (78, 68)]
    draw_outlined_polygon(d, barrel, teal)
    draw_outlined_ellipse(d, (36, 20, 72, 56), teal)
    save(img, "T_DefIcon_Turret")


# --- Barricade: tan two crossed planks ---
def make_barricade():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    tan = (200, 160, 90, 255)
    plank1 = [(18, 40), (34, 26), (110, 88), (94, 102)]
    plank2 = [(94, 26), (110, 40), (34, 102), (18, 88)]
    draw_outlined_polygon(d, plank1, tan)
    draw_outlined_polygon(d, plank2, tan)
    save(img, "T_DefIcon_Barricade")


# --- SlowStrip: blue three zigzag lines ---
def make_slow_strip():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    blue = (60, 120, 230, 255)
    for y in (34, 64, 94):
        points = [(16, y + 10), (40, y - 6), (64, y + 10), (88, y - 6), (112, y + 10)]
        d.line(points, fill=OUTLINE_COLOR, width=14, joint="curve")
        d.line(points, fill=blue, width=8, joint="curve")
    save(img, "T_DefIcon_SlowStrip")


# --- GasTrap: green canister + 3-circle cloud above ---
def make_gas_trap():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    green = (90, 200, 60, 255)
    canister = [(46, 60), (82, 60), (88, 116), (40, 116)]
    draw_outlined_polygon(d, canister, green)
    cap = [(52, 46), (76, 46), (76, 60), (52, 60)]
    draw_outlined_polygon(d, cap, green)
    draw_outlined_ellipse(d, (30, 14, 62, 46), green)
    draw_outlined_ellipse(d, (58, 8, 94, 44), green)
    draw_outlined_ellipse(d, (78, 20, 110, 52), green)
    save(img, "T_DefIcon_GasTrap")


if __name__ == "__main__":
    make_spike_trap()
    make_swinging_trap()
    make_turret()
    make_barricade()
    make_slow_strip()
    make_gas_trap()
    print("Done.")

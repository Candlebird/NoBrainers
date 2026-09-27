"""
Generate 128x128 RGBA customer archetype icon PNGs for No Brainers.

Outputs to PlaceholderAssets/UI/CustomerIcons/. Re-run any time the
glyphs need to change; the icons are then re-imported into
/Game/UI/Icons/Customer/ via Monolith (editor.run_python or
material.import_texture with replace_existing=true).

Run: py Tools/UI/make_customer_icons.py
"""
import math
import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "PlaceholderAssets", "UI", "CustomerIcons",
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


# --- Rich: gold "$" in a gold ring ---
def make_rich():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    gold = (255, 200, 40, 255)
    draw_outlined_ellipse(d, (12, 12, 116, 116), (0, 0, 0, 0))
    # ring: draw outer gold circle, then cut inner transparent circle
    d.ellipse((12, 12, 116, 116), outline=OUTLINE_COLOR, width=OUTLINE_WIDTH + 4)
    d.ellipse((18, 18, 110, 110), outline=gold, width=10)
    # dollar sign glyph using a bold font-less shape: vertical bar + S-curve via arcs
    d.line([(64, 26), (64, 102)], fill=OUTLINE_COLOR, width=16)
    d.line([(64, 26), (64, 102)], fill=gold, width=8)
    # S shape approximated with two arcs
    d.arc((40, 32, 84, 66), start=200, end=380, fill=OUTLINE_COLOR, width=16)
    d.arc((40, 32, 84, 66), start=200, end=380, fill=gold, width=8)
    d.arc((40, 62, 84, 96), start=20, end=200, fill=OUTLINE_COLOR, width=16)
    d.arc((40, 62, 84, 96), start=20, end=200, fill=gold, width=8)
    save(img, "T_CustIcon_Rich")


# --- Fighter: red fist ---
def make_fighter():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    red = (220, 40, 40, 255)
    # fist: rounded square palm + four knuckle bumps + thumb
    palm = [(34, 50), (94, 50), (94, 104), (34, 104)]
    draw_outlined_polygon(d, palm, red)
    for i, kx in enumerate((40, 56, 72, 88)):
        draw_outlined_ellipse(d, (kx - 10, 26, kx + 10, 56), red)
    thumb = [(20, 66), (40, 58), (40, 90), (22, 92)]
    draw_outlined_polygon(d, thumb, red)
    save(img, "T_CustIcon_Fighter")


# --- Nurse: white cross on red circle ---
def make_nurse():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    red = (200, 30, 30, 255)
    white = (250, 250, 250, 255)
    draw_outlined_ellipse(d, (10, 10, 118, 118), red)
    # cross
    vbar = [(54, 30), (74, 30), (74, 98), (54, 98)]
    hbar = [(30, 54), (98, 54), (98, 74), (30, 74)]
    d.polygon(vbar, fill=OUTLINE_COLOR)
    d.polygon(hbar, fill=OUTLINE_COLOR)
    inset_v = [(58, 34), (70, 34), (70, 94), (58, 94)]
    inset_h = [(34, 58), (94, 58), (94, 70), (34, 70)]
    d.polygon(inset_v, fill=white)
    d.polygon(inset_h, fill=white)
    save(img, "T_CustIcon_Nurse")


# --- Scavenger: brown magnifier ---
def make_scavenger():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    brown = (150, 100, 50, 255)
    # lens ring
    d.ellipse((22, 16, 90, 84), outline=OUTLINE_COLOR, width=OUTLINE_WIDTH + 4)
    d.ellipse((28, 22, 84, 78), outline=brown, width=12)
    # handle
    handle = [(78, 78), (108, 108), (98, 118), (68, 88)]
    draw_outlined_polygon(d, handle, brown)
    save(img, "T_CustIcon_Scavenger")


# --- TrinketCollector: purple gem ---
def make_trinket_collector():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    purple = (170, 80, 230, 255)
    gem = [
        (64, 18), (96, 44), (110, 50), (96, 58),
        (64, 112), (32, 58), (18, 50), (32, 44),
    ]
    draw_outlined_polygon(d, gem, purple)
    # facet lines
    d.line([(64, 44), (64, 112)], fill=OUTLINE_COLOR, width=3)
    d.line([(32, 58), (96, 58)], fill=OUTLINE_COLOR, width=3)
    save(img, "T_CustIcon_TrinketCollector")


if __name__ == "__main__":
    make_rich()
    make_fighter()
    make_nurse()
    make_scavenger()
    make_trinket_collector()
    print("Done.")

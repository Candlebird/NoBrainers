"""Headless Blender: cheap visual-QA contact sheet for zombie placeholder animations.

Renders one PNG per zombie type: a grid of low-res workbench snapshots, a few sampled frames per clip, camera
side/3-quarter, mesh visible. Meant to catch obvious breakage (T-pose arms, limbs through the body, backward
bends, feet far through the floor) -- not for polish.

"C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background --factory-startup \
    PlaceholderAssets/Blender/Zombie/A_Z_Anims.blend --python Tools/Characters/blender_zombie_anim_preview.py \
    -- --type Shambler --out C:/Users/brest/.claude/jobs/23a78492/tmp

Reads the combined A_Z_Anims.blend (all actions, fake-user'd) produced by blender_zombie_anims.py. Does not save
anything.
"""
import math
import os
import sys

import bpy

argv = sys.argv
ARGS_TYPE = None
OUT_DIR = os.path.join("C:/Users/brest/.claude/jobs/23a78492/tmp")
if "--" in argv:
    tail = argv[argv.index("--") + 1:]
    i = 0
    while i < len(tail):
        if tail[i] == "--type" and i + 1 < len(tail):
            ARGS_TYPE = tail[i + 1]
            i += 2
        elif tail[i] == "--out" and i + 1 < len(tail):
            OUT_DIR = tail[i + 1]
            i += 2
        else:
            i += 1

CELL_W, CELL_H = 320, 240
SAMPLES_PER_CLIP = 5


def get_rig():
    arm = mesh = None
    for ob in bpy.data.objects:
        if ob.type == "ARMATURE":
            arm = ob
        elif ob.type == "MESH":
            mesh = ob
    return arm, mesh


def setup_scene(arm, mesh):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    if mesh is not None:
        mesh.hide_set(False)
        mesh.hide_render = False
    scene.render.resolution_x = CELL_W
    scene.render.resolution_y = CELL_H
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    for ob in list(bpy.data.objects):
        if ob.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(ob)

    cam_data = bpy.data.cameras.new("QA_Cam")
    cam = bpy.data.objects.new("QA_Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    # 3/4 side view, framed on the character (~180cm tall, standing near origin)
    cam.location = (280.0, -320.0, 130.0)
    cam.rotation_euler = (math.radians(80.0), 0.0, math.radians(41.0))
    cam_data.lens = 45.0
    scene.camera = cam

    light_data = bpy.data.lights.new("QA_Sun", type="SUN")
    light = bpy.data.objects.new("QA_Sun", light_data)
    light.rotation_euler = (math.radians(55.0), 0.0, math.radians(35.0))
    light_data.energy = 3.0
    bpy.context.collection.objects.link(light)


def render_frame(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def build_sheet(type_name, out_dir):
    arm, mesh = get_rig()
    if arm is None:
        print(f"ZOMBIE_PREVIEW_FAIL no armature")
        sys.exit(1)
    setup_scene(arm, mesh)
    prefix = f"A_Z_{type_name}_"
    actions = [a for a in bpy.data.actions if a.name.startswith(prefix)]
    if not actions:
        print(f"ZOMBIE_PREVIEW_FAIL no actions for type {type_name}")
        sys.exit(1)
    actions.sort(key=lambda a: a.name)

    tmp_dir = os.path.join(out_dir, f"_cells_{type_name}")
    os.makedirs(tmp_dir, exist_ok=True)
    cell_paths = []
    labels = []
    if arm.animation_data is None:
        arm.animation_data_create()
    for act in actions:
        arm.animation_data.action = act
        frame_range = act.frame_range
        f0, f1 = int(frame_range[0]), int(frame_range[1])
        if f1 <= f0:
            f1 = f0 + 1
        for i in range(SAMPLES_PER_CLIP):
            frame = round(f0 + (f1 - f0) * i / (SAMPLES_PER_CLIP - 1))
            bpy.context.scene.frame_set(frame)
            cell_path = os.path.join(tmp_dir, f"{act.name}_{i}.png")
            render_frame(cell_path)
            cell_paths.append(cell_path)
        labels.append(act.name[len(prefix):])

    # assemble grid: one row per clip, SAMPLES_PER_CLIP columns
    try:
        import numpy as np
    except ImportError:
        np = None

    sheet_path = os.path.join(out_dir, f"zanim_{type_name}.png")
    rows = len(actions)
    cols = SAMPLES_PER_CLIP
    if np is not None:
        big = np.zeros((rows * CELL_H, cols * CELL_W, 4), dtype=np.float32)
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                img = bpy.data.images.load(cell_paths[idx])
                w, h = img.size
                pix = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
                pix = pix[::-1, :, :]  # blender pixel origin bottom-left
                big[r * CELL_H:(r + 1) * CELL_H, c * CELL_W:(c + 1) * CELL_W, :] = pix[:CELL_H, :CELL_W, :]
                bpy.data.images.remove(img)
        out_img = bpy.data.images.new("QA_Sheet", cols * CELL_W, rows * CELL_H)
        out_img.pixels = big[::-1, :, :].flatten().tolist()
        out_img.filepath_raw = sheet_path
        out_img.file_format = "PNG"
        out_img.save()
        bpy.data.images.remove(out_img)
        for p in cell_paths:
            pass
        print(f"ZOMBIE_PREVIEW OK {type_name} rows={rows} cols={cols} -> {sheet_path}")
        for lbl in labels:
            print(f"ZOMBIE_PREVIEW ROW {type_name} {lbl}")
    else:
        print(f"ZOMBIE_PREVIEW_FAIL numpy unavailable, cells left in {tmp_dir}")
        sys.exit(1)


def main():
    out_dir = OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    if ARGS_TYPE:
        build_sheet(ARGS_TYPE, out_dir)
    else:
        prefixes = sorted({a.name.split("_")[2] for a in bpy.data.actions if a.name.startswith("A_Z_")})
        for t in prefixes:
            build_sheet(t, out_dir)


if __name__ == "__main__":
    main()

"""In-editor: render the open editor level to PNG with a SceneCapture2D (no PIE needed).

Run via Monolith editor.run_python {command: "<abs>/ue_capture.py <preset> [args...]", unattended: true}

Presets (all write <project>/Saved/LevelView/cap_<name>.png + .json camera sidecar):
  top  [cx cy width_cm]          orthographic top-down, roof (tag LV_roof) hidden. +X right, +Y down.
  iso  [yaw_deg] [pitch] [dist]  perspective 3/4 view of the whole level from outside, roof hidden
  eye  x y yaw [pitch] [z]       player-eye perspective at (x,y), z default 165 (eye height)
  cam  x y z pitch yaw [fov]     arbitrary perspective camera
Common trailing flags: res=WxH  name=<file stem>  roof=1 (keep roof visible)  fov=<deg>
"""
import json
import math
import os
import sys

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
OUT_DIR = os.path.join(PROJ, "Saved", "LevelView")


def level_bounds(actors):
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]
    for a in actors:
        if not a.tags or not any(str(t) == "LV" for t in a.tags):
            continue
        o, e = a.get_actor_bounds(False)
        for i, (c, x) in enumerate(((o.x, e.x), (o.y, e.y), (o.z, e.z))):
            lo[i] = min(lo[i], c - x)
            hi[i] = max(hi[i], c + x)
    if lo[0] > hi[0]:
        return [-2500, -2500, 0], [2500, 2500, 1000]
    return lo, hi


def main(argv):
    flags = {}
    pos = []
    for t in argv:
        if "=" in t:
            k, v = t.split("=", 1)
            flags[k] = v
        else:
            pos.append(t)
    preset = pos[0] if pos else "top"
    nums = [float(v) for v in pos[1:]]
    w, h = [int(v) for v in flags.get("res", "1200x900").split("x")]
    name = flags.get("name", preset)
    keep_roof = flags.get("roof", "0") == "1"

    ess = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = ess.get_all_level_actors()
    lo, hi = level_bounds(actors)
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    span_x, span_y = hi[0] - lo[0], hi[1] - lo[1]

    cam = {"preset": preset, "res": [w, h]}
    ortho = False
    fov = float(flags.get("fov", 90))
    if preset == "top":
        ortho = True
        if len(nums) >= 2:
            cx, cy = nums[0], nums[1]
        ow = nums[2] if len(nums) >= 3 else max(span_x, span_y * w / h) * 1.04
        loc = unreal.Vector(cx, cy, hi[2] + 2000)
        rot = unreal.Rotator(roll=0, pitch=-90, yaw=-90)
        # yaw -90 with pitch -90: image right = +X, image down = +Y
        cam.update(ortho_width=ow, center=[cx, cy])
    elif preset == "iso":
        yaw = nums[0] if len(nums) >= 1 else 35.0
        pitch = nums[1] if len(nums) >= 2 else -35.0
        dist = nums[2] if len(nums) >= 3 else max(span_x, span_y) * 1.05
        fov = float(flags.get("fov", 60))
        cz = (lo[2] + hi[2]) / 3
        yr, pr = math.radians(yaw), math.radians(pitch)
        # camera sits opposite its look direction
        loc = unreal.Vector(cx - dist * math.cos(pr) * math.cos(yr), cy - dist * math.cos(pr) * math.sin(yr),
                            cz - dist * math.sin(pr))
        rot = unreal.Rotator(roll=0, pitch=pitch, yaw=yaw)
    elif preset == "eye":
        x, y, yaw = nums[0], nums[1], nums[2]
        pitch = nums[3] if len(nums) >= 4 else -5.0
        z = nums[4] if len(nums) >= 5 else 165.0
        keep_roof = flags.get("roof", "1") == "1"
        loc = unreal.Vector(x, y, z)
        rot = unreal.Rotator(roll=0, pitch=pitch, yaw=yaw)
    elif preset == "cam":
        loc = unreal.Vector(nums[0], nums[1], nums[2])
        rot = unreal.Rotator(roll=0, pitch=nums[3], yaw=nums[4])
        if len(nums) >= 6:
            fov = nums[5]
        keep_roof = flags.get("roof", "1") == "1"
    else:
        raise SystemExit(f"unknown preset {preset}")

    rt = unreal.RenderingLibrary.create_render_target2d(world, w, h, unreal.TextureRenderTargetFormat.RTF_RGBA8,
                                                         unreal.LinearColor(0, 0, 0, 1))
    cap = ess.spawn_actor_from_class(unreal.SceneCapture2D, loc, rot, transient=True)
    try:
        comp = cap.capture_component2d
        comp.set_editor_property("texture_target", rt)
        comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        comp.set_editor_property("capture_every_frame", False)
        comp.set_editor_property("capture_on_movement", False)
        if ortho:
            comp.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
            comp.set_editor_property("ortho_width", cam["ortho_width"])
        else:
            comp.set_editor_property("fov_angle", fov)
        pps = comp.get_editor_property("post_process_settings")
        pps.set_editor_property("override_auto_exposure_method", True)
        pps.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
        pps.set_editor_property("override_auto_exposure_bias", True)
        pps.set_editor_property("auto_exposure_bias", float(flags.get("ev", 10 if ortho else 11)))
        pps.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
        pps.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
        comp.set_editor_property("post_process_settings", pps)
        comp.set_editor_property("post_process_blend_weight", 1.0)
        if not keep_roof:
            for a in actors:  # hidden_actors can't be set via editor props on spawned comps; use the API
                if any(str(t) in ("LV_roof", "LV_ceiling") for t in a.tags):
                    comp.hide_actor_components(a, False)
        comp.capture_scene()
        os.makedirs(OUT_DIR, exist_ok=True)
        fname = f"cap_{name}.png"
        unreal.RenderingLibrary.export_render_target(world, rt, OUT_DIR, fname)
    finally:
        cap.destroy_actor()
    cam.update(loc=[loc.x, loc.y, loc.z], rot=[rot.pitch, rot.yaw, rot.roll], fov=fov, ortho=ortho,
               level_lo=lo, level_hi=hi)
    with open(os.path.join(OUT_DIR, f"cap_{name}.json"), "w") as f:
        json.dump(cam, f)
    print(f"LEVELVIEW_CAPTURE {os.path.join(OUT_DIR, fname)}")


main(sys.argv[1:])

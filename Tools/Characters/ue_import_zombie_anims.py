"""In-editor: import blender_zombie_anims.py output.

  PlaceholderAssets/FBX/Zombie/A_Z_<Type>_<Clip>.fbx -> /Game/Characters/Zombie/Animations/<Type>/A_Z_<Type>_<Clip>
  (AnimSequence, SK_Zombie_Skeleton, animation only, no mesh).

Every HitReact clip is set up as a local-space additive (ref pose = animation frame 0 of itself), so it can be
layered over any base pose in the ABP. All imported clips have root motion disabled.

Run via Monolith editor.run_python {command: "<abs>/ue_import_zombie_anims.py", unattended: true}.
Do NOT run this outside the editor -- it only makes sense as an in-editor Unreal Python call.
"""
import os

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC_DIR = os.path.join(PROJ, "PlaceholderAssets", "FBX", "Zombie")
DEST_ROOT = "/Game/Characters/Zombie/Animations"
SKELETON = "/Game/Characters/Zombie/SK_Zombie_Skeleton"


def parse_name(filename):
    # A_Z_<Type>_<Clip>.fbx -- Type and Clip are themselves single CamelCase tokens (no underscores), so a
    # straight split on "_" is safe: A, Z, Type, Clip.
    stem = os.path.splitext(filename)[0]
    parts = stem.split("_")
    if len(parts) != 4 or parts[0] != "A" or parts[1] != "Z":
        return None, None
    return parts[2], parts[3]


def import_one(skeleton, filename, type_name, clip_name):
    dest_path = f"{DEST_ROOT}/{type_name}"
    dest_name = f"A_Z_{type_name}_{clip_name}"
    src = os.path.join(SRC_DIR, filename)

    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", False)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_animations", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    ui.set_editor_property("skeleton", skeleton)

    anim_data = ui.get_editor_property("anim_sequence_import_data")
    anim_data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    anim_data.set_editor_property("use_default_sample_rate", False)
    anim_data.set_editor_property("custom_sample_rate", 30)
    anim_data.set_editor_property("import_uniform_scale", 1.0)
    anim_data.set_editor_property("import_custom_attribute", False)
    anim_data.set_editor_property("import_bone_tracks", True)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", src)
    task.set_editor_property("destination_path", dest_path)
    task.set_editor_property("destination_name", dest_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    seq = unreal.load_asset(f"{dest_path}/{dest_name}.{dest_name}")
    if not seq:
        print(f"ZOMBIE_IMPORT_FAIL {dest_name} sequence not created")
        return False

    if clip_name == "HitReact":
        try:
            seq.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
            seq.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_ANIM_FRAME)
            seq.set_editor_property("ref_pose_seq", seq)
            seq.set_editor_property("ref_frame_index", 0)
        except Exception as e:
            print(f"ZOMBIE_IMPORT NOTE {dest_name} additive setup failed: {e}")

    try:
        seq.set_editor_property("enable_root_motion", False)
    except Exception as e:
        print(f"ZOMBIE_IMPORT NOTE {dest_name} enable_root_motion failed: {e}")

    unreal.EditorAssetLibrary.save_loaded_asset(seq)
    return True


def main():
    skeleton = unreal.load_asset(SKELETON)
    if not skeleton:
        print(f"ZOMBIE_IMPORT_FAIL skeleton not found {SKELETON}")
        return

    if not os.path.isdir(SRC_DIR):
        print(f"ZOMBIE_IMPORT_FAIL src dir not found {SRC_DIR}")
        return

    files = sorted(f for f in os.listdir(SRC_DIR) if f.lower().endswith(".fbx"))
    if not files:
        print(f"ZOMBIE_IMPORT_FAIL no fbx files in {SRC_DIR}")
        return

    ok = 0
    fail = 0
    for filename in files:
        type_name, clip_name = parse_name(filename)
        if not type_name:
            print(f"ZOMBIE_IMPORT NOTE skipped unrecognized filename {filename}")
            continue
        try:
            if import_one(skeleton, filename, type_name, clip_name):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            fail += 1
            print(f"ZOMBIE_IMPORT_FAIL {filename}: {e}")

    if fail:
        print(f"ZOMBIE_IMPORT_FAIL {fail} of {len(files)} imports failed, {ok} ok")
    else:
        print(f"ZOMBIE_IMPORT OK {ok}")


main()

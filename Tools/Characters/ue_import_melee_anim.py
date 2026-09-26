"""In-editor: import blender_melee_anim.py output.

  PlaceholderAssets/FBX/A_MeleeSwing.fbx -> /Game/Characters/Hero/Animations/A_MeleeSwing (AnimSequence,
  UE4_Mannequin_Skeleton, animation only, no mesh).

Run via Monolith editor.run_python {command: "<abs>/ue_import_melee_anim.py", unattended: true}.
"""
import os

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJ, "PlaceholderAssets", "FBX", "A_MeleeSwing.fbx")
DEST = "/Game/Characters/Hero/Animations"
SKELETON = "/Game/AnimStarterPack/UE4_Mannequin/Mesh/UE4_Mannequin_Skeleton"


def main():
    skeleton = unreal.load_asset(SKELETON)
    if not skeleton:
        print(f"MELEE_IMPORT_FAIL skeleton not found {SKELETON}")
        return

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
    task.set_editor_property("filename", SRC)
    task.set_editor_property("destination_path", DEST)
    task.set_editor_property("destination_name", "A_MeleeSwing")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    seq = unreal.load_asset(f"{DEST}/A_MeleeSwing.A_MeleeSwing")
    if not seq:
        print("MELEE_IMPORT_FAIL sequence not created")
        return
    unreal.EditorAssetLibrary.save_loaded_asset(seq)
    n_frames = seq.get_editor_property("number_of_sampled_keys") if hasattr(seq, "get_editor_property") else None
    print(f"MELEE_IMPORT OK path={DEST}/A_MeleeSwing")


main()

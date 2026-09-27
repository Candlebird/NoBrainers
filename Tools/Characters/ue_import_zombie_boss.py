"""In-editor: import blender_zombie_boss.py output.

  PlaceholderAssets/FBX/Zombie/SK_Zombie_Boss.fbx -> /Game/Characters/Zombie/SK_Zombie_Boss
  (SkeletalMesh, mesh + generated physics asset PA_SK_Zombie_Boss, on SK_Zombie_Skeleton, no animation).

Run via Monolith editor.run_python {command: "<abs>/ue_import_zombie_boss.py", unattended: true}.
Do NOT run this outside the editor -- it only makes sense as an in-editor Unreal Python call.

Notes for anyone re-running this:
  - FbxImportUI's create_physics_asset flag is not honored by the automated AssetImportTask path in this
    engine build (no _PhysicsAsset asset is produced). Physics asset is created explicitly afterward via
    SkeletalMeshEditorSubsystem.create_physics_asset(), then renamed to PA_SK_Zombie_Boss.
  - USkeletalMesh.materials returned by get_editor_property is a copy of the struct array; mutating an
    element in place and writing it back does not stick. Build a fresh unreal.SkeletalMaterial() and
    set_editor_property('materials', [...]) with the whole new list instead.
"""
import os

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJ, "PlaceholderAssets", "FBX", "Zombie", "SK_Zombie_Boss.fbx")
DEST_PATH = "/Game/Characters/Zombie"
DEST_NAME = "SK_Zombie_Boss"
SKELETON_PATH = "/Game/Characters/Zombie/SK_Zombie_Skeleton"
BASE_MESH_PATH = "/Game/Characters/Zombie/SK_Zombie"
MATERIAL_PATH = "/Game/GASDocumentation/Characters/Minions/Zombie/Zombie_Mat"


def fail(reason):
    print(f"BOSS_IMPORT_FAIL {reason}")


def main():
    skeleton = unreal.load_asset(SKELETON_PATH)
    if not skeleton:
        fail(f"skeleton not found {SKELETON_PATH}")
        return

    if not os.path.isfile(SRC):
        fail(f"src fbx not found {SRC}")
        return

    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("skeleton", skeleton)
    ui.set_editor_property("create_physics_asset", True)

    mesh_data = ui.get_editor_property("skeletal_mesh_import_data")
    mesh_data.set_editor_property("update_skeleton_reference_pose", False)
    mesh_data.set_editor_property("import_uniform_scale", 1.0)
    mesh_data.set_editor_property("use_t0_as_ref_pose", False)
    mesh_data.set_editor_property("import_morph_targets", False)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", SRC)
    task.set_editor_property("destination_path", DEST_PATH)
    task.set_editor_property("destination_name", DEST_NAME)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    mesh = unreal.load_asset(f"{DEST_PATH}/{DEST_NAME}.{DEST_NAME}")
    if not mesh:
        fail(f"{DEST_NAME} skeletal mesh not created")
        return

    # create_physics_asset on FbxImportUI isn't honored by the automated import path here -- build it
    # explicitly and rename to the packet's expected name.
    target_pa_path = f"{DEST_PATH}/PA_SK_Zombie_Boss"
    pa = unreal.load_asset(target_pa_path)
    if pa is None:
        sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
        pa = sub.create_physics_asset(mesh, True, 0)
        if pa is None:
            fail("SkeletalMeshEditorSubsystem.create_physics_asset returned None")
        else:
            auto_pa_path = pa.get_path_name().split(".")[0]
            if auto_pa_path != target_pa_path:
                if not unreal.EditorAssetLibrary.rename_asset(auto_pa_path, target_pa_path):
                    fail(f"could not rename {auto_pa_path} to {target_pa_path}")
                else:
                    pa = unreal.load_asset(target_pa_path)

    material = unreal.load_asset(MATERIAL_PATH)
    if material:
        old = mesh.get_editor_property("materials")[0]
        new_slot = unreal.SkeletalMaterial()
        new_slot.set_editor_property("material_slot_name", old.get_editor_property("material_slot_name"))
        new_slot.set_editor_property("material_interface", material)
        mesh.set_editor_property("materials", [new_slot])
    else:
        fail(f"material not found {MATERIAL_PATH}")

    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    if pa:
        unreal.EditorAssetLibrary.save_loaded_asset(pa)

    boss_bone_tree = mesh.get_editor_property("skeleton").get_editor_property("bone_tree")
    boss_bones = len(boss_bone_tree) if boss_bone_tree is not None else -1

    base_mesh = unreal.load_asset(BASE_MESH_PATH)
    base_bones = -1
    base_z = -1.0
    if base_mesh:
        base_bone_tree = base_mesh.get_editor_property("skeleton").get_editor_property("bone_tree")
        base_bones = len(base_bone_tree) if base_bone_tree is not None else -1
        base_z = base_mesh.get_bounds().box_extent.z * 2.0

    boss_z = mesh.get_bounds().box_extent.z * 2.0

    print(f"BOSS_IMPORT bones={boss_bones} base_bones={base_bones} boundsZ={boss_z:.2f} baseZ={base_z:.2f}")


if __name__ == "__main__":
    main()

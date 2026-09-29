"""In-editor: import blender_rig_zombie_variants.py output onto the shared zombie skeleton.

  PlaceholderAssets/FBX/Zombie/SK_Zombie_<Variant>.fbx -> /Game/Characters/Zombie/SK_Zombie_<Variant>
  (SkeletalMesh + physics asset PA_SK_Zombie_<Variant>, on SK_Zombie_Skeleton, no animation, no materials).

Run via Monolith editor.run_python {command: "<abs>/ue_import_zombie_variants.py", unattended: true}.
Same import notes as ue_import_zombie_boss.py (physics asset created explicitly after import).
The source meshes ship without textures, so the material slot keeps the engine default.
"""
import os

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
FBX_DIR = os.path.join(PROJ, "PlaceholderAssets", "FBX", "Zombie")
DEST_PATH = "/Game/Characters/Zombie"
SKELETON_PATH = "/Game/Characters/Zombie/SK_Zombie_Skeleton"
VARIANTS = ["SK_Zombie_Female", "SK_Zombie_Swamp"]


def fail(reason):
    print(f"VARIANT_IMPORT_FAIL {reason}")


def import_one(name, skeleton):
    src = os.path.join(FBX_DIR, f"{name}.fbx")
    if not os.path.isfile(src):
        fail(f"src fbx not found {src}")
        return

    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("skeleton", skeleton)
    mesh_data = ui.get_editor_property("skeletal_mesh_import_data")
    mesh_data.set_editor_property("update_skeleton_reference_pose", False)
    mesh_data.set_editor_property("import_uniform_scale", 1.0)
    mesh_data.set_editor_property("use_t0_as_ref_pose", False)
    mesh_data.set_editor_property("import_morph_targets", False)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", src)
    task.set_editor_property("destination_path", DEST_PATH)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    mesh = unreal.load_asset(f"{DEST_PATH}/{name}.{name}")
    if not mesh:
        fail(f"{name} skeletal mesh not created")
        return

    target_pa_path = f"{DEST_PATH}/PA_{name}"
    pa = unreal.load_asset(target_pa_path)
    if pa is None:
        sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
        pa = sub.create_physics_asset(mesh, True, 0)
        if pa is None:
            fail(f"{name}: create_physics_asset returned None")
        else:
            auto_pa_path = pa.get_path_name().split(".")[0]
            if auto_pa_path != target_pa_path:
                if not unreal.EditorAssetLibrary.rename_asset(auto_pa_path, target_pa_path):
                    fail(f"could not rename {auto_pa_path} to {target_pa_path}")
                pa = unreal.load_asset(target_pa_path)

    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    if pa:
        unreal.EditorAssetLibrary.save_loaded_asset(pa)

    skel = mesh.get_editor_property("skeleton")
    ext = mesh.get_bounds().box_extent
    print(f"VARIANT_IMPORT {name} skeleton={skel.get_name() if skel else None} "
          f"boundsZ={ext.z * 2:.1f} pa={'ok' if pa else 'missing'}")


def main():
    skeleton = unreal.load_asset(SKELETON_PATH)
    if not skeleton:
        fail(f"skeleton not found {SKELETON_PATH}")
        return
    for name in VARIANTS:
        import_one(name, skeleton)


if __name__ == "__main__":
    main()

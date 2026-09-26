"""In-editor: import blender_zombie_projectiles.py output.

  PlaceholderAssets/FBX/Props/SM_SpitterGlob.fbx -> /Game/Props/Zombie/SM_SpitterGlob
  PlaceholderAssets/FBX/Props/SM_AcidPuddle.fbx  -> /Game/Props/Zombie/SM_AcidPuddle
  (static mesh, no collision, no auto lightmap UVs)

Assigns /Game/Props/Zombie/M_Acid to every material slot and sets collision to NoCollision.

Run via Monolith editor.run_python {command: "<abs>/ue_import_zombie_projectiles.py", unattended: true}.
"""
import os

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC_DIR = os.path.join(PROJ, "PlaceholderAssets", "FBX", "Props")
DEST = "/Game/Props/Zombie"
MAT = "/Game/Props/Zombie/M_Acid"
NAMES = ["SM_SpitterGlob", "SM_AcidPuddle"]


def import_one(name):
    src = os.path.join(SRC_DIR, f"{name}.fbx")
    if not os.path.isfile(src):
        print(f"PROJECTILES_IMPORT_FAIL {name} missing_fbx")
        return None

    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("combine_meshes", True)
    sm.set_editor_property("auto_generate_collision", False)
    sm.set_editor_property("generate_lightmap_u_vs", False)
    sm.set_editor_property("import_uniform_scale", 1.0)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", src)
    task.set_editor_property("destination_path", DEST)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return unreal.load_asset(f"{DEST}/{name}.{name}")


def main():
    sml = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    acid = unreal.load_asset(MAT)
    n = 0
    for name in NAMES:
        mesh = import_one(name)
        if not mesh:
            continue
        for i in range(len(mesh.get_editor_property("static_materials"))):
            mesh.set_material(i, acid)
        sml.remove_collisions(mesh)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        b = mesh.get_bounding_box()
        n += 1
        print(f"PROJECTILES_IMPORT {name} min=({b.min.x:.1f},{b.min.y:.1f},{b.min.z:.1f}) "
              f"max=({b.max.x:.1f},{b.max.y:.1f},{b.max.z:.1f})")
    print(f"PROJECTILES_IMPORT_DONE {n}")


main()

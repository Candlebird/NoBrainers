"""In-editor: import blender_fx.py output.

  PlaceholderAssets/FBX/SM_FX_*.fbx -> /Game/Weapons/Meshes (static, no collision, no lightmap UVs)

Run via Monolith editor.run_python {command: "<abs>/ue_import_fx.py", unattended: true}.
Every slot gets M_LaserProjectile (the only FX material so far).
"""
import glob
import os

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJ, "PlaceholderAssets", "FBX")
DEST = "/Game/Weapons/Meshes"
MAT = "/Game/GASDocumentation/Characters/Hero/Abilities/FireGun/M_LaserProjectile"


def import_fbx(path):
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
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", DEST)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    name = os.path.splitext(os.path.basename(path))[0]
    return unreal.load_asset(f"{DEST}/{name}.{name}")


def main():
    sml = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    mat = unreal.load_asset(MAT)
    n = 0
    for path in sorted(glob.glob(os.path.join(SRC, "SM_FX_*.fbx"))):
        name = os.path.splitext(os.path.basename(path))[0]
        mesh = import_fbx(path)
        if not mesh:
            print(f"FX_IMPORT_FAIL {name}")
            continue
        for i in range(len(mesh.get_editor_property("static_materials"))):
            mesh.set_material(i, mat)
        sml.remove_collisions(mesh)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        b = mesh.get_bounding_box()
        n += 1
        print(f"FX_IMPORT {name} min=({b.min.x:.1f},{b.min.y:.1f},{b.min.z:.1f}) "
              f"max=({b.max.x:.1f},{b.max.y:.1f},{b.max.z:.1f})")
    print(f"FX_IMPORT_DONE {n}")


main()

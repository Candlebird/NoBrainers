"""In-editor: import PlaceholderAssets/FBX/SM_PH_*.fbx into /Game/Environment/Placeholder.

Run via Monolith editor.run_python {command: "<abs>/ue_import_placeholders.py [only=Name1,Name2] [nocollide=Name,...]",
unattended: true}. Re-running reimports (replaces) the meshes.

Each material slot is named after an lvlib.MATERIALS key and gets MI_LV_<key> (run ue_make_materials.py first).
Collision is one simple box around the whole mesh, so navigation/blocking matches the old greybox Cube.
"""
import glob
import os
import sys

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJ, "PlaceholderAssets", "FBX")
DEST = "/Game/Environment/Placeholder"
MAT_DIR = "/Game/Environment/Greybox/MI_LV_"


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
    sm.set_editor_property("generate_lightmap_u_vs", True)
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


def slot_key(slot_name):
    # FBX/Blender may suffix duplicates (".001") or UE may add "_Mat"/"_N"; strip back to a palette key
    key = str(slot_name).split(".")[0]
    for suf in ("_Mat",):
        if key.endswith(suf):
            key = key[: -len(suf)]
    return key


def main(argv):
    flags = dict(a.split("=", 1) for a in argv if "=" in a)
    only = set(flags["only"].split(",")) if "only" in flags else None
    nocollide = set(flags.get("nocollide", "").split(",")) - {""}
    sml = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    done = []
    for path in sorted(glob.glob(os.path.join(SRC, "SM_PH_*.fbx"))):
        name = os.path.splitext(os.path.basename(path))[0]
        short = name[len("SM_PH_"):]
        if only and short not in only:
            continue
        mesh = import_fbx(path)
        if not mesh:
            print(f"PH_IMPORT_FAIL {name}")
            continue
        missing = []
        mats = mesh.get_editor_property("static_materials")
        for i, sm in enumerate(mats):
            key = slot_key(sm.get_editor_property("material_slot_name"))
            mi = unreal.load_asset(MAT_DIR + key)
            if mi:
                mesh.set_material(i, mi)
            else:
                missing.append(key)
        sml.remove_collisions(mesh)
        if short not in nocollide:
            sml.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        b = mesh.get_bounding_box()
        done.append(name)
        print(f"PH_IMPORT {name} bounds_min=({b.min.x:.1f},{b.min.y:.1f},{b.min.z:.1f}) "
              f"bounds_max=({b.max.x:.1f},{b.max.y:.1f},{b.max.z:.1f}) slots={len(mats)} missing_mats={missing}")
    print(f"PH_IMPORT_DONE {len(done)}")


main(sys.argv[1:])

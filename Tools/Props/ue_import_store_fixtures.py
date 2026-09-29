"""In-editor: import Tools/Props/blender_store_fixtures.py output.

  PlaceholderAssets/FBX/<store fixtures + ammo pickup> -> /Game/Environment/StoreFixtures (static, box collision)

Run via Monolith editor.run_python {command: "<abs>/ue_import_store_fixtures.py [only=StockShelf,AmmoPickup]", unattended: true}.
Each material slot is named after an lvlib.MATERIALS key and gets MI_LV_<key> (run ue_make_materials.py first).
"""
import glob
import os
import sys

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJ, "PlaceholderAssets", "FBX")
DEST = "/Game/Environment/StoreFixtures"
NAMES = ["StockShelf", "CheckoutCounter", "AmmoKiosk", "DiscountKiosk", "CloseShopStation", "AmmoPickup",
         "StockShelf_T0", "StockShelf_T1", "StockShelf_T2", "StockShelf_T3", "StockShelf_T4"]
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


def main(argv):
    flags = dict(a.split("=", 1) for a in argv if "=" in a)
    only = set(flags["only"].split(",")) if "only" in flags else None
    sml = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    n = 0
    for short in NAMES:
        path = os.path.join(SRC, f"SM_{short}.fbx")
        name = os.path.splitext(os.path.basename(path))[0]
        if only and short not in only:
            continue
        mesh = import_fbx(path)
        if not mesh:
            print(f"FIX_IMPORT_FAIL {name}")
            continue
        missing = []
        for i, s in enumerate(mesh.get_editor_property("static_materials")):
            k = str(s.get_editor_property("material_slot_name")).split(".")[0]
            k = k[:-4] if k.endswith("_Mat") else k
            mi = unreal.load_asset(MAT_DIR + k)
            if mi:
                mesh.set_material(i, mi)
            else:
                missing.append(k)
        sml.remove_collisions(mesh)
        sml.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        b = mesh.get_bounding_box()
        n += 1
        print(f"FIX_IMPORT {name} min=({b.min.x:.0f},{b.min.y:.0f},{b.min.z:.0f}) "
              f"max=({b.max.x:.0f},{b.max.y:.0f},{b.max.z:.0f})" + (f" missing_mats={missing}" if missing else ""))
    print(f"FIX_IMPORT_DONE {n}")


main(sys.argv[1:])

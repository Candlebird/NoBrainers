"""In-editor: import blender_gear.py output.

  PlaceholderAssets/FBX/SK_Wpn_*.fbx  -> /Game/Weapons/Meshes (skeletal, own skeleton, no physics asset)
  PlaceholderAssets/FBX/SM_Wpn_*.fbx  -> /Game/Weapons/Meshes (static, box collision)
  PlaceholderAssets/FBX/SM_Item_*.fbx -> /Game/Items/Meshes   (static, box collision)

Run via Monolith editor.run_python {command: "<abs>/ue_import_gear.py [only=Pistol,CannedBeans] [probe=1]",
unattended: true}. probe=1 only prints SK_FPGun's bounds (to confirm the weapon long axis) and exits.
Each material slot is named after an lvlib.MATERIALS key and gets MI_LV_<key> (run ue_make_materials.py first).
"""
import glob
import os
import sys

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJ, "PlaceholderAssets", "FBX")
MAT_DIR = "/Game/Environment/Greybox/MI_LV_"


def import_fbx(path, dest, skeletal):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", skeletal)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    if skeletal:
        ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
        ui.set_editor_property("create_physics_asset", False)
    else:
        ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        sm = ui.get_editor_property("static_mesh_import_data")
        sm.set_editor_property("combine_meshes", True)
        sm.set_editor_property("auto_generate_collision", False)
        sm.set_editor_property("generate_lightmap_u_vs", True)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    name = os.path.splitext(os.path.basename(path))[0]
    return unreal.load_asset(f"{dest}/{name}.{name}")


def key(slot_name):
    k = str(slot_name).split(".")[0]
    return k[:-4] if k.endswith("_Mat") else k


def fix_static(mesh, sml):
    missing = []
    for i, s in enumerate(mesh.get_editor_property("static_materials")):
        k = key(s.get_editor_property("material_slot_name"))
        mi = unreal.load_asset(MAT_DIR + k)
        if mi:
            mesh.set_material(i, mi)
        else:
            missing.append(k)
    sml.remove_collisions(mesh)
    sml.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
    b = mesh.get_bounding_box()
    return missing, f"min=({b.min.x:.0f},{b.min.y:.0f},{b.min.z:.0f}) max=({b.max.x:.0f},{b.max.y:.0f},{b.max.z:.0f})"


def fix_skeletal(mesh):
    missing = []
    mats = list(mesh.get_editor_property("materials"))
    for s in mats:
        k = key(s.get_editor_property("material_slot_name"))
        mi = unreal.load_asset(MAT_DIR + k)
        if mi:
            s.set_editor_property("material_interface", mi)
        else:
            missing.append(k)
    mesh.set_editor_property("materials", mats)
    b = mesh.get_bounds()
    o, e = b.origin, b.box_extent
    return missing, (f"min=({o.x - e.x:.0f},{o.y - e.y:.0f},{o.z - e.z:.0f}) "
                     f"max=({o.x + e.x:.0f},{o.y + e.y:.0f},{o.z + e.z:.0f})")


def main(argv):
    flags = dict(a.split("=", 1) for a in argv if "=" in a)
    if flags.get("probe"):
        m = unreal.load_asset("/Game/FPWeapon/Mesh/SK_FPGun")
        b = m.get_bounds()
        print(f"GEAR_PROBE SK_FPGun origin={b.origin} extent={b.box_extent}")
        return
    only = set(flags["only"].split(",")) if "only" in flags else None
    sml = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    n = 0
    for prefix, dest, skel in (("SK_Wpn_", "/Game/Weapons/Meshes", True),
                               ("SM_Wpn_", "/Game/Weapons/Meshes", False),
                               ("SM_Item_", "/Game/Items/Meshes", False)):
        for path in sorted(glob.glob(os.path.join(SRC, prefix + "*.fbx"))):
            name = os.path.splitext(os.path.basename(path))[0]
            if only and name[len(prefix):] not in only:
                continue
            mesh = import_fbx(path, dest, skel)
            if not mesh:
                print(f"GEAR_IMPORT_FAIL {name}")
                continue
            missing, bounds = fix_skeletal(mesh) if skel else fix_static(mesh, sml)
            unreal.EditorAssetLibrary.save_loaded_asset(mesh)
            if skel:
                sk = mesh.get_editor_property("skeleton")
                if sk:
                    unreal.EditorAssetLibrary.save_loaded_asset(sk)
            n += 1
            print(f"GEAR_IMPORT {name} {bounds}" + (f" missing_mats={missing}" if missing else ""))
    print(f"GEAR_IMPORT_DONE {n}")


main(sys.argv[1:])

"""In-editor: export the UE4 mannequin skeletal mesh to FBX for Blender.

  /Game/AnimStarterPack/UE4_Mannequin/Mesh/SK_Mannequin (skeleton UE4_Mannequin_Skeleton)
  -> PlaceholderAssets/FBX/SK_Mannequin_Ref.fbx

Run via Monolith editor.run_python {command: "<abs>/ue_export_mannequin.py", unattended: true}.
"""
import os

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
OUT_DIR = os.path.join(PROJ, "PlaceholderAssets", "FBX")
OUT = os.path.join(OUT_DIR, "SK_Mannequin_Ref.fbx")
MESH_PATH = "/Game/AnimStarterPack/UE4_Mannequin/Mesh/SK_Mannequin"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    mesh = unreal.load_asset(MESH_PATH)
    if not mesh:
        print(f"MANNEQUIN_EXPORT ok=False error=asset_not_found:{MESH_PATH}")
        return

    opt = unreal.FbxExportOption()
    opt.set_editor_property("fbx_export_compatibility", unreal.FbxExportCompatibility.FBX_2013)
    opt.set_editor_property("ascii", False)
    opt.set_editor_property("force_front_x_axis", False)
    opt.set_editor_property("vertex_color", False)
    opt.set_editor_property("level_of_detail", False)
    opt.set_editor_property("collision", False)
    opt.set_editor_property("export_morph_targets", False)
    opt.set_editor_property("export_preview_mesh", False)
    opt.set_editor_property("map_skeletal_motion_to_root", False)
    opt.set_editor_property("export_local_time", True)

    task = unreal.AssetExportTask()
    task.set_editor_property("object", mesh)
    task.set_editor_property("filename", OUT)
    task.set_editor_property("exporter", unreal.SkeletalMeshExporterFBX())
    task.set_editor_property("options", opt)
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)

    ok = unreal.Exporter.run_asset_export_task(task)
    size = os.path.getsize(OUT) if os.path.exists(OUT) else 0
    print(f"MANNEQUIN_EXPORT ok={bool(ok)} bytes={size}")


main()

"""In-editor: dump every actor in the open editor level to JSON for offline plotting.

Run via Monolith: editor.run_python {command: "<abs path>/ue_dump_level.py [out.json]"}
Default output: <project>/Saved/LevelView/<MapName>_actors.json

Each record: label, class, location [x,y,z], rotation [p,y,r], scale, bounds
(origin + box extent in world space), tags, folder, and a few gameplay props when present.
"""
import json
import os
import sys

import unreal

GAMEPLAY_PROPS = ["SocketType", "ShelfIndex", "ItemCategory"]


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def main():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    map_name = world.get_name()
    proj = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(proj, "Saved", "LevelView", f"{map_name}_actors.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    records = []
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        cls = a.get_class().get_name()
        if cls in ("WorldSettings", "Brush", "DefaultPhysicsVolume", "GameplayDebuggerPlayerManager",
                   "AbstractNavData", "ChaosDebugDrawActor", "WorldDataLayers", "WorldPartitionMiniMap"):
            continue
        origin, extent = a.get_actor_bounds(False)
        rec = {
            "label": a.get_actor_label(),
            "class": cls,
            "loc": vec(a.get_actor_location()),
            "rot": [round(a.get_actor_rotation().pitch, 1), round(a.get_actor_rotation().yaw, 1),
                    round(a.get_actor_rotation().roll, 1)],
            "scale": vec(a.get_actor_scale3d()),
            "bounds_origin": vec(origin),
            "bounds_extent": vec(extent),
            "tags": [str(t) for t in a.tags],
            "folder": str(a.get_folder_path()),
        }
        if isinstance(a, unreal.StaticMeshActor):
            m = a.static_mesh_component.static_mesh
            rec["mesh"] = m.get_path_name() if m else None
        for p in GAMEPLAY_PROPS:
            try:
                rec.setdefault("props", {})[p] = str(a.get_editor_property(p))
            except Exception:
                pass
        if rec.get("props") == {}:
            rec.pop("props")
        records.append(rec)

    with open(out, "w") as f:
        json.dump({"map": world.get_path_name(), "actors": records}, f, indent=1)
    print(f"LEVELVIEW_DUMP {len(records)} actors -> {out}")


main()

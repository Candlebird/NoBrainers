"""In-editor: (re)build the open level from a layout JSON (store_layout.py export).

Run via Monolith editor.run_python {command: "<abs>/ue_apply_layout.py <layout.json> [only=cat1,cat2]", unattended: true}

Idempotent: deletes every actor tagged "LV" (optionally only those in the given categories), then spawns
the layout. Every spawned actor gets tags "LV" and "LV_<cat>", label = element id, folder = LV/<cat>.
  box/cyl -> StaticMeshActor (/Engine/BasicShapes/Cube|Cylinder, scale = size/100) + MI_LV_<mat>
  bp      -> Blueprint class at el["bp"], props applied after all spawns ("@id" -> actor refs)
  light   -> Point/Spot/Rect/Directional/SkyLight actor
  volume  -> PostProcessVolume (unbound) only; nav bounds are added via Monolith ai.add_nav_bounds_volume
  marker  -> TargetPoint / PlayerStart (el["cls"])
Does not save; call editor save afterwards.
"""
import json
import sys

import unreal

ess = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MESH = {"box": "/Engine/BasicShapes/Cube.Cube", "cyl": "/Engine/BasicShapes/Cylinder.Cylinder"}
MAT_DIR = "/Game/Environment/Greybox/MI_LV_"
_mesh_cache, _mat_cache, _cls_cache = {}, {}, {}


def _mesh(kind):
    """kind is "box"/"cyl" or a full StaticMesh object path (placeholder meshes)."""
    if kind not in _mesh_cache:
        _mesh_cache[kind] = unreal.load_asset(MESH.get(kind, kind))
    return _mesh_cache[kind]


def _mat(key):
    if key not in _mat_cache:
        _mat_cache[key] = unreal.load_asset(MAT_DIR + key) if key else None
    return _mat_cache[key]


def _bp_class(path):
    if path not in _cls_cache:
        if path.startswith("/Script/"):
            _cls_cache[path] = unreal.load_class(None, path)
        else:
            name = path.rsplit("/", 1)[-1]
            _cls_cache[path] = unreal.load_class(None, f"{path}.{name}_C")
    return _cls_cache[path]


def _v(p):
    return unreal.Vector(float(p[0]), float(p[1]), float(p[2]))


def _finish(actor, el):
    actor.set_actor_label(el["id"])
    actor.tags = [unreal.Name("LV"), unreal.Name("LV_" + el["cat"])] + [unreal.Name(t) for t in el.get("tags", [])]
    actor.set_folder_path(unreal.Name("LV/" + el["cat"]))


def spawn_prim(el):
    rot = unreal.Rotator(roll=el.get("roll", 0), pitch=el.get("pitch", 0), yaw=el.get("yaw", 0))
    a = ess.spawn_actor_from_class(unreal.StaticMeshActor, _v(el["pos"]), rot)
    smc = a.static_mesh_component
    smc.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    mesh = el.get("mesh")  # placeholder mesh: authored to a centered 1 m cube, so size/100 still applies
    smc.set_static_mesh(_mesh(mesh or el["kind"]))
    s = el["size"]
    a.set_actor_scale3d(unreal.Vector(s[0] / 100.0, s[1] / 100.0, s[2] / 100.0))
    if mesh:
        pass  # keeps the MI_LV_<slot> materials assigned at import
    else:
        m = _mat(el.get("mat"))
        if m:
            smc.set_material(0, m)
    if el.get("nocollide"):
        smc.set_collision_profile_name("NoCollision")
    if el.get("noshadow"):
        smc.set_editor_property("cast_shadow", False)
    _finish(a, el)
    return a


def spawn_light(el):
    lt = el.get("light", "point")
    cls = {"point": unreal.PointLight, "spot": unreal.SpotLight, "rect": unreal.RectLight,
           "directional": unreal.DirectionalLight, "sky": unreal.SkyLight}[lt]
    rot = unreal.Rotator(roll=0, pitch=el.get("pitch", -90 if lt in ("spot", "rect") else 0), yaw=el.get("yaw", 0))
    a = ess.spawn_actor_from_class(cls, _v(el["pos"]), rot)
    comp = a.get_component_by_class(unreal.LightComponentBase)
    if "intensity" in el:
        comp.set_editor_property("intensity", float(el["intensity"]))
    if "color" in el:
        c = el["color"]
        comp.set_editor_property("light_color", unreal.Color(int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), 255))
    if "radius" in el and lt in ("point", "spot", "rect"):
        comp.set_editor_property("attenuation_radius", float(el["radius"]))
    if lt in ("point", "spot", "rect"):
        comp.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        comp.set_editor_property("cast_shadows", bool(el.get("shadows", False)))
    if lt == "spot" and "cone" in el:
        comp.set_editor_property("outer_cone_angle", float(el["cone"]))
    if lt == "rect":
        comp.set_editor_property("source_width", float(el.get("w", 200)))
        comp.set_editor_property("source_height", float(el.get("h", 200)))
    if lt == "directional":
        comp.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        try:
            comp.set_editor_property("atmosphere_sun_light", True)
        except Exception:
            pass
    if lt == "sky":
        comp.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        comp.set_editor_property("real_time_capture", True)
    _finish(a, el)
    return a


def spawn_volume(el):
    if el.get("cls") == "PostProcessVolume":
        a = ess.spawn_actor_from_class(unreal.PostProcessVolume, _v(el["pos"]), unreal.Rotator())
        a.set_editor_property("unbound", True)
        pps = a.get_editor_property("settings")
        for k, v in el.get("pp", {}).items():
            pps.set_editor_property("override_" + k, True)
            pps.set_editor_property(k, v)
        a.set_editor_property("settings", pps)
        _finish(a, el)
        return a
    return None


def spawn_misc(el):
    cls = {"TargetPoint": unreal.TargetPoint, "PlayerStart": unreal.PlayerStart,
           "SkyAtmosphere": unreal.SkyAtmosphere, "ExponentialHeightFog": unreal.ExponentialHeightFog}[el["cls"]]
    a = ess.spawn_actor_from_class(cls, _v(el["pos"]), unreal.Rotator(roll=0, pitch=0, yaw=el.get("yaw", 0)))
    _finish(a, el)
    return a


def spawn_bp(el):
    cls = _bp_class(el["bp"])
    if cls is None:
        raise RuntimeError(f"class not found: {el['bp']}")
    a = ess.spawn_actor_from_class(cls, _v(el["pos"]), unreal.Rotator(roll=0, pitch=0, yaw=el.get("yaw", 0)))
    if "scale" in el:
        a.set_actor_scale3d(_v(el["scale"]))
    _finish(a, el)
    return a


def _enum_value(cur, val):
    et = type(cur)
    name = str(val).split(".")[-1].split(":")[0].strip(" <>")
    for cand in (name, name.upper()):
        if hasattr(et, cand):
            return getattr(et, cand)
    if str(val).isdigit():
        return et.cast(int(val))
    raise ValueError(f"{et.__name__} has no member {val}; members: {[m for m in dir(et) if m.isupper()]}")


def apply_props(actor, props, by_id, errors):
    for k, v in props.items():
        try:
            cur = actor.get_editor_property(k)

            def res(x):
                return by_id[x[1:]] if isinstance(x, str) and x.startswith("@") else x

            if isinstance(v, list):
                v = [res(x) for x in v]
            elif isinstance(cur, unreal.EnumBase) or hasattr(type(cur), "cast") and not isinstance(cur, (int, float, bool)):
                v = _enum_value(cur, v)
            else:
                v = res(v)
            actor.set_editor_property(k, v)
        except Exception as e:  # keep going; report at the end
            errors.append(f"{actor.get_actor_label()}.{k}: {e}")


def main(argv):
    path = argv[0]
    only = None
    for t in argv[1:]:
        if t.startswith("only="):
            only = set(t[5:].split(","))
    layout = json.load(open(path))

    removed = 0
    for a in ess.get_all_level_actors():
        tags = [str(t) for t in a.tags]
        if "LV" in tags and (only is None or any(t[3:] in only for t in tags if t.startswith("LV_"))):
            ess.destroy_actor(a)
            removed += 1

    by_id, errors, counts = {}, [], {}
    with unreal.ScopedEditorTransaction("LevelView apply layout"):
        for el in layout["elements"]:
            if only is not None and el["cat"] not in only:
                continue
            if el.get("skip_ue"):
                continue
            try:
                k = el["kind"]
                if k in ("box", "cyl"):
                    a = spawn_prim(el)
                elif k == "bp":
                    a = spawn_bp(el)
                elif k == "light":
                    a = spawn_light(el)
                elif k == "volume":
                    a = spawn_volume(el)
                elif k == "marker":
                    a = spawn_misc(el)
                else:
                    a = None
                if a:
                    by_id[el["id"]] = a
                    counts[k] = counts.get(k, 0) + 1
            except Exception as e:
                errors.append(f"{el['id']}: {e}")
        if only is not None:  # allow @refs to actors that were not rebuilt
            for a in ess.get_all_level_actors():
                by_id.setdefault(a.get_actor_label(), a)
        for el in layout["elements"]:
            if el["id"] in by_id and el.get("props") and el["kind"] == "bp":
                apply_props(by_id[el["id"]], el["props"], by_id, errors)
    print(f"LEVELVIEW_APPLY removed={removed} spawned={counts} errors={len(errors)}")
    for e in errors[:25]:
        print("  ERR", e)


main(sys.argv[1:])

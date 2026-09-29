"""In-editor: import the Female/Swamp zombie PBR textures and build their materials.

  Assets/FemaleZombieTextures/lambert2_*.png   -> /Game/Characters/Zombie/Textures/Female/T_Zombie_Female_*
  Assets/SwampMonsterTextures/SwampCreature_* -> /Game/Characters/Zombie/Textures/Swamp/T_Zombie_Swamp_*
  M_Zombie_PBR (parent, texture params) + MI_Zombie_Female / MI_Zombie_Swamp in /Game/Characters/Zombie/Materials,
  each MI assigned to slot 0 of SK_Zombie_Female / SK_Zombie_Swamp.

Run via Monolith editor.run_python {command: "<abs>/ue_zombie_variant_materials.py", unattended: true}.
Texture notes:
  - Normals use the *_Normal_OpenGL export with flip_green_channel. The female's DirectX *_Normal.png is
    effectively flat, the OpenGL one has the detail.
  - Metalness/roughness/AO are separate grayscale maps: linear (sRGB off), TC_MASKS, Masks sampler.
  - Height maps are not used. The swamp emission uses the *_Emission_color_Correct export.
"""
import os

import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJ, "Assets")
TEX_ROOT = "/Game/Characters/Zombie/Textures"
MAT_DIR = "/Game/Characters/Zombie/Materials"
PARENT = "M_Zombie_PBR"

# variant -> (source folder, file prefix, emission file or None, mesh path)
VARIANTS = {
    "Female": ("FemaleZombieTextures", "lambert2", None, "/Game/Characters/Zombie/SK_Zombie_Female"),
    "Swamp": ("SwampMonsterTextures", "SwampCreature", "SwampCreature_Emission_color_Correct.png",
              "/Game/Characters/Zombie/SK_Zombie_Swamp"),
}
# map key -> (file suffix, compression, srgb, flip green)
MAPS = {
    "BaseColor": ("_Base_color.png", unreal.TextureCompressionSettings.TC_DEFAULT, True, False),
    "Normal": ("_Normal_OpenGL.png", unreal.TextureCompressionSettings.TC_NORMALMAP, False, True),
    "Metallic": ("_Base_metalness.png", unreal.TextureCompressionSettings.TC_MASKS, False, False),
    "Roughness": ("_Specular_roughness.png", unreal.TextureCompressionSettings.TC_MASKS, False, False),
    "AO": ("_Mixed_AO.png", unreal.TextureCompressionSettings.TC_MASKS, False, False),
    "Emissive": (None, unreal.TextureCompressionSettings.TC_DEFAULT, True, False),
}
SAMPLER = {
    "BaseColor": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
    "Normal": unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
    "Metallic": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
    "Roughness": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
    "AO": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
    "Emissive": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
}

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def fail(reason):
    print(f"ZMAT_FAIL {reason}")


def import_texture(path, dest_dir, name, compression, srgb, flip):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", dest_dir)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    tex = unreal.load_asset(f"{dest_dir}/{name}")
    if not tex:
        fail(f"texture import failed {path}")
        return None
    tex.set_editor_property("compression_settings", compression)
    tex.set_editor_property("srgb", srgb)
    tex.set_editor_property("flip_green_channel", flip)
    eal.save_loaded_asset(tex)
    return tex


def import_variant_textures(variant):
    folder, prefix, emission, _ = VARIANTS[variant]
    dest = f"{TEX_ROOT}/{variant}"
    out = {}
    for key, (suffix, comp, srgb, flip) in MAPS.items():
        fname = emission if key == "Emissive" else (prefix + suffix if suffix else None)
        if not fname:
            continue
        path = os.path.join(SRC, folder, fname)
        if not os.path.isfile(path):
            fail(f"missing {path}")
            continue
        tex = import_texture(path, dest, f"T_Zombie_{variant}_{key}", comp, srgb, flip)
        if tex:
            out[key] = tex
    return out


def build_parent(defaults, emissive_default):
    path = f"{MAT_DIR}/{PARENT}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    mat = tools.create_asset(PARENT, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("used_with_skeletal_mesh", True)
    MP = unreal.MaterialProperty
    targets = {"BaseColor": (MP.MP_BASE_COLOR, "RGB"), "Normal": (MP.MP_NORMAL, "RGB"),
               "Metallic": (MP.MP_METALLIC, "R"), "Roughness": (MP.MP_ROUGHNESS, "R"),
               "AO": (MP.MP_AMBIENT_OCCLUSION, "R")}
    y = -400
    for key, (prop, out_pin) in targets.items():
        node = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -500, y)
        node.set_editor_property("parameter_name", key)
        node.set_editor_property("sampler_type", SAMPLER[key])
        node.set_editor_property("texture", defaults[key])
        mel.connect_material_property(node, out_pin, prop)
        y += 260

    # Emissive = texture * EmissiveStrength (0 by default so variants without a glow map stay dark).
    em = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -800, y)
    em.set_editor_property("parameter_name", "Emissive")
    em.set_editor_property("sampler_type", SAMPLER["Emissive"])
    em.set_editor_property("texture", emissive_default)
    strength = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -800, y + 260)
    strength.set_editor_property("parameter_name", "EmissiveStrength")
    strength.set_editor_property("default_value", 0.0)
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, y)
    mel.connect_material_expressions(em, "RGB", mul, "A")
    mel.connect_material_expressions(strength, "", mul, "B")
    mel.connect_material_property(mul, "", MP.MP_EMISSIVE_COLOR)

    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


def build_instance(variant, parent, textures, emissive_strength):
    name = f"MI_Zombie_{variant}"
    path = f"{MAT_DIR}/{name}"
    mi = unreal.load_asset(path) or tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant,
                                                        unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    for key, tex in textures.items():
        mel.set_material_instance_texture_parameter_value(mi, key, tex)
    mel.set_material_instance_scalar_parameter_value(mi, "EmissiveStrength", emissive_strength)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi


def assign(mesh_path, mi):
    mesh = unreal.load_asset(mesh_path)
    if not mesh:
        fail(f"mesh not found {mesh_path}")
        return
    # ImportedMaterialSlotName is read-only from Python, so edit a copy of the existing slot and write it back.
    slots = list(mesh.get_editor_property("materials"))
    slots[0].set_editor_property("material_interface", mi)
    mesh.set_editor_property("materials", slots)
    eal.save_loaded_asset(mesh)


def main():
    tex = {v: import_variant_textures(v) for v in VARIANTS}
    if "Emissive" not in tex["Swamp"]:
        fail("swamp emissive texture missing")
        return
    parent = build_parent(tex["Female"], tex["Swamp"]["Emissive"])
    for variant, (_, _, emission, mesh_path) in VARIANTS.items():
        mi = build_instance(variant, parent, tex[variant], 1.0 if emission else 0.0)
        assign(mesh_path, mi)
        print(f"ZMAT {variant} textures={sorted(tex[variant])} mi={mi.get_name()}")


if __name__ == "__main__":
    main()

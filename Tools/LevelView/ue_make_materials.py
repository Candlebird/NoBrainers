"""In-editor: create the greybox flat-color master material and one instance per lvlib.MATERIALS key.

Run via Monolith editor.run_python {command: "<abs>/ue_make_materials.py", unattended: true}
Creates /Game/Environment/Greybox/M_LV_Flat and MI_LV_<key>. Idempotent (updates params if present).
"""
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib

import lvlib

importlib.reload(lvlib)

FOLDER = "/Game/Environment/Greybox"
MASTER = f"{FOLDER}/M_LV_Flat"
MEL = unreal.MaterialEditingLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()


def make_master():
    if unreal.EditorAssetLibrary.does_asset_exist(MASTER):
        return unreal.load_asset(MASTER)
    m = at.create_asset("M_LV_Flat", FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    col = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -600, -200)
    col.set_editor_property("parameter_name", "Color")
    col.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1))
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -600, 50)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.8)
    metal = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -600, 150)
    metal.set_editor_property("parameter_name", "Metallic")
    metal.set_editor_property("default_value", 0.0)
    emis = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -600, 250)
    emis.set_editor_property("parameter_name", "Emissive")
    emis.set_editor_property("default_value", 0.0)
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 250)
    MEL.connect_material_expressions(col, "", mul, "A")
    MEL.connect_material_expressions(emis, "", mul, "B")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(MASTER)
    return m


def main():
    master = make_master()
    n = 0
    for key, (rgb, rough, metal, emis) in lvlib.MATERIALS.items():
        path = f"{FOLDER}/MI_LV_{key}"
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            mi = unreal.load_asset(path)
        else:
            mi = at.create_asset(f"MI_LV_{key}", FOLDER, unreal.MaterialInstanceConstant,
                                 unreal.MaterialInstanceConstantFactoryNew())
            MEL.set_material_instance_parent(mi, master)
        MEL.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(*rgb, 1.0))
        MEL.set_material_instance_scalar_parameter_value(mi, "Roughness", rough)
        MEL.set_material_instance_scalar_parameter_value(mi, "Metallic", metal)
        MEL.set_material_instance_scalar_parameter_value(mi, "Emissive", emis)
        MEL.update_material_instance(mi)
        unreal.EditorAssetLibrary.save_asset(path)
        n += 1
    print(f"LEVELVIEW_MATERIALS master={MASTER} instances={n}")


main()

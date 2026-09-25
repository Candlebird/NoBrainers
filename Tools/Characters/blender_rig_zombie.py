"""Headless Blender: re-rig the existing zombie (Assets/ZombieTest.blend) with a UE4-Mannequin-compatible skeleton.

blender --background --factory-startup Assets/ZombieTest.blend --python Tools/Characters/blender_rig_zombie.py

Keeps the original mesh and its skin weights (they deform cleanly); fixes the skeleton so an IK Retargeter from
UE4_Mannequin_Skeleton maps 1:1 by bone name:
  - armature object renamed "Armature" so the FBX importer doesn't turn it into a root bone,
  - stray "Bone" removed, real "root" bone at the origin added as pelvis's parent,
  - mannequin IK bones added (ik_foot_root/_l/_r, ik_hand_root/_gun/_l/_r), non-deforming,
  - no leaf (_end) bones on export.
Rest pose stays a T-pose; the retargeter's retarget pose handles the mannequin's A-pose.
Writes PlaceholderAssets/Blender/SK_Zombie.blend and PlaceholderAssets/FBX/SK_Zombie.fbx. Never saves the source.
"""
import os

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BDIR = os.path.join(ROOT, "PlaceholderAssets", "Blender")
FDIR = os.path.join(ROOT, "PlaceholderAssets", "FBX")


def main():
    mesh = bpy.data.objects["Standard_Zombie_MESH"]
    arm = bpy.data.objects["StandardZombie_Arma"]
    for ob in list(bpy.data.objects):  # drop the reference mannequin and the empty import groups
        if ob not in (mesh, arm):
            bpy.data.objects.remove(ob)

    # Bake the mesh's 90deg/0.01 import transform into its vertices so it sits at identity under the armature.
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mesh.parent = arm
    mesh.matrix_parent_inverse.identity()
    mesh.name = mesh.data.name = "SK_Zombie"
    for m in mesh.modifiers:
        if m.type == "ARMATURE":
            m.object = arm
    if "Bone" in mesh.vertex_groups:
        mesh.vertex_groups.remove(mesh.vertex_groups["Bone"])

    arm.name = arm.data.name = "Armature"
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    eb.remove(eb["Bone"])

    def add(name, head, tail, parent):
        b = eb.new(name)
        b.head, b.tail, b.roll = Vector(head), Vector(tail), 0.0
        b.parent = eb[parent] if parent else None
        b.use_deform = False
        return b

    add("root", (0, 0, 0), (0, 0.2, 0), None)
    eb["pelvis"].parent = eb["root"]
    add("ik_foot_root", (0, 0, 0), (0, 0.15, 0), "root")
    add("ik_hand_root", (0, 0, 0), (0, 0.15, 0), "root")
    for s in ("l", "r"):
        h = eb[f"foot_{s}"].head.copy()
        add(f"ik_foot_{s}", h, h + Vector((0, 0, 0.1)), "ik_foot_root")
    h = eb["hand_r"].head.copy()
    add("ik_hand_gun", h, h + Vector((0, 0, 0.1)), "ik_hand_root")
    for s in ("l", "r"):
        h = eb[f"hand_{s}"].head.copy()
        add(f"ik_hand_{s}", h, h + Vector((0, 0, 0.1)), "ik_hand_gun")
    bpy.ops.object.mode_set(mode="OBJECT")

    # Work in centimeters (1 BU = 1 cm) with every transform applied. Exporting meters with FBX_SCALE_UNITS
    # makes UE fold a x100 scale into the root bone, which collapses the skeleton once an animation keys root scale 1.
    bpy.context.scene.unit_settings.scale_length = 0.01
    arm.scale = (100.0, 100.0, 100.0)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    for ob in (arm, mesh):
        ob.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    os.makedirs(BDIR, exist_ok=True)
    os.makedirs(FDIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BDIR, "SK_Zombie.blend"))
    bpy.ops.export_scene.fbx(filepath=os.path.join(FDIR, "SK_Zombie.fbx"), use_selection=False,
                             object_types={"ARMATURE", "MESH"}, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_UNITS", add_leaf_bones=False, bake_anim=False,
                             use_armature_deform_only=False, mesh_smooth_type="FACE")
    names = [b.name for b in arm.data.bones]
    print(f"ZOMBIE_RIG bones={len(names)} deform={sum(b.use_deform for b in arm.data.bones)} "
          f"verts={len(mesh.data.vertices)} groups={len(mesh.vertex_groups)} mats={[m.name for m in mesh.data.materials]}")


if __name__ == "__main__":
    main()

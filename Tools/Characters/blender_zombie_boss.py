r"""Headless Blender: scale SK_Zombie's rig up 1.6x to build a "Boss" variant skeletal mesh.

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --factory-startup \
    PlaceholderAssets/Blender/SK_Zombie.blend --python Tools/Characters/blender_zombie_boss.py

Input : PlaceholderAssets/Blender/SK_Zombie.blend (read only, never saved over).
Output: PlaceholderAssets/FBX/Zombie/SK_Zombie_Boss.fbx (armature + mesh, no animation)
        PlaceholderAssets/Blender/Zombie/SK_Zombie_Boss.blend

Optional args after `--`: <output name> <scale>. The Swamp boss is built from the rigged swamp variant:
  blender -b --factory-startup PlaceholderAssets/Blender/Zombie/SK_Zombie_Swamp.blend \
      --python Tools/Characters/blender_zombie_boss.py -- SK_Zombie_SwampBoss 1.5

Technique: select the armature ("Armature") and every MESH object, scale the armature by 1.6 (children
follow via parenting), then apply scale on the whole selection. That folds the 1.6x into the armature's
bone rest lengths/positions and each mesh's vertices, leaving every object's own scale at (1,1,1) -- so
nothing downstream (UE import, retargeter, gameplay component scale) needs to compensate with a scale
factor. Rest pose is forced to REST before scaling so the bones being scaled are the bind pose, not
whatever pose the file happened to be saved in; restored to POSE afterward to match the source file.
"""
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BDIR = os.path.join(ROOT, "PlaceholderAssets", "Blender", "Zombie")
FDIR = os.path.join(ROOT, "PlaceholderAssets", "FBX", "Zombie")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_NAME = ARGS[0] if ARGS else "SK_Zombie_Boss"
SCALE = float(ARGS[1]) if len(ARGS) > 1 else 1.6
TOL = 0.01


def fail(reason):
    print(f"BOSS_MESH_FAIL {reason}")
    sys.stdout.flush()
    sys.exit(1)


def get_rig():
    arm = None
    meshes = []
    for ob in bpy.data.objects:
        if ob.type == "ARMATURE":
            arm = ob
        elif ob.type == "MESH":
            meshes.append(ob)
    if arm is None:
        fail("no armature object in SK_Zombie.blend")
    if not meshes:
        fail("no mesh objects in SK_Zombie.blend")
    return arm, meshes



def main():
    arm, meshes = get_rig()

    bpy.ops.object.mode_set(mode="OBJECT")

    def bbox_height():
        min_z = None
        max_z = None
        for ob in meshes:
            for corner in ob.bound_box:
                world = ob.matrix_world @ Vector(corner)
                z = world.z
                if min_z is None or z < min_z:
                    min_z = z
                if max_z is None or z > max_z:
                    max_z = z
        return max_z - min_z

    orig_h = bbox_height()

    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action="DESELECT")
    for ob in meshes:
        ob.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm

    arm.scale = (arm.scale[0] * SCALE, arm.scale[1] * SCALE, arm.scale[2] * SCALE)
    bpy.context.view_layer.update()

    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    arm.data.pose_position = "POSE"
    bpy.context.view_layer.update()

    boss_h = bbox_height()
    ratio = boss_h / orig_h if orig_h else 0.0
    print(f"BOSS_MESH ORIG_H={orig_h:.4f} BOSS_H={boss_h:.4f} RATIO={ratio:.4f}")
    if abs(ratio - SCALE) > TOL:
        fail(f"ratio {ratio:.4f} outside {SCALE} +/- {TOL}")

    for ob in [arm] + meshes:
        sx, sy, sz = ob.scale
        if abs(sx - 1.0) > 1e-4 or abs(sy - 1.0) > 1e-4 or abs(sz - 1.0) > 1e-4:
            fail(f"{ob.name} scale not (1,1,1): {ob.scale}")

    os.makedirs(FDIR, exist_ok=True)
    os.makedirs(BDIR, exist_ok=True)

    bpy.ops.object.select_all(action="DESELECT")
    for ob in [arm] + meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = arm

    bpy.ops.export_scene.fbx(
        filepath=os.path.join(FDIR, f"{OUT_NAME}.fbx"),
        use_selection=False,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        add_leaf_bones=False,
        bake_anim=False,
        use_armature_deform_only=False,
        mesh_smooth_type="FACE",
    )

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BDIR, f"{OUT_NAME}.blend"), copy=False)

    print(f"BOSS_MESH OK ratio={ratio:.4f}")


if __name__ == "__main__":
    main()

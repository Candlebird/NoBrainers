"""In-editor: import Sledgehammer/Katana FBX from PlaceholderAssets/Weapons using ue_import_gear.py's logic."""
import os
import unreal
PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
src = open(os.path.join(PROJ, "Tools", "LevelView", "ue_import_gear.py")).read().rsplit("main(sys.argv[1:])", 1)[0]
src = src.replace('SRC = os.path.join(PROJ, "PlaceholderAssets", "FBX")', 'SRC = os.path.join(PROJ, "PlaceholderAssets", "Weapons")')
g = {"__name__": "gear"}
exec(compile(src, "ue_import_gear", "exec"), g)
g["main"](["only=Sledgehammer,Katana"])

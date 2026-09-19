using UnrealBuildTool;

public class MonolithBlueprint : ModuleRules
{
	public MonolithBlueprint(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine"
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"MonolithCore",
			"UnrealEd",
			"BlueprintGraph",
			"BlueprintEditorLibrary",
			"SubobjectDataInterface",
			"Kismet",
			"KismetCompiler",
			"EditorScriptingUtilities",
			"EnhancedInput",
			// K2Node_EnhancedInputAction / K2Node_GetInputActionValue live in this
			// editor-only module (not EnhancedInput itself) — needed for add_input_action_node.
			"InputBlueprintNodes",
			"Json",
			"JsonUtilities"
			// (Historical: StructUtils was added here by PR #40 but is deprecated
			// since UE 5.5 — FInstancedStruct relocated into CoreUObject and resolves
			// transparently via the existing CoreUObject Public dep above.)
		});
	}
}

// Copyright Vesper System, 2026. All Rights Reserved.

using UnrealBuildTool;

public class VesperNodeCleaner : ModuleRules
{
	public VesperNodeCleaner(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
			}
		);

		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"CoreUObject",
				"Engine",
				"Slate",
				"SlateCore",
				"InputCore",
				"Projects"
			}
		);

		// Protegemos los módulos que pertenecen estrictamente al Editor de UE
		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.AddRange(
				new string[]
				{
					"UnrealEd",
					"EditorFramework",
					"ToolMenus",
					"GraphEditor",
					"BlueprintGraph",
					"Kismet",
					"KismetCompiler"
				}
			);
		}
	}
}
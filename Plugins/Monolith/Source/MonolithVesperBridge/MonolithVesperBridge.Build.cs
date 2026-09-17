using UnrealBuildTool;
using System.IO;

public class MonolithVesperBridge : ModuleRules
{
	public MonolithVesperBridge(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		// Probe for Vesper Node Cleaner the same way MonolithBABridge probes
		// for Blueprint Assist: link against it only if it's actually present,
		// so a project without the (paid) plugin still compiles clean.
		//
		// Release builds: set MONOLITH_RELEASE_BUILD=1 to force all optional
		// deps off, same convention as MonolithBABridge.
		bool bHasVesper = false;
		bool bReleaseBuild = System.Environment.GetEnvironmentVariable("MONOLITH_RELEASE_BUILD") == "1";

		if (!bReleaseBuild)
		{
			// 1. Project Plugins/ folder -- this project keeps its copy here
			// (relocated from the Engine Marketplace install so it's a normal
			// source plugin the editor rebuilds instead of a stale "Installed" one).
			string ProjectPluginsDir = Path.Combine(
				Target.ProjectFile.Directory.FullName, "Plugins");
			if (Directory.Exists(ProjectPluginsDir))
			{
				bHasVesper = Directory.Exists(
					Path.Combine(ProjectPluginsDir, "VesperNodeCleaner"));
			}

			// 2. Engine Plugins/Marketplace/ folder (default Fab/launcher install location)
			if (!bHasVesper)
			{
				string EngineDir = Path.GetFullPath(Target.RelativeEnginePath);
				string MarketplaceDir = Path.Combine(EngineDir, "Plugins", "Marketplace");
				if (Directory.Exists(MarketplaceDir))
				{
					bHasVesper = Directory.GetDirectories(
						MarketplaceDir, "VesperNo*",
						SearchOption.TopDirectoryOnly).Length > 0;
				}
			}
		}

		if (bHasVesper)
		{
			// Full implementation -- link against VesperNodeCleaner
			PrivateDependencyModuleNames.AddRange(new string[]
			{
				"Core", "CoreUObject", "Engine",
				"MonolithCore",
				"VesperNodeCleaner",
				"UnrealEd", "GraphEditor",
				"Json"
			});
			PublicDefinitions.Add("WITH_VESPER_NODE_CLEANER=1");
		}
		else
		{
			// Empty shell -- compiles clean, does nothing at runtime
			PrivateDependencyModuleNames.AddRange(new string[]
			{
				"Core", "CoreUObject", "Engine",
				"MonolithCore"
			});
			PublicDefinitions.Add("WITH_VESPER_NODE_CLEANER=0");
		}
	}
}

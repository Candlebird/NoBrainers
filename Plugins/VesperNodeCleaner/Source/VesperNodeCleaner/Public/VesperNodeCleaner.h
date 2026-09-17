// Copyright Vesper System, 2026. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class FUICommandList;
class FToolBarBuilder;
class FMenuBuilder;

/**
 * Editor module for VesperNodeCleaner — a one-click Blueprint graph
 * formatting and comment auto-fit tool.
 *
 * Registers two commands (Auto-Format Graph, Auto-Fit Comment Box) that are
 * exposed via the Graph Editor context menu, the Blueprint Editor toolbar,
 * and the main Window menu. The actual layout math lives in
 * FVesperGraphLayout; this class only wires UI -> command -> handler.
 */
class FVesperNodeCleanerModule : public IModuleInterface
{
public:
	/** IModuleInterface implementation */
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	/** Registers the plugin's entries into the Graph Editor context menu, Blueprint toolbar, and Window menu. */
	void RegisterMenus();

	/** Handler for the Auto-Format Graph command. Delegates to FVesperGraphLayout::FormatSelectedNodes(). */
	void OnAutoFormatClicked();

	/** Handler for the Auto-Fit Comment Box command. Delegates to FVesperGraphLayout::AutoFitSelectedComments(). */
	void OnAutoFitCommentsClicked();

private:
	/** Command list this module owns; maps FVesperNodeCleanerCommands entries to the handlers above. */
	TSharedPtr<FUICommandList> PluginCommands;
};
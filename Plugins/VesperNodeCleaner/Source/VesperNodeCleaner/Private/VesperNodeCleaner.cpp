// Copyright Vesper System, 2026. All Rights Reserved.

#include "VesperNodeCleaner.h"
#include "VesperNodeCleanerStyle.h"
#include "VesperNodeCleanerCommands.h"
#include "VesperGraphLayout.h"
#include "ToolMenus.h"
#include "Framework/Commands/UICommandList.h"
#include "Engine/Engine.h"

#define LOCTEXT_NAMESPACE "FVesperNodeCleanerModule"

DEFINE_LOG_CATEGORY_STATIC(LogVesperCleaner, Log, All);

void FVesperNodeCleanerModule::StartupModule()
{
	UE_LOG(LogVesperCleaner, Log, TEXT("[Vesper] VesperNodeCleaner module starting up..."));

	// 1. Initialize styles and commands.
	FVesperNodeCleanerStyle::Initialize();
	FVesperNodeCleanerStyle::ReloadTextures();
	FVesperNodeCleanerCommands::Register();

	// Track keyboard focus globally so FVesperGraphLayout can still find the
	// right Graph Editor when a command is triggered from a toolbar/menu
	// button, which steals focus to itself before the handler runs.
	FVesperGraphLayout::RegisterFocusTracking();

	PluginCommands = MakeShareable(new FUICommandList);

	// 2. Bind commands to their handlers.
	PluginCommands->MapAction(
		FVesperNodeCleanerCommands::Get().AutoFormatGraph,
		FExecuteAction::CreateRaw(this, &FVesperNodeCleanerModule::OnAutoFormatClicked),
		FCanExecuteAction());

	PluginCommands->MapAction(
		FVesperNodeCleanerCommands::Get().AutoFitComments,
		FExecuteAction::CreateRaw(this, &FVesperNodeCleanerModule::OnAutoFitCommentsClicked),
		FCanExecuteAction());

	// 3. Register callbacks for ToolMenus (menus aren't ready this early in startup).
	UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FVesperNodeCleanerModule::RegisterMenus));
}

void FVesperNodeCleanerModule::ShutdownModule()
{
	// Unregister menus to avoid leaks or crashes during Live Coding / hot reload.
	UToolMenus::UnRegisterStartupCallback(this);
	UToolMenus::UnregisterOwner(this);

	FVesperGraphLayout::UnregisterFocusTracking();

	FVesperNodeCleanerStyle::Shutdown();
	FVesperNodeCleanerCommands::Unregister();

	UE_LOG(LogVesperCleaner, Log, TEXT("[Vesper] VesperNodeCleaner module shut down."));
}

void FVesperNodeCleanerModule::OnAutoFormatClicked()
{
	UE_LOG(LogVesperCleaner, Verbose, TEXT("[Vesper] Executing AutoFormatGraph..."));
	FVesperGraphLayout::FormatSelectedNodes();
}

void FVesperNodeCleanerModule::OnAutoFitCommentsClicked()
{
	UE_LOG(LogVesperCleaner, Verbose, TEXT("[Vesper] Executing AutoFitComments..."));
	FVesperGraphLayout::AutoFitSelectedComments();
}

void FVesperNodeCleanerModule::RegisterMenus()
{
	FToolMenuOwnerScoped OwnerScoped(this);

	// -------------------------------------------------------------------
	// 1. Context menu (right-click inside the Graph Editor)
	// -------------------------------------------------------------------
	if (UToolMenu* GraphContextMenu = UToolMenus::Get()->ExtendMenu("GraphEditor.GraphContextMenu"))
	{
		FToolMenuSection& Section = GraphContextMenu->FindOrAddSection("NodeOperations", LOCTEXT("VesperSectionHeader", "Vesper Tools"));

		Section.AddMenuEntryWithCommandList(
			FVesperNodeCleanerCommands::Get().AutoFormatGraph,
			PluginCommands,
			LOCTEXT("VesperFormatNodesLabel", "Vesper: Auto-Format Selected"),
			LOCTEXT("VesperFormatNodesTooltip", "Automatically arranges the selected nodes into clean, non-overlapping columns based on their connections.")
		);

		// NOTE: this entry was missing entirely in the previous version, so
		// Auto-Fit Comments had no way to be triggered from the UI even
		// though the command and handler both existed.
		Section.AddMenuEntryWithCommandList(
			FVesperNodeCleanerCommands::Get().AutoFitComments,
			PluginCommands,
			LOCTEXT("VesperFitCommentsLabel", "Vesper: Auto-Fit Comment Box"),
			LOCTEXT("VesperFitCommentsTooltip", "Resizes the selected Comment box(es) to tightly wrap the nodes they contain.")
		);
	}

	// -------------------------------------------------------------------
	// 2. Blueprint Editor toolbar (next to Compile / Save)
	// -------------------------------------------------------------------
	if (UToolMenu* BlueprintToolbar = UToolMenus::Get()->ExtendMenu("AssetEditor.BlueprintEditor.ToolBar"))
	{
		FToolMenuSection& Section = BlueprintToolbar->FindOrAddSection("PluginCommands");

		FToolMenuEntry FormatEntry = FToolMenuEntry::InitToolBarButton(
			FVesperNodeCleanerCommands::Get().AutoFormatGraph,
			LOCTEXT("VesperCleanLabel", "Clean Graph"),
			LOCTEXT("VesperCleanToolTip", "Auto-format the selected nodes with Vesper."),
			FSlateIcon(FVesperNodeCleanerStyle::GetStyleSetName(), "VesperNodeCleaner.AutoFormatGraph")
		);
		FormatEntry.SetCommandList(PluginCommands);
		Section.AddEntry(FormatEntry);

		FToolMenuEntry FitCommentsEntry = FToolMenuEntry::InitToolBarButton(
			FVesperNodeCleanerCommands::Get().AutoFitComments,
			LOCTEXT("VesperFitCommentsToolbarLabel", "Fit Comment"),
			LOCTEXT("VesperFitCommentsToolbarToolTip", "Resize the selected Comment box to fit its contents."),
			FSlateIcon(FVesperNodeCleanerStyle::GetStyleSetName(), "VesperNodeCleaner.AutoFitComments")
		);
		FitCommentsEntry.SetCommandList(PluginCommands);
		Section.AddEntry(FitCommentsEntry);
	}

	// -------------------------------------------------------------------
	// 3. Top menu bar (Window)
	// -------------------------------------------------------------------
	if (UToolMenu* MainMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Window"))
	{
		FToolMenuSection& Section = MainMenu->FindOrAddSection("WindowLayout");
		Section.AddMenuEntryWithCommandList(FVesperNodeCleanerCommands::Get().AutoFormatGraph, PluginCommands);
	}
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FVesperNodeCleanerModule, VesperNodeCleaner)
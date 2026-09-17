// Copyright Vesper System, 2026. All Rights Reserved.
#include "VesperNodeCleanerStyle.h"
#include "VesperNodeCleaner.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/SlateStyleRegistry.h"
#include "Slate/SlateGameResources.h"
#include "Interfaces/IPluginManager.h"
#include "Styling/SlateStyleMacros.h"
#define RootToContentDir Style->RootToContentDir
TSharedPtr<FSlateStyleSet> FVesperNodeCleanerStyle::StyleInstance = nullptr;
void FVesperNodeCleanerStyle::Initialize()
{
	if (!StyleInstance.IsValid())
	{
		StyleInstance = Create();
		FSlateStyleRegistry::RegisterSlateStyle(*StyleInstance);
	}
}
void FVesperNodeCleanerStyle::Shutdown()
{
	FSlateStyleRegistry::UnRegisterSlateStyle(*StyleInstance);
	ensure(StyleInstance.IsUnique());
	StyleInstance.Reset();
}
FName FVesperNodeCleanerStyle::GetStyleSetName()
{
	static FName StyleSetName(TEXT("VesperNodeCleanerStyle"));
	return StyleSetName;
}
const FVector2D Icon16x16(16.0f, 16.0f);
const FVector2D Icon20x20(20.0f, 20.0f);
TSharedRef< FSlateStyleSet > FVesperNodeCleanerStyle::Create()
{
	TSharedRef< FSlateStyleSet > Style = MakeShareable(new FSlateStyleSet("VesperNodeCleanerStyle"));
	Style->SetContentRoot(IPluginManager::Get().FindPlugin("VesperNodeCleaner")->GetBaseDir() / TEXT("Resources"));
	Style->Set("VesperNodeCleaner.PluginAction", new IMAGE_BRUSH_SVG(TEXT("PlaceholderButtonIcon"), Icon20x20));

	// The module looks these two up by name when building the Blueprint
	// Editor toolbar buttons (AutoFormatGraph and AutoFitComments). Both
	// currently share the same placeholder artwork — swap in dedicated SVGs
	// (e.g. "AutoFormatIcon" / "AutoFitCommentsIcon") once final art is
	// ready for the FAB listing, no other code needs to change.
	Style->Set("VesperNodeCleaner.AutoFormatGraph", new IMAGE_BRUSH_SVG(TEXT("PlaceholderButtonIcon"), Icon20x20));
	Style->Set("VesperNodeCleaner.AutoFitComments", new IMAGE_BRUSH_SVG(TEXT("PlaceholderButtonIcon"), Icon20x20));

	return Style;
}
void FVesperNodeCleanerStyle::ReloadTextures()
{
	if (FSlateApplication::IsInitialized())
	{
		FSlateApplication::Get().GetRenderer()->ReloadTextureResources();
	}
}
const ISlateStyle& FVesperNodeCleanerStyle::Get()
{
	return *StyleInstance;
}
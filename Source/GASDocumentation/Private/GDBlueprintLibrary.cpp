// Copyright 2020 Dan Kestranek.


#include "GDBlueprintLibrary.h"
#include "Blueprint/DragDropOperation.h"
#include "Components/Image.h"

UDragDropOperation* UGDBlueprintLibrary::MakeItemDragOp(UImage* SourceIcon, const FString& Tag, UObject* Payload)
{
	UDragDropOperation* Op = NewObject<UDragDropOperation>(GetTransientPackage());
	Op->Tag = Tag;
	Op->Payload = Payload;
	Op->Pivot = EDragPivot::CenterCenter;

	if (IsValid(SourceIcon))
	{
		UImage* Vis = NewObject<UImage>(Op);
		Vis->SetBrush(SourceIcon->GetBrush());
		Vis->SetDesiredSizeOverride(FVector2D(64, 64));
		Op->DefaultDragVisual = Vis;
	}

	return Op;
}

void UGDBlueprintLibrary::GetItemDragOpInfo(UDragDropOperation* Operation, FString& Tag, UObject*& Payload)
{
	if (!Operation)
	{
		Tag = TEXT("");
		Payload = nullptr;
		return;
	}

	Tag = Operation->Tag;
	Payload = Operation->Payload;
}

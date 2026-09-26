// Copyright 2020 Dan Kestranek.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GameplayEffect.h"
#include "GDBlueprintLibrary.generated.h"

class UDragDropOperation;
class UImage;

/**
 *
 */
UCLASS()
class GASDOCUMENTATION_API UGDBlueprintLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:

	UFUNCTION(BlueprintCallable, Category = "NoBrainers|DragDrop")
	static UDragDropOperation* MakeItemDragOp(UImage* SourceIcon, const FString& Tag, UObject* Payload);

	UFUNCTION(BlueprintPure, Category = "NoBrainers|DragDrop")
	static void GetItemDragOpInfo(UDragDropOperation* Operation, FString& Tag, UObject*& Payload);

};

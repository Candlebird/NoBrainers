// Copyright 2020 Dan Kestranek.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GameplayEffect.h"
#include "GDBlueprintLibrary.generated.h"

class UDragDropOperation;
class UImage;
class UGameplayAbility;
class APlayerState;

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

	UFUNCTION(BlueprintPure, Category = "NoBrainers|Abilities")
	static bool IsAbilityLocalPredicted(TSubclassOf<UGameplayAbility> AbilityClass);

	/** Stable per-player id for save data: unique net id string if valid, else the player name. */
	UFUNCTION(BlueprintPure, Category = "NoBrainers|Save")
	static FString GetPlayerStableId(const APlayerState* PlayerState);

	/** Test-harness only (automation test bed); not for gameplay use.
	 *  Calls a zero-input-parameter function on Target by name. Returns false if not found or it takes inputs. */
	UFUNCTION(BlueprintCallable, Category = "NoBrainers|Testing", meta = (DefaultToSelf = "Target"))
	static bool CallFunctionByName(UObject* Target, FName FunctionName);

	/** Test-harness only (automation test bed); not for gameplay use.
	 *  Returns sorted, de-duplicated names of Target's functions (incl. inherited) starting with Prefix (case-sensitive). */
	UFUNCTION(BlueprintCallable, Category = "NoBrainers|Testing", meta = (DefaultToSelf = "Target"))
	static TArray<FName> GetFunctionNamesWithPrefix(UObject* Target, const FString& Prefix);

};

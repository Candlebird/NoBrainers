#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GSStatics.generated.h"

class UBehaviorTree;

UCLASS()
class GASDOCUMENTATION_API UGSStatics : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** * Finds the closest actor from a provided array relative to a source actor.
	 * Returns nullptr if the array is empty or the source is invalid.
	 */
	UFUNCTION(BlueprintCallable, Category = "GSHelpers|Utility")
	static AActor* GetClosestActor(const TArray<AActor*>& ActorsToSearch, const AActor* SourceActor);

	/** Editor-only: reparent BT node instances (Outer = editor graph node) to the UBehaviorTree asset so cooking keeps them. */
	UFUNCTION(BlueprintCallable, Category = "Diagnostics")
	static FString FixBehaviorTreeNodeOuters(UBehaviorTree* Tree);
};
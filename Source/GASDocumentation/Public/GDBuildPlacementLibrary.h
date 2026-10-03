#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Engine/HitResult.h"
#include "GDBuildPlacementLibrary.generated.h"

UCLASS()
class GASDOCUMENTATION_API UGDBuildPlacementLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintPure, Category = "NoBrainers|Build")
	static float GetMaxBuildRange();

	UFUNCTION(BlueprintCallable, Category = "NoBrainers|Build", meta = (WorldContext = "WorldContextObject"))
	static bool TraceBuildSurface(const UObject* WorldContextObject, FVector Start, FVector End, const TArray<AActor*>& IgnoreActors, FHitResult& OutHit);

	UFUNCTION(BlueprintPure, Category = "NoBrainers|Build")
	static bool ComputePlacementTransform(const FHitResult& AimHit, bool bIsWallItem, float YawDegrees, FTransform& OutTransform, FText& OutFailReason);

	UFUNCTION(BlueprintCallable, Category = "NoBrainers|Build", meta = (WorldContext = "WorldContextObject"))
	static bool ValidatePlacement(const UObject* WorldContextObject, const FTransform& PlacementTransform, bool bIsWallItem, FVector PlacementExtent, FVector ViewerLocation, float RangeSlack, const TArray<AActor*>& IgnoreActors, FText& OutFailReason);

	UFUNCTION(BlueprintPure, Category = "NoBrainers|Build", meta = (WorldContext = "WorldContextObject"))
	static bool IsPointInBuildArea(const UObject* WorldContextObject, FVector Point);

	UFUNCTION(BlueprintPure, Category = "NoBrainers|Build")
	static bool GetBuildableDefaults(TSubclassOf<AActor> DefenseClass, FVector& OutPlacementExtent, float& OutPreviewRadius, bool& bOutBlocksPath);
};

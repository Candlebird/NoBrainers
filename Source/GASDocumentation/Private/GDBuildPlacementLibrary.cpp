#include "GDBuildPlacementLibrary.h"

#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Engine/StaticMeshActor.h"
#include "Components/BoxComponent.h"
#include "Components/MeshComponent.h"
#include "CollisionQueryParams.h"
#include "CollisionShape.h"
#include "Math/RotationMatrix.h"

#define LOCTEXT_NAMESPACE "GDBuildPlacement"

namespace
{
	const float RangeCm = 600.f;
	const float MaxSlopeDeg = 15.f;
	const float WallMaxAbsNormalZ = 0.25f;
	const float Shrink = 2.f;
	const float DoorReserveXY = 120.f;
	const float FloorProbeUp = 20.f;
	const float FloorProbeDown = 30.f;
	const float FloorProbeTolerance = 10.f;

	const FName TagBuildable(TEXT("Buildable"));
	const FName TagBuildGhost(TEXT("BuildGhost"));
	const FName TagBuildReserve(TEXT("BuildReserve"));
	const FName TagBuildArea(TEXT("BuildArea"));
	const FName TagBuildIgnore(TEXT("BuildIgnore"));

	float FloorMinNormalZ()
	{
		return FMath::Cos(FMath::DegreesToRadians(MaxSlopeDeg));
	}

	void FillFail(FText& Out, const FText& Reason)
	{
		Out = Reason;
	}

	bool PointInBox(const UBoxComponent* Box, const FVector& P)
	{
		const FVector L = Box->GetComponentTransform().InverseTransformPosition(P);
		const FVector Ext = Box->GetUnscaledBoxExtent();
		return FMath::Abs(L.X) <= Ext.X && FMath::Abs(L.Y) <= Ext.Y && FMath::Abs(L.Z) <= Ext.Z;
	}

	void GatherAreaBoxes(const UWorld* World, TArray<const UBoxComponent*>& OutBoxes)
	{
		for (TActorIterator<AActor> It(const_cast<UWorld*>(World)); It; ++It)
		{
			AActor* A = *It;
			if (!A || !A->ActorHasTag(TagBuildArea))
			{
				continue;
			}
			TArray<UBoxComponent*> Comps;
			A->GetComponents<UBoxComponent>(Comps);
			for (UBoxComponent* B : Comps)
			{
				if (B)
				{
					OutBoxes.Add(B);
				}
			}
		}
	}

	bool PointInAnyBox(const TArray<const UBoxComponent*>& Boxes, const FVector& P)
	{
		for (const UBoxComponent* B : Boxes)
		{
			if (PointInBox(B, P))
			{
				return true;
			}
		}
		return false;
	}

	bool StrictIntersect(const FBox& A, const FBox& B)
	{
		return A.Min.X < B.Max.X && A.Max.X > B.Min.X
			&& A.Min.Y < B.Max.Y && A.Max.Y > B.Min.Y
			&& A.Min.Z < B.Max.Z && A.Max.Z > B.Min.Z;
	}

	void BoxCorners(const FTransform& T, const FVector& Center, const FVector& Ext, TArray<FVector>& Out)
	{
		for (int32 i = 0; i < 8; ++i)
		{
			const FVector Sign((i & 1) ? 1.f : -1.f, (i & 2) ? 1.f : -1.f, (i & 4) ? 1.f : -1.f);
			Out.Add(T.TransformPosition(Center + Sign * Ext));
		}
	}
}

float UGDBuildPlacementLibrary::GetMaxBuildRange()
{
	return RangeCm;
}

bool UGDBuildPlacementLibrary::TraceBuildSurface(const UObject* WorldContextObject, FVector Start, FVector End, const TArray<AActor*>& IgnoreActors, FHitResult& OutHit)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::LogAndReturnNull) : nullptr;
	if (!World)
	{
		return false;
	}

	FCollisionQueryParams Params(SCENE_QUERY_STAT(GDTraceBuildSurface), false);
	Params.AddIgnoredActors(IgnoreActors);

	FCollisionObjectQueryParams ObjParams;
	ObjParams.AddObjectTypesToQuery(ECC_WorldStatic);
	ObjParams.AddObjectTypesToQuery(ECC_WorldDynamic);

	TArray<FHitResult> Hits;
	World->LineTraceMultiByObjectType(Hits, Start, End, ObjParams, Params);

	for (const FHitResult& H : Hits)
	{
		const AActor* Actor = H.GetActor();
		UPrimitiveComponent* Comp = H.GetComponent();
		if (!Actor || !Comp)
		{
			continue;
		}
		if (Actor->IsA<APawn>())
		{
			continue;
		}
		if (IgnoreActors.Contains(Actor))
		{
			continue;
		}
		if (Comp->IsSimulatingPhysics())
		{
			continue;
		}
		if (Comp->GetCollisionResponseToChannel(ECC_Pawn) != ECR_Block)
		{
			continue;
		}
		OutHit = H;
		OutHit.bBlockingHit = true;
		return true;
	}
	return false;
}

bool UGDBuildPlacementLibrary::ComputePlacementTransform(const FHitResult& AimHit, bool bIsWallItem, float YawDegrees, FTransform& OutTransform, FText& OutFailReason)
{
	OutFailReason = FText::GetEmpty();

	if (!AimHit.bBlockingHit)
	{
		OutTransform = FTransform(FQuat::Identity, FVector(AimHit.TraceEnd));
		FillFail(OutFailReason, LOCTEXT("NoAim", "Nothing to aim at"));
		return false;
	}

	const FVector N = AimHit.ImpactNormal.GetSafeNormal();
	const FVector Loc = AimHit.ImpactPoint;

	if (!bIsWallItem)
	{
		const float Yaw = FMath::DegreesToRadians(YawDegrees);
		const FVector Ref(FMath::Cos(Yaw), FMath::Sin(Yaw), 0.f);
		const FQuat Rot = FRotationMatrix::MakeFromZX(N, Ref).ToQuat();
		OutTransform = FTransform(Rot, Loc);
		if (N.Z < FloorMinNormalZ())
		{
			FillFail(OutFailReason, LOCTEXT("TooSteep", "Too steep"));
			return false;
		}
		return true;
	}

	FVector H(N.X, N.Y, 0.f);
	if (H.IsNearlyZero())
	{
		H = FVector(1.f, 0.f, 0.f);
	}
	else
	{
		H.Normalize();
	}
	const FQuat Rot = FRotationMatrix::MakeFromXZ(H, FVector::UpVector).ToQuat();
	OutTransform = FTransform(Rot, Loc);

	const UPrimitiveComponent* Comp = AimHit.GetComponent();
	if (FMath::Abs(N.Z) > WallMaxAbsNormalZ || !Comp || Comp->GetCollisionObjectType() != ECC_WorldStatic)
	{
		FillFail(OutFailReason, LOCTEXT("NeedsWall", "Needs a wall"));
		return false;
	}
	return true;
}

bool UGDBuildPlacementLibrary::ValidatePlacement(const UObject* WorldContextObject, const FTransform& PlacementTransform, bool bIsWallItem, FVector PlacementExtent, FVector ViewerLocation, float RangeSlack, const TArray<AActor*>& IgnoreActors, FText& OutFailReason)
{
	OutFailReason = FText::GetEmpty();

	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::LogAndReturnNull) : nullptr;
	if (!World)
	{
		FillFail(OutFailReason, LOCTEXT("NoWorld", "Nothing to aim at"));
		return false;
	}

	const FVector E = PlacementExtent;
	const FVector C = bIsWallItem ? FVector(E.X, 0.f, 0.f) : FVector(0.f, 0.f, E.Z);
	const FVector Loc = PlacementTransform.GetLocation();

	// 1. Range
	if (FVector::Dist(ViewerLocation, Loc) > RangeCm + RangeSlack)
	{
		FillFail(OutFailReason, LOCTEXT("TooFar", "Too far"));
		return false;
	}

	// 2. Surface
	FVector SurfaceNormal;
	if (!bIsWallItem)
	{
		const FVector Up = PlacementTransform.GetUnitAxis(EAxis::Z);
		SurfaceNormal = Up;
		if (Up.Z < FloorMinNormalZ() - 0.001f)
		{
			FillFail(OutFailReason, LOCTEXT("TooSteep2", "Too steep"));
			return false;
		}
		FHitResult Hit;
		if (!TraceBuildSurface(WorldContextObject, Loc + Up * FloorProbeUp, Loc - Up * FloorProbeDown, IgnoreActors, Hit)
			|| FVector::Dist(Hit.Location, Loc) > FloorProbeTolerance)
		{
			FillFail(OutFailReason, LOCTEXT("NeedsFloor", "Needs a floor"));
			return false;
		}
	}
	else
	{
		const FVector Fwd = PlacementTransform.GetUnitAxis(EAxis::X);
		SurfaceNormal = Fwd;
		if (FMath::Abs(Fwd.Z) > WallMaxAbsNormalZ)
		{
			FillFail(OutFailReason, LOCTEXT("NeedsWall2", "Needs a wall"));
			return false;
		}
		FHitResult Hit;
		if (!TraceBuildSurface(WorldContextObject, Loc + Fwd * 10.f, Loc - Fwd * 20.f, IgnoreActors, Hit)
			|| !Hit.GetComponent() || Hit.GetComponent()->GetCollisionObjectType() != ECC_WorldStatic)
		{
			FillFail(OutFailReason, LOCTEXT("NeedsWall3", "Needs a wall"));
			return false;
		}
	}

	// 3. Area
	{
		TArray<const UBoxComponent*> Boxes;
		GatherAreaBoxes(World, Boxes);

		const FVector Shrunk = (E - FVector(Shrink)).ComponentMax(FVector::ZeroVector);
		TArray<FVector> Pts;
		BoxCorners(PlacementTransform, C, Shrunk, Pts);
		Pts.Add(PlacementTransform.TransformPosition(C));

		for (const FVector& P : Pts)
		{
			if (!PointInAnyBox(Boxes, P))
			{
				FillFail(OutFailReason, LOCTEXT("Outside", "Outside store"));
				return false;
			}
		}
	}

	// 4. Tag pass
	{
		TArray<FVector> Corners;
		BoxCorners(PlacementTransform, C, E, Corners);
		FBox FootBox(Corners);
		FootBox = FootBox.ExpandBy(-Shrink);

		for (TActorIterator<AActor> It(const_cast<UWorld*>(World)); It; ++It)
		{
			AActor* A = *It;
			if (!A || IgnoreActors.Contains(A))
			{
				continue;
			}
			const bool bBuildable = A->ActorHasTag(TagBuildable);
			const bool bGhost = A->ActorHasTag(TagBuildGhost);
			const bool bReserve = A->ActorHasTag(TagBuildReserve);
			if (!bBuildable && !bGhost && !bReserve)
			{
				continue;
			}

			FBox ActorBox(ForceInit);
			TArray<UMeshComponent*> Meshes;
			A->GetComponents<UMeshComponent>(Meshes);
			for (UMeshComponent* M : Meshes)
			{
				if (M && M->IsVisible())
				{
					ActorBox += M->Bounds.GetBox();
				}
			}
			if (!ActorBox.IsValid)
			{
				continue;
			}
			ActorBox = ActorBox.ExpandBy(-Shrink);

			if (bBuildable && StrictIntersect(FootBox, ActorBox))
			{
				FillFail(OutFailReason, LOCTEXT("OverBuildable", "Overlaps a buildable"));
				return false;
			}
			if (bGhost && StrictIntersect(FootBox, ActorBox))
			{
				FillFail(OutFailReason, LOCTEXT("OverGhost", "Overlaps a ghost"));
				return false;
			}
			if (bReserve)
			{
				FBox Reserve = ActorBox;
				Reserve.Min.X -= DoorReserveXY;
				Reserve.Min.Y -= DoorReserveXY;
				Reserve.Max.X += DoorReserveXY;
				Reserve.Max.Y += DoorReserveXY;
				if (StrictIntersect(FootBox, Reserve))
				{
					FillFail(OutFailReason, LOCTEXT("BlocksDoor", "Blocks a door"));
					return false;
				}
			}
		}
	}

	// 5. Physical pass
	{
		const FVector BoxExtent = (E - FVector(1.f)).ComponentMax(FVector(0.1f));
		const FVector Center = PlacementTransform.TransformPosition(C) + SurfaceNormal * 2.f;

		FCollisionObjectQueryParams ObjParams;
		ObjParams.AddObjectTypesToQuery(ECC_WorldStatic);
		ObjParams.AddObjectTypesToQuery(ECC_WorldDynamic);
		ObjParams.AddObjectTypesToQuery(ECC_PhysicsBody);
		ObjParams.AddObjectTypesToQuery(ECC_Destructible);

		FCollisionQueryParams Params(SCENE_QUERY_STAT(GDValidatePlacement), false);
		Params.AddIgnoredActors(IgnoreActors);

		TArray<FOverlapResult> Overlaps;
		World->OverlapMultiByObjectType(Overlaps, Center, PlacementTransform.GetRotation(), ObjParams, FCollisionShape::MakeBox(BoxExtent), Params);

		for (const FOverlapResult& O : Overlaps)
		{
			AActor* Owner = O.GetActor();
			UPrimitiveComponent* Comp = O.GetComponent();
			if (!Owner || !Comp)
			{
				continue;
			}
			if (Owner->IsA<APawn>())
			{
				continue;
			}
			if (Owner->ActorHasTag(TagBuildable) || Owner->ActorHasTag(TagBuildGhost) || Owner->ActorHasTag(TagBuildReserve)
				|| Owner->ActorHasTag(TagBuildArea) || Owner->ActorHasTag(TagBuildIgnore))
			{
				continue;
			}
			if (IgnoreActors.Contains(Owner))
			{
				continue;
			}
			if (Comp->IsSimulatingPhysics())
			{
				continue;
			}
			if (Comp->GetCollisionResponseToChannel(ECC_Pawn) != ECR_Block)
			{
				continue;
			}
			if (Owner->IsA<AStaticMeshActor>())
			{
				FillFail(OutFailReason, LOCTEXT("OverWall", "Overlaps a wall"));
			}
			else
			{
				FillFail(OutFailReason, LOCTEXT("OverObject", "Overlaps an object"));
			}
			return false;
		}
	}

	OutFailReason = FText::GetEmpty();
	return true;
}

bool UGDBuildPlacementLibrary::IsPointInBuildArea(const UObject* WorldContextObject, FVector Point)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::LogAndReturnNull) : nullptr;
	if (!World)
	{
		return false;
	}
	TArray<const UBoxComponent*> Boxes;
	GatherAreaBoxes(World, Boxes);
	return PointInAnyBox(Boxes, Point);
}

bool UGDBuildPlacementLibrary::GetBuildableDefaults(TSubclassOf<AActor> DefenseClass, FVector& OutPlacementExtent, float& OutPreviewRadius, bool& bOutBlocksPath)
{
	OutPlacementExtent = FVector(50.f, 50.f, 40.f);
	OutPreviewRadius = 0.f;
	bOutBlocksPath = false;

	if (!DefenseClass)
	{
		return false;
	}
	const UObject* CDO = DefenseClass->GetDefaultObject();
	if (!CDO)
	{
		return false;
	}
	const UClass* Cls = DefenseClass.Get();

	if (const FStructProperty* P = FindFProperty<FStructProperty>(Cls, TEXT("PlacementExtent")))
	{
		if (P->Struct == TBaseStructure<FVector>::Get())
		{
			OutPlacementExtent = *P->ContainerPtrToValuePtr<FVector>(CDO);
		}
	}
	if (const FDoubleProperty* P = FindFProperty<FDoubleProperty>(Cls, TEXT("PreviewRadius")))
	{
		OutPreviewRadius = (float)P->GetPropertyValue_InContainer(CDO);
	}
	else if (const FFloatProperty* PF = FindFProperty<FFloatProperty>(Cls, TEXT("PreviewRadius")))
	{
		OutPreviewRadius = PF->GetPropertyValue_InContainer(CDO);
	}
	if (const FBoolProperty* P = FindFProperty<FBoolProperty>(Cls, TEXT("bBlocksPath")))
	{
		bOutBlocksPath = P->GetPropertyValue_InContainer(CDO);
	}
	return true;
}

#undef LOCTEXT_NAMESPACE

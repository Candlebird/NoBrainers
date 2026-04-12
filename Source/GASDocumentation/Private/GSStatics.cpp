#include "GSStatics.h"

AActor *UGSStatics::GetClosestActor(const TArray<AActor *> &ActorsToSearch, const AActor *SourceActor)
{
    if (!SourceActor || ActorsToSearch.Num() == 0)
    {
        return nullptr;
    }

    AActor *ClosestActor = nullptr;
    float MinDistanceSq = MAX_FLT; // Start with the highest possible number
    FVector SourceLocation = SourceActor->GetActorLocation();

    for (AActor *CurrentActor : ActorsToSearch)
    {
        if (CurrentActor)
        {
            // GetSquaredDistanceTo is faster than GetDistanceTo
            float DistanceSq = CurrentActor->GetSquaredDistanceTo(SourceActor);

            if (DistanceSq < MinDistanceSq)
            {
                MinDistanceSq = DistanceSq;
                ClosestActor = CurrentActor;
            }
        }
    }

    return ClosestActor;
}
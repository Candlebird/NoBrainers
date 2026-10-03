#pragma once

#include "CoreMinimal.h"
#include "NavFilters/NavigationQueryFilter.h"
#include "GDNavFilter_AvoidDefenseBlockers.generated.h"

/** Query filter that excludes the DefenseBlocker nav area. */
UCLASS()
class GASDOCUMENTATION_API UGDNavFilter_AvoidDefenseBlockers : public UNavigationQueryFilter
{
	GENERATED_BODY()

public:
	UGDNavFilter_AvoidDefenseBlockers();
};

#pragma once

#include "CoreMinimal.h"
#include "NavAreas/NavArea.h"
#include "GDNavArea_DefenseBlocker.generated.h"

/** Traversable-by-default nav area stamped under path-blocking defenses so AI filters can avoid it. */
UCLASS()
class GASDOCUMENTATION_API UGDNavArea_DefenseBlocker : public UNavArea
{
	GENERATED_BODY()

public:
	UGDNavArea_DefenseBlocker();
};

#include "GDNavFilter_AvoidDefenseBlockers.h"
#include "GDNavArea_DefenseBlocker.h"

UGDNavFilter_AvoidDefenseBlockers::UGDNavFilter_AvoidDefenseBlockers()
{
	AddExcludedArea(UGDNavArea_DefenseBlocker::StaticClass());
}

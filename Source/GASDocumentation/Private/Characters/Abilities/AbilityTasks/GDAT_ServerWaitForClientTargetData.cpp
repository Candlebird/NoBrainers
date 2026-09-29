// Copyright 2020 Dan Kestranek.

#include "Characters/Abilities/AbilityTasks/GDAT_ServerWaitForClientTargetData.h"
#include "AbilitySystemComponent.h"

UGDAT_ServerWaitForClientTargetData* UGDAT_ServerWaitForClientTargetData::ServerWaitForClientTargetData(UGameplayAbility* OwningAbility, FName TaskInstanceName, bool TriggerOnce)
{
	UGDAT_ServerWaitForClientTargetData* MyObj = NewAbilityTask<UGDAT_ServerWaitForClientTargetData>(OwningAbility, TaskInstanceName);
	MyObj->bTriggerOnce = TriggerOnce;
	return MyObj;
}

void UGDAT_ServerWaitForClientTargetData::Activate()
{
	if (!Ability || !Ability->GetCurrentActorInfo()->IsNetAuthority() || !AbilitySystemComponent.IsValid())
	{
		return;
	}

	const FGameplayAbilitySpecHandle H = GetAbilitySpecHandle();
	const FPredictionKey K = GetActivationPredictionKey();
	AbilitySystemComponent->AbilityTargetDataSetDelegate(H, K).AddUObject(this, &ThisClass::OnTargetDataReplicatedCallback);
	AbilitySystemComponent->CallReplicatedTargetDataDelegatesIfSet(H, K);
}

void UGDAT_ServerWaitForClientTargetData::OnTargetDataReplicatedCallback(const FGameplayAbilityTargetDataHandle& Data, FGameplayTag ActivationTag)
{
	FGameplayAbilityTargetDataHandle Copy = Data;
	AbilitySystemComponent->ConsumeClientReplicatedTargetData(GetAbilitySpecHandle(), GetActivationPredictionKey());

	if (ShouldBroadcastAbilityTaskDelegates())
	{
		ValidData.Broadcast(Copy);
		if (bTriggerOnce)
		{
			EndTask();
		}
	}
}

void UGDAT_ServerWaitForClientTargetData::OnDestroy(bool AbilityIsEnding)
{
	if (AbilitySystemComponent.IsValid())
	{
		AbilitySystemComponent->AbilityTargetDataSetDelegate(GetAbilitySpecHandle(), GetActivationPredictionKey()).RemoveAll(this);
	}
	Super::OnDestroy(AbilityIsEnding);
}

// Copyright 2020 Dan Kestranek.


#include "Characters/Abilities/GDGameplayAbility.h"
#include "AbilitySystemComponent.h"
#include "GameplayTagContainer.h"

UGDGameplayAbility::UGDGameplayAbility()
{
	// Default to Instance Per Actor
	InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;

	// Default tags that block this ability from activating
	ActivationBlockedTags.AddTag(FGameplayTag::RequestGameplayTag(FName("State.Dead")));
	ActivationBlockedTags.AddTag(FGameplayTag::RequestGameplayTag(FName("State.Debuff.Stun")));
}

void UGDGameplayAbility::OnAvatarSet(const FGameplayAbilityActorInfo * ActorInfo, const FGameplayAbilitySpec & Spec)
{
	Super::OnAvatarSet(ActorInfo, Spec);

	if (ActivateAbilityOnGranted)
	{
		ActorInfo->AbilitySystemComponent->TryActivateAbility(Spec.Handle, false);
	}
}

void UGDGameplayAbility::SendShotTargetDataToServer(const FGameplayAbilityTargetDataHandle& TargetData)
{
	UAbilitySystemComponent* ASC = GetAbilitySystemComponentFromActorInfo();
	const FGameplayAbilityActorInfo* Info = GetCurrentActorInfo();
	if (!ASC || !Info || Info->IsNetAuthority() || !Info->IsLocallyControlled())
	{
		return;
	}

	FScopedPredictionWindow ScopedPrediction(ASC, true);
	ASC->CallServerSetReplicatedTargetData(CurrentSpecHandle, CurrentActivationInfo.GetActivationPredictionKey(), TargetData, FGameplayTag(), ASC->ScopedPredictionKey);
}

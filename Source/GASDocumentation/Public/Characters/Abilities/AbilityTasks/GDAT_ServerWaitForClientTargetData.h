// Copyright 2020 Dan Kestranek.

#pragma once

#include "CoreMinimal.h"
#include "Abilities/Tasks/AbilityTask.h"
#include "Abilities/Tasks/AbilityTask_WaitTargetData.h"
#include "GDAT_ServerWaitForClientTargetData.generated.h"

/**
 * Server-side: waits for target data replicated from the predicting client.
 */
UCLASS()
class GASDOCUMENTATION_API UGDAT_ServerWaitForClientTargetData : public UAbilityTask
{
	GENERATED_BODY()

public:
	UPROPERTY(BlueprintAssignable)
	FWaitTargetDataDelegate ValidData;

	UFUNCTION(BlueprintCallable, Category = "Ability|Tasks", meta = (HidePin = "OwningAbility", DefaultToSelf = "OwningAbility", BlueprintInternalUseOnly = "true"))
	static UGDAT_ServerWaitForClientTargetData* ServerWaitForClientTargetData(UGameplayAbility* OwningAbility, FName TaskInstanceName, bool TriggerOnce);

	virtual void Activate() override;

	UFUNCTION()
	void OnTargetDataReplicatedCallback(const FGameplayAbilityTargetDataHandle& Data, FGameplayTag ActivationTag);

protected:
	bool bTriggerOnce = true;

	virtual void OnDestroy(bool AbilityIsEnding) override;
};

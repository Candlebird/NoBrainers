// Copyright 2020 Dan Kestranek.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GASDocumentationGameMode.generated.h"

UCLASS(minimalapi)
class AGASDocumentationGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AGASDocumentationGameMode();

	void HeroDied(AController* Controller);

	// Blueprint hook so subclasses (e.g. BP_GameMode_ZombieStore) can react to a player death
	// (e.g. tracking downed players for Night pickup) without overriding HeroDied() in C++.
	UFUNCTION(BlueprintImplementableEvent, Category = "GASDocumentation|GameMode")
	void OnPlayerDied(AController* DeadPlayer);

protected:
	float RespawnDelay;

	TSubclassOf<class AGDHeroCharacter> HeroClass;

	AActor* EnemySpawnPoint;

	virtual void BeginPlay() override;

	void RespawnHero(AController* Controller);
};

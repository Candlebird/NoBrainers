// Copyright 2020 Dan Kestranek.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "SpectatorController_ZombieStore.generated.h"

class AGDHeroCharacter;
class UInputMappingContext;
class UInputAction;
struct FInputActionValue;

/**
 * Player controller that takes over spectating between surviving AGDHeroCharacter actors
 * once the owning client's hero has died.
 */
UCLASS()
class GASDOCUMENTATION_API ASpectatorController_ZombieStore : public APlayerController
{
	GENERATED_BODY()

public:
	ASpectatorController_ZombieStore();

	// Called on the owning client when this controller's hero dies. Builds the list of
	// surviving heroes and switches the view target to the first one found.
	UFUNCTION(Client, Reliable)
	void Client_EnterSpectatorMode();

protected:
	//~ Begin AActor Interface
	virtual void SetupInputComponent() override;
	//~ End AActor Interface

	UPROPERTY(EditDefaultsOnly, Category = "GASDocumentation|Input")
	TSoftObjectPtr<UInputMappingContext> DefaultMappingContext;

	UPROPERTY(EditDefaultsOnly, Category = "GASDocumentation|Input")
	TSoftObjectPtr<UInputAction> PrimaryActionInputAction;

	// Client-local cache of surviving heroes to cycle through while spectating.
	UPROPERTY(Transient)
	TArray<AGDHeroCharacter*> SurvivingCharacters;

	UPROPERTY(Transient)
	int32 CurrentSpectateIndex = -1;

	// Rebuilds SurvivingCharacters from all AGDHeroCharacter actors in the world that are
	// alive and are not this controller's own (dead) pawn.
	void RefreshSurvivingCharacters();

	// Bound to IA_PrimaryAction. Cycles to the next surviving hero in SurvivingCharacters.
	void OnPrimaryAction(const FInputActionValue& Value);
};

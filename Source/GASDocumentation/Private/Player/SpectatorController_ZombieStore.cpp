// Copyright 2020 Dan Kestranek.

#include "Player/SpectatorController_ZombieStore.h"
#include "Characters/Heroes/GDHeroCharacter.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputMappingContext.h"
#include "InputAction.h"
#include "Kismet/GameplayStatics.h"

ASpectatorController_ZombieStore::ASpectatorController_ZombieStore()
{
}

void ASpectatorController_ZombieStore::SetupInputComponent()
{
	Super::SetupInputComponent();

	if (IsLocalPlayerController())
	{
		if (ULocalPlayer* LocalPlayer = GetLocalPlayer())
		{
			if (UEnhancedInputLocalPlayerSubsystem* Subsystem = LocalPlayer->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
			{
				if (UInputMappingContext* MappingContext = DefaultMappingContext.LoadSynchronous())
				{
					Subsystem->AddMappingContext(MappingContext, 0);
				}
			}
		}
	}

	if (UEnhancedInputComponent* EnhancedInputComponent = Cast<UEnhancedInputComponent>(InputComponent))
	{
		if (UInputAction* PrimaryAction = PrimaryActionInputAction.LoadSynchronous())
		{
			EnhancedInputComponent->BindAction(PrimaryAction, ETriggerEvent::Triggered, this, &ASpectatorController_ZombieStore::OnPrimaryAction);
		}
	}
}

void ASpectatorController_ZombieStore::Client_EnterSpectatorMode_Implementation()
{
	RefreshSurvivingCharacters();

	if (SurvivingCharacters.Num() > 0)
	{
		CurrentSpectateIndex = 0;
		SetViewTargetWithBlend(SurvivingCharacters[CurrentSpectateIndex]);
	}
	else
	{
		CurrentSpectateIndex = -1;

		// No survivors found. Leave the view target as-is (self/no-op).
	}
}

void ASpectatorController_ZombieStore::RefreshSurvivingCharacters()
{
	SurvivingCharacters.Reset();

	APawn* MyPawn = GetPawn();

	TArray<AActor*> FoundActors;
	UGameplayStatics::GetAllActorsOfClass(GetWorld(), AGDHeroCharacter::StaticClass(), FoundActors);

	for (AActor* Actor : FoundActors)
	{
		AGDHeroCharacter* Hero = Cast<AGDHeroCharacter>(Actor);
		if (!Hero || Hero == MyPawn)
		{
			continue;
		}

		if (Hero->IsAlive())
		{
			SurvivingCharacters.Add(Hero);
		}
	}
}

void ASpectatorController_ZombieStore::OnPrimaryAction(const FInputActionValue& Value)
{
	if (SurvivingCharacters.Num() == 0)
	{
		RefreshSurvivingCharacters();
	}

	if (SurvivingCharacters.Num() == 0)
	{
		return;
	}

	CurrentSpectateIndex = (CurrentSpectateIndex + 1) % SurvivingCharacters.Num();

	AGDHeroCharacter* NextHero = SurvivingCharacters[CurrentSpectateIndex];
	if (IsValid(NextHero) && NextHero->IsAlive())
	{
		SetViewTargetWithBlend(NextHero);
	}
	else
	{
		// Stale entry (died since last refresh). Rebuild and try again next input.
		RefreshSurvivingCharacters();
	}
}

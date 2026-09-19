// Copyright 2020 Dan Kestranek.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "Characters/GDCharacterBase.h"
#include "GDPlayerController.generated.h"

/**
 * 
 */
UCLASS()
class GASDOCUMENTATION_API AGDPlayerController : public APlayerController
{
	GENERATED_BODY()
	
public:
	void CreateHUD();

	UPROPERTY(EditAnywhere, Category = "GASDocumentation|UI")
	TSubclassOf<class UGDDamageTextWidgetComponent> DamageNumberClass;

	class UGDHUDWidget* GetHUD();

	UFUNCTION(Client, Reliable, WithValidation)
	void ShowDamageNumber(float DamageAmount, AGDCharacterBase* TargetCharacter);
	void ShowDamageNumber_Implementation(float DamageAmount, AGDCharacterBase* TargetCharacter);
	bool ShowDamageNumber_Validate(float DamageAmount, AGDCharacterBase* TargetCharacter);

	// Simple way to RPC to the client the countdown until they respawn from the GameMode. Will be latency amount of out sync with the Server.
	UFUNCTION(Client, Reliable, WithValidation)
	void SetRespawnCountdown(float RespawnTimeRemaining);
	void SetRespawnCountdown_Implementation(float RespawnTimeRemaining);
	bool SetRespawnCountdown_Validate(float RespawnTimeRemaining);

	UFUNCTION(Server, Reliable, WithValidation, BlueprintCallable)
	void Server_PlaceDefenseOnSocket(AActor* TargetSocket, TSubclassOf<AActor> DefenseClass);
	void Server_PlaceDefenseOnSocket_Implementation(AActor* TargetSocket, TSubclassOf<AActor> DefenseClass);
	bool Server_PlaceDefenseOnSocket_Validate(AActor* TargetSocket, TSubclassOf<AActor> DefenseClass);

	UFUNCTION(Server, Reliable, WithValidation, BlueprintCallable)
	void Server_RepairDefense(AActor* TargetSocket);
	void Server_RepairDefense_Implementation(AActor* TargetSocket);
	bool Server_RepairDefense_Validate(AActor* TargetSocket);

	UFUNCTION(Server, Reliable, WithValidation, BlueprintCallable)
	void Server_SellDefense(AActor* TargetSocket);
	void Server_SellDefense_Implementation(AActor* TargetSocket);
	bool Server_SellDefense_Validate(AActor* TargetSocket);

	UFUNCTION(Server, Reliable, WithValidation, BlueprintCallable)
	void Server_RequestKioskPurchase(FName EntryID);
	void Server_RequestKioskPurchase_Implementation(FName EntryID);
	bool Server_RequestKioskPurchase_Validate(FName EntryID);

	UFUNCTION(BlueprintImplementableEvent, Category = "GASDocumentation|Defense")
	void OnServerPlaceDefenseOnSocket(AActor* TargetSocket, TSubclassOf<AActor> DefenseClass);

	UFUNCTION(BlueprintImplementableEvent, Category = "GASDocumentation|Defense")
	void OnServerRepairDefense(AActor* TargetSocket);

	UFUNCTION(BlueprintImplementableEvent, Category = "GASDocumentation|Defense")
	void OnServerSellDefense(AActor* TargetSocket);

	UFUNCTION(BlueprintImplementableEvent, Category = "GASDocumentation|Defense")
	void OnServerRequestKioskPurchase(FName EntryID);

protected:
	UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "GASDocumentation|UI")
	TSubclassOf<class UGDHUDWidget> UIHUDWidgetClass;

	UPROPERTY(BlueprintReadWrite, Category = "GASDocumentation|UI")
	class UGDHUDWidget* UIHUDWidget;

	// Server only
	virtual void OnPossess(APawn* InPawn) override;

	virtual void OnRep_PlayerState() override;
};

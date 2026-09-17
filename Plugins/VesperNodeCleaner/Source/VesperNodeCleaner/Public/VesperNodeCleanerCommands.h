// Copyright Vesper System, 2026. All Rights Reserved.
#pragma once

#include "CoreMinimal.h"
#include "Framework/Commands/Commands.h"
#include "VesperNodeCleanerStyle.h"

class FVesperNodeCleanerCommands : public TCommands<FVesperNodeCleanerCommands>
{
public:
	FVesperNodeCleanerCommands()
		: TCommands<FVesperNodeCleanerCommands>(
			TEXT("VesperNodeCleaner"),
			NSLOCTEXT("Contexts", "VesperNodeCleaner", "Vesper Node Cleaner Plugin"),
			NAME_None,
			FVesperNodeCleanerStyle::GetStyleSetName()
		)
	{}

	// Registrar todos los comandos de acceso rápido
	virtual void RegisterCommands() override;

public:
	// Declaración de nuestras acciones
	TSharedPtr<FUICommandInfo> AutoFormatGraph;
	TSharedPtr<FUICommandInfo> AutoFitComments;
};
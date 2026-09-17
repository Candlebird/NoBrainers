// Copyright Vesper System, 2026. All Rights Reserved.
#include "VesperNodeCleanerCommands.h"

#define LOCTEXT_NAMESPACE "FVesperNodeCleanerModule"

void FVesperNodeCleanerCommands::RegisterCommands()
{
	UI_COMMAND(
		AutoFormatGraph, 
		"Vesper: Auto-Format Graph", 
		"Organiza y alinea automáticamente los nodos seleccionados (Shift + Q)", 
		EUserInterfaceActionType::Button, 
		FInputChord(EKeys::Q, EModifierKey::Shift)
	);

	UI_COMMAND(
		AutoFitComments, 
		"Vesper: Auto-Fit Comments", 
		"Ajusta la caja de comentarios al tamaño exacto de sus nodos (Shift + C)", 
		EUserInterfaceActionType::Button, 
		FInputChord(EKeys::C, EModifierKey::Shift)
	);
}

#undef LOCTEXT_NAMESPACE
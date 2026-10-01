// Copyright 2020 Dan Kestranek.


#include "GDBlueprintLibrary.h"
#include "Blueprint/DragDropOperation.h"
#include "Components/Image.h"
#include "Abilities/GameplayAbility.h"
#include "UObject/UnrealType.h"

bool UGDBlueprintLibrary::IsAbilityLocalPredicted(TSubclassOf<UGameplayAbility> AbilityClass)
{
	return AbilityClass && AbilityClass->GetDefaultObject<UGameplayAbility>()->GetNetExecutionPolicy() == EGameplayAbilityNetExecutionPolicy::LocalPredicted;
}

UDragDropOperation* UGDBlueprintLibrary::MakeItemDragOp(UImage* SourceIcon, const FString& Tag, UObject* Payload)
{
	UDragDropOperation* Op = NewObject<UDragDropOperation>(GetTransientPackage());
	Op->Tag = Tag;
	Op->Payload = Payload;
	Op->Pivot = EDragPivot::CenterCenter;

	if (IsValid(SourceIcon))
	{
		UImage* Vis = NewObject<UImage>(Op);
		Vis->SetBrush(SourceIcon->GetBrush());
		Vis->SetDesiredSizeOverride(FVector2D(64, 64));
		Op->DefaultDragVisual = Vis;
	}

	return Op;
}

void UGDBlueprintLibrary::GetItemDragOpInfo(UDragDropOperation* Operation, FString& Tag, UObject*& Payload)
{
	if (!Operation)
	{
		Tag = TEXT("");
		Payload = nullptr;
		return;
	}

	Tag = Operation->Tag;
	Payload = Operation->Payload;
}

bool UGDBlueprintLibrary::CallFunctionByName(UObject* Target, FName FunctionName)
{
	if (!Target || FunctionName.IsNone())
	{
		return false;
	}

	UFunction* Fn = Target->FindFunction(FunctionName);
	if (!Fn)
	{
		return false;
	}

	for (TFieldIterator<FProperty> It(Fn); It; ++It)
	{
		const FProperty* Prop = *It;
		if (Prop->HasAnyPropertyFlags(CPF_Parm) && !Prop->HasAnyPropertyFlags(CPF_OutParm | CPF_ReturnParm))
		{
			return false;
		}
	}

	uint8* Buffer = Fn->ParmsSize > 0 ? static_cast<uint8*>(FMemory_Alloca(Fn->ParmsSize)) : nullptr;
	if (Buffer)
	{
		FMemory::Memzero(Buffer, Fn->ParmsSize);
	}
	for (TFieldIterator<FProperty> It(Fn); It; ++It)
	{
		if (It->HasAnyPropertyFlags(CPF_Parm))
		{
			It->InitializeValue_InContainer(Buffer);
		}
	}

	Target->ProcessEvent(Fn, Buffer);

	for (TFieldIterator<FProperty> It(Fn); It; ++It)
	{
		if (It->HasAnyPropertyFlags(CPF_Parm))
		{
			It->DestroyValue_InContainer(Buffer);
		}
	}
	return true;
}

TArray<FName> UGDBlueprintLibrary::GetFunctionNamesWithPrefix(UObject* Target, const FString& Prefix)
{
	TArray<FName> Result;
	if (!Target)
	{
		return Result;
	}

	for (TFieldIterator<UFunction> It(Target->GetClass(), EFieldIteratorFlags::IncludeSuper); It; ++It)
	{
		if (It->GetName().StartsWith(Prefix, ESearchCase::CaseSensitive))
		{
			Result.AddUnique(It->GetFName());
		}
	}
	Result.Sort([](const FName& A, const FName& B) { return A.LexicalLess(B); });
	return Result;
}

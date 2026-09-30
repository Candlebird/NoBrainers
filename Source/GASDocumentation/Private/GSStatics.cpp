#include "GSStatics.h"
#include "AIController.h"
#include "AISystem.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "UObject/UnrealType.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BehaviorTreeComponent.h"
#include "BehaviorTree/BehaviorTreeManager.h"
#include "BehaviorTree/BTCompositeNode.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "BehaviorTree/BlackboardData.h"


AActor *UGSStatics::GetClosestActor(const TArray<AActor *> &ActorsToSearch, const AActor *SourceActor)
{
    if (!SourceActor || ActorsToSearch.Num() == 0)
    {
        return nullptr;
    }

    AActor *ClosestActor = nullptr;
    float MinDistanceSq = MAX_FLT; // Start with the highest possible number
    FVector SourceLocation = SourceActor->GetActorLocation();

    for (AActor *CurrentActor : ActorsToSearch)
    {
        if (CurrentActor)
        {
            // GetSquaredDistanceTo is faster than GetDistanceTo
            float DistanceSq = CurrentActor->GetSquaredDistanceTo(SourceActor);

            if (DistanceSq < MinDistanceSq)
            {
                MinDistanceSq = DistanceSq;
                ClosestActor = CurrentActor;
            }
        }
    }

    return ClosestActor;
}

FString UGSStatics::FixBehaviorTreeNodeOuters(UBehaviorTree* Tree)
{
#if WITH_EDITORONLY_DATA
    if (!Tree) { return TEXT("null tree"); }
    UEdGraph* Graph = Tree->BTGraph;
    if (!Graph) { return TEXT("no graph"); }

    int32 Reparented = 0, AlreadyOk = 0, Nodes = 0;
    const int32 RootBefore = Tree->RootNode ? 1 : 0;

    TFunction<void(UObject*)> ProcessGraphNode;
    ProcessGraphNode = [&](UObject* GraphNode)
    {
        if (!GraphNode) { return; }
        UClass* Cls = GraphNode->GetClass();
        if (FObjectProperty* Prop = FindFProperty<FObjectProperty>(Cls, TEXT("NodeInstance")))
        {
            if (UObject* Inst = Prop->GetObjectPropertyValue_InContainer(GraphNode))
            {
                ++Nodes;
                if (Inst->GetOuter() != Tree)
                {
                    Inst->Rename(nullptr, Tree, REN_DontCreateRedirectors | REN_ForceNoResetLoaders);
                    Inst->Modify();
                    ++Reparented;
                }
                else
                {
                    ++AlreadyOk;
                }
            }
        }
        static const TCHAR* ArrayNames[] = { TEXT("Decorators"), TEXT("Services"), TEXT("SubNodes") };
        for (const TCHAR* Name : ArrayNames)
        {
            FArrayProperty* ArrProp = FindFProperty<FArrayProperty>(Cls, Name);
            if (!ArrProp) { continue; }
            FObjectProperty* Inner = CastField<FObjectProperty>(ArrProp->Inner);
            if (!Inner) { continue; }
            FScriptArrayHelper Helper(ArrProp, ArrProp->ContainerPtrToValuePtr<void>(GraphNode));
            for (int32 i = 0; i < Helper.Num(); ++i)
            {
                ProcessGraphNode(Inner->GetObjectPropertyValue(Helper.GetRawPtr(i)));
            }
        }
    };

    for (UEdGraphNode* N : Graph->Nodes)
    {
        ProcessGraphNode(N);
    }

    Tree->Modify();
    Tree->MarkPackageDirty();
    const FString S = FString::Printf(TEXT("reparented=%d alreadyOk=%d nodes=%d rootBefore=%d "), Reparented, AlreadyOk, Nodes, RootBefore);
    UE_LOG(LogTemp, Warning, TEXT("FixBehaviorTreeNodeOuters: %s"), *S);
    return S;
#else
    return TEXT("editor-only");
#endif
}

// Copyright Vesper System, 2026. All Rights Reserved.

#include "VesperGraphLayout.h"
#include "Editor.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraphNode_Comment.h"
#include "K2Node_VariableGet.h"
#include "K2Node_CallFunction.h"
#include "EdGraphSchema_K2.h"
#include "GraphEditor.h"
#include "Layout/WidgetPath.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Notifications/NotificationManager.h"
#include "Widgets/Notifications/SNotificationList.h"
#include "Input/Events.h"
#include "ScopedTransaction.h"

DEFINE_LOG_CATEGORY_STATIC(LogVesperLayout, Log, All);

namespace
{
	// The last Graph Editor widget observed to hold keyboard focus, kept as a
	// fallback for GetActiveGraphEditor(). Weak so a closed editor tab is
	// never kept alive by this cache.
	TWeakPtr<SGraphEditor> GLastKnownGraphEditor;
	FDelegateHandle GFocusChangingHandle;

	// Walks a widget path looking for the deepest SGraphEditor ancestor.
	// Shared by GetActiveGraphEditor() and the global focus-change handler.
	//
	// NOTE: SGraphEditor is an abstract base class — every real graph editor
	// widget instantiated at runtime (e.g. inside the Blueprint editor) is
	// actually the private `SGraphEditorImpl` subclass, so GetTypeAsString()
	// never returns the literal string "SGraphEditor". The original exact-
	// match here was the actual root cause of "Detected: 0": it meant this
	// lookup silently found nothing in *every* case, focus-related or not.
	// Match by substring instead so both SGraphEditor and any subclass name
	// (SGraphEditorImpl, etc.) are recognized.
	TSharedPtr<SGraphEditor> FindGraphEditorInPath(const FWidgetPath& Path)
	{
		for (int32 i = Path.Widgets.Num() - 1; i >= 0; --i)
		{
			const TSharedPtr<SWidget> Widget = Path.Widgets[i].Widget;
			if (Widget->GetTypeAsString().Contains(TEXT("GraphEditor")))
			{
				return StaticCastSharedPtr<SGraphEditor>(Widget);
			}
		}
		return nullptr;
	}

	// Bound to FSlateApplication::OnFocusChanging(). Every time keyboard
	// focus moves anywhere in the editor, remember the Graph Editor it was
	// last inside — so that if focus later moves to something outside any
	// Graph Editor (e.g. a toolbar button), we still have a recent, valid
	// editor to fall back to.
	void HandleGlobalFocusChanging(const FFocusEvent& /*FocusEvent*/, const FWeakWidgetPath& /*OldFocusedWidgetPath*/,
		const TSharedPtr<SWidget>& /*OldFocusedWidget*/, const FWidgetPath& NewFocusedWidgetPath,
		const TSharedPtr<SWidget>& /*NewFocusedWidget*/)
	{
		if (const TSharedPtr<SGraphEditor> FoundEditor = FindGraphEditorInPath(NewFocusedWidgetPath))
		{
			GLastKnownGraphEditor = FoundEditor;
		}
	}
}

namespace VesperLayoutSettings
{
	// Horizontal distance between layers (columns).
	static constexpr float ColumnSpacing = 350.f;

	// Vertical gap left between two stacked nodes in the same layer.
	static constexpr float RowSpacing = 60.f;

	// Padding applied around the contents of a Comment box when auto-fitting.
	static constexpr float CommentPadding = 40.f;

	// Extra vertical space reserved for the Comment box title bar.
	static constexpr float CommentTitleBarHeight = 40.f;

	// Fallback node height used when a node has no pins to estimate from.
	static constexpr float MinNodeHeight = 80.f;

	// Approximate vertical space a single pin row occupies.
	static constexpr float HeightPerPin = 22.f;

	// A fan-out pure node (variable getter or BlueprintPure function call)
	// only gets split into a dedicated duplicate for a consumer that sits
	// farther than this from the original node; consumers within this
	// distance keep sharing it since the shared link doesn't read as
	// clutter at that range.
	static constexpr float VariableSplitMaxDistance = 450.f;
}

TSharedPtr<SGraphEditor> FVesperGraphLayout::GetActiveGraphEditor()
{
	TSharedPtr<SWidget> FocusedWidget = FSlateApplication::Get().GetKeyboardFocusedWidget();
	if (FocusedWidget.IsValid())
	{
		FWidgetPath FocusedWidgetPath;
		if (FSlateApplication::Get().FindPathToWidget(FocusedWidget.ToSharedRef(), FocusedWidgetPath))
		{
			if (const TSharedPtr<SGraphEditor> FoundEditor = FindGraphEditorInPath(FocusedWidgetPath))
			{
				return FoundEditor;
			}
		}
	}

	// Nothing focused is inside a Graph Editor right now — most commonly
	// because a toolbar/menu button (e.g. "Clean Graph") just took keyboard
	// focus for itself when it was clicked. Fall back to the last Graph
	// Editor we actually saw focused; the node selection made just before
	// the click is still valid there.
	return GLastKnownGraphEditor.Pin();
}

void FVesperGraphLayout::RegisterFocusTracking()
{
	if (!GFocusChangingHandle.IsValid())
	{
		GFocusChangingHandle = FSlateApplication::Get().OnFocusChanging().AddStatic(&HandleGlobalFocusChanging);
	}
}

void FVesperGraphLayout::UnregisterFocusTracking()
{
	if (GFocusChangingHandle.IsValid())
	{
		if (FSlateApplication::IsInitialized())
		{
			FSlateApplication::Get().OnFocusChanging().Remove(GFocusChangingHandle);
		}
		GFocusChangingHandle.Reset();
	}
	GLastKnownGraphEditor.Reset();
}

float FVesperGraphLayout::EstimateNodeHeight(const UEdGraphNode* Node)
{
	if (!Node)
	{
		return VesperLayoutSettings::MinNodeHeight;
	}

	const float PinBasedHeight = Node->Pins.Num() * VesperLayoutSettings::HeightPerPin;
	return FMath::Max(VesperLayoutSettings::MinNodeHeight, PinBasedHeight);
}

float FVesperGraphLayout::EstimatePinYOffset(const UEdGraphNode* Node, const UEdGraphPin* Pin)
{
	if (!Node || !Pin)
	{
		return Node ? EstimateNodeHeight(Node) * 0.5f : 0.f;
	}

	// Input and output pins are each rendered in their own top-to-bottom
	// column, so only same-direction pins that come before this one push it
	// further down.
	float Offset = VesperLayoutSettings::HeightPerPin * 0.5f;
	for (const UEdGraphPin* OtherPin : Node->Pins)
	{
		if (!OtherPin || OtherPin->bHidden || OtherPin->Direction != Pin->Direction)
		{
			continue;
		}
		if (OtherPin == Pin)
		{
			break;
		}
		Offset += VesperLayoutSettings::HeightPerPin;
	}
	return Offset;
}

void FVesperGraphLayout::ComputeLayers(const TArray<UEdGraphNode*>& Nodes, TMap<UEdGraphNode*, int32>& OutLayers)
{
	const TSet<UEdGraphNode*> NodeSet(Nodes);
	TMap<UEdGraphNode*, TArray<UEdGraphNode*>> Predecessors;

	// Only edges between two nodes that are BOTH part of the current
	// selection count — this keeps formatting scoped to what the user
	// selected instead of pulling in the whole graph.
	for (UEdGraphNode* Node : Nodes)
	{
		OutLayers.Add(Node, 0);
		TArray<UEdGraphNode*>& NodePredecessors = Predecessors.Add(Node);

		for (const UEdGraphPin* Pin : Node->Pins)
		{
			if (!Pin || Pin->Direction != EGPD_Input)
			{
				continue;
			}

			for (const UEdGraphPin* LinkedPin : Pin->LinkedTo)
			{
				UEdGraphNode* SourceNode = LinkedPin ? LinkedPin->GetOwningNode() : nullptr;
				if (SourceNode && SourceNode != Node && NodeSet.Contains(SourceNode))
				{
					NodePredecessors.AddUnique(SourceNode);
				}
			}
		}
	}

	// Longest-path layering: relax layers until stable. Bounded by node
	// count so a cyclic subgraph (e.g. two nodes feeding each other through
	// a delay/event chain) can never cause an infinite loop.
	bool bChanged = true;
	int32 SafetyIterations = Nodes.Num() + 1;

	while (bChanged && SafetyIterations-- > 0)
	{
		bChanged = false;

		for (UEdGraphNode* Node : Nodes)
		{
			int32 MaxPredecessorLayer = -1;
			for (UEdGraphNode* Pred : Predecessors[Node])
			{
				MaxPredecessorLayer = FMath::Max(MaxPredecessorLayer, OutLayers[Pred]);
			}

			const int32 DesiredLayer = MaxPredecessorLayer + 1;
			if (DesiredLayer > OutLayers[Node])
			{
				OutLayers[Node] = DesiredLayer;
				bChanged = true;
			}
		}
	}
}

void FVesperGraphLayout::ApplyLayout(const TArray<UEdGraphNode*>& Nodes, const TMap<UEdGraphNode*, int32>& Layers,
	TMap<int32, TArray<TPair<float, float>>>& OutOccupiedRanges, float& OutOriginX, int32& OutMinLayer)
{
	OutOccupiedRanges.Reset();
	OutOriginX = 0.f;
	OutMinLayer = 0;

	if (Nodes.Num() == 0)
	{
		return;
	}

	TMap<int32, TArray<UEdGraphNode*>> NodesByLayer;
	int32 MinLayer = TNumericLimits<int32>::Max();
	float OriginX = TNumericLimits<float>::Max();
	float OriginY = TNumericLimits<float>::Max();

	for (UEdGraphNode* Node : Nodes)
	{
		const int32 Layer = Layers[Node];
		NodesByLayer.FindOrAdd(Layer).Add(Node);
		MinLayer = FMath::Min(MinLayer, Layer);

		// Anchor the new layout to the top-left of the original selection so
		// the whole graph doesn't jump to the origin every time it's used.
		OriginX = FMath::Min(OriginX, static_cast<float>(Node->NodePosX));
		OriginY = FMath::Min(OriginY, static_cast<float>(Node->NodePosY));
	}

	NodesByLayer.KeySort([](int32 A, int32 B) { return A < B; });

	for (TPair<int32, TArray<UEdGraphNode*>>& Pair : NodesByLayer)
	{
		TArray<UEdGraphNode*>& LayerNodes = Pair.Value;

		// Keep nodes within a layer roughly in their original top-to-bottom
		// order. This is a simple but effective heuristic for reducing wire
		// crossings without a full barycenter-crossing-minimization pass.
		LayerNodes.Sort([](const UEdGraphNode& A, const UEdGraphNode& B)
		{
			return A.NodePosY < B.NodePosY;
		});

		const float ColumnX = OriginX + static_cast<float>(Pair.Key - MinLayer) * VesperLayoutSettings::ColumnSpacing;
		float RunningY = OriginY;
		TArray<TPair<float, float>>& OccupiedInLayer = OutOccupiedRanges.FindOrAdd(Pair.Key);

		for (UEdGraphNode* Node : LayerNodes)
		{
			const float Height = EstimateNodeHeight(Node);

			Node->NodePosX = FMath::RoundToInt(ColumnX);
			Node->NodePosY = FMath::RoundToInt(RunningY);
			OccupiedInLayer.Add(TPair<float, float>(RunningY, RunningY + Height));

			RunningY += Height + VesperLayoutSettings::RowSpacing;
		}
	}

	OutOriginX = OriginX;
	OutMinLayer = MinLayer;
}

bool FVesperGraphLayout::TryGetSingleVariableConsumer(UEdGraphNode* Node, const TSet<UEdGraphNode*>& CandidateConsumers, UEdGraphNode*& OutConsumer, UEdGraphPin*& OutConsumerPin)
{
	OutConsumer = nullptr;
	OutConsumerPin = nullptr;

	// Only pure data taps (variable getters and BlueprintPure function
	// calls) are re-attached to their reader; anything else stays in the
	// normal exec-flow layering since it has exec pins and belongs wherever
	// the flow actually places it.
	if (!IsSplittableFanOutNode(Node))
	{
		return false;
	}

	for (UEdGraphPin* Pin : Node->Pins)
	{
		if (!Pin || Pin->Direction != EGPD_Output)
		{
			continue;
		}

		for (UEdGraphPin* LinkedPin : Pin->LinkedTo)
		{
			UEdGraphNode* TargetNode = LinkedPin ? LinkedPin->GetOwningNode() : nullptr;
			if (!TargetNode || !CandidateConsumers.Contains(TargetNode))
			{
				continue;
			}

			// A getter feeding more than one distinct node doesn't have a
			// single obvious "above/below" spot, so leave it in the normal
			// column layering rather than guessing.
			if (OutConsumer && OutConsumer != TargetNode)
			{
				OutConsumer = nullptr;
				OutConsumerPin = nullptr;
				return false;
			}
			OutConsumer = TargetNode;
			OutConsumerPin = LinkedPin;
		}
	}

	return OutConsumer != nullptr;
}

void FVesperGraphLayout::PlaceAttachedVariableNodes(const TMap<UEdGraphNode*, TArray<TPair<UEdGraphNode*, UEdGraphPin*>>>& AttachedByConsumer,
	const TMap<UEdGraphNode*, int32>& ConsumerLayers, TMap<int32, TArray<TPair<float, float>>>& OccupiedRanges,
	float OriginX, int32 MinLayer)
{
	// Finds the Y closest to DesiredTop where a node of the given Height can
	// sit without overlapping (within Spacing) anything already recorded for
	// that column, searching outward alternately above and below.
	auto FindFreeSlot = [](TArray<TPair<float, float>>& Occupied, float DesiredTop, float Height, float Spacing) -> float
	{
		auto Overlaps = [&](float Top)
		{
			const float Bottom = Top + Height;
			for (const TPair<float, float>& Range : Occupied)
			{
				if (Top < Range.Value + Spacing && Bottom + Spacing > Range.Key)
				{
					return true;
				}
			}
			return false;
		};

		if (!Overlaps(DesiredTop))
		{
			return DesiredTop;
		}

		const float Step = Height + Spacing;
		for (int32 i = 1; i <= 50; ++i)
		{
			const float Up = DesiredTop - Step * static_cast<float>(i);
			if (!Overlaps(Up))
			{
				return Up;
			}

			const float Down = DesiredTop + Step * static_cast<float>(i);
			if (!Overlaps(Down))
			{
				return Down;
			}
		}
		return DesiredTop;
	};

	for (const TPair<UEdGraphNode*, TArray<TPair<UEdGraphNode*, UEdGraphPin*>>>& Entry : AttachedByConsumer)
	{
		UEdGraphNode* Consumer = Entry.Key;
		const int32* ConsumerLayerPtr = ConsumerLayers.Find(Consumer);
		if (!ConsumerLayerPtr)
		{
			continue;
		}

		// One layer to the left of the consumer, same as where a genuine
		// data-flow predecessor would land, but instead of stacking every
		// variable node from every consumer into that shared column one
		// after another, each is pinned to sit right beside the specific
		// node it feeds.
		const int32 VarLayer = *ConsumerLayerPtr - 1;
		const float ColumnX = OriginX + static_cast<float>(VarLayer - MinLayer) * VesperLayoutSettings::ColumnSpacing;
		TArray<TPair<float, float>>& OccupiedInLayer = OccupiedRanges.FindOrAdd(VarLayer);

		const float ConsumerY = static_cast<float>(Consumer->NodePosY);

		for (const TPair<UEdGraphNode*, UEdGraphPin*>& VarEntry : Entry.Value)
		{
			UEdGraphNode* VarNode = VarEntry.Key;
			UEdGraphPin* ConsumerPin = VarEntry.Value;
			const float VarHeight = EstimateNodeHeight(VarNode);

			// Center the variable node on the exact row of the pin it feeds
			// rather than the consumer's overall vertical center, so it reads
			// as sitting right next to the connection point instead of just
			// floating somewhere near the node.
			const float PinCenterY = ConsumerY + EstimatePinYOffset(Consumer, ConsumerPin);
			const float DesiredTop = PinCenterY - VarHeight * 0.5f;

			const float FinalTop = FindFreeSlot(OccupiedInLayer, DesiredTop, VarHeight, VesperLayoutSettings::RowSpacing);

			VarNode->NodePosX = FMath::RoundToInt(ColumnX);
			VarNode->NodePosY = FMath::RoundToInt(FinalTop);
			OccupiedInLayer.Add(TPair<float, float>(FinalTop, FinalTop + VarHeight));
		}
	}
}

bool FVesperGraphLayout::IsSplittableFanOutNode(UEdGraphNode* Node)
{
	if (!Node)
	{
		return false;
	}

	// Only two classes of node are treated as safe, behavior-neutral taps to
	// duplicate: a plain variable read, and a pure (BlueprintPure) function
	// call. Both only ever expose data pins, so re-running the call through
	// a duplicate can never reorder or skip anything the exec flow depends
	// on -- unlike an impure function, which has to stay a single shared
	// node so it only executes once, in its one real place in the flow.
	const UK2Node_CallFunction* CallFunction = Cast<UK2Node_CallFunction>(Node);
	const bool bIsSupportedClass = Node->IsA<UK2Node_VariableGet>() || (CallFunction && CallFunction->IsNodePure());
	if (!bIsSupportedClass)
	{
		return false;
	}

	// A pure node should never have an exec pin, but this is checked
	// explicitly anyway -- duplicating a node with any exec wiring could
	// change execution order, which must never happen.
	for (const UEdGraphPin* Pin : Node->Pins)
	{
		if (Pin && Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
		{
			return false;
		}
	}

	return true;
}

UEdGraphNode* FVesperGraphLayout::DuplicateFanOutNode(UEdGraphNode* Original)
{
	if (!Original)
	{
		return nullptr;
	}

	UEdGraph* Graph = Original->GetGraph();
	if (!Graph)
	{
		return nullptr;
	}

	Graph->Modify();

	UEdGraphNode* NewNode = NewObject<UEdGraphNode>(Graph, Original->GetClass());
	if (UK2Node_VariableGet* NewGetter = Cast<UK2Node_VariableGet>(NewNode))
	{
		NewGetter->VariableReference = CastChecked<UK2Node_VariableGet>(Original)->VariableReference;
	}
	else if (UK2Node_CallFunction* NewCall = Cast<UK2Node_CallFunction>(NewNode))
	{
		NewCall->FunctionReference = CastChecked<UK2Node_CallFunction>(Original)->FunctionReference;
	}
	else
	{
		// Unsupported node class -- IsSplittableFanOutNode should have
		// already filtered this out, but bail rather than add a
		// half-initialized node to the graph.
		return nullptr;
	}

	NewNode->SetFlags(RF_Transactional);
	NewNode->NodePosX = Original->NodePosX;
	NewNode->NodePosY = Original->NodePosY;
	Graph->AddNode(NewNode, /*bFromUI=*/false, /*bSelectNewNode=*/false);
	NewNode->CreateNewGuid();
	NewNode->PostPlacedNewNode();
	NewNode->AllocateDefaultPins();

	// Replicate every input pin's wiring (and, for anything left unlinked,
	// its literal default) from Original onto the duplicate, matched by pin
	// name -- otherwise the duplicate would silently fall back to whatever
	// default the node ships with instead of reading the same upstream
	// value as Original (e.g. Get Owner's Target, Break Hit Result's
	// InHitResult), changing what the graph actually computes.
	for (UEdGraphPin* OriginalPin : Original->Pins)
	{
		if (!OriginalPin || OriginalPin->Direction != EGPD_Input)
		{
			continue;
		}

		UEdGraphPin* NewPin = NewNode->FindPin(OriginalPin->PinName, EGPD_Input);
		if (!NewPin)
		{
			continue;
		}

		if (OriginalPin->LinkedTo.Num() > 0)
		{
			for (UEdGraphPin* SourcePin : OriginalPin->LinkedTo)
			{
				if (SourcePin)
				{
					NewPin->MakeLinkTo(SourcePin);
				}
			}
		}
		else
		{
			NewPin->DefaultValue = OriginalPin->DefaultValue;
			NewPin->DefaultObject = OriginalPin->DefaultObject;
			NewPin->DefaultTextValue = OriginalPin->DefaultTextValue;
		}
	}

	return NewNode;
}

void FVesperGraphLayout::SplitFanOutNodes(TArray<UEdGraphNode*>& WorkingNodes)
{
	const TSet<UEdGraphNode*> NodeSet(WorkingNodes);

	// Snapshot the starting nodes since WorkingNodes grows as duplicates are
	// appended below.
	const TArray<UEdGraphNode*> OriginalNodes = WorkingNodes;

	for (UEdGraphNode* Node : OriginalNodes)
	{
		if (!IsSplittableFanOutNode(Node))
		{
			continue;
		}

		// A pure node can expose more than one output pin (e.g. Break Hit
		// Result), so each one is treated as its own independent fan-out --
		// a consumer reading pin A doesn't care how far away pin B's
		// readers are.
		for (UEdGraphPin* SourcePin : Node->Pins)
		{
			if (!SourcePin || SourcePin->Direction != EGPD_Output || SourcePin->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
			{
				continue;
			}

			// Distinct consumer pins this output feeds, restricted to nodes
			// that are actually part of this format pass.
			TArray<UEdGraphPin*> ConsumerPins;
			for (UEdGraphPin* LinkedPin : SourcePin->LinkedTo)
			{
				UEdGraphNode* ConsumerNode = LinkedPin ? LinkedPin->GetOwningNode() : nullptr;
				if (ConsumerNode && NodeSet.Contains(ConsumerNode))
				{
					ConsumerPins.Add(LinkedPin);
				}
			}

			if (ConsumerPins.Num() < 2)
			{
				// Nothing to fan out -- either unused, or the single-consumer case
				// TryGetSingleVariableConsumer already handles.
				continue;
			}

			const FVector2D OriginalPos(static_cast<float>(Node->NodePosX), static_cast<float>(Node->NodePosY));

			// Whichever consumer already sits closest to the original node always
			// keeps sharing it, no matter the distance -- otherwise a node whose
			// every consumer happens to be far away would end up with all of its
			// links peeled onto duplicates and nothing left attached to it,
			// stranding it as inert clutter in the graph.
			int32 ClosestIndex = 0;
			float ClosestDistSq = TNumericLimits<float>::Max();
			for (int32 Index = 0; Index < ConsumerPins.Num(); ++Index)
			{
				const UEdGraphNode* ConsumerNode = ConsumerPins[Index]->GetOwningNode();
				const FVector2D ConsumerPos(static_cast<float>(ConsumerNode->NodePosX), static_cast<float>(ConsumerNode->NodePosY));
				const float DistSq = FVector2D::DistSquared(OriginalPos, ConsumerPos);
				if (DistSq < ClosestDistSq)
				{
					ClosestDistSq = DistSq;
					ClosestIndex = Index;
				}
			}

			// Every other consumer within VariableSplitMaxDistance of the original
			// node also keeps sharing it -- splitting only pays off once the line
			// it would draw is actually long. Each remaining consumer farther away
			// gets peeled onto its own duplicate reading the same pin, so the
			// value read never changes and execution behavior is identical.
			for (int32 Index = 0; Index < ConsumerPins.Num(); ++Index)
			{
				if (Index == ClosestIndex)
				{
					continue;
				}

				UEdGraphPin* ConsumerPin = ConsumerPins[Index];
				UEdGraphNode* ConsumerNode = ConsumerPin->GetOwningNode();
				const FVector2D ConsumerPos(static_cast<float>(ConsumerNode->NodePosX), static_cast<float>(ConsumerNode->NodePosY));
				if (FVector2D::DistSquared(OriginalPos, ConsumerPos) <= FMath::Square(VesperLayoutSettings::VariableSplitMaxDistance))
				{
					continue;
				}

				UEdGraphNode* NewNode = DuplicateFanOutNode(Node);
				if (!NewNode)
				{
					continue;
				}

				UEdGraphPin* NewSourcePin = NewNode->FindPin(SourcePin->PinName, EGPD_Output);
				if (!NewSourcePin)
				{
					continue;
				}

				ConsumerPin->BreakLinkTo(SourcePin);
				ConsumerPin->MakeLinkTo(NewSourcePin);

				WorkingNodes.Add(NewNode);
			}
		}
	}
}

int32 FVesperGraphLayout::FormatNodes(const TArray<UEdGraphNode*>& Nodes)
{
	if (Nodes.Num() < 2)
	{
		return 0;
	}

	// Peel off dedicated duplicate pure nodes (variable getters and
	// BlueprintPure function calls) for consumers that sit far enough apart
	// that sharing one node would draw a long line across the graph -- see
	// SplitFanOutNodes for the distance rule and why this never changes
	// what the graph actually executes.
	TArray<UEdGraphNode*> WorkingNodes = Nodes;
	SplitFanOutNodes(WorkingNodes);

	// Split out variable-getter nodes that read into exactly one other
	// selected node -- those are placed directly beside their reader below
	// instead of being layered like normal flow nodes, which is what used to
	// dump every variable node into one shared far-left column.
	const TSet<UEdGraphNode*> ConsumerCandidates(WorkingNodes);
	TArray<UEdGraphNode*> PrimaryNodes;
	TMap<UEdGraphNode*, TArray<TPair<UEdGraphNode*, UEdGraphPin*>>> AttachedByConsumer;

	for (UEdGraphNode* Node : WorkingNodes)
	{
		UEdGraphNode* Consumer = nullptr;
		UEdGraphPin* ConsumerPin = nullptr;
		if (TryGetSingleVariableConsumer(Node, ConsumerCandidates, Consumer, ConsumerPin))
		{
			AttachedByConsumer.FindOrAdd(Consumer).Add(TPair<UEdGraphNode*, UEdGraphPin*>(Node, ConsumerPin));
		}
		else
		{
			PrimaryNodes.Add(Node);
		}
	}

	TMap<UEdGraphNode*, int32> Layers;
	ComputeLayers(PrimaryNodes, Layers);

	TMap<int32, TArray<TPair<float, float>>> OccupiedRanges;
	float OriginX = 0.f;
	int32 MinLayer = 0;
	ApplyLayout(PrimaryNodes, Layers, OccupiedRanges, OriginX, MinLayer);
	PlaceAttachedVariableNodes(AttachedByConsumer, Layers, OccupiedRanges, OriginX, MinLayer);

	return WorkingNodes.Num();
}

void FVesperGraphLayout::FormatSelectedNodes()
{
	const TSharedPtr<SGraphEditor> CurrentGraphEditor = GetActiveGraphEditor();

	FGraphPanelSelectionSet SelectedNodes;
	if (CurrentGraphEditor.IsValid())
	{
		SelectedNodes = CurrentGraphEditor->GetSelectedNodes();
	}

	TArray<UEdGraphNode*> ValidNodes;
	for (UObject* Obj : SelectedNodes)
	{
		if (UEdGraphNode* GraphNode = Cast<UEdGraphNode>(Obj))
		{
			ValidNodes.Add(GraphNode);
		}
	}

	if (ValidNodes.Num() < 2)
	{
		FNotificationInfo Info(FText::FromString(FString::Printf(
			TEXT("Vesper: Select at least 2 nodes to format. (Detected: %d)"), ValidNodes.Num())));
		Info.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return;
	}

	const FScopedTransaction Transaction(FText::FromString(TEXT("Vesper: Format Selected Nodes")));

	for (UEdGraphNode* Node : ValidNodes)
	{
		Node->Modify();
	}

	const int32 FormattedCount = FormatNodes(ValidNodes);

	if (CurrentGraphEditor.IsValid())
	{
		CurrentGraphEditor->NotifyGraphChanged();
	}

	FNotificationInfo SuccessInfo(FText::FromString(FString::Printf(
		TEXT("Vesper: %d nodes formatted successfully!"), FormattedCount)));
	SuccessInfo.ExpireDuration = 2.5f;
	FSlateNotificationManager::Get().AddNotification(SuccessInfo);
}

void FVesperGraphLayout::AutoFitSelectedComments()
{
	const TSharedPtr<SGraphEditor> CurrentGraphEditor = GetActiveGraphEditor();

	FGraphPanelSelectionSet SelectedNodes;
	if (CurrentGraphEditor.IsValid())
	{
		SelectedNodes = CurrentGraphEditor->GetSelectedNodes();
	}

	TArray<UEdGraphNode_Comment*> CommentNodes;
	for (UObject* Obj : SelectedNodes)
	{
		if (UEdGraphNode_Comment* CommentNode = Cast<UEdGraphNode_Comment>(Obj))
		{
			CommentNodes.Add(CommentNode);
		}
	}

	if (CommentNodes.Num() == 0)
	{
		FNotificationInfo Info(FText::FromString(TEXT("Vesper: Select at least 1 Comment box to resize.")));
		Info.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return;
	}

	const FScopedTransaction Transaction(FText::FromString(TEXT("Vesper: Auto-Fit Comments")));
	int32 ResizedCount = 0;

	for (UEdGraphNode_Comment* CommentNode : CommentNodes)
	{
		// GetNodesUnderComment() returns whatever currently falls inside the
		// comment's existing bounds, so this fits to what's visually inside
		// it right now rather than requiring a separate "assign" step.
		const TArray<UObject*> ContainedNodes = CommentNode->GetNodesUnderComment();
		if (ContainedNodes.Num() == 0)
		{
			continue;
		}

		float MinX = TNumericLimits<float>::Max();
		float MinY = TNumericLimits<float>::Max();
		float MaxX = TNumericLimits<float>::Lowest();
		float MaxY = TNumericLimits<float>::Lowest();
		bool bFoundValidBounds = false;

		for (UObject* Obj : ContainedNodes)
		{
			UEdGraphNode* ChildNode = Cast<UEdGraphNode>(Obj);
			if (!ChildNode || ChildNode == CommentNode)
			{
				continue;
			}

			// Comment nodes track their own resizable width/height; regular
			// K2 nodes generally don't persist a pixel size in the data
			// model, so we fall back to the same pin-based estimate used by
			// the layout pass above.
			const float ChildWidth = ChildNode->NodeWidth > 0.f ? ChildNode->NodeWidth : 200.f;
			const float ChildHeight = ChildNode->NodeHeight > 0.f ? ChildNode->NodeHeight : EstimateNodeHeight(ChildNode);

			MinX = FMath::Min(MinX, static_cast<float>(ChildNode->NodePosX));
			MinY = FMath::Min(MinY, static_cast<float>(ChildNode->NodePosY));
			MaxX = FMath::Max(MaxX, static_cast<float>(ChildNode->NodePosX) + ChildWidth);
			MaxY = FMath::Max(MaxY, static_cast<float>(ChildNode->NodePosY) + ChildHeight);
			bFoundValidBounds = true;
		}

		if (!bFoundValidBounds)
		{
			continue;
		}

		CommentNode->Modify();
		CommentNode->NodePosX = FMath::RoundToInt(MinX - VesperLayoutSettings::CommentPadding);
		CommentNode->NodePosY = FMath::RoundToInt(MinY - VesperLayoutSettings::CommentPadding - VesperLayoutSettings::CommentTitleBarHeight);
		CommentNode->NodeWidth = FMath::RoundToInt((MaxX - MinX) + VesperLayoutSettings::CommentPadding * 2.f);
		CommentNode->NodeHeight = FMath::RoundToInt((MaxY - MinY) + VesperLayoutSettings::CommentPadding * 2.f + VesperLayoutSettings::CommentTitleBarHeight);

		++ResizedCount;
	}

	if (CurrentGraphEditor.IsValid())
	{
		CurrentGraphEditor->NotifyGraphChanged();
	}

	if (ResizedCount == 0)
	{
		FNotificationInfo EmptyInfo(FText::FromString(TEXT("Vesper: Selected comment box(es) contain no nodes to fit.")));
		EmptyInfo.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(EmptyInfo);
		return;
	}

	FNotificationInfo SuccessInfo(FText::FromString(FString::Printf(
		TEXT("Vesper: %d comment box(es) resized."), ResizedCount)));
	SuccessInfo.ExpireDuration = 2.5f;
	FSlateNotificationManager::Get().AddNotification(SuccessInfo);
}
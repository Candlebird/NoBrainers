// Copyright Vesper System, 2026. All Rights Reserved.

#include "VesperGraphLayout.h"
#include "Editor.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraphNode_Comment.h"
#include "EdGraphSchema_K2.h"
#include "K2Node.h"
#include "K2Node_VariableGet.h"
#include "K2Node_CallFunction.h"
#include "K2Node_Event.h"
#include "K2Node_CustomEvent.h"
#include "K2Node_FunctionEntry.h"
#include "K2Node_Knot.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "GraphEditor.h"
#include "SGraphPanel.h"
#include "SGraphNode.h"
#include "SGraphPin.h"
#include "Layout/WidgetPath.h"
#include "Layout/SlateRect.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Notifications/NotificationManager.h"
#include "Widgets/Notifications/SNotificationList.h"
#include "Widgets/SWindow.h"
#include "Input/Events.h"
#include "Misc/ConfigCacheIni.h"
#include "ScopedTransaction.h"

DEFINE_LOG_CATEGORY_STATIC(LogVesperLayout, Log, All);

namespace
{
	// The last Graph Editor widget observed to hold keyboard focus, kept as a
	// fallback for GetActiveGraphEditor(). Weak so a closed editor tab is
	// never kept alive by this cache.
	TWeakPtr<SGraphEditor> GLastKnownGraphEditor;
	FDelegateHandle GFocusChangingHandle;

	// SGraphEditor is a thin wrapper. The widget doing the real work is the
	// private SGraphEditorImpl subclass. Match both names exactly: a substring
	// match on "GraphEditor" also hits unrelated widgets (action menus,
	// minimaps) and static-casting those to SGraphEditor would crash.
	bool IsGraphEditorWidget(const SWidget& Widget)
	{
		static const FName GraphEditorType(TEXT("SGraphEditor"));
		static const FName GraphEditorImplType(TEXT("SGraphEditorImpl"));
		const FName Type = Widget.GetType();
		return Type == GraphEditorType || Type == GraphEditorImplType;
	}

	TSharedPtr<SGraphEditor> FindGraphEditorInPath(const FWidgetPath& Path)
	{
		for (int32 i = Path.Widgets.Num() - 1; i >= 0; --i)
		{
			const TSharedRef<SWidget>& Widget = Path.Widgets[i].Widget;
			if (IsGraphEditorWidget(*Widget))
			{
				return StaticCastSharedRef<SGraphEditor>(Widget);
			}
		}
		return nullptr;
	}

	// Depth-first search of a widget tree for a graph editor showing Graph.
	TSharedPtr<SGraphEditor> FindGraphEditorInTree(const TSharedRef<SWidget>& Widget, const UEdGraph* Graph, int32 Depth)
	{
		if (IsGraphEditorWidget(*Widget))
		{
			TSharedRef<SGraphEditor> Editor = StaticCastSharedRef<SGraphEditor>(Widget);
			if (Editor->GetCurrentGraph() == Graph)
			{
				return Editor;
			}
		}
		if (Depth > 256)
		{
			return nullptr;
		}
		if (FChildren* Children = Widget->GetChildren())
		{
			for (int32 i = 0; i < Children->Num(); ++i)
			{
				if (TSharedPtr<SGraphEditor> Found = FindGraphEditorInTree(Children->GetChildAt(i), Graph, Depth + 1))
				{
					return Found;
				}
			}
		}
		return nullptr;
	}

	// Finds the live graph panel for Graph so real node sizes can be measured.
	// Returns null when the graph isn't open in any visible editor tab.
	SGraphPanel* FindPanelForGraph(const UEdGraph* Graph)
	{
		if (!Graph || !FSlateApplication::IsInitialized())
		{
			return nullptr;
		}
		if (const TSharedPtr<SGraphEditor> Last = GLastKnownGraphEditor.Pin())
		{
			if (Last->GetCurrentGraph() == Graph)
			{
				return Last->GetGraphPanel();
			}
		}
		TArray<TSharedRef<SWindow>> Windows;
		FSlateApplication::Get().GetAllVisibleWindowsOrdered(Windows);
		for (const TSharedRef<SWindow>& Window : Windows)
		{
			if (const TSharedPtr<SGraphEditor> Found = FindGraphEditorInTree(Window, Graph, 0))
			{
				return Found->GetGraphPanel();
			}
		}
		return nullptr;
	}

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

namespace VesperLayout
{
	// Generated comment boxes get this value in NodeGuid.A so a later run can
	// find and regenerate them without touching user-authored comments.
	static constexpr uint32 GeneratedCommentTag = 0x5E5BE800;
	static const TCHAR* ConfigSection = TEXT("VesperNodeCleaner");

	// All spacing values are graph units (pixels at 1:1 zoom). Every field can
	// be overridden in DefaultEditor.ini under [VesperNodeCleaner] using the
	// exact field name (e.g. ExecGap=60, bGenerateComments=False,
	// SingleColor=(R=0.1,G=0.28,B=0.5,A=1)).
	struct FSettings
	{
		float ExecGap = 50.f;             // horizontal gap between exec nodes (feeder columns are added on top)
		float DataGap = 32.f;             // horizontal gap between a data feeder and the node it feeds
		float StackGap = 14.f;            // vertical gap between stacked feeders of the same node
		float BranchRowGap = 36.f;        // vertical gap between exec branch rows
		float ExecLaneClearance = 8.f;    // feeders stay this far below the consumer's exec wire
		float AboveTolerance = 12.f;      // how far a straight first feeder may rise above a pure consumer's top
		float BlockGap = 100.f;           // vertical gap between function blocks / groups
		float GroupInnerGap = 40.f;       // vertical gap between blocks inside one group
		float CommentPadding = 28.f;      // padding between comment edge and its contents
		int32 CommentFontSize = 18;
		int32 InnerCommentFontSize = 14;
		bool bGenerateComments = true;    // wrap each block / group in a titled comment
		bool bInnerGroupComments = true;  // also give each block inside a group its own comment
		bool bGroupSimilar = true;        // group similar blocks
		bool bDuplicateSharedGetters = true; // give each exec consumer its own copy of a shared self-variable getter
		FLinearColor SingleColor = FLinearColor(0.10f, 0.28f, 0.50f);
		FLinearColor GroupColor = FLinearColor(0.38f, 0.20f, 0.52f);
		FLinearColor InnerColor = FLinearColor(0.16f, 0.16f, 0.18f);
		FLinearColor LooseColor = FLinearColor(0.30f, 0.30f, 0.30f);

		static FSettings Load()
		{
			FSettings S;
			if (!GConfig)
			{
				return S;
			}
			auto F = [](const TCHAR* Key, float& Value) { GConfig->GetFloat(ConfigSection, Key, Value, GEditorIni); };
			auto I = [](const TCHAR* Key, int32& Value) { GConfig->GetInt(ConfigSection, Key, Value, GEditorIni); };
			auto B = [](const TCHAR* Key, bool& Value) { GConfig->GetBool(ConfigSection, Key, Value, GEditorIni); };
			auto C = [](const TCHAR* Key, FLinearColor& Value)
			{
				FString Str;
				FLinearColor Parsed;
				if (GConfig->GetString(ConfigSection, Key, Str, GEditorIni) && Parsed.InitFromString(Str))
				{
					Value = Parsed;
				}
			};
			F(TEXT("ExecGap"), S.ExecGap);
			F(TEXT("DataGap"), S.DataGap);
			F(TEXT("StackGap"), S.StackGap);
			F(TEXT("BranchRowGap"), S.BranchRowGap);
			F(TEXT("ExecLaneClearance"), S.ExecLaneClearance);
			F(TEXT("AboveTolerance"), S.AboveTolerance);
			F(TEXT("BlockGap"), S.BlockGap);
			F(TEXT("GroupInnerGap"), S.GroupInnerGap);
			F(TEXT("CommentPadding"), S.CommentPadding);
			I(TEXT("CommentFontSize"), S.CommentFontSize);
			I(TEXT("InnerCommentFontSize"), S.InnerCommentFontSize);
			B(TEXT("bGenerateComments"), S.bGenerateComments);
			B(TEXT("bInnerGroupComments"), S.bInnerGroupComments);
			B(TEXT("bGroupSimilar"), S.bGroupSimilar);
			B(TEXT("bDuplicateSharedGetters"), S.bDuplicateSharedGetters);
			C(TEXT("SingleColor"), S.SingleColor);
			C(TEXT("GroupColor"), S.GroupColor);
			C(TEXT("InnerColor"), S.InnerColor);
			C(TEXT("LooseColor"), S.LooseColor);
			return S;
		}
	};

	float CommentTitleHeight(int32 FontSize)
	{
		return FontSize * 1.5f + 14.f;
	}

	bool IsGeneratedComment(const UEdGraphNode* Node)
	{
		return Node && Node->IsA<UEdGraphNode_Comment>() && Node->NodeGuid.A == GeneratedCommentTag;
	}

	bool HasExecPin(const UEdGraphNode* Node)
	{
		for (const UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin && !Pin->bHidden && Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
			{
				return true;
			}
		}
		return false;
	}

	bool IsPinVisible(const UEdGraphNode* Node, const UEdGraphPin* Pin)
	{
		if (!Pin || Pin->bHidden)
		{
			return false;
		}
		return !(Pin->bAdvancedView && Node->AdvancedPinDisplay == ENodeAdvancedPins::Hidden);
	}

	// The event delegate pin draws in the title bar, not as its own pin row.
	bool IsHeaderPin(const UEdGraphNode* Node, const UEdGraphPin* Pin)
	{
		return Pin->Direction == EGPD_Output && Node->IsA<UK2Node_Event>() && Pin->PinName == UK2Node_Event::DelegateOutputName;
	}

	FString FirstLine(const FString& Text)
	{
		int32 Index;
		return Text.FindChar(TEXT('\n'), Index) ? Text.Left(Index) : Text;
	}

	// ---------------------------------------------------------------------
	// Node metrics: measured from the live graph panel when one is open,
	// otherwise estimated from pins and titles.
	// ---------------------------------------------------------------------
	struct FMetrics
	{
		SGraphPanel* Panel = nullptr;
		TMap<const UEdGraphNode*, FVector2D> SizeCache;

		enum class EShape : uint8 { Normal, Compact, Variable, Knot };

		static EShape GetShape(const UEdGraphNode* Node)
		{
			if (Node->IsA<UK2Node_Knot>())
			{
				return EShape::Knot;
			}
			if (Node->IsA<UK2Node_VariableGet>() && !HasExecPin(Node))
			{
				return EShape::Variable;
			}
			if (const UK2Node* K2 = Cast<UK2Node>(Node))
			{
				if (K2->ShouldDrawCompact())
				{
					return EShape::Compact;
				}
			}
			return EShape::Normal;
		}

		TSharedPtr<SGraphNode> Widget(const UEdGraphNode* Node) const
		{
			return Panel ? Panel->GetNodeWidgetFromGuid(Node->NodeGuid) : nullptr;
		}

		FVector2D Size(const UEdGraphNode* Node)
		{
			if (const FVector2D* Cached = SizeCache.Find(Node))
			{
				return *Cached;
			}
			FVector2D Result = FVector2D::ZeroVector;
			if (const TSharedPtr<SGraphNode> NodeWidget = Widget(Node))
			{
				const FVector2D Desired = NodeWidget->GetDesiredSize();
				if (Desired.X > 4.f && Desired.Y > 4.f)
				{
					Result = Desired;
				}
			}
			if (Result.IsZero())
			{
				Result = EstimateSize(Node);
			}
			SizeCache.Add(Node, Result);
			return Result;
		}

		// Vertical distance from the node's top edge to the pin's center.
		float PinOffset(const UEdGraphNode* Node, const UEdGraphPin* Pin)
		{
			if (!Pin)
			{
				return Size(Node).Y * 0.5f;
			}
			if (const TSharedPtr<SGraphNode> NodeWidget = Widget(Node))
			{
				if (const TSharedPtr<SGraphPin> PinWidget = NodeWidget->FindWidgetForPin(const_cast<UEdGraphPin*>(Pin)))
				{
					const FVector2D Offset = PinWidget->GetNodeOffset();
					if (Offset.Y > 0.f && Offset.Y <= Size(Node).Y + 1.f)
					{
						return Offset.Y;
					}
				}
			}
			return EstimatePinOffset(Node, Pin);
		}

		static float TextWidth(const FString& Text, float CharWidth)
		{
			return Text.Len() * CharWidth;
		}

		static bool ShowsDefaultValueBox(const UEdGraphPin* Pin)
		{
			if (Pin->Direction != EGPD_Input || Pin->LinkedTo.Num() > 0)
			{
				return false;
			}
			const FName Category = Pin->PinType.PinCategory;
			return Category != UEdGraphSchema_K2::PC_Exec && Category != UEdGraphSchema_K2::PC_Object
				&& Category != UEdGraphSchema_K2::PC_Interface && Category != UEdGraphSchema_K2::PC_Wildcard
				&& Category != UEdGraphSchema_K2::PC_Delegate && !Pin->PinType.IsContainer()
				&& Pin->PinName != UEdGraphSchema_K2::PN_Self;
		}

		static float DefaultValueBoxWidth(const UEdGraphPin* Pin)
		{
			const FName Category = Pin->PinType.PinCategory;
			if (Category == UEdGraphSchema_K2::PC_Boolean)
			{
				return 24.f;
			}
			if (Category == UEdGraphSchema_K2::PC_Struct)
			{
				return 150.f; // vectors / rotators show three fields
			}
			if (Category == UEdGraphSchema_K2::PC_String || Category == UEdGraphSchema_K2::PC_Text || Category == UEdGraphSchema_K2::PC_Name)
			{
				return FMath::Clamp(Pin->DefaultValue.Len() * 7.f + 30.f, 60.f, 220.f);
			}
			return 56.f;
		}

		static void CollectRows(const UEdGraphNode* Node, TArray<const UEdGraphPin*>& Inputs, TArray<const UEdGraphPin*>& Outputs)
		{
			for (const UEdGraphPin* Pin : Node->Pins)
			{
				if (!IsPinVisible(Node, Pin) || IsHeaderPin(Node, Pin))
				{
					continue;
				}
				(Pin->Direction == EGPD_Input ? Inputs : Outputs).Add(Pin);
			}
		}

		static constexpr float RowHeight = 24.f;
		static constexpr float HeaderHeight = 34.f;
		static constexpr float ExtraTitleLine = 14.f;
		static constexpr float CompactTopPad = 8.f;
		static constexpr float VariableTopPad = 4.f;

		static float NormalHeaderHeight(const UEdGraphNode* Node)
		{
			TArray<FString> Lines;
			Node->GetNodeTitle(ENodeTitleType::FullTitle).ToString().ParseIntoArrayLines(Lines);
			return HeaderHeight + ExtraTitleLine * FMath::Max(0, Lines.Num() - 1);
		}

		static FVector2D EstimateSize(const UEdGraphNode* Node)
		{
			TArray<const UEdGraphPin*> Inputs, Outputs;
			CollectRows(Node, Inputs, Outputs);
			const int32 Rows = FMath::Max(Inputs.Num(), Outputs.Num());

			float RowWidth = 0.f;
			for (int32 Row = 0; Row < Rows; ++Row)
			{
				float InWidth = 0.f, OutWidth = 0.f;
				if (Inputs.IsValidIndex(Row))
				{
					const UEdGraphPin* Pin = Inputs[Row];
					InWidth = 28.f + TextWidth(Pin->GetDisplayName().ToString(), 7.f) + (ShowsDefaultValueBox(Pin) ? DefaultValueBoxWidth(Pin) : 0.f);
				}
				if (Outputs.IsValidIndex(Row))
				{
					OutWidth = 28.f + TextWidth(Outputs[Row]->GetDisplayName().ToString(), 7.f);
				}
				RowWidth = FMath::Max(RowWidth, InWidth + OutWidth + 16.f);
			}

			switch (GetShape(Node))
			{
			case EShape::Knot:
				return FVector2D(42.f, 16.f);
			case EShape::Variable:
			{
				const UK2Node_VariableGet* Getter = CastChecked<UK2Node_VariableGet>(Node);
				const float Width = 48.f + TextWidth(FName::NameToDisplayString(Getter->GetVarNameString(), false), 7.f);
				return FVector2D(FMath::Max(Width, RowWidth), VariableTopPad * 2.f + FMath::Max(1, Rows) * RowHeight);
			}
			case EShape::Compact:
			{
				const FString Title = FirstLine(Node->GetNodeTitle(ENodeTitleType::FullTitle).ToString());
				const float Width = FMath::Max(70.f, 40.f + TextWidth(Title, 12.f)) + RowWidth * 0.6f;
				return FVector2D(Width, CompactTopPad * 2.f + FMath::Max(1, Rows) * RowHeight);
			}
			default:
			{
				TArray<FString> Lines;
				Node->GetNodeTitle(ENodeTitleType::FullTitle).ToString().ParseIntoArrayLines(Lines);
				float TitleWidth = 0.f;
				for (const FString& Line : Lines)
				{
					TitleWidth = FMath::Max(TitleWidth, TextWidth(Line, 7.5f));
				}
				const float Width = FMath::Max3(120.f, TitleWidth + 64.f, RowWidth);
				float Height = NormalHeaderHeight(Node) + Rows * RowHeight + 10.f;
				if (Node->AdvancedPinDisplay != ENodeAdvancedPins::NoPins)
				{
					Height += 22.f;
				}
				return FVector2D(Width, Height);
			}
			}
		}

		static float EstimatePinOffset(const UEdGraphNode* Node, const UEdGraphPin* Pin)
		{
			if (IsHeaderPin(Node, Pin))
			{
				return 16.f;
			}
			TArray<const UEdGraphPin*> Inputs, Outputs;
			CollectRows(Node, Inputs, Outputs);
			const TArray<const UEdGraphPin*>& Column = Pin->Direction == EGPD_Input ? Inputs : Outputs;
			const int32 Row = FMath::Max(0, Column.IndexOfByKey(Pin));

			switch (GetShape(Node))
			{
			case EShape::Knot:
				return 8.f;
			case EShape::Variable:
				return VariableTopPad + Row * RowHeight + RowHeight * 0.5f;
			case EShape::Compact:
				return CompactTopPad + Row * RowHeight + RowHeight * 0.5f;
			default:
				return NormalHeaderHeight(Node) + Row * RowHeight + RowHeight * 0.5f;
			}
		}
	};

	// ---------------------------------------------------------------------
	// Layout data
	// ---------------------------------------------------------------------

	// A data wire used as a tree edge: Child feeds Parent through ParentIn.
	struct FFeedLink
	{
		UEdGraphNode* Child = nullptr;
		UEdGraphPin* ChildOut = nullptr;
		UEdGraphPin* ParentIn = nullptr;
		UEdGraphNode* Parent = nullptr;
		int32 ParentPinIndex = 0;
	};

	// Positions and occupied rectangles for a (partial) layout.
	struct FLayoutCtx
	{
		TMap<UEdGraphNode*, FVector2D> Pos;
		TArray<FBox2D> Rects;

		FBox2D Bounds() const
		{
			FBox2D Result(ForceInit);
			for (const FBox2D& Rect : Rects)
			{
				Result += Rect;
			}
			return Result;
		}

		void MergeFrom(const FLayoutCtx& Other, const FVector2D& Delta)
		{
			for (const TPair<UEdGraphNode*, FVector2D>& Pair : Other.Pos)
			{
				Pos.Add(Pair.Key, Pair.Value + Delta);
			}
			for (const FBox2D& Rect : Other.Rects)
			{
				Rects.Add(Rect.ShiftBy(Delta));
			}
		}
	};

	struct FBlock
	{
		TArray<UEdGraphNode*> Roots;     // exec roots, or data sinks for data-only blocks
		TArray<UEdGraphNode*> ExecNodes;
		TArray<UEdGraphNode*> Members;   // every node owned by the block
		bool bDataOnly = false;
		bool bLoose = false;
		float OrigMinY = 0.f;
		FString Title;
		FString GroupKey;
		FString GroupTitle;
		TSet<FName> MemberRefs;
		FLayoutCtx Layout;
		UEdGraphNode_Comment* Adopted = nullptr;
	};

	struct FUserComment
	{
		UEdGraphNode_Comment* Comment = nullptr;
		TArray<UEdGraphNode*> Contained;
	};

	// ---------------------------------------------------------------------
	// The layout engine. One instance per format call.
	// ---------------------------------------------------------------------
	class FEngine
	{
	public:
		FEngine(UEdGraph* InGraph, SGraphPanel* Panel)
			: Graph(InGraph)
			, S(FSettings::Load())
		{
			M.Panel = Panel;

			// Function and macro graphs are already named by the graph itself,
			// so a wrapping comment adds nothing. Previously generated comments
			// are still deleted by CollectComments, and user comments are kept.
			if (const UEdGraphSchema* Schema = Graph ? Graph->GetSchema() : nullptr)
			{
				const EGraphType Type = Schema->GetGraphType(Graph);
				if (Type == GT_Function || Type == GT_Macro)
				{
					S.bGenerateComments = false;
				}
			}
		}

		int32 Run(const TArray<UEdGraphNode*>& InNodes);

	private:
		UEdGraph* Graph;
		FSettings S;
		FMetrics M;

		TArray<UEdGraphNode*> LayoutNodes;
		TSet<UEdGraphNode*> NodeSet;
		FVector2D Anchor = FVector2D::ZeroVector;
		TArray<FUserComment> UserComments;

		TArray<FBlock> Blocks;
		TMap<UEdGraphNode*, int32> BlockOf;
		TMap<UEdGraphNode*, int32> ExecOrder;
		TMap<UEdGraphNode*, FFeedLink> ParentLink;
		TMap<UEdGraphNode*, TArray<FFeedLink>> Children;
		TMap<UEdGraphNode*, float> FeederWidthCache;
		TSet<UEdGraphNode*> Visited;

		static constexpr int32 NoOwner = MAX_int32;

		bool IsExec(const UEdGraphNode* Node) const { return HasExecPin(Node); }
		FVector2D OrigPos(const UEdGraphNode* Node) const { return FVector2D(Node->NodePosX, Node->NodePosY); }

		void CollectComments(const TArray<UEdGraphNode*>& InNodes);
		void BuildExecBlocks();
		void ResolveOwners();
		int32 ResolvePure(UEdGraphNode* Node, TSet<UEdGraphNode*>& InProgress, TMap<UEdGraphNode*, int32>& OwnerKey);
		UEdGraphNode* OwnerExec(UEdGraphNode* Node) const;
		bool DuplicateSharedGetters();
		void BuildDataOnlyBlocks();

		void Place(UEdGraphNode* Node, const FVector2D& Pos, FLayoutCtx& Ctx);
		float Drop(FLayoutCtx& Sub, FLayoutCtx& Ctx, float MinDy, float GapY);
		float FeederWidth(UEdGraphNode* Node);
		void LayoutExec(UEdGraphNode* Node, const UEdGraphPin* EnterPin, float X, float PinY, FLayoutCtx& Ctx);
		void LayoutFeedersOf(UEdGraphNode* Node, FLayoutCtx& Ctx);
		void LayoutFeederTree(UEdGraphNode* Node, const FVector2D& Pos, FLayoutCtx& Ctx);
		void LayoutBlock(FBlock& Block);

		void DescribeBlocks();
		void PlaceBlocksAndComments();
		void ApplyBlock(const FBlock& Block, const FVector2D& Offset);
		UEdGraphNode_Comment* MakeOrFitComment(UEdGraphNode_Comment* Existing, const FBox2D& Rect, const FString& Title,
			const FLinearColor& Color, int32 FontSize, int32 Depth);
		void RefitUserComments();
	};

	int32 FEngine::Run(const TArray<UEdGraphNode*>& InNodes)
	{
		for (UEdGraphNode* Node : InNodes)
		{
			if (Node && !Node->IsA<UEdGraphNode_Comment>() && Node->GetGraph() == Graph)
			{
				LayoutNodes.Add(Node);
			}
		}
		if (LayoutNodes.Num() < 2)
		{
			return 0;
		}
		NodeSet = TSet<UEdGraphNode*>(LayoutNodes);

		Anchor = FVector2D(TNumericLimits<float>::Max(), TNumericLimits<float>::Max());
		for (UEdGraphNode* Node : LayoutNodes)
		{
			Anchor.X = FMath::Min(Anchor.X, static_cast<float>(Node->NodePosX));
			Anchor.Y = FMath::Min(Anchor.Y, static_cast<float>(Node->NodePosY));
		}

		CollectComments(InNodes);
		BuildExecBlocks();
		ResolveOwners();
		if (S.bDuplicateSharedGetters && DuplicateSharedGetters())
		{
			ResolveOwners();
		}
		BuildDataOnlyBlocks();

		for (FBlock& Block : Blocks)
		{
			LayoutBlock(Block);
		}

		// Safety net: anything the tree walk never reached (e.g. pure nodes in
		// a data cycle) goes into one loose block laid out in a row.
		TArray<UEdGraphNode*> Unplaced;
		for (UEdGraphNode* Node : LayoutNodes)
		{
			if (!Visited.Contains(Node))
			{
				Unplaced.Add(Node);
			}
		}
		if (Unplaced.Num() > 0)
		{
			FBlock& Leftover = Blocks.AddDefaulted_GetRef();
			Leftover.bDataOnly = true;
			Leftover.bLoose = true;
			Leftover.Members = Unplaced;
			Leftover.Roots = Unplaced;
			Leftover.OrigMinY = TNumericLimits<float>::Max();
			float X = 0.f;
			for (UEdGraphNode* Node : Unplaced)
			{
				Visited.Add(Node);
				Place(Node, FVector2D(X, 0.f), Leftover.Layout);
				X += M.Size(Node).X + S.DataGap;
			}
		}

		DescribeBlocks();
		PlaceBlocksAndComments();
		RefitUserComments();

		if (UBlueprint* Blueprint = FBlueprintEditorUtils::FindBlueprintForGraph(Graph))
		{
			FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);
		}
		return LayoutNodes.Num();
	}

	// Sorts out comments before anything moves: generated comments touching
	// this layout are deleted (they get regenerated), user comments remember
	// which nodes they currently wrap so they can be refit afterwards.
	void FEngine::CollectComments(const TArray<UEdGraphNode*>& InNodes)
	{
		const TSet<UEdGraphNode*> InputSet(InNodes);
		TArray<UEdGraphNode_Comment*> ToDelete;

		for (UEdGraphNode* Node : Graph->Nodes)
		{
			UEdGraphNode_Comment* Comment = Cast<UEdGraphNode_Comment>(Node);
			if (!Comment)
			{
				continue;
			}
			const FBox2D CommentRect(FVector2D(Comment->NodePosX, Comment->NodePosY),
				FVector2D(Comment->NodePosX + Comment->NodeWidth, Comment->NodePosY + Comment->NodeHeight));

			TArray<UEdGraphNode*> Contained;
			for (UEdGraphNode* Candidate : LayoutNodes)
			{
				const FVector2D Center = OrigPos(Candidate) + M.Size(Candidate) * 0.5f;
				if (CommentRect.IsInside(Center))
				{
					Contained.Add(Candidate);
				}
			}

			const bool bRelevant = InputSet.Contains(Comment) || Contained.Num() > 0;
			if (!bRelevant)
			{
				continue;
			}
			if (IsGeneratedComment(Comment))
			{
				ToDelete.Add(Comment);
			}
			else if (Contained.Num() > 0)
			{
				UserComments.Add({ Comment, MoveTemp(Contained) });
			}
		}

		if (ToDelete.Num() > 0)
		{
			Graph->Modify();
			for (UEdGraphNode_Comment* Comment : ToDelete)
			{
				Comment->Modify();
				Graph->RemoveNode(Comment);
			}
		}
	}

	// Exec blocks = connected components of exec wires. Exec order is a DFS in
	// pin order from each block's roots, used to decide which exec node owns
	// a shared pure node.
	void FEngine::BuildExecBlocks()
	{
		TArray<UEdGraphNode*> ExecNodes;
		for (UEdGraphNode* Node : LayoutNodes)
		{
			if (IsExec(Node))
			{
				ExecNodes.Add(Node);
			}
		}

		TMap<UEdGraphNode*, UEdGraphNode*> UnionParent;
		for (UEdGraphNode* Node : ExecNodes)
		{
			UnionParent.Add(Node, Node);
		}
		auto Find = [&UnionParent](UEdGraphNode* Node)
		{
			while (UnionParent[Node] != Node)
			{
				UnionParent[Node] = UnionParent[UnionParent[Node]];
				Node = UnionParent[Node];
			}
			return Node;
		};

		TMap<UEdGraphNode*, bool> HasExecInputInSet;
		for (UEdGraphNode* Node : ExecNodes)
		{
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (!Pin || Pin->Direction != EGPD_Output || Pin->PinType.PinCategory != UEdGraphSchema_K2::PC_Exec)
				{
					continue;
				}
				for (UEdGraphPin* Linked : Pin->LinkedTo)
				{
					UEdGraphNode* Target = Linked ? Linked->GetOwningNode() : nullptr;
					if (Target && Target != Node && UnionParent.Contains(Target))
					{
						UnionParent[Find(Node)] = Find(Target);
						HasExecInputInSet.Add(Target, true);
					}
				}
			}
		}

		TMap<UEdGraphNode*, int32> BlockByRep;
		for (UEdGraphNode* Node : ExecNodes)
		{
			UEdGraphNode* Rep = Find(Node);
			int32* Existing = BlockByRep.Find(Rep);
			const int32 Index = Existing ? *Existing : Blocks.AddDefaulted();
			BlockByRep.Add(Rep, Index);
			Blocks[Index].ExecNodes.Add(Node);
			BlockOf.Add(Node, Index);
		}

		auto ByOriginalPos = [](const UEdGraphNode& A, const UEdGraphNode& B)
		{
			return A.NodePosY != B.NodePosY ? A.NodePosY < B.NodePosY : A.NodePosX < B.NodePosX;
		};

		int32 Counter = 0;
		TFunction<void(UEdGraphNode*)> Visit = [&](UEdGraphNode* Node)
		{
			if (ExecOrder.Contains(Node))
			{
				return;
			}
			ExecOrder.Add(Node, Counter++);
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (!Pin || Pin->Direction != EGPD_Output || Pin->PinType.PinCategory != UEdGraphSchema_K2::PC_Exec)
				{
					continue;
				}
				for (UEdGraphPin* Linked : Pin->LinkedTo)
				{
					UEdGraphNode* Target = Linked ? Linked->GetOwningNode() : nullptr;
					if (Target && BlockOf.Contains(Target))
					{
						Visit(Target);
					}
				}
			}
		};

		for (FBlock& Block : Blocks)
		{
			Block.ExecNodes.Sort(ByOriginalPos);
			for (UEdGraphNode* Node : Block.ExecNodes)
			{
				if (!HasExecInputInSet.Contains(Node))
				{
					Block.Roots.Add(Node);
				}
			}
			for (UEdGraphNode* Root : Block.Roots)
			{
				Visit(Root);
			}
			// Cycles with no entry point: start from whatever is left, top-left first.
			for (UEdGraphNode* Node : Block.ExecNodes)
			{
				if (!ExecOrder.Contains(Node))
				{
					Block.Roots.Add(Node);
					Visit(Node);
				}
			}
		}
	}

	// Each pure node gets a tree parent: the direct consumer that leads to the
	// earliest exec node. Children[] is the resulting feeder forest.
	void FEngine::ResolveOwners()
	{
		ParentLink.Reset();
		Children.Reset();
		FeederWidthCache.Reset();
		TMap<UEdGraphNode*, int32> OwnerKey;
		TSet<UEdGraphNode*> InProgress;
		for (UEdGraphNode* Node : LayoutNodes)
		{
			if (!IsExec(Node))
			{
				ResolvePure(Node, InProgress, OwnerKey);
			}
		}
		for (const TPair<UEdGraphNode*, FFeedLink>& Pair : ParentLink)
		{
			Children.FindOrAdd(Pair.Value.Parent).Add(Pair.Value);
		}
		for (TPair<UEdGraphNode*, TArray<FFeedLink>>& Pair : Children)
		{
			Pair.Value.Sort([](const FFeedLink& A, const FFeedLink& B) { return A.ParentPinIndex < B.ParentPinIndex; });
		}
	}

	int32 FEngine::ResolvePure(UEdGraphNode* Node, TSet<UEdGraphNode*>& InProgress, TMap<UEdGraphNode*, int32>& OwnerKey)
	{
		if (const int32* Known = OwnerKey.Find(Node))
		{
			return *Known;
		}
		if (InProgress.Contains(Node))
		{
			return NoOwner;
		}
		InProgress.Add(Node);

		int32 Best = NoOwner;
		FFeedLink BestLink;
		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (!Pin || Pin->Direction != EGPD_Output)
			{
				continue;
			}
			for (UEdGraphPin* Linked : Pin->LinkedTo)
			{
				UEdGraphNode* Consumer = Linked ? Linked->GetOwningNode() : nullptr;
				if (!Consumer || Consumer == Node || !NodeSet.Contains(Consumer))
				{
					continue;
				}
				const int32 Key = IsExec(Consumer)
					? ExecOrder.FindRef(Consumer)
					: ResolvePure(Consumer, InProgress, OwnerKey);
				// Prefer the earliest owner. For data-only nodes (no owner) still
				// pick a consumer so the feeder tree stays connected.
				if (!BestLink.Child || Key < Best)
				{
					Best = Key;
					BestLink.Child = Node;
					BestLink.ChildOut = Pin;
					BestLink.ParentIn = Linked;
					BestLink.Parent = Consumer;
					BestLink.ParentPinIndex = Consumer->Pins.IndexOfByKey(Linked);
				}
			}
		}

		InProgress.Remove(Node);
		OwnerKey.Add(Node, Best);
		if (BestLink.Child)
		{
			ParentLink.Add(Node, BestLink);
		}
		return Best;
	}

	UEdGraphNode* FEngine::OwnerExec(UEdGraphNode* Node) const
	{
		for (int32 Guard = 0; Node && Guard < 4096; ++Guard)
		{
			if (IsExec(Node))
			{
				return Node;
			}
			const FFeedLink* Link = ParentLink.Find(Node);
			Node = Link ? Link->Parent : nullptr;
		}
		return nullptr;
	}

	// A self-variable getter read by several exec nodes gets one copy per exec
	// node, so each copy can sit right next to its reader with a short straight
	// wire. Only plain getters with no linked inputs qualify: they are
	// side-effect free and fully described by their VariableReference, so a
	// copy is always identical. Pure function calls are never duplicated.
	bool FEngine::DuplicateSharedGetters()
	{
		bool bAny = false;
		const TArray<UEdGraphNode*> Snapshot = LayoutNodes;
		for (UEdGraphNode* Node : Snapshot)
		{
			UK2Node_VariableGet* Getter = Cast<UK2Node_VariableGet>(Node);
			if (!Getter || IsExec(Getter))
			{
				continue;
			}

			UEdGraphPin* Out = nullptr;
			bool bQualifies = true;
			for (UEdGraphPin* Pin : Getter->Pins)
			{
				if (!Pin)
				{
					continue;
				}
				if (Pin->Direction == EGPD_Input && Pin->LinkedTo.Num() > 0)
				{
					bQualifies = false;
				}
				else if (Pin->Direction == EGPD_Output && Pin->LinkedTo.Num() > 0)
				{
					bQualifies &= (Out == nullptr);
					Out = Pin;
				}
			}
			if (!bQualifies || !Out)
			{
				continue;
			}

			TMap<UEdGraphNode*, TArray<UEdGraphPin*>> Buckets;
			for (UEdGraphPin* Linked : Out->LinkedTo)
			{
				UEdGraphNode* Consumer = Linked ? Linked->GetOwningNode() : nullptr;
				if (Consumer && NodeSet.Contains(Consumer))
				{
					Buckets.FindOrAdd(OwnerExec(Consumer)).Add(Linked);
				}
			}
			if (Buckets.Num() < 2)
			{
				continue;
			}

			// Earliest exec owner keeps the original. A null owner (data-only
			// consumers) goes last. TArray::Sort dereferences pointer elements,
			// so the null key is pulled out before sorting.
			TArray<UEdGraphNode*> Owners;
			Buckets.GetKeys(Owners);
			const bool bHasNullOwner = Owners.Remove(nullptr) > 0;
			Owners.Sort([this](const UEdGraphNode& A, const UEdGraphNode& B)
			{
				return ExecOrder.FindRef(&A) < ExecOrder.FindRef(&B);
			});
			if (bHasNullOwner)
			{
				Owners.Add(nullptr);
			}

			Graph->Modify();
			Getter->Modify();
			for (int32 i = 1; i < Owners.Num(); ++i)
			{
				UK2Node_VariableGet* Copy = NewObject<UK2Node_VariableGet>(Graph);
				Copy->VariableReference = Getter->VariableReference;
				Copy->SetFlags(RF_Transactional);
				Copy->NodePosX = Getter->NodePosX;
				Copy->NodePosY = Getter->NodePosY;
				Graph->AddNode(Copy, /*bFromUI=*/false, /*bSelectNewNode=*/false);
				Copy->CreateNewGuid();
				Copy->PostPlacedNewNode();
				Copy->AllocateDefaultPins();

				UEdGraphPin* CopyOut = Copy->FindPin(Out->PinName, EGPD_Output);
				if (!CopyOut || !(CopyOut->PinType == Out->PinType))
				{
					UE_LOG(LogVesperLayout, Warning, TEXT("[Vesper] Could not duplicate getter %s cleanly, leaving it shared."), *Getter->GetName());
					Copy->DestroyNode();
					break;
				}

				for (UEdGraphPin* ConsumerPin : Buckets[Owners[i]])
				{
					ConsumerPin->GetOwningNode()->Modify();
					Out->BreakLinkTo(ConsumerPin);
					CopyOut->MakeLinkTo(ConsumerPin);
				}
				LayoutNodes.Add(Copy);
				NodeSet.Add(Copy);
				bAny = true;
			}
		}
		return bAny;
	}

	// Pure nodes with no exec owner form data-only blocks, one per connected
	// data component. Owned pure nodes join their owner's block.
	void FEngine::BuildDataOnlyBlocks()
	{
		TArray<UEdGraphNode*> Orphans;
		for (UEdGraphNode* Node : LayoutNodes)
		{
			if (IsExec(Node))
			{
				Blocks[BlockOf[Node]].Members.Add(Node);
				continue;
			}
			if (UEdGraphNode* Owner = OwnerExec(Node))
			{
				const int32 Index = BlockOf[Owner];
				BlockOf.Add(Node, Index);
				Blocks[Index].Members.Add(Node);
			}
			else
			{
				Orphans.Add(Node);
			}
		}

		// Group orphans by their feeder-tree root.
		TMap<UEdGraphNode*, int32> BlockByRoot;
		for (UEdGraphNode* Node : Orphans)
		{
			UEdGraphNode* Root = Node;
			for (int32 Guard = 0; Guard < 4096; ++Guard)
			{
				const FFeedLink* Link = ParentLink.Find(Root);
				if (!Link || Link->Parent == Node)
				{
					break;
				}
				Root = Link->Parent;
			}
			int32* Existing = BlockByRoot.Find(Root);
			int32 Index;
			if (Existing)
			{
				Index = *Existing;
			}
			else
			{
				Index = Blocks.AddDefaulted();
				Blocks[Index].bDataOnly = true;
				Blocks[Index].Roots.Add(Root);
				BlockByRoot.Add(Root, Index);
			}
			BlockOf.Add(Node, Index);
			Blocks[Index].Members.Add(Node);
		}

		for (FBlock& Block : Blocks)
		{
			Block.OrigMinY = TNumericLimits<float>::Max();
			for (UEdGraphNode* Node : Block.Members)
			{
				Block.OrigMinY = FMath::Min(Block.OrigMinY, static_cast<float>(Node->NodePosY));
			}
		}
	}

	void FEngine::Place(UEdGraphNode* Node, const FVector2D& Pos, FLayoutCtx& Ctx)
	{
		Ctx.Pos.Add(Node, Pos);
		Ctx.Rects.Add(FBox2D(Pos, Pos + M.Size(Node)));
	}

	// Moves Sub down (never up) by the smallest amount >= MinDy that keeps
	// every rect in Sub GapY clear of every rect in Ctx, then merges it.
	// Returns the applied offset.
	float FEngine::Drop(FLayoutCtx& Sub, FLayoutCtx& Ctx, float MinDy, float GapY)
	{
		static constexpr float GapX = 10.f;
		float Dy = MinDy;
		for (int32 Iteration = 0; Iteration < 4096; ++Iteration)
		{
			bool bMoved = false;
			for (const FBox2D& Rect : Sub.Rects)
			{
				const FBox2D Shifted = Rect.ShiftBy(FVector2D(0.f, Dy));
				for (const FBox2D& Other : Ctx.Rects)
				{
					const bool bOverlapX = Shifted.Min.X < Other.Max.X + GapX && Shifted.Max.X + GapX > Other.Min.X;
					const bool bOverlapY = Shifted.Min.Y < Other.Max.Y + GapY && Shifted.Max.Y + GapY > Other.Min.Y;
					if (bOverlapX && bOverlapY)
					{
						Dy = Other.Max.Y + GapY - Rect.Min.Y;
						bMoved = true;
						break;
					}
				}
				if (bMoved)
				{
					break;
				}
			}
			if (!bMoved)
			{
				break;
			}
		}
		Ctx.MergeFrom(Sub, FVector2D(0.f, Dy));
		return Dy;
	}

	// Horizontal room a node's feeder tree needs to its left.
	float FEngine::FeederWidth(UEdGraphNode* Node)
	{
		if (const float* Cached = FeederWidthCache.Find(Node))
		{
			return *Cached;
		}
		FeederWidthCache.Add(Node, 0.f); // cycle guard
		float Width = 0.f;
		if (const TArray<FFeedLink>* Kids = Children.Find(Node))
		{
			for (const FFeedLink& Link : *Kids)
			{
				Width = FMath::Max(Width, S.DataGap + M.Size(Link.Child).X + FeederWidth(Link.Child));
			}
		}
		FeederWidthCache.Add(Node, Width);
		return Width;
	}

	// Places Node so the pin it was entered through sits exactly on PinY
	// (straight exec wire), then its feeders, then its exec outputs: the
	// first continues on the same row, every other one gets its own row
	// dropped below everything placed so far.
	void FEngine::LayoutExec(UEdGraphNode* Node, const UEdGraphPin* EnterPin, float X, float PinY, FLayoutCtx& Ctx)
	{
		Visited.Add(Node);

		const UEdGraphPin* AnchorPin = EnterPin;
		if (!AnchorPin)
		{
			for (const UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin && !Pin->bHidden && Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
				{
					if (Pin->Direction == EGPD_Output)
					{
						AnchorPin = Pin;
						break;
					}
					if (!AnchorPin)
					{
						AnchorPin = Pin;
					}
				}
			}
		}

		const FVector2D Pos(X, PinY - M.PinOffset(Node, AnchorPin));
		Place(Node, Pos, Ctx);
		LayoutFeedersOf(Node, Ctx);

		TArray<TPair<UEdGraphPin*, UEdGraphPin*>> Outs;
		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (!Pin || Pin->bHidden || Pin->Direction != EGPD_Output || Pin->PinType.PinCategory != UEdGraphSchema_K2::PC_Exec)
			{
				continue;
			}
			for (UEdGraphPin* Linked : Pin->LinkedTo)
			{
				UEdGraphNode* Target = Linked ? Linked->GetOwningNode() : nullptr;
				if (Target && NodeSet.Contains(Target) && IsExec(Target))
				{
					Outs.Add(TPair<UEdGraphPin*, UEdGraphPin*>(Pin, Linked));
				}
			}
		}

		bool bFirst = true;
		const float Right = Pos.X + M.Size(Node).X;
		for (const TPair<UEdGraphPin*, UEdGraphPin*>& Out : Outs)
		{
			UEdGraphNode* Target = Out.Value->GetOwningNode();
			if (Visited.Contains(Target))
			{
				continue; // merge point: already placed, the wire just joins it
			}
			const float OutPinY = Pos.Y + M.PinOffset(Node, Out.Key);
			const float TargetX = Right + S.ExecGap + FeederWidth(Target);
			if (bFirst)
			{
				LayoutExec(Target, Out.Value, TargetX, OutPinY, Ctx);
				bFirst = false;
			}
			else
			{
				FLayoutCtx Branch;
				LayoutExec(Target, Out.Value, TargetX, 0.f, Branch);
				Drop(Branch, Ctx, OutPinY, S.BranchRowGap);
			}
		}
	}

	// Stacks Node's feeders to its left. The first one is placed so its wire
	// is straight; each later one goes directly under the previous feeder's
	// whole subtree. Nothing is allowed above the floor: for exec consumers
	// the floor is just under the exec wire, for pure consumers it's the
	// consumer's top edge (minus a small tolerance so a first wire can stay
	// straight).
	void FEngine::LayoutFeedersOf(UEdGraphNode* Node, FLayoutCtx& Ctx)
	{
		const TArray<FFeedLink>* Kids = Children.Find(Node);
		if (!Kids)
		{
			return;
		}
		const FVector2D NodePos = Ctx.Pos[Node];

		float Floor = NodePos.Y - S.AboveTolerance;
		if (IsExec(Node))
		{
			Floor = NodePos.Y;
			for (const UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin && !Pin->bHidden && Pin->Direction == EGPD_Input && Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
				{
					Floor = FMath::Max(Floor, NodePos.Y + M.PinOffset(Node, Pin) + S.ExecLaneClearance);
					break;
				}
			}
		}

		bool bHaveCursor = false;
		float Cursor = 0.f;
		for (const FFeedLink& Link : *Kids)
		{
			if (Visited.Contains(Link.Child))
			{
				continue;
			}
			const FVector2D ChildSize = M.Size(Link.Child);
			const float TargetPinY = NodePos.Y + M.PinOffset(Node, Link.ParentIn);
			const FVector2D ChildPos(NodePos.X - S.DataGap - ChildSize.X, TargetPinY - M.PinOffset(Link.Child, Link.ChildOut));

			FLayoutCtx Sub;
			LayoutFeederTree(Link.Child, ChildPos, Sub);
			const FBox2D SubBounds = Sub.Bounds();

			const float MinTop = bHaveCursor ? Cursor + S.StackGap : Floor;
			const float MinDy = FMath::Max(0.f, MinTop - SubBounds.Min.Y);
			const float Dy = Drop(Sub, Ctx, MinDy, S.StackGap);

			Cursor = SubBounds.Max.Y + Dy;
			bHaveCursor = true;
		}
	}

	void FEngine::LayoutFeederTree(UEdGraphNode* Node, const FVector2D& Pos, FLayoutCtx& Ctx)
	{
		Visited.Add(Node);
		Place(Node, Pos, Ctx);
		LayoutFeedersOf(Node, Ctx);
	}

	void FEngine::LayoutBlock(FBlock& Block)
	{
		FLayoutCtx& Ctx = Block.Layout;
		bool bFirst = true;
		for (UEdGraphNode* Root : Block.Roots)
		{
			if (Visited.Contains(Root))
			{
				continue;
			}
			if (bFirst)
			{
				if (Block.bDataOnly)
				{
					LayoutFeederTree(Root, FVector2D::ZeroVector, Ctx);
				}
				else
				{
					LayoutExec(Root, nullptr, 0.f, 0.f, Ctx);
				}
				bFirst = false;
				continue;
			}
			// Extra roots (several events merging into one chain, several data
			// sinks) each get their own row under what's already there.
			FLayoutCtx Sub;
			if (Block.bDataOnly)
			{
				LayoutFeederTree(Root, FVector2D::ZeroVector, Sub);
			}
			else
			{
				LayoutExec(Root, nullptr, 0.f, 0.f, Sub);
			}
			Drop(Sub, Ctx, 0.f, S.BranchRowGap);
		}
	}

	FString PrefixToken(const FString& Name)
	{
		int32 Underscore;
		if (Name.FindChar(TEXT('_'), Underscore) && Underscore >= 2)
		{
			return Name.Left(Underscore);
		}
		int32 Index = 1;
		while (Index < Name.Len() && !FChar::IsUpper(Name[Index]) && Name[Index] != TEXT(' '))
		{
			++Index;
		}
		return (Index >= 2 && Index < Name.Len()) ? Name.Left(Index) : FString();
	}

	bool IsLifecycleEvent(const FName& Name)
	{
		static const TSet<FName> Names = {
			TEXT("ReceiveBeginPlay"), TEXT("ReceiveTick"), TEXT("ReceiveEndPlay"), TEXT("ReceiveDestroyed"),
			TEXT("UserConstructionScript"), TEXT("ReceivePossessed"), TEXT("ReceiveUnpossessed"), TEXT("ReceiveRestarted"),
			TEXT("ReceiveControllerChanged"), TEXT("Construct"), TEXT("PreConstruct"), TEXT("Destruct"), TEXT("Tick"),
			TEXT("OnInitialized"), TEXT("BlueprintInitializeAnimation"), TEXT("BlueprintUpdateAnimation"),
			TEXT("BlueprintBeginPlay"), TEXT("BlueprintPostEvaluateAnimation"), TEXT("ReceiveInitializeComponent"),
		};
		return Names.Contains(Name);
	}

	// Titles every block and assigns group keys. Blocks sharing a key (2+)
	// become one group.
	void FEngine::DescribeBlocks()
	{
		for (FBlock& Block : Blocks)
		{
			UEdGraphNode* Root = Block.Roots.Num() > 0 ? Block.Roots[0] : (Block.Members.Num() > 0 ? Block.Members[0] : nullptr);
			if (!Root)
			{
				continue;
			}

			if (Root->IsA<UK2Node_FunctionEntry>())
			{
				Block.Title = FName::NameToDisplayString(Graph->GetName(), false);
			}
			else
			{
				Block.Title = FirstLine(Root->GetNodeTitle(ENodeTitleType::ListView).ToString());
			}

			for (UEdGraphNode* Node : Block.Members)
			{
				if (const UK2Node_Variable* Variable = Cast<UK2Node_Variable>(Node))
				{
					Block.MemberRefs.Add(Variable->GetVarName());
				}
				else if (const UK2Node_CallFunction* Call = Cast<UK2Node_CallFunction>(Node))
				{
					if (Call->FunctionReference.IsSelfContext())
					{
						Block.MemberRefs.Add(Call->FunctionReference.GetMemberName());
					}
				}
			}

			const bool bEntryLike = Root->IsA<UK2Node_Event>() || Root->IsA<UK2Node_FunctionEntry>()
				|| Root->GetClass()->GetName().Contains(TEXT("Input"));
			Block.bLoose = Block.bLoose || Block.bDataOnly || (Block.ExecNodes.Num() == 1 && !bEntryLike);

			if (Block.bLoose)
			{
				Block.GroupKey = TEXT("~Loose");
				Block.GroupTitle = TEXT("Unconnected Nodes");
				continue;
			}
			if (!S.bGroupSimilar)
			{
				continue;
			}

			const FString ClassName = Root->GetClass()->GetName();
			if (ClassName.Contains(TEXT("Input")))
			{
				Block.GroupKey = TEXT("Input");
				Block.GroupTitle = TEXT("Input Events");
			}
			else if (const UK2Node_CustomEvent* Custom = Cast<UK2Node_CustomEvent>(Root))
			{
				const FString Token = PrefixToken(Custom->CustomFunctionName.ToString());
				if (!Token.IsEmpty())
				{
					Block.GroupKey = TEXT("Prefix:") + Token;
					Block.GroupTitle = Token + TEXT(" Events");
				}
			}
			else if (const UK2Node_Event* Event = Cast<UK2Node_Event>(Root))
			{
				const FName FunctionName = Event->GetFunctionName();
				const FString NameStr = FunctionName.ToString();
				if (IsLifecycleEvent(FunctionName))
				{
					Block.GroupKey = TEXT("Lifecycle");
					Block.GroupTitle = TEXT("Lifecycle Events");
				}
				else if (NameStr.Contains(TEXT("Overlap")) || NameStr.Contains(TEXT("Hit")) || NameStr.Contains(TEXT("Collision")))
				{
					Block.GroupKey = TEXT("Collision");
					Block.GroupTitle = TEXT("Collision & Overlap Events");
				}
				else
				{
					Block.GroupKey = TEXT("Overrides");
					Block.GroupTitle = TEXT("Event Overrides");
				}
			}
		}

		if (!S.bGroupSimilar)
		{
			return;
		}

		// A key used by a single block is no group at all.
		TMap<FString, int32> KeyCounts;
		for (const FBlock& Block : Blocks)
		{
			if (!Block.GroupKey.IsEmpty())
			{
				KeyCounts.FindOrAdd(Block.GroupKey)++;
			}
		}
		for (FBlock& Block : Blocks)
		{
			if (!Block.bLoose && !Block.GroupKey.IsEmpty() && KeyCounts[Block.GroupKey] < 2)
			{
				Block.GroupKey.Reset();
				Block.GroupTitle.Reset();
			}
		}

		// Remaining solo blocks: group the ones that mostly touch the same
		// variables/functions (Jaccard similarity >= 0.5).
		TArray<int32> Solo;
		for (int32 i = 0; i < Blocks.Num(); ++i)
		{
			if (Blocks[i].GroupKey.IsEmpty() && Blocks[i].MemberRefs.Num() >= 2)
			{
				Solo.Add(i);
			}
		}
		for (int32 a = 0; a < Solo.Num(); ++a)
		{
			FBlock& First = Blocks[Solo[a]];
			for (int32 b = a + 1; b < Solo.Num(); ++b)
			{
				FBlock& Second = Blocks[Solo[b]];
				if (!Second.GroupKey.IsEmpty() && Second.GroupKey != First.GroupKey)
				{
					continue;
				}
				const TSet<FName> Shared = First.MemberRefs.Intersect(Second.MemberRefs);
				const TSet<FName> Union = First.MemberRefs.Union(Second.MemberRefs);
				if (Union.Num() == 0 || static_cast<float>(Shared.Num()) / Union.Num() < 0.5f)
				{
					continue;
				}
				if (First.GroupKey.IsEmpty())
				{
					TArray<FName> SharedNames = Shared.Array();
					SharedNames.Sort(FNameLexicalLess());
					First.GroupKey = FString::Printf(TEXT("Related:%d"), Solo[a]);
					First.GroupTitle = TEXT("Uses ") + FName::NameToDisplayString(SharedNames[0].ToString(), false);
				}
				Second.GroupKey = First.GroupKey;
				Second.GroupTitle = First.GroupTitle;
			}
		}
	}

	void FEngine::ApplyBlock(const FBlock& Block, const FVector2D& Offset)
	{
		for (const TPair<UEdGraphNode*, FVector2D>& Pair : Block.Layout.Pos)
		{
			Pair.Key->NodePosX = FMath::RoundToInt(Pair.Value.X + Offset.X);
			Pair.Key->NodePosY = FMath::RoundToInt(Pair.Value.Y + Offset.Y);
		}
	}

	UEdGraphNode_Comment* FEngine::MakeOrFitComment(UEdGraphNode_Comment* Existing, const FBox2D& Rect, const FString& Title,
		const FLinearColor& Color, int32 FontSize, int32 Depth)
	{
		UEdGraphNode_Comment* Comment = Existing;
		if (!Comment)
		{
			Graph->Modify();
			Comment = NewObject<UEdGraphNode_Comment>(Graph);
			Comment->SetFlags(RF_Transactional);
			Graph->AddNode(Comment, /*bFromUI=*/false, /*bSelectNewNode=*/false);
			Comment->CreateNewGuid();
			Comment->PostPlacedNewNode();
			Comment->AllocateDefaultPins();
			Comment->NodeGuid.A = GeneratedCommentTag;
			Comment->NodeComment = Title;
			Comment->CommentColor = Color;
			Comment->FontSize = FontSize;
			Comment->CommentDepth = Depth;
			Comment->bCommentBubbleVisible_InDetailsPanel = false;
			Comment->bCommentBubbleVisible = false;
		}
		else
		{
			Comment->Modify();
		}
		Comment->NodePosX = FMath::RoundToInt(Rect.Min.X);
		Comment->NodePosY = FMath::RoundToInt(Rect.Min.Y);
		Comment->NodeWidth = FMath::RoundToInt(Rect.GetSize().X);
		Comment->NodeHeight = FMath::RoundToInt(Rect.GetSize().Y);
		return Comment;
	}

	struct FGroup
	{
		FString Key;
		FString Title;
		TArray<FBlock*> Blocks;
		float OrigY = 0.f;
		bool bIsGroup = false;
		bool bLoose = false;
	};

	void FEngine::PlaceBlocksAndComments()
	{
		// A user comment that wraps exactly one block (including its root)
		// becomes that block's frame, keeping the user's title and color.
		for (FUserComment& User : UserComments)
		{
			const int32* FirstBlock = User.Contained.Num() > 0 ? BlockOf.Find(User.Contained[0]) : nullptr;
			if (!FirstBlock)
			{
				continue;
			}
			bool bSingleBlock = true;
			for (UEdGraphNode* Node : User.Contained)
			{
				const int32* Index = BlockOf.Find(Node);
				bSingleBlock &= (Index && *Index == *FirstBlock);
			}
			FBlock& Block = Blocks[*FirstBlock];
			if (bSingleBlock && !Block.bLoose && Block.Roots.Num() > 0 && User.Contained.Contains(Block.Roots[0]) && !Block.Adopted)
			{
				Block.Adopted = User.Comment;
				User.Contained.Reset(); // handled here, skip the generic refit
			}
		}

		// Build groups.
		TArray<FGroup> Groups;
		TMap<FString, int32> GroupByKey;
		for (FBlock& Block : Blocks)
		{
			if (Block.Layout.Rects.Num() == 0)
			{
				continue;
			}
			if (Block.GroupKey.IsEmpty())
			{
				FGroup& Group = Groups.AddDefaulted_GetRef();
				Group.Blocks.Add(&Block);
				Group.OrigY = Block.OrigMinY;
				continue;
			}
			int32* Existing = GroupByKey.Find(Block.GroupKey);
			FGroup& Group = Existing ? Groups[*Existing] : Groups.AddDefaulted_GetRef();
			if (!Existing)
			{
				GroupByKey.Add(Block.GroupKey, Groups.Num() - 1);
				Group.Key = Block.GroupKey;
				Group.Title = Block.GroupTitle;
				Group.OrigY = Block.OrigMinY;
				Group.bLoose = Block.bLoose;
			}
			Group.Blocks.Add(&Block);
			Group.OrigY = FMath::Min(Group.OrigY, Block.OrigMinY);
		}
		for (FGroup& Group : Groups)
		{
			Group.bIsGroup = Group.Blocks.Num() > 1;
			Group.Blocks.Sort([](const FBlock& A, const FBlock& B) { return A.OrigMinY < B.OrigMinY; });
			if (!Group.bIsGroup && Group.bLoose)
			{
				Group.Blocks[0]->Title = TEXT("Unconnected: ") + Group.Blocks[0]->Title;
			}
		}
		Groups.Sort([](const FGroup& A, const FGroup& B)
		{
			if (A.bLoose != B.bLoose)
			{
				return B.bLoose; // loose nodes always last
			}
			return A.OrigY < B.OrigY;
		});

		const float Pad = S.CommentPadding;
		const float TitleH = CommentTitleHeight(S.CommentFontSize);
		const float InnerTitleH = CommentTitleHeight(S.InnerCommentFontSize);
		float CursorY = Anchor.Y;
		const float LeftX = Anchor.X;

		for (const FGroup& Group : Groups)
		{
			if (!Group.bIsGroup)
			{
				FBlock& Block = *Group.Blocks[0];
				const FBox2D Local = Block.Layout.Bounds();
				const bool bFrame = S.bGenerateComments || Block.Adopted;
				const float Top = bFrame ? Pad + TitleH : 0.f;
				const float Side = bFrame ? Pad : 0.f;
				ApplyBlock(Block, FVector2D(LeftX + Side - Local.Min.X, CursorY + Top - Local.Min.Y));
				const FBox2D Frame(FVector2D(LeftX, CursorY),
					FVector2D(LeftX + Side * 2.f + Local.GetSize().X, CursorY + Top + Local.GetSize().Y + Side));
				if (bFrame)
				{
					MakeOrFitComment(Block.Adopted, Frame, Block.Title, Block.bLoose ? S.LooseColor : S.SingleColor, S.CommentFontSize, -1);
				}
				CursorY = Frame.Max.Y + S.BlockGap;
				continue;
			}

			const bool bOuter = S.bGenerateComments;
			const float OuterTop = bOuter ? Pad + TitleH : 0.f;
			const float OuterSide = bOuter ? Pad : 0.f;
			float Y = CursorY + OuterTop;
			float MaxRight = LeftX;
			for (FBlock* Block : Group.Blocks)
			{
				const FBox2D Local = Block->Layout.Bounds();
				const bool bInner = (S.bGenerateComments && S.bInnerGroupComments && !Group.bLoose) || Block->Adopted;
				const float InnerTop = bInner ? Pad + InnerTitleH : 0.f;
				const float InnerSide = bInner ? Pad * 0.75f : 0.f;
				const float X0 = LeftX + OuterSide;
				ApplyBlock(*Block, FVector2D(X0 + InnerSide - Local.Min.X, Y + InnerTop - Local.Min.Y));
				const FBox2D Frame(FVector2D(X0, Y),
					FVector2D(X0 + InnerSide * 2.f + Local.GetSize().X, Y + InnerTop + Local.GetSize().Y + InnerSide));
				if (bInner)
				{
					MakeOrFitComment(Block->Adopted, Frame, Block->Title, S.InnerColor, S.InnerCommentFontSize, -1);
				}
				MaxRight = FMath::Max(MaxRight, Frame.Max.X);
				Y = Frame.Max.Y + S.GroupInnerGap;
			}
			const float Bottom = Y - S.GroupInnerGap + OuterSide;
			if (bOuter)
			{
				const FString Title = FString::Printf(TEXT("%s (%d)"), *Group.Title, Group.Blocks.Num());
				MakeOrFitComment(nullptr, FBox2D(FVector2D(LeftX, CursorY), FVector2D(MaxRight + OuterSide, Bottom)),
					Title, Group.bLoose ? S.LooseColor : S.GroupColor, S.CommentFontSize, -2);
			}
			CursorY = Bottom + S.BlockGap;
		}
	}

	// User comments that weren't adopted as a block frame get resized around
	// the same nodes they wrapped before the layout moved them.
	void FEngine::RefitUserComments()
	{
		for (const FUserComment& User : UserComments)
		{
			if (User.Contained.Num() == 0)
			{
				continue;
			}
			FBox2D Bounds(ForceInit);
			for (UEdGraphNode* Node : User.Contained)
			{
				const FVector2D Pos = OrigPos(Node);
				Bounds += FBox2D(Pos, Pos + M.Size(Node));
			}
			const float Pad = S.CommentPadding;
			const float TitleH = CommentTitleHeight(User.Comment->FontSize);
			MakeOrFitComment(User.Comment, FBox2D(Bounds.Min - FVector2D(Pad, Pad + TitleH), Bounds.Max + FVector2D(Pad, Pad)),
				FString(), FLinearColor::White, 0, 0);
		}
	}
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

	// A toolbar/menu button just took keyboard focus for itself. Fall back to
	// the last Graph Editor we saw focused.
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

int32 FVesperGraphLayout::FormatNodesInternal(const TArray<UEdGraphNode*>& Nodes, SGraphPanel* Panel)
{
	UEdGraph* Graph = nullptr;
	for (UEdGraphNode* Node : Nodes)
	{
		if (Node && Node->GetGraph())
		{
			Graph = Node->GetGraph();
			break;
		}
	}
	if (!Graph || Nodes.Num() < 2)
	{
		return 0;
	}
	VesperLayout::FEngine Engine(Graph, Panel);
	const int32 Count = Engine.Run(Nodes);
	UE_LOG(LogVesperLayout, Log, TEXT("[Vesper] Formatted %d nodes in %s (%s sizes)."), Count, *Graph->GetName(),
		Panel ? TEXT("measured") : TEXT("estimated"));
	return Count;
}

int32 FVesperGraphLayout::FormatNodes(const TArray<UEdGraphNode*>& Nodes)
{
	const UEdGraph* Graph = nullptr;
	for (const UEdGraphNode* Node : Nodes)
	{
		if (Node && Node->GetGraph())
		{
			Graph = Node->GetGraph();
			break;
		}
	}
	return FormatNodesInternal(Nodes, FindPanelForGraph(Graph));
}

void FVesperGraphLayout::FormatSelectedNodes()
{
	const TSharedPtr<SGraphEditor> CurrentGraphEditor = GetActiveGraphEditor();
	UEdGraph* Graph = CurrentGraphEditor.IsValid() ? CurrentGraphEditor->GetCurrentGraph() : nullptr;
	if (!Graph)
	{
		FNotificationInfo Info(FText::FromString(TEXT("Vesper: Click inside a Blueprint graph first.")));
		Info.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return;
	}

	TArray<UEdGraphNode*> ValidNodes;
	for (UObject* Obj : CurrentGraphEditor->GetSelectedNodes())
	{
		if (UEdGraphNode* GraphNode = Cast<UEdGraphNode>(Obj))
		{
			ValidNodes.Add(GraphNode);
		}
	}

	// With (almost) nothing selected, clean the whole graph.
	const bool bWholeGraph = ValidNodes.Num() < 2;
	if (bWholeGraph)
	{
		ValidNodes.Reset();
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (Node)
			{
				ValidNodes.Add(Node);
			}
		}
	}

	if (ValidNodes.Num() < 2)
	{
		FNotificationInfo Info(FText::FromString(TEXT("Vesper: Nothing to format in this graph.")));
		Info.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return;
	}

	const FScopedTransaction Transaction(FText::FromString(TEXT("Vesper: Clean Graph")));
	Graph->Modify();
	for (UEdGraphNode* Node : ValidNodes)
	{
		Node->Modify();
	}

	// Generated comments may be deleted and recreated; don't leave them selected.
	CurrentGraphEditor->ClearSelectionSet();
	const int32 FormattedCount = FormatNodesInternal(ValidNodes, CurrentGraphEditor->GetGraphPanel());
	CurrentGraphEditor->NotifyGraphChanged();

	FNotificationInfo SuccessInfo(FText::FromString(FString::Printf(
		TEXT("Vesper: %d nodes formatted%s."), FormattedCount, bWholeGraph ? TEXT(" (whole graph)") : TEXT(""))));
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
	VesperLayout::FMetrics Metrics;
	Metrics.Panel = CurrentGraphEditor->GetGraphPanel();
	const VesperLayout::FSettings Settings = VesperLayout::FSettings::Load();
	int32 ResizedCount = 0;

	for (UEdGraphNode_Comment* CommentNode : CommentNodes)
	{
		// GetNodesUnderComment() returns whatever currently falls inside the
		// comment's bounds, as tracked by its on-screen widget.
		FBox2D Bounds(ForceInit);
		for (UObject* Obj : CommentNode->GetNodesUnderComment())
		{
			UEdGraphNode* ChildNode = Cast<UEdGraphNode>(Obj);
			if (!ChildNode || ChildNode == CommentNode)
			{
				continue;
			}
			const FVector2D Pos(ChildNode->NodePosX, ChildNode->NodePosY);
			const FVector2D Size = ChildNode->IsA<UEdGraphNode_Comment>()
				? FVector2D(ChildNode->NodeWidth, ChildNode->NodeHeight)
				: Metrics.Size(ChildNode);
			Bounds += FBox2D(Pos, Pos + Size);
		}

		if (!Bounds.bIsValid)
		{
			continue;
		}

		const float Pad = Settings.CommentPadding;
		const float TitleH = VesperLayout::CommentTitleHeight(CommentNode->FontSize);
		CommentNode->Modify();
		CommentNode->NodePosX = FMath::RoundToInt(Bounds.Min.X - Pad);
		CommentNode->NodePosY = FMath::RoundToInt(Bounds.Min.Y - Pad - TitleH);
		CommentNode->NodeWidth = FMath::RoundToInt(Bounds.GetSize().X + Pad * 2.f);
		CommentNode->NodeHeight = FMath::RoundToInt(Bounds.GetSize().Y + Pad * 2.f + TitleH);
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

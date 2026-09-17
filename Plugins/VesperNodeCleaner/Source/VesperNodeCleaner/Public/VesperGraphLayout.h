// Copyright Vesper System, 2026. All Rights Reserved.
#pragma once

#include "CoreMinimal.h"

class SGraphEditor;
class SWidget;
class UEdGraphNode;
class UEdGraphPin;
class UK2Node_VariableGet;
class UK2Node_CallFunction;

/**
 * Static utility class that performs Blueprint graph node layout operations
 * (auto-format / auto-arrange) and comment box resizing for the
 * VesperNodeCleaner editor plugin.
 *
 * All entry points here are safe to call from a UI command (toolbar button,
 * context menu entry, or keyboard shortcut) — they resolve the currently
 * focused Graph Editor themselves and no-op gracefully if none is found.
 */
class VESPERNODECLEANER_API FVesperGraphLayout
{
public:
	/**
	 * Arranges the currently selected nodes in the focused Blueprint graph
	 * into left-to-right layers based on their exec/data pin connectivity,
	 * removing overlap and reducing wire crossings.
	 * Requires at least 2 selected nodes. Fully undoable.
	 */
	static void FormatSelectedNodes();

	/**
	 * Same layout pipeline as FormatSelectedNodes(), but takes an explicit
	 * node list instead of reading the current Graph Editor selection, and
	 * does not touch Slate/notifications at all. This lets external
	 * automation (e.g. the Monolith MCP bridge) invoke the exact same
	 * "Clean Graph" behavior headlessly, without a Blueprint editor tab
	 * open or any nodes manually selected first.
	 * Returns the number of nodes repositioned (0 if Nodes.Num() < 2).
	 * Caller is responsible for wrapping this in a transaction and calling
	 * Modify() on the nodes beforehand if undo support is desired.
	 */
	static int32 FormatNodes(const TArray<UEdGraphNode*>& Nodes);

	/**
	 * Resizes every selected Comment node so its bounding box tightly wraps
	 * the nodes currently contained within it, plus a small padding margin.
	 * Requires at least 1 selected Comment node. Fully undoable.
	 */
	static void AutoFitSelectedComments();

	/**
	 * Hooks a global Slate focus-change delegate so the plugin can remember
	 * the last Graph Editor that actually held keyboard focus. Toolbar/menu
	 * button clicks move keyboard focus to the button itself before the
	 * command handler runs, which made GetActiveGraphEditor() find nothing
	 * (0 nodes detected) even with a valid node selection still present in
	 * the graph. Call once from module StartupModule().
	 */
	static void RegisterFocusTracking();

	/** Unhooks the delegate registered by RegisterFocusTracking(). Call from module ShutdownModule(). */
	static void UnregisterFocusTracking();

private:
	/** Walks the current keyboard focus path to find the active SGraphEditor, if any. */
	static TSharedPtr<SGraphEditor> GetActiveGraphEditor();

	/**
	 * Computes a "layer" (column index) for each node using a longest-path
	 * layering pass over the subgraph induced by the selection only — links
	 * to nodes outside the selection are ignored so formatting a subset of a
	 * large graph never drags in unrelated nodes.
	 */
	static void ComputeLayers(const TArray<UEdGraphNode*>& Nodes, TMap<UEdGraphNode*, int32>& OutLayers);

	/**
	 * Applies final NodePosX / NodePosY values derived from the computed layers.
	 * Also records, per layer, the vertical [top, bottom] ranges every placed
	 * node ends up occupying (OutOccupiedRanges) plus the OriginX/MinLayer used
	 * to convert a layer index into an X coordinate — both are needed by
	 * PlaceAttachedVariableNodes() so it can slot variable-getter nodes in
	 * without overlapping anything this pass already placed.
	 */
	static void ApplyLayout(const TArray<UEdGraphNode*>& Nodes, const TMap<UEdGraphNode*, int32>& Layers,
		TMap<int32, TArray<TPair<float, float>>>& OutOccupiedRanges, float& OutOriginX, int32& OutMinLayer);

	/**
	 * Returns true if Node is a "Get" node for a variable (UK2Node_VariableGet)
	 * whose output is read by exactly one other node within Nodes — i.e. a
	 * plain data tap rather than something feeding multiple consumers. Such
	 * nodes are excluded from the normal column layering (see ComputeLayers)
	 * and instead placed directly above/below the one node that reads them,
	 * matching how the user manually arranges variable nodes by hand instead
	 * of clumping every variable node into a single far-left column.
	 */
	static bool TryGetSingleVariableConsumer(UEdGraphNode* Node, const TSet<UEdGraphNode*>& CandidateConsumers, UEdGraphNode*& OutConsumer, UEdGraphPin*& OutConsumerPin);

	/**
	 * Returns true if Node is a pure, side-effect-free data tap -- either a
	 * plain UK2Node_VariableGet or a BlueprintPure UK2Node_CallFunction --
	 * and is therefore safe to duplicate without changing behavior. Also
	 * checks (as an explicit guard, since it should always already be true
	 * for these node classes) that Node has no exec pins.
	 */
	static bool IsSplittableFanOutNode(UEdGraphNode* Node);

	/**
	 * Creates a second node of the same class as Original (variable getter
	 * or pure function call), reading the same variable / calling the same
	 * function, placed at Original's current position. Every input pin's
	 * wiring (or literal default, if unlinked) is replicated from Original
	 * onto the copy so it reads from the exact same upstream sources.
	 * Caller is responsible for rewiring whichever output link should move
	 * onto it.
	 */
	static UEdGraphNode* DuplicateFanOutNode(UEdGraphNode* Original);

	/**
	 * Finds pure data nodes in WorkingNodes that fan out to several distinct
	 * consumers (per output pin) within the same selection, and -- only for
	 * consumers farther apart than VariableSplitMaxDistance, and only when
	 * IsSplittableFanOutNode() says it's safe -- peels off a dedicated
	 * duplicate per distant consumer so each can be attached beside its own
	 * reader (see TryGetSingleVariableConsumer) instead of one shared node
	 * drawing a long line across the graph. Consumers close enough to the
	 * original keep sharing it. Newly created duplicates are appended to
	 * WorkingNodes.
	 */
	static void SplitFanOutNodes(TArray<UEdGraphNode*>& WorkingNodes);

	/**
	 * Places each variable-getter node directly above or below the one node
	 * that consumes it (alternating sides as more attach to the same
	 * consumer), sliding further out only as far as needed to avoid
	 * overlapping anything else already occupying that column.
	 */
	static void PlaceAttachedVariableNodes(const TMap<UEdGraphNode*, TArray<TPair<UEdGraphNode*, UEdGraphPin*>>>& AttachedByConsumer,
		const TMap<UEdGraphNode*, int32>& ConsumerLayers, TMap<int32, TArray<TPair<float, float>>>& OccupiedRanges,
		float OriginX, int32 MinLayer);

	/**
	 * Rough visual height of a node in pixels, estimated from its pin count.
	 * NOTE: UEdGraphNode does not store its rendered pixel size in the data
	 * model (that lives only in the runtime SGraphNode widget), so this is a
	 * heuristic rather than an exact measurement. It is intentionally
	 * generous to avoid visual overlap across all standard K2 node types.
	 */
	static float EstimateNodeHeight(const UEdGraphNode* Node);

	/**
	 * Estimates the vertical offset (in pixels) from a node's top edge down
	 * to the given pin's row, counting only same-direction pins (input or
	 * output) that come before it in Node->Pins. Lets an attached variable
	 * node line up with the exact pin it feeds instead of just the
	 * consumer's overall vertical center.
	 */
	static float EstimatePinYOffset(const UEdGraphNode* Node, const UEdGraphPin* Pin);
};
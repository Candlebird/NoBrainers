// Copyright Vesper System, 2026. All Rights Reserved.
#pragma once

#include "CoreMinimal.h"

class SGraphEditor;
class SGraphPanel;
class UEdGraphNode;

/**
 * Static utility class that performs Blueprint graph node layout operations
 * ("Clean Graph") and comment box resizing for the VesperNodeCleaner editor
 * plugin.
 *
 * Layout pipeline (see VesperGraphLayout.cpp for details):
 *   1. Exec nodes are split into "function blocks": connected components of
 *      exec wires. Every pure (no-exec) node is owned by the first exec node
 *      it feeds.
 *   2. Each block is laid out left-to-right with every exec wire straight.
 *      The first exec output of a node continues on the same row; every
 *      further output (Branch False, Sequence Then 1+, ...) starts its own
 *      row below, also straight.
 *   3. Data feeders are stacked to the left of the pin they feed, tightly on
 *      the Y axis and biased below the consumer. The first input of each node
 *      is wired straight and the chain above it is aligned recursively.
 *   4. Similar blocks (input events, lifecycle events, custom events sharing
 *      a name prefix, blocks touching the same variables) are grouped. Blocks
 *      and groups are stacked vertically and wrapped in titled comment boxes.
 *
 * Tunables live in DefaultEditor.ini under [VesperNodeCleaner] (see the
 * FSettings struct in the .cpp for the key names and defaults).
 */
class VESPERNODECLEANER_API FVesperGraphLayout
{
public:
	/**
	 * Formats the currently selected nodes in the focused Blueprint graph.
	 * If fewer than 2 nodes are selected, formats the whole focused graph.
	 * Fully undoable.
	 */
	static void FormatSelectedNodes();

	/**
	 * Same pipeline as FormatSelectedNodes(), but takes an explicit node list
	 * and does not touch notifications. Used by the Monolith MCP bridge. If a
	 * graph editor showing this graph is open, the real on-screen node sizes
	 * are measured. Otherwise sizes are estimated.
	 * Returns the number of nodes repositioned (0 if fewer than 2 nodes).
	 * The caller is responsible for the transaction and for calling Modify().
	 */
	static int32 FormatNodes(const TArray<UEdGraphNode*>& Nodes);

	/**
	 * Resizes every selected Comment node so its bounding box tightly wraps
	 * the nodes currently contained within it, plus a small padding margin.
	 * Requires at least 1 selected Comment node. Fully undoable.
	 */
	static void AutoFitSelectedComments();

	/**
	 * Hooks a global Slate focus-change delegate so the plugin remembers the
	 * last Graph Editor that held keyboard focus (toolbar clicks steal focus
	 * before the command handler runs). Call once from StartupModule().
	 */
	static void RegisterFocusTracking();

	/** Unhooks the delegate registered by RegisterFocusTracking(). Call from ShutdownModule(). */
	static void UnregisterFocusTracking();

private:
	/** Walks the current keyboard focus path to find the active SGraphEditor, if any. */
	static TSharedPtr<SGraphEditor> GetActiveGraphEditor();

	/** Shared implementation. Panel may be null, in which case sizes are estimated. */
	static int32 FormatNodesInternal(const TArray<UEdGraphNode*>& Nodes, SGraphPanel* Panel);
};

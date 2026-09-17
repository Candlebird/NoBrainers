#pragma once

#include "CoreMinimal.h"
#include "Features/IModularFeature.h"
#include "Features/IModularFeatures.h"

class UEdGraph;

/**
 * Abstract interface for the optional Vesper Node Cleaner bridge, letting
 * blueprint_query's auto_layout action drive the actual paid Vesper plugin
 * ("Clean Graph") headlessly instead of only Monolith's own built-in
 * Sugiyama formatter.
 *
 * Deliberately its own IModularFeature rather than folded into
 * IMonolithGraphFormatter: that interface's Get() only ever returns the
 * first registered provider, which is fine when there's one "best available"
 * formatter (built-in vs. Blueprint Assist), but Vesper needs to remain
 * independently selectable via its own `formatter: "vesper"` value even
 * when a Blueprint Assist bridge is also registered.
 *
 * MonolithVesperBridge is the canonical (and, as of now, only) implementation.
 * Consumers call IsAvailable() then Get().FormatNodes() -- zero Vesper
 * dependency for callers that don't need it.
 */
class IMonolithVesperFormatter : public IModularFeature
{
public:
	static FName GetModularFeatureName()
	{
		static const FName Name(TEXT("MonolithVesperFormatter"));
		return Name;
	}

	/**
	 * Formats nodes in Graph using Vesper's own layout pipeline (the same
	 * code path as its "Clean Graph" toolbar button). Unlike
	 * IMonolithGraphFormatter::FormatGraph(), Graph does NOT need to be open
	 * in an editor tab -- Vesper's layout only ever touches the UEdGraphNode
	 * data model, never live Slate widgets.
	 *
	 * @param Graph              The graph to format.
	 * @param NodeNames          If non-empty, only format the nodes whose
	 *                           GetName() is in this set; if empty, format
	 *                           every layoutable node in the graph.
	 * @param OutNodesFormatted  Number of nodes repositioned.
	 * @param OutErrorMessage    Populated on failure (e.g. fewer than 2
	 *                           matching nodes found).
	 * @return true on success.
	 */
	virtual bool FormatNodes(
		UEdGraph* Graph,
		const TSet<FString>& NodeNames,
		int32& OutNodesFormatted,
		FString& OutErrorMessage) = 0;

	// --- Static helpers for consumers ---

	/** Check if the Vesper formatter bridge is registered and active. */
	static bool IsAvailable()
	{
		return IModularFeatures::Get().IsModularFeatureAvailable(GetModularFeatureName());
	}

	/** Get the registered formatter (check IsAvailable() first!). */
	static IMonolithVesperFormatter& Get()
	{
		return IModularFeatures::Get().GetModularFeature<IMonolithVesperFormatter>(
			GetModularFeatureName());
	}
};

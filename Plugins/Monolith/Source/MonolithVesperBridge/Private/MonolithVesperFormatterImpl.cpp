#include "MonolithVesperFormatterImpl.h"

DEFINE_LOG_CATEGORY(LogMonolithVesperBridge);

#if WITH_VESPER_NODE_CLEANER

#include "VesperGraphLayout.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "ScopedTransaction.h"

bool FMonolithVesperFormatterImpl::FormatNodes(UEdGraph* Graph, const TSet<FString>& NodeNames,
	int32& OutNodesFormatted, FString& OutErrorMessage)
{
	OutNodesFormatted = 0;

	if (!Graph)
	{
		OutErrorMessage = TEXT("No graph provided.");
		return false;
	}

	TArray<UEdGraphNode*> TargetNodes;
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (!Node)
		{
			continue;
		}
		if (NodeNames.Num() == 0 || NodeNames.Contains(Node->GetName()))
		{
			TargetNodes.Add(Node);
		}
	}

	if (TargetNodes.Num() < 2)
	{
		OutErrorMessage = FString::Printf(
			TEXT("Vesper needs at least 2 matching nodes to format (found %d)."), TargetNodes.Num());
		return false;
	}

	const FScopedTransaction Transaction(FText::FromString(TEXT("Vesper: Format Nodes (Monolith)")));
	Graph->Modify();
	for (UEdGraphNode* Node : TargetNodes)
	{
		Node->Modify();
	}

	OutNodesFormatted = FVesperGraphLayout::FormatNodes(TargetNodes);
	Graph->NotifyGraphChanged();

	if (OutNodesFormatted <= 0)
	{
		OutErrorMessage = TEXT("Vesper's layout pipeline reported 0 nodes formatted.");
		return false;
	}

	return true;
}

#endif // WITH_VESPER_NODE_CLEANER

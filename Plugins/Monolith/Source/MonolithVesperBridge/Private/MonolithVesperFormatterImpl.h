#pragma once
#include "IMonolithVesperFormatter.h"

DECLARE_LOG_CATEGORY_EXTERN(LogMonolithVesperBridge, Log, All);

#if WITH_VESPER_NODE_CLEANER

class FMonolithVesperFormatterImpl : public IMonolithVesperFormatter
{
public:
	virtual bool FormatNodes(UEdGraph* Graph, const TSet<FString>& NodeNames,
		int32& OutNodesFormatted, FString& OutErrorMessage) override;
};

#endif // WITH_VESPER_NODE_CLEANER

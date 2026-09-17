#include "Modules/ModuleManager.h"
#include "IMonolithVesperFormatter.h"
#include "MonolithVesperFormatterImpl.h"

class FMonolithVesperBridgeModule : public IModuleInterface
{
public:
	virtual void StartupModule() override
	{
#if WITH_VESPER_NODE_CLEANER
		Formatter = MakeUnique<FMonolithVesperFormatterImpl>();
		IModularFeatures::Get().RegisterModularFeature(
			IMonolithVesperFormatter::GetModularFeatureName(),
			Formatter.Get());
		UE_LOG(LogMonolithVesperBridge, Log,
			TEXT("MonolithVesperBridge: Registered Vesper graph formatter"));
#else
		UE_LOG(LogMonolithVesperBridge, Log,
			TEXT("MonolithVesperBridge: Vesper Node Cleaner not found at compile time, bridge inactive"));
#endif
	}

	virtual void ShutdownModule() override
	{
#if WITH_VESPER_NODE_CLEANER
		if (Formatter.IsValid())
		{
			IModularFeatures::Get().UnregisterModularFeature(
				IMonolithVesperFormatter::GetModularFeatureName(),
				Formatter.Get());
			Formatter.Reset();
		}
#endif
	}

private:
#if WITH_VESPER_NODE_CLEANER
	TUniquePtr<FMonolithVesperFormatterImpl> Formatter;
#endif
};

IMPLEMENT_MODULE(FMonolithVesperBridgeModule, MonolithVesperBridge)

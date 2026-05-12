using UnrealBuildTool;

public class Peregrine : ModuleRules
{
    public Peregrine(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new string[] {
                "Core",
                "CoreUObject",
                "Engine",
                "InputCore",
                "AirSim"
            }
        );
    }
}

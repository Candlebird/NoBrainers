# Rebuilds the NoBrainers editor target (game module + project plugins such as
# VesperNodeCleaner / Monolith) with UBT, then relaunches the editor.
#
# Use this after C++ header changes or plugin changes that Live Coding can't
# hot-patch. Closing the editor discards unsaved changes, so save first.
#
#   powershell -ExecutionPolicy Bypass -File .claude/monolith/rebuild_editor.ps1
#   powershell -ExecutionPolicy Bypass -File .claude/monolith/rebuild_editor.ps1 -NoLaunch
#   powershell -ExecutionPolicy Bypass -File .claude/monolith/rebuild_editor.ps1 -Clean   # wipes plugin Intermediate first
param(
    [switch]$NoLaunch,
    [switch]$Clean,
    [string]$EngineDir = "C:\Program Files\Epic Games\UE_5.7"
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$UProject = Join-Path $ProjectDir "GASDocumentation.uproject"
$BuildBat = Join-Path $EngineDir "Engine\Build\BatchFiles\Build.bat"
$EditorExe = Join-Path $EngineDir "Engine\Binaries\Win64\UnrealEditor.exe"

# 1. Close the editor (UBT can't overwrite loaded DLLs).
$editor = Get-Process UnrealEditor -ErrorAction SilentlyContinue
if ($editor) {
    Write-Host "Closing Unreal Editor (PID $($editor.Id -join ', '))..."
    $editor | ForEach-Object { $_.CloseMainWindow() | Out-Null }
    try { $editor | Wait-Process -Timeout 60 -ErrorAction Stop } catch { }
    $still = Get-Process UnrealEditor -ErrorAction SilentlyContinue
    if ($still) {
        Write-Host "Editor did not close within 60s (save dialog?), forcing it."
        $still | Stop-Process -Force
        Start-Sleep -Seconds 2
    }
}
Get-Process LiveCodingConsole -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Optional clean of plugin build intermediates.
if ($Clean) {
    foreach ($plugin in @("VesperNodeCleaner")) {
        foreach ($sub in @("Binaries", "Intermediate")) {
            $path = Join-Path $ProjectDir "Plugins\$plugin\$sub"
            if (Test-Path $path) {
                Write-Host "Removing $path"
                Remove-Item -Recurse -Force $path
            }
        }
    }
}

# 3. Build.
Write-Host "Building GASDocumentationEditor Win64 Development..."
& $BuildBat GASDocumentationEditor Win64 Development "-Project=$UProject" -WaitMutex -NoHotReloadFromIDE
if ($LASTEXITCODE -ne 0) {
    Write-Host "BUILD FAILED (exit $LASTEXITCODE). Editor not relaunched."
    exit $LASTEXITCODE
}
Write-Host "BUILD SUCCEEDED"

# 4. Relaunch.
if (-not $NoLaunch) {
    Write-Host "Launching editor..."
    Start-Process -FilePath $EditorExe -ArgumentList "`"$UProject`""
}
exit 0

@echo off
echo Starting Peregrine Unreal Simulation...
echo.

REM Configuration
set UNREAL_PROJECT_PATH=%~dp0..\..\unreal\Peregrine.uproject
set AIRSIM_SETTINGS=%~dp0..\..\unreal\AirSim\settings.json

REM Check if project exists
if not exist "%UNREAL_PROJECT_PATH%" (
    echo ERROR: Unreal project not found at %UNREAL_PROJECT_PATH%
    exit /b 1
)

REM Check if AirSim settings exist
if not exist "%AIRSIM_SETTINGS%" (
    echo WARNING: AirSim settings not found at %AIRSIM_SETTINGS%
    echo Using default settings.
)

echo Starting Unreal Engine Editor...
echo Project: %UNREAL_PROJECT_PATH%
echo.

REM Launch Unreal Editor with the Peregrine project
start "" "UnrealEditor.exe" "%UNREAL_PROJECT_PATH%"

echo.
echo Unreal Editor launched. Please:
echo 1. Press "Play" in the Unreal Editor to start AirSim simulation
echo 2. Select "Fly" or "Sim" mode as needed
echo 3. Run 'scripts\start_peregrine.bat' to start the ROS 2 stack
echo.
echo To run headless (no editor window):
echo   Use 'AirSimExe.exe' from AirSim binaries
echo.
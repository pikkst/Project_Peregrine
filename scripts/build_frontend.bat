@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0\..\ui"
if not exist node_modules (
  echo Installing frontend dependencies...
  npm install
)
echo Building frontend...
npm run build
echo Frontend built to ui\dist

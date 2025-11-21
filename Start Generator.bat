@echo off
:: Get the current directory
set "BASE_DIR=%~dp0"

:: Run the script using the full python copy
"%BASE_DIR%bin\python.exe" "%BASE_DIR%Generator.py"
pause
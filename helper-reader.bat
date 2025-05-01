@echo off
setlocal enabledelayedexpansion

:: Exclude common special directories
set EXCLUDED_DIRS=venv .venv .git __pycache__ node_modules

:: Find all .py files and filter out excluded directories
for /f "delims=" %%F in ('dir /s /b *.py ^| findstr /v /i /c:"\\venv\\" /c:"\\.venv\\" /c:"\\.git\\" /c:"\\__pycache__\\" /c:"\\node_modules\\"') do (
    echo [FILE] %%F
    type "%%F"
    echo(
    echo -------------------------------
    echo(
)

endlocal
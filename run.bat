@echo off
call .venv\Scripts\activate.bat

echo Starting Telerium Pokemon Bot...
echo Press Ctrl+C to gracefully shut down at any time.
echo.

python main.py
set EXIT_CODE=%errorlevel%

if %EXIT_CODE% neq 0 (
    echo.
    echo Program exited with code %EXIT_CODE%
    echo.
    pause
)

exit /b %EXIT_CODE%

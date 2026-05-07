@echo off
echo Setting up Python Virtual Environment...

:: 1. Create virtual environment if it doesn't exist
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
) else (
    echo Virtual environment already exists.
)

:: 2. Activate the environment and install requirements
echo Activating environment and installing requirements...
call .venv\Scripts\activate && python -m pip install --upgrade pip && pip install -r requirements.txt

echo.
echo Setup Complete!
pause
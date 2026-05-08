@echo off
title Business Data Analyzer

echo =====================================
echo Business Data Analyzer
echo =====================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed.
    echo Please install Python from:
    echo https://www.python.org/downloads/
    pause
    exit
)

REM Create virtual environment
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate environment
call venv\Scripts\activate

REM First-time dependency install
if not exist venv\installed.flag (

    echo Installing dependencies...
    
    python -m pip install --upgrade pip
    pip install -r requirements.txt

    echo done > venv\installed.flag
)

REM Launch app
echo Launching app...
streamlit run app.py

pause
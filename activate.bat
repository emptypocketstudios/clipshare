@echo off
REM Batch script to activate the virtual environment
echo Checking virtual environment...

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Creating new virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment!
        echo Make sure Python is installed and accessible.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
)

REM Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if activation was successful
if defined VIRTUAL_ENV (
    echo Virtual environment activated!
    python --version
    pip --version
    echo.
    
    REM Check if requirements.txt exists and install requirements
    if exist "requirements.txt" (
        echo Installing requirements...
        pip install -r requirements.txt
        if errorlevel 1 (
            echo Failed to install some requirements!
        ) else (
            echo Requirements installed successfully!
        )
    ) else (
        echo No requirements.txt found. Skipping package installation.
    )
    
    echo.
    echo To deactivate, run: deactivate
) else (
    echo Failed to activate virtual environment!
    echo Make sure the virtual environment exists at venv\
    pause
) 
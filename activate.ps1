# PowerShell script to activate the virtual environment
Write-Host "Checking virtual environment..." -ForegroundColor Green

# Check if virtual environment exists
if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "Virtual environment not found. Creating new virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment!" -ForegroundColor Red
        Write-Host "Make sure Python is installed and accessible." -ForegroundColor Red
        exit 1
    }
    Write-Host "Virtual environment created successfully!" -ForegroundColor Green
}

# Activate the virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
& ".\venv\Scripts\Activate.ps1"

# Check if activation was successful
if ($env:VIRTUAL_ENV) {
    Write-Host "Virtual environment activated!" -ForegroundColor Green
    Write-Host "Python version: $(python --version)" -ForegroundColor Cyan
    Write-Host "Pip version: $(pip --version)" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if requirements.txt exists and install requirements
    if (Test-Path "requirements.txt") {
        Write-Host "Installing requirements..." -ForegroundColor Yellow
        pip install -r requirements.txt
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Requirements installed successfully!" -ForegroundColor Green
        } else {
            Write-Host "Failed to install some requirements!" -ForegroundColor Red
        }
    } else {
        Write-Host "No requirements.txt found. Skipping package installation." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "To deactivate, run: deactivate" -ForegroundColor Yellow
} else {
    Write-Host "Failed to activate virtual environment!" -ForegroundColor Red
    Write-Host "Make sure the virtual environment exists at .\venv\" -ForegroundColor Red
} 
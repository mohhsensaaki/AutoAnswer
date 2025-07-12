# ==================================================================
# Deployment Script for NewAfzzinaAI FastAPI Application (Windows)
# ==================================================================

param(
    [switch]$AsService = $false,
    [switch]$Help = $false
)

# Configuration
$ProjectName = "NewAfzzinaAI"
$VenvName = "env"
$PythonMinVersion = "3.8"
$ServicePort = 8000

# Colors for output
$Red = [ConsoleColor]::Red
$Green = [ConsoleColor]::Green
$Yellow = [ConsoleColor]::Yellow
$Blue = [ConsoleColor]::Blue
$White = [ConsoleColor]::White

# Get project directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir

function Write-ColoredOutput {
    param(
        [string]$Message,
        [ConsoleColor]$Color = $White,
        [string]$Prefix = ""
    )
    
    if ($Prefix) {
        Write-Host "[$Prefix] " -ForegroundColor $Color -NoNewline
    }
    Write-Host $Message -ForegroundColor $Color
}

function Write-Status {
    param([string]$Message)
    Write-ColoredOutput -Message $Message -Color $Green -Prefix "INFO"
}

function Write-Warning {
    param([string]$Message)
    Write-ColoredOutput -Message $Message -Color $Yellow -Prefix "WARNING"
}

function Write-Error {
    param([string]$Message)
    Write-ColoredOutput -Message $Message -Color $Red -Prefix "ERROR"
}

function Show-Help {
    Write-Host ""
    Write-Host "NewAfzzinaAI Deployment Script for Windows" -ForegroundColor $Blue
    Write-Host "==========================================" -ForegroundColor $Blue
    Write-Host ""
    Write-Host "Usage: .\deploy.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -AsService    Create and start as Windows service (requires admin)"
    Write-Host "  -Help         Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\deploy.ps1                 # Deploy and run directly"
    Write-Host "  .\deploy.ps1 -AsService      # Deploy as Windows service"
    Write-Host ""
    exit 0
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Compare-Version {
    param(
        [string]$Version1,
        [string]$Version2
    )
    
    $v1 = [version]$Version1
    $v2 = [version]$Version2
    
    return $v1.CompareTo($v2)
}

if ($Help) {
    Show-Help
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor $Blue
Write-Host "           Deploying $ProjectName FastAPI Application" -ForegroundColor $Blue
Write-Host "==================================================================" -ForegroundColor $Blue
Write-Host ""

# Step 1: Check if Python is installed
Write-Status "Checking Python installation..."
try {
    $pythonVersion = (python --version 2>&1) -replace "Python ", ""
    Write-Status "Found Python version: $pythonVersion"
    
    if ((Compare-Version $pythonVersion $PythonMinVersion) -lt 0) {
        Write-Error "Python version $pythonVersion is too old. Please install Python $PythonMinVersion or higher."
        Write-Error "Visit https://www.python.org/downloads/ to download Python."
        exit 1
    }
    
    Write-Status "Python version check passed ✓"
} catch {
    Write-Error "Python is not installed or not in PATH. Please install Python $PythonMinVersion or higher."
    Write-Error "Visit https://www.python.org/downloads/ to download Python."
    exit 1
}

# Step 2: Check if pip is installed
Write-Status "Checking pip installation..."
try {
    $pipVersion = python -m pip --version
    Write-Status "pip is available ✓"
} catch {
    Write-Error "pip is not installed. Please install pip."
    exit 1
}

# Step 3: Navigate to project directory
Write-Status "Navigating to project directory: $ProjectDir"
Set-Location $ProjectDir

# Step 4: Create virtual environment
Write-Status "Setting up virtual environment..."
if (-not (Test-Path $VenvName)) {
    Write-Status "Creating virtual environment '$VenvName'..."
    python -m venv $VenvName
    Write-Status "Virtual environment created ✓"
} else {
    Write-Warning "Virtual environment '$VenvName' already exists. Skipping creation."
}

# Step 5: Activate virtual environment
Write-Status "Activating virtual environment..."
$activateScript = Join-Path $VenvName "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    Write-Status "Virtual environment activated ✓"
} else {
    Write-Error "Failed to find activation script at: $activateScript"
    exit 1
}

# Step 6: Upgrade pip
Write-Status "Upgrading pip..."
python -m pip install --upgrade pip

# Step 7: Install dependencies
Write-Status "Installing dependencies from requirements.txt..."
if (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt
    Write-Status "Dependencies installed ✓"
} else {
    Write-Error "requirements.txt not found in project directory!"
    exit 1
}

# Step 8: Setup as service or run directly
if ($AsService) {
    if (-not (Test-Administrator)) {
        Write-Error "Administrator privileges required to create Windows service."
        Write-Error "Please run PowerShell as Administrator and try again."
        exit 1
    }
    
    Write-Status "Setting up Windows service..."
    
    # Install NSSM (Non-Sucking Service Manager) if not available
    if (-not (Get-Command "nssm" -ErrorAction SilentlyContinue)) {
        Write-Warning "NSSM is not installed. Installing via winget..."
        try {
            winget install NSSM
            Write-Status "NSSM installed ✓"
        } catch {
            Write-Error "Failed to install NSSM. Please install it manually from https://nssm.cc/"
            Write-Error "Or run without -AsService flag to run directly."
            exit 1
        }
    }
    
    $serviceName = "NewAfzzinaAI"
    $pythonPath = Join-Path $ProjectDir "$VenvName\Scripts\python.exe"
    $mainPath = Join-Path $ProjectDir "main.py"
    
    # Remove existing service if it exists
    $existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Status "Removing existing service..."
        Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
        nssm remove $serviceName confirm
    }
    
    # Create new service
    Write-Status "Creating Windows service '$serviceName'..."
    nssm install $serviceName $pythonPath $mainPath
    nssm set $serviceName AppDirectory $ProjectDir
    nssm set $serviceName DisplayName "NewAfzzinaAI FastAPI Service"
    nssm set $serviceName Description "FastAPI application for NewAfzzinaAI"
    nssm set $serviceName Start SERVICE_AUTO_START
    
    # Start the service
    Write-Status "Starting service..."
    Start-Service -Name $serviceName
    
    $serviceStatus = Get-Service -Name $serviceName
    if ($serviceStatus.Status -eq "Running") {
        Write-Status "Service is running ✓"
    } else {
        Write-Error "Service failed to start. Check Windows Event Viewer for details."
        exit 1
    }
    
} else {
    Write-Status "Starting application directly..."
    Write-Status "Application will run on port $ServicePort"
    Write-Status "Press Ctrl+C to stop the application"
    Write-Host ""
    
    # Create a batch file to run the application
    $batchContent = @"
@echo off
cd /d "$ProjectDir"
call "$VenvName\Scripts\activate.bat"
python main.py
pause
"@
    
    $batchFile = Join-Path $ProjectDir "run_app.bat"
    $batchContent | Out-File -FilePath $batchFile -Encoding ASCII
    
    Write-Status "Created run_app.bat for easy execution"
    Write-Status "Starting application..."
    
    # Start the application
    Start-Process -FilePath "python" -ArgumentList "main.py" -NoNewWindow
    
    Write-Status "Application started! Check if it's running on http://localhost:$ServicePort"
}

# Step 9: Display useful information
Write-Host ""
Write-Host "==================================================================" -ForegroundColor $Blue
Write-Host "                    Deployment Complete!" -ForegroundColor $Green
Write-Host "==================================================================" -ForegroundColor $Blue
Write-Host ""
Write-Status "Application Details:"
Write-Host "  • Project Directory: $ProjectDir"
Write-Host "  • Virtual Environment: $ProjectDir\$VenvName"
Write-Host "  • Application URL: http://localhost:$ServicePort"
Write-Host "  • Health Check: http://localhost:$ServicePort/health"
Write-Host "  • API Documentation: http://localhost:$ServicePort/docs"
Write-Host ""

if ($AsService) {
    Write-Status "Service Management Commands:"
    Write-Host "  • Start service: Start-Service -Name NewAfzzinaAI"
    Write-Host "  • Stop service: Stop-Service -Name NewAfzzinaAI"
    Write-Host "  • Restart service: Restart-Service -Name NewAfzzinaAI"
    Write-Host "  • Check status: Get-Service -Name NewAfzzinaAI"
    Write-Host ""
} else {
    Write-Status "To run the application again:"
    Write-Host "  • Run: .\run_app.bat"
    Write-Host "  • Or: .\scripts\deploy.ps1"
    Write-Host ""
}

Write-Status "To test the API, try:"
Write-Host "  Invoke-RestMethod -Uri http://localhost:$ServicePort/health"
Write-Host ""
Write-Host "Happy coding! 🚀" -ForegroundColor $Green 
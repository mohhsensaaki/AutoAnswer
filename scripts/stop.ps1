# ==================================================================
# Stop Script for NewAfzzinaAI FastAPI Application (Windows)
# ==================================================================

param(
    [switch]$Help = $false
)

# Colors for output
$Red = [ConsoleColor]::Red
$Green = [ConsoleColor]::Green
$Yellow = [ConsoleColor]::Yellow
$Blue = [ConsoleColor]::Blue
$White = [ConsoleColor]::White

# Configuration
$ServiceName = "NewAfzzinaAI"
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
    Write-Host "NewAfzzinaAI Stop Script for Windows" -ForegroundColor $Blue
    Write-Host "===================================" -ForegroundColor $Blue
    Write-Host ""
    Write-Host "Usage: .\stop.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Help         Show this help message"
    Write-Host ""
    Write-Host "This script will:"
    Write-Host "  1. Stop the Windows service if it exists"
    Write-Host "  2. Stop any running Python processes for main.py"
    Write-Host "  3. Clean up temporary files"
    Write-Host ""
    exit 0
}

if ($Help) {
    Show-Help
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor $Blue
Write-Host "           Stopping NewAfzzinaAI FastAPI Application" -ForegroundColor $Blue
Write-Host "==================================================================" -ForegroundColor $Blue
Write-Host ""

# Check if service exists and stop it
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service) {
    Write-Status "Found Windows service '$ServiceName'"
    
    if ($service.Status -eq "Running") {
        Write-Status "Stopping service..."
        try {
            Stop-Service -Name $ServiceName -Force
            Write-Status "Service stopped ✓"
        } catch {
            Write-Error "Failed to stop service: $_"
        }
    } else {
        Write-Warning "Service was not running"
    }
    
    # Ask if user wants to remove the service
    $removeService = Read-Host "Do you want to remove the service completely? (y/N)"
    if ($removeService -match "^[Yy]") {
        try {
            if (Get-Command "nssm" -ErrorAction SilentlyContinue) {
                nssm remove $ServiceName confirm
                Write-Status "Service removed ✓"
            } else {
                Write-Warning "NSSM not found. Please remove the service manually."
            }
        } catch {
            Write-Error "Failed to remove service: $_"
        }
    }
} else {
    Write-Warning "No Windows service found with name '$ServiceName'"
}

# Stop any running Python processes for main.py
Write-Status "Checking for running Python processes..."
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*main.py*"
}

if ($pythonProcesses) {
    Write-Status "Found $($pythonProcesses.Count) Python process(es) running main.py"
    foreach ($process in $pythonProcesses) {
        try {
            Write-Status "Stopping process PID: $($process.Id)"
            Stop-Process -Id $process.Id -Force
            Write-Status "Process stopped ✓"
        } catch {
            Write-Error "Failed to stop process $($process.Id): $_"
        }
    }
} else {
    Write-Warning "No Python processes running main.py found"
}

# Clean up temporary files
Write-Status "Cleaning up temporary files..."
Set-Location $ProjectDir

$filesToClean = @(
    "run_app.bat",
    "app.log",
    "*.pid"
)

foreach ($pattern in $filesToClean) {
    $files = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue
    if ($files) {
        $cleanFiles = Read-Host "Remove $($files.Count) file(s) matching '$pattern'? (y/N)"
        if ($cleanFiles -match "^[Yy]") {
            try {
                Remove-Item -Path $pattern -Force
                Write-Status "Cleaned up files matching '$pattern' ✓"
            } catch {
                Write-Warning "Failed to clean up '$pattern': $_"
            }
        }
    }
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor $Blue
Write-Host "                    Stop Complete!" -ForegroundColor $Green
Write-Host "==================================================================" -ForegroundColor $Blue
Write-Host ""
Write-Status "Application stopped successfully! 🛑"
Write-Host ""
Write-Status "To start the application again:"
Write-Host "  • Run: .\scripts\deploy.ps1"
Write-Host "  • Or as service: .\scripts\deploy.ps1 -AsService"
Write-Host "" 
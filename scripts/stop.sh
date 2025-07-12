#!/bin/bash

# ==================================================================
# Stop Script for NewAfzzinaAI FastAPI Application
# ==================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="newafzzinaai"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${BLUE}===================================================================${NC}"
echo -e "${BLUE}           Stopping NewAfzzinaAI FastAPI Application${NC}"
echo -e "${BLUE}===================================================================${NC}"

# Check if service exists and stop it
if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
    print_status "Stopping systemd service..."
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        sudo systemctl stop "$SERVICE_NAME"
        print_status "Service stopped ✓"
    else
        print_warning "Service was not running"
    fi
    
    # Optionally disable the service
    read -p "Do you want to disable the service from auto-starting? (y/N): " disable_service
    if [[ $disable_service =~ ^[Yy]$ ]]; then
        sudo systemctl disable "$SERVICE_NAME"
        print_status "Service disabled ✓"
    fi
    
    # Optionally remove the service file
    read -p "Do you want to remove the service file completely? (y/N): " remove_service
    if [[ $remove_service =~ ^[Yy]$ ]]; then
        sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
        sudo systemctl daemon-reload
        print_status "Service file removed ✓"
    fi
else
    print_warning "No systemd service found. Checking for direct process..."
    
    # Check if there's a PID file from direct execution
    if [ -f "$PROJECT_DIR/app.pid" ]; then
        APP_PID=$(cat "$PROJECT_DIR/app.pid")
        if ps -p "$APP_PID" > /dev/null 2>&1; then
            print_status "Stopping application process (PID: $APP_PID)..."
            kill "$APP_PID"
            print_status "Application stopped ✓"
        else
            print_warning "Process with PID $APP_PID is not running"
        fi
        rm -f "$PROJECT_DIR/app.pid"
    else
        print_warning "No PID file found. Checking for running Python processes..."
        
        # Look for main.py processes
        MAIN_PIDS=$(pgrep -f "python.*main.py" || true)
        if [ -n "$MAIN_PIDS" ]; then
            print_status "Found running main.py processes: $MAIN_PIDS"
            echo "$MAIN_PIDS" | xargs kill
            print_status "Processes stopped ✓"
        else
            print_warning "No running main.py processes found"
        fi
    fi
fi

# Clean up log files if they exist
if [ -f "$PROJECT_DIR/app.log" ]; then
    read -p "Do you want to remove the log file? (y/N): " remove_log
    if [[ $remove_log =~ ^[Yy]$ ]]; then
        rm -f "$PROJECT_DIR/app.log"
        print_status "Log file removed ✓"
    fi
fi

echo ""
echo -e "${GREEN}Application stopped successfully! 🛑${NC}"
echo ""
print_status "To start the application again, run:"
echo "  ./scripts/deploy.sh"
echo "" 
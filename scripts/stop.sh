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
TELEGRAM_SERVICE_NAME="newafzzinaai-telegram"
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

# Function to stop a systemd service
stop_service() {
    local svc_name=$1
    local svc_desc=$2
    
    if systemctl list-unit-files | grep -q "${svc_name}.service"; then
        print_status "Stopping $svc_desc service..."
        if sudo systemctl is-active --quiet "$svc_name"; then
            sudo systemctl stop "$svc_name"
            print_status "$svc_desc service stopped ✓"
        else
            print_warning "$svc_desc service was not running"
        fi
    else
        print_warning "No $svc_desc systemd service found"
    fi
}

# Stop both services
stop_service "$SERVICE_NAME" "Main API"
stop_service "$TELEGRAM_SERVICE_NAME" "Telegram Listener"

# Check if main service exists for disable/remove options
if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
    # Optionally disable the services
    read -p "Do you want to disable services from auto-starting? (y/N): " disable_service
    if [[ $disable_service =~ ^[Yy]$ ]]; then
        sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        sudo systemctl disable "$TELEGRAM_SERVICE_NAME" 2>/dev/null || true
        print_status "Services disabled ✓"
    fi
    
    # Optionally remove the service files
    read -p "Do you want to remove the service files completely? (y/N): " remove_service
    if [[ $remove_service =~ ^[Yy]$ ]]; then
        sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
        sudo rm -f "/etc/systemd/system/${TELEGRAM_SERVICE_NAME}.service"
        sudo systemctl daemon-reload
        print_status "Service files removed ✓"
    fi
else
    print_warning "No systemd services found. Checking for direct processes..."
    
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
            print_status "main.py processes stopped ✓"
        else
            print_warning "No running main.py processes found"
        fi
        
        # Look for telegramlistener.py processes
        TELEGRAM_PIDS=$(pgrep -f "python.*telegramlistener.py" || true)
        if [ -n "$TELEGRAM_PIDS" ]; then
            print_status "Found running telegramlistener.py processes: $TELEGRAM_PIDS"
            echo "$TELEGRAM_PIDS" | xargs kill
            print_status "telegramlistener.py processes stopped ✓"
        else
            print_warning "No running telegramlistener.py processes found"
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
echo -e "${GREEN}All services stopped successfully! 🛑${NC}"
echo ""
print_status "To start the services again, run:"
echo "  ./scripts/deploy.sh"
echo ""
print_status "Or start individual services:"
echo "  sudo systemctl start $SERVICE_NAME"
echo "  sudo systemctl start $TELEGRAM_SERVICE_NAME"
echo "" 
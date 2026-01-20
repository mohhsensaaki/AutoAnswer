#!/bin/bash

# ==================================================================
# Deployment Script for NewAfzzinaAI FastAPI Application
# 
# This script:
# 1. Collects environment variables from user (Database, OpenAI, etc.)
# 2. Creates .env file with configuration
# 3. Installs requirements in virtual environment
# 4. Creates and starts systemd service for main.py
# deploy new feature
# ==================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="NewAfzzinaAI"
VENV_NAME="env"
SERVICE_NAME="newafzzinaai"
TELEGRAM_SERVICE_NAME="newafzzinaai-telegram"
SERVICE_USER=$(whoami)
SERVICE_PORT=8110

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}===================================================================${NC}"
echo -e "${BLUE}           Deploying $PROJECT_NAME FastAPI Application${NC}"
echo -e "${BLUE}===================================================================${NC}"

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 3: Navigate to project directory
print_status "Navigating to project directory: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Step 4: Check if Python3 is available
if ! command_exists python3; then
    print_error "Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi
print_status "Python 3 found ✓"

# Step 5: Create virtual environment
print_status "Setting up virtual environment..."
if [ ! -d "$VENV_NAME" ]; then
    print_status "Creating virtual environment '$VENV_NAME'..."
    python3 -m venv "$VENV_NAME"
    print_status "Virtual environment created ✓"
else
    print_warning "Virtual environment '$VENV_NAME' already exists. Skipping creation."
fi

# Step 6: Activate virtual environment
print_status "Activating virtual environment..."
source "$VENV_NAME/bin/activate"
print_status "Virtual environment activated ✓"

# Step 7: Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Step 8: Install dependencies
print_status "Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_status "Dependencies installed ✓"
else
    print_error "requirements.txt not found in project directory!"
    exit 1
fi

# Step 8.5: Validate required files exist
print_status "Validating required files..."
if [ ! -f "$PROJECT_DIR/main.py" ]; then
    print_error "main.py not found in $PROJECT_DIR"
    exit 1
fi
print_status "main.py found ✓"

if [ ! -f "$PROJECT_DIR/telegramlistener.py" ]; then
    print_error "telegramlistener.py not found in $PROJECT_DIR"
    exit 1
fi
print_status "telegramlistener.py found ✓"

if [ ! -f "$PROJECT_DIR/.env" ]; then
    print_warning ".env file not found. Creating a minimal .env file..."
    cat > "$PROJECT_DIR/.env" <<ENVEOF
# Telegram API credentials
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
SESSION_NAME=telegram_user_session
CALLBACK_URL=
CALLBACK_TIMEOUT=10
CALLBACK_RETRIES=3
ENABLE_MEDIA_DOWNLOAD=true
MAX_MEDIA_SIZE=10
MEDIA_GROUP_TIMEOUT=5.0
DOWNLOAD_MEDIA_TYPES=all

# Service configuration
SERVICE_PORT=8110
IS_PRODUCTION=no
LOG_URL=.

# Swagger credentials
SWAGGER_USERNAME=admin
SWAGGER_PASSWORD=admin
ENVEOF
    print_warning "Please edit $PROJECT_DIR/.env and fill in required values before starting services"
else
    print_status ".env file found ✓"
fi

# Validate Python executable exists
PYTHON_EXEC="$PROJECT_DIR/$VENV_NAME/bin/python"
if [ ! -f "$PYTHON_EXEC" ]; then
    print_error "Python executable not found at $PYTHON_EXEC"
    exit 1
fi
print_status "Python executable found ✓"

# Step 9: Create and start systemd service
print_status "Creating systemd service..."
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=$PROJECT_NAME FastAPI Application
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/$VENV_NAME/bin
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/$VENV_NAME/bin/python $PROJECT_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

print_status "Systemd service file created ✓"

# Step 10: Create and start Telegram Listener systemd service
print_status "Creating Telegram Listener systemd service..."
TELEGRAM_SERVICE_FILE="/etc/systemd/system/${TELEGRAM_SERVICE_NAME}.service"

sudo tee "$TELEGRAM_SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=$PROJECT_NAME Telegram Listener
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/$VENV_NAME/bin
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/$VENV_NAME/bin/python $PROJECT_DIR/telegramlistener.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

print_status "Telegram Listener systemd service file created ✓"

# Reload systemd and enable the services
print_status "Reloading systemd daemon..."
sudo systemctl daemon-reload

print_status "Enabling $SERVICE_NAME service..."
sudo systemctl enable "$SERVICE_NAME"

print_status "Enabling $TELEGRAM_SERVICE_NAME service..."
sudo systemctl enable "$TELEGRAM_SERVICE_NAME"

print_status "Starting $SERVICE_NAME service..."
sudo systemctl start "$SERVICE_NAME"

print_status "Starting $TELEGRAM_SERVICE_NAME service..."
sudo systemctl start "$TELEGRAM_SERVICE_NAME"

# Wait a moment for the services to start
sleep 5

# Check main service status
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    print_status "Main service is running ✓"
else
    print_error "Main service failed to start!"
    print_error "Service logs:"
    sudo journalctl -u "$SERVICE_NAME" --no-pager -n 20
    print_error "Check logs with: sudo journalctl -u $SERVICE_NAME -f"
    exit 1
fi

# Check telegram listener service status
if sudo systemctl is-active --quiet "$TELEGRAM_SERVICE_NAME"; then
    print_status "Telegram Listener service is running ✓"
else
    print_error "Telegram Listener service failed to start!"
    print_error "Service logs:"
    sudo journalctl -u "$TELEGRAM_SERVICE_NAME" --no-pager -n 20
    print_error "Check logs with: sudo journalctl -u $TELEGRAM_SERVICE_NAME -f"
    exit 1
fi

print_status "Services status:"
sudo systemctl status "$SERVICE_NAME" --no-pager -l
sudo systemctl status "$TELEGRAM_SERVICE_NAME" --no-pager -l

# Step 10: Display useful information
echo ""
echo -e "${BLUE}===================================================================${NC}"
echo -e "${GREEN}                    Deployment Complete!${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo ""
print_status "Application Details:"
echo "  • Project Directory: $PROJECT_DIR"
echo "  • Virtual Environment: $PROJECT_DIR/$VENV_NAME"
echo "  • Application URL: http://localhost:$SERVICE_PORT"
echo "  • Health Check: http://localhost:$SERVICE_PORT/health"
echo "  • API Documentation: http://localhost:$SERVICE_PORT/docs"
echo "  • Environment File: $PROJECT_DIR/.env"
echo ""
print_status "Configuration Summary:"
echo "  • Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo "  • OpenAI API: Configured ✓"
echo "  • Channel Manager API: Configured ✓"
echo "  • n8n Workflow Service: $N8N_BASE_URL (API Key: ${N8N_API_KEY:+Configured}${N8N_API_KEY:-Not Set})"
echo "  • Production Mode: $IS_PRODUCTION"
echo ""
print_status "Service Management Commands:"
echo "  Main API Service:"
echo "    • Start: sudo systemctl start $SERVICE_NAME"
echo "    • Stop: sudo systemctl stop $SERVICE_NAME"
echo "    • Restart: sudo systemctl restart $SERVICE_NAME"
echo "    • Status: sudo systemctl status $SERVICE_NAME"
echo "    • Logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "  Telegram Listener Service:"
echo "    • Start: sudo systemctl start $TELEGRAM_SERVICE_NAME"
echo "    • Stop: sudo systemctl stop $TELEGRAM_SERVICE_NAME"
echo "    • Restart: sudo systemctl restart $TELEGRAM_SERVICE_NAME"
echo "    • Status: sudo systemctl status $TELEGRAM_SERVICE_NAME"
echo "    • Logs: sudo journalctl -u $TELEGRAM_SERVICE_NAME -f"
echo ""
print_status "To test the API:"
echo "  curl http://localhost:$SERVICE_PORT/health"
echo "  curl http://localhost:$SERVICE_PORT/api/v1/workflow/health"
echo "  curl http://localhost:$SERVICE_PORT/api/v1/workflow/templates"
echo ""
echo -e "${GREEN}Happy services! 🚀${NC}" 

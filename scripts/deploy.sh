#!/bin/bash

# ==================================================================
# Deployment Script for NewAfzzinaAI FastAPI Application
# 
# This script:
# 1. Collects environment variables from user (Database, OpenAI, etc.)
# 2. Creates .env file with configuration
# 3. Installs requirements in virtual environment
# 4. Creates and starts systemd service for main.py
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

# Step 1: Get environment variables from user
print_status "Environment Configuration"
echo "Please provide the following environment variables:"
echo ""

# Database configuration
read -p "Enter Database Host (default: localhost): " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "Enter Database Port (default: 5432): " DB_PORT
DB_PORT=${DB_PORT:-5432}

read -p "Enter Database Name (default: aidb): " DB_NAME
DB_NAME=${DB_NAME:-aidb}

read -p "Enter Database Username (default: admin): " DB_USER
DB_USER=${DB_USER:-admin}

read -s -p "Enter Database Password: " DB_PASSWORD
echo
if [[ -z "$DB_PASSWORD" ]]; then
    print_error "Database password is required!"
    exit 1
fi

# OpenAI Configuration
read -p "Enter OpenAI API Key: " OPENAI_API_KEY
if [[ -z "$OPENAI_API_KEY" ]]; then
    print_error "OpenAI API Key is required!"
    exit 1
fi

read -p "Enter Channel Manager API Key: " CHANNEL_MANAGER_API_KEY
if [[ -z "$CHANNEL_MANAGER_API_KEY" ]]; then
    print_error "Channel Manager API Key is required!"
    exit 1
fi

# Application configuration
read -p "Enter Production mode (yes/no, default: no): " IS_PRODUCTION
IS_PRODUCTION=${IS_PRODUCTION:-no}

read -p "Enter Log directory (default: .): " LOG_URL
LOG_URL=${LOG_URL:-"."}

# Step 2: Create .env file with configuration
print_status "Creating .env file with configuration..."
cat > "$PROJECT_DIR/.env" << EOF
# Database Configuration
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# OpenAI Configuration
OPENAI_API_KEY=$OPENAI_API_KEY

# Channel Manager Configuration
CHANNEL_MANAGER_API_KEY=$CHANNEL_MANAGER_API_KEY

# Application Configuration
IS_PRODUCTION=$IS_PRODUCTION
LOG_URL=$LOG_URL
EOF

print_status ".env file created ✓"

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

# Reload systemd and enable the service
print_status "Reloading systemd daemon..."
sudo systemctl daemon-reload

print_status "Enabling $SERVICE_NAME service..."
sudo systemctl enable "$SERVICE_NAME"

print_status "Starting $SERVICE_NAME service..."
sudo systemctl start "$SERVICE_NAME"

# Wait a moment for the service to start
sleep 5

# Check service status
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    print_status "Service is running ✓"
    print_status "Service status:"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l
else
    print_error "Service failed to start!"
    print_error "Service logs:"
    sudo journalctl -u "$SERVICE_NAME" --no-pager -n 20
    print_error "Check logs with: sudo journalctl -u $SERVICE_NAME -f"
    exit 1
fi

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
echo "  • Production Mode: $IS_PRODUCTION"
echo ""
print_status "Service Management Commands:"
echo "  • Start service: sudo systemctl start $SERVICE_NAME"
echo "  • Stop service: sudo systemctl stop $SERVICE_NAME"
echo "  • Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  • Check status: sudo systemctl status $SERVICE_NAME"
echo "  • View logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
print_status "To test the API:"
echo "  curl http://localhost:$SERVICE_PORT/health"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}" 
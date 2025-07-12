#!/bin/bash

# ==================================================================
# Deployment Script for NewAfzzinaAI FastAPI Application
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
PYTHON_MIN_VERSION="3.13"
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

# Function to compare version numbers
version_compare() {
    if [[ $1 == $2 ]]; then
        return 0
    fi
    local IFS=.
    local i ver1=($1) ver2=($2)
    # fill empty fields in ver1 with zeros
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++)); do
        ver1[i]=0
    done
    for ((i=0; i<${#ver1[@]}; i++)); do
        if [[ -z ${ver2[i]} ]]; then
            # fill empty fields in ver2 with zeros
            ver2[i]=0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]})); then
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]})); then
            return 2
        fi
    done
    return 0
}

# Step 1: Install and Configure PostgreSQL
print_status "Checking PostgreSQL installation..."
if ! command_exists psql; then
    print_status "PostgreSQL not found. Installing PostgreSQL..."
    
    # Detect OS and install PostgreSQL
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command_exists apt-get; then
            # Ubuntu/Debian
            sudo apt-get update
            sudo apt-get install -y postgresql postgresql-contrib
        elif command_exists yum; then
            # CentOS/RHEL
            sudo yum install -y postgresql-server postgresql-contrib
            sudo postgresql-setup initdb
        elif command_exists dnf; then
            # Fedora
            sudo dnf install -y postgresql-server postgresql-contrib
            sudo postgresql-setup --initdb
        else
            print_error "Unsupported Linux distribution. Please install PostgreSQL manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install postgresql
        else
            print_error "Homebrew not found. Please install PostgreSQL manually."
            exit 1
        fi
    else
        print_error "Unsupported operating system. Please install PostgreSQL manually."
        exit 1
    fi
    
    print_status "PostgreSQL installation completed ✓"
    
    # Start PostgreSQL service
    if command_exists systemctl; then
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    elif command_exists service; then
        sudo service postgresql start
    fi
    
    print_status "PostgreSQL service started ✓"
else
    print_status "PostgreSQL found ✓"
fi

# Step 2: Get database credentials from user
print_status "Database Configuration Required"
echo "Please provide PostgreSQL database credentials:"

# Get database credentials
read -p "Enter PostgreSQL host (default: localhost): " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "Enter PostgreSQL port (default: 5432): " DB_PORT
DB_PORT=${DB_PORT:-5432}

read -p "Enter database username for 'ai' database: " DB_USERNAME
if [[ -z "$DB_USERNAME" ]]; then
    print_error "Database username is required!"
    exit 1
fi

read -s -p "Enter database password: " DB_PASSWORD
echo
if [[ -z "$DB_PASSWORD" ]]; then
    print_error "Database password is required!"
    exit 1
fi

# Get PostgreSQL superuser credentials for database creation
echo
print_status "PostgreSQL superuser credentials needed to create database and user"
read -p "Enter PostgreSQL superuser username (default: postgres): " POSTGRES_USER
POSTGRES_USER=${POSTGRES_USER:-postgres}

read -s -p "Enter PostgreSQL superuser password: " POSTGRES_PASSWORD
echo

# Step 3: Create database and user
print_status "Creating database and user..."
export PGPASSWORD="$POSTGRES_PASSWORD"

# Create user
print_status "Creating database user '$DB_USERNAME'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d postgres -c "CREATE USER $DB_USERNAME WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true

# Create database
print_status "Creating database 'ai'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE ai OWNER $DB_USERNAME;" 2>/dev/null || true

# Grant privileges
print_status "Granting privileges..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE ai TO $DB_USERNAME;" 2>/dev/null || true

# Clear password from environment
unset PGPASSWORD

print_status "Database setup completed ✓"

# Test connection
print_status "Testing database connection..."
export PGPASSWORD="$DB_PASSWORD"
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d ai -c "SELECT 1;" >/dev/null 2>&1; then
    print_status "Database connection test successful ✓"
else
    print_warning "Database connection test failed, but continuing with deployment..."
fi
unset PGPASSWORD

# Step 4: Create .env file with database configuration
print_status "Creating .env file with database configuration..."
cat > "$PROJECT_DIR/.env" << EOF
# Database Configuration
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=ai
DB_USER=$DB_USERNAME
DB_PASSWORD=$DB_PASSWORD

# Application Configuration
IS_PRODUCTION=no
LOG_URL=.
EOF

print_status ".env file created ✓"

# Step 5: Check if Python is installed
print_status "Checking Python installation..."
if ! command_exists python3; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    print_error "Visit https://www.python.org/downloads/ to download Python."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
print_status "Found Python version: $PYTHON_VERSION"

if version_compare $PYTHON_VERSION $PYTHON_MIN_VERSION; then
    if [[ $? -eq 2 ]]; then
        print_error "Python version $PYTHON_VERSION is too old. Please install Python $PYTHON_MIN_VERSION or higher."
        exit 1
    fi
fi

print_status "Python version check passed ✓"

# Step 6: Check if pip is installed
print_status "Checking pip installation..."
if ! command_exists pip3; then
    print_error "pip3 is not installed. Please install pip3."
    exit 1
fi
print_status "pip3 is available ✓"

# Step 7: Navigate to project directory
print_status "Navigating to project directory: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Step 8: Create virtual environment
print_status "Setting up virtual environment..."
if [ ! -d "$VENV_NAME" ]; then
    print_status "Creating virtual environment '$VENV_NAME'..."
    python3 -m venv "$VENV_NAME"
    print_status "Virtual environment created ✓"
else
    print_warning "Virtual environment '$VENV_NAME' already exists. Skipping creation."
fi

# Step 9: Activate virtual environment
print_status "Activating virtual environment..."
source "$VENV_NAME/bin/activate"
print_status "Virtual environment activated ✓"

# Step 10: Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Step 11: Install dependencies
print_status "Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_status "Dependencies installed ✓"
else
    print_error "requirements.txt not found in project directory!"
    exit 1
fi

# Step 12: Create systemd service file
print_status "Creating systemd service file..."
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Check if we have sudo privileges
if sudo -n true 2>/dev/null; then
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=$PROJECT_NAME FastAPI Application
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/$VENV_NAME/bin
ExecStart=$PROJECT_DIR/$VENV_NAME/bin/python main.py
Restart=always
RestartSec=10

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
    
    # Check service status
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "Service is running ✓"
        print_status "Service status:"
        sudo systemctl status "$SERVICE_NAME" --no-pager
    else
        print_error "Service failed to start!"
        print_error "Check logs with: sudo journalctl -u $SERVICE_NAME -f"
        exit 1
    fi
    
else
    print_warning "No sudo privileges. Creating service file manually..."
    print_warning "Please run the following commands as root:"
    echo ""
    echo "sudo tee $SERVICE_FILE > /dev/null <<EOF"
    echo "[Unit]"
    echo "Description=$PROJECT_NAME FastAPI Application"
    echo "After=network.target"
    echo ""
    echo "[Service]"
    echo "Type=simple"
    echo "User=$SERVICE_USER"
    echo "WorkingDirectory=$PROJECT_DIR"
    echo "Environment=PATH=$PROJECT_DIR/$VENV_NAME/bin"
    echo "ExecStart=$PROJECT_DIR/$VENV_NAME/bin/python main.py"
    echo "Restart=always"
    echo "RestartSec=10"
    echo ""
    echo "[Install]"
    echo "WantedBy=multi-user.target"
    echo "EOF"
    echo ""
    echo "sudo systemctl daemon-reload"
    echo "sudo systemctl enable $SERVICE_NAME"
    echo "sudo systemctl start $SERVICE_NAME"
    echo ""
    print_status "Alternatively, running the application directly..."
    
    # Run the application directly
    print_status "Starting application on port $SERVICE_PORT..."
    nohup python main.py > app.log 2>&1 &
    APP_PID=$!
    echo $APP_PID > app.pid
    print_status "Application started with PID: $APP_PID"
    print_status "Logs are being written to app.log"
    print_status "To stop the application, run: kill $APP_PID"
fi

# Step 13: Display useful information
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
echo ""
print_status "Service Management Commands:"
echo "  • Start service: sudo systemctl start $SERVICE_NAME"
echo "  • Stop service: sudo systemctl stop $SERVICE_NAME"
echo "  • Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  • Check status: sudo systemctl status $SERVICE_NAME"
echo "  • View logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
print_status "To test the API, try:"
echo "  curl http://localhost:$SERVICE_PORT/health"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}" 
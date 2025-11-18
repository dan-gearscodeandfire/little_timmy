#!/bin/bash
# startup.sh - WSL Preprocessor Startup Script
# This script configures networking and starts the preprocessor application

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
APP_FILE="$SCRIPT_DIR/app.py"

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}       WSL Preprocessor Startup        ${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is not installed. Please install Python3 first."
        exit 1
    fi
    
    # Check if pip is installed
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install pip3 first."
        exit 1
    fi
    
    # Check if required files exist
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        print_error "requirements.txt not found in $SCRIPT_DIR"
        exit 1
    fi
    
    if [ ! -f "$APP_FILE" ]; then
        print_error "app.py not found in $SCRIPT_DIR"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

setup_virtual_environment() {
    print_status "Setting up virtual environment..."
    
    if [ ! -d "$VENV_PATH" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv "$VENV_PATH"
        if [ $? -ne 0 ]; then
            print_error "Failed to create virtual environment"
            exit 1
        fi
        print_success "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    if [ $? -ne 0 ]; then
        print_error "Failed to activate virtual environment"
        exit 1
    fi
    
    print_success "Virtual environment activated"
}

install_dependencies() {
    print_status "Installing/updating dependencies..."
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    pip install -r "$REQUIREMENTS_FILE"
    if [ $? -ne 0 ]; then
        print_error "Failed to install dependencies"
        exit 1
    fi
    
    print_success "Dependencies installed successfully"
}

configure_network() {
    print_status "Configuring network..."
    
    # Check if network configuration script exists
    if [ -f "/usr/local/bin/wsl-network-config.sh" ]; then
        print_status "Running network configuration..."
        /usr/local/bin/wsl-network-config.sh
        if [ $? -eq 0 ]; then
            print_success "Network configuration completed"
        else
            print_error "Network configuration failed"
            return 1
        fi
    else
        print_error "Network configuration script not found"
        print_error "Please run the Windows PowerShell setup script first"
        return 1
    fi
}

check_services() {
    print_status "Checking service connectivity..."
    
    # Test connectivity to required services
    services=(
        "windows-host:11434:Ollama LLM"
        "windows-host:8888:STT Server"
        "tts-server:5000:TTS Server"
        "motor-raspi:8080:Motor Controller"
    )
    
    for service in "${services[@]}"; do
        IFS=':' read -r host port name <<< "$service"
        if timeout 3 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
            print_success "$name ($host:$port) is reachable"
        else
            print_error "$name ($host:$port) is not reachable"
        fi
    done
}

check_database() {
    print_status "Checking database connectivity..."
    
    # Test PostgreSQL connection
    if command -v psql &> /dev/null; then
        if PGPASSWORD="timmy_postgres_pwd" psql -h localhost -p 5433 -U postgres -d timmy_memory_v16 -c "SELECT 1;" &> /dev/null; then
            print_success "Database connection successful"
        else
            print_error "Database connection failed"
            print_error "Please ensure PostgreSQL is running on port 5433"
        fi
    else
        print_error "psql not found. Please install PostgreSQL client"
    fi
}

start_preprocessor() {
    print_status "Starting preprocessor application..."
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Start the application
    echo -e "${YELLOW}Starting Flask application...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the application${NC}"
    echo -e "${YELLOW}Application will be available at:${NC}"
    echo -e "${GREEN}  - Local: http://localhost:5000${NC}"
    echo -e "${GREEN}  - LAN: http://192.168.1.157:5000${NC}"
    echo -e "${GREEN}  - WSL: http://$(hostname -I | awk '{print $1}'):5000${NC}"
    echo ""
    
    # Start with debug mode if --debug flag is passed
    if [ "$1" = "--debug" ]; then
        python app.py --debug
    else
        python app.py
    fi
}

cleanup() {
    print_status "Cleaning up..."
    # Deactivate virtual environment if active
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate
    fi
    print_success "Cleanup completed"
}

# Trap cleanup function on script exit
trap cleanup EXIT

# Main execution
print_header

# Parse command line arguments
DEBUG_MODE=false
if [ "$1" = "--debug" ]; then
    DEBUG_MODE=true
    print_status "Debug mode enabled"
fi

# Run setup steps
check_prerequisites
setup_virtual_environment
install_dependencies
configure_network

# Check services and database
check_services
check_database

# Start the application
start_preprocessor "$@" 
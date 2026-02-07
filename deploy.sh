#!/bin/bash
# =============================================================================
# RRG Streamlit App - VPS Deployment Script
# =============================================================================
# Usage: chmod +x deploy.sh && ./deploy.sh
# =============================================================================

set -e

echo "=========================================="
echo "  RRG Streamlit App - VPS Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Note: Some commands may require sudo${NC}"
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# =============================================================================
# Step 1: Install Docker if not present
# =============================================================================
echo ""
echo -e "${GREEN}Step 1: Checking Docker installation...${NC}"

if ! command_exists docker; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}Docker installed successfully!${NC}"
else
    echo "Docker is already installed."
fi

if ! command_exists docker-compose; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose installed successfully!${NC}"
else
    echo "Docker Compose is already installed."
fi

# =============================================================================
# Step 2: Build and Start the Application
# =============================================================================
echo ""
echo -e "${GREEN}Step 2: Building and starting the application...${NC}"

# Stop existing containers if running
docker-compose down 2>/dev/null || true

# Build and start
docker-compose up -d --build rrg-app

echo ""
echo -e "${GREEN}=========================================="
echo "  Deployment Complete!"
echo "==========================================${NC}"
echo ""
echo "Your RRG app is now running at:"
echo -e "  ${YELLOW}http://YOUR_VPS_IP:8501${NC}"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f rrg-app"
echo ""
echo "To stop the app:"
echo "  docker-compose down"
echo ""
echo "To restart the app:"
echo "  docker-compose restart rrg-app"
echo ""
echo -e "${YELLOW}Next steps for production:${NC}"
echo "1. Set up a domain name pointing to your VPS IP"
echo "2. Run: ./setup-ssl.sh your-domain.com"
echo "3. Update nginx.conf with your domain"
echo "4. Run: docker-compose up -d nginx"

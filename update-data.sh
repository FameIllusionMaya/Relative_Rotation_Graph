#!/bin/bash
# =============================================================================
# Data Update Script - Pull latest data from GitHub
# =============================================================================
# Usage: chmod +x update-data.sh && ./update-data.sh
# Add to crontab for automatic updates:
#   crontab -e
#   # Daily update at 18:00 ICT (11:00 UTC)
#   0 11 * * 1-5 /path/to/update-data.sh
#   # Hourly update during market hours
#   20 3-5,7-9 * * 1-5 /path/to/update-data.sh
# =============================================================================

set -e

# Navigate to app directory
cd "$(dirname "$0")"

echo "$(date): Updating data from GitHub..."

# Pull latest changes (only data folder)
git fetch origin master
git checkout origin/master -- data/

echo "$(date): Data updated successfully!"

# Optionally restart the container to clear cache
# docker-compose restart rrg-app

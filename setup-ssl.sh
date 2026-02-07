#!/bin/bash
# =============================================================================
# SSL Setup Script using Let's Encrypt (Certbot)
# =============================================================================
# Usage: chmod +x setup-ssl.sh && ./setup-ssl.sh your-domain.com
# =============================================================================

set -e

DOMAIN=$1

if [ -z "$DOMAIN" ]; then
    echo "Usage: ./setup-ssl.sh your-domain.com"
    exit 1
fi

echo "=========================================="
echo "  Setting up SSL for: $DOMAIN"
echo "=========================================="

# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    sudo apt update
    sudo apt install -y certbot
fi

# Stop nginx temporarily to free port 80
docker-compose stop nginx 2>/dev/null || true

# Get SSL certificate
echo "Obtaining SSL certificate..."
sudo certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# Create ssl directory and copy certificates
mkdir -p ssl
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/
sudo chown -R $USER:$USER ssl/

# Update nginx.conf
echo "Updating nginx configuration..."
sed -i "s/server_name _;/server_name $DOMAIN;/" nginx.conf
sed -i 's/# listen 443 ssl;/listen 443 ssl;/' nginx.conf
sed -i 's/# ssl_certificate/ssl_certificate/' nginx.conf
sed -i 's/# ssl_protocols/ssl_protocols/' nginx.conf
sed -i 's/# ssl_ciphers/ssl_ciphers/' nginx.conf

# Uncomment HTTP to HTTPS redirect
sed -i 's/# server {/server {/' nginx.conf
sed -i "s/# server_name your-domain.com;/server_name $DOMAIN;/" nginx.conf
sed -i 's/# return 301/return 301/' nginx.conf
sed -i 's/# }/}/' nginx.conf

# Start nginx with SSL
docker-compose up -d nginx

echo ""
echo "=========================================="
echo "  SSL Setup Complete!"
echo "=========================================="
echo ""
echo "Your app is now available at:"
echo "  https://$DOMAIN"
echo ""
echo "SSL certificate will auto-renew. To manually renew:"
echo "  sudo certbot renew"
echo ""

# Set up auto-renewal cron job
echo "Setting up auto-renewal..."
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker-compose restart nginx") | crontab -
echo "Auto-renewal cron job added (runs daily at 3 AM)"

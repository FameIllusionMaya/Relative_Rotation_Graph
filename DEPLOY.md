# VPS Deployment Guide - RRG Streamlit App

## VPS Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| OS | Ubuntu 20.04/22.04 | Ubuntu 22.04 LTS |
| RAM | 1 GB | 2 GB |
| CPU | 1 vCPU | 2 vCPU |
| Storage | 10 GB | 20 GB SSD |
| Ports | 22, 80, 8501 | 22, 80, 443 |

## Quick Start (5 minutes)

### 1. SSH into your VPS
```bash
ssh root@YOUR_VPS_IP
```

### 2. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/Relative_Rotation_Graph.git
cd Relative_Rotation_Graph
```

### 3. Run deployment script
```bash
chmod +x deploy.sh
./deploy.sh
```

### 4. Access your app
Open in browser: `http://YOUR_VPS_IP:8501`

---

## Detailed Setup

### Option A: Docker (Recommended)

#### Step 1: Install Docker
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Re-login to apply docker group
exit
# SSH back in
```

#### Step 2: Deploy the app
```bash
cd Relative_Rotation_Graph

# Build and run (app only, without nginx)
docker-compose up -d --build rrg-app

# Check logs
docker-compose logs -f rrg-app
```

#### Step 3: Configure firewall
```bash
# Allow Streamlit port
sudo ufw allow 8501

# Or if using nginx
sudo ufw allow 80
sudo ufw allow 443
```

---

### Option B: Without Docker (Systemd Service)

#### Step 1: Install Python
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
```

#### Step 2: Setup application
```bash
cd /opt
sudo git clone https://github.com/YOUR_USERNAME/Relative_Rotation_Graph.git
cd Relative_Rotation_Graph

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 3: Create systemd service
```bash
sudo nano /etc/systemd/system/rrg.service
```

Paste this content:
```ini
[Unit]
Description=RRG Streamlit App
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/Relative_Rotation_Graph
Environment="PATH=/opt/Relative_Rotation_Graph/venv/bin"
ExecStart=/opt/Relative_Rotation_Graph/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Step 4: Start the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable rrg
sudo systemctl start rrg

# Check status
sudo systemctl status rrg
```

---

## SSL Setup (HTTPS)

### With a Domain Name

#### Step 1: Point your domain to VPS
Add an A record in your DNS settings:
- Type: A
- Name: @ (or subdomain like `rrg`)
- Value: YOUR_VPS_IP

#### Step 2: Run SSL setup
```bash
chmod +x setup-ssl.sh
./setup-ssl.sh your-domain.com
```

#### Step 3: Start nginx
```bash
docker-compose up -d nginx
```

Your app will now be available at `https://your-domain.com`

---

## Data Updates

### Option 1: Keep GitHub Actions (Recommended)
Your existing GitHub workflows will continue to update data. Pull updates on VPS:

```bash
# Manual update
cd /path/to/Relative_Rotation_Graph
git pull origin master

# Automatic updates (add to crontab)
crontab -e
# Add these lines:
0 11 * * 1-5 cd /path/to/Relative_Rotation_Graph && git pull origin master
20 3-5,7-9 * * 1-5 cd /path/to/Relative_Rotation_Graph && git pull origin master
```

### Option 2: Run data fetcher on VPS
```bash
# Install tradingview-datafeed
pip install tradingview-datafeed==2.1.1

# Run manually
python fetch_sector_data.py

# Or add to crontab
crontab -e
# Daily at 17:30 ICT
30 10 * * 1-5 cd /path/to/Relative_Rotation_Graph && python fetch_sector_data.py
```

---

## Commands Reference

| Action | Command |
|--------|---------|
| Start app | `docker-compose up -d rrg-app` |
| Stop app | `docker-compose down` |
| Restart app | `docker-compose restart rrg-app` |
| View logs | `docker-compose logs -f rrg-app` |
| Rebuild | `docker-compose up -d --build rrg-app` |
| Update data | `git pull origin master` |

---

## Troubleshooting

### App not accessible
```bash
# Check if container is running
docker ps

# Check container logs
docker-compose logs rrg-app

# Check port is open
sudo ufw status
sudo netstat -tlnp | grep 8501
```

### Container keeps restarting
```bash
# Check logs for errors
docker-compose logs --tail=100 rrg-app

# Common issues:
# - Missing data files: ensure data/ folder exists
# - Permission issues: check file ownership
```

### SSL certificate issues
```bash
# Renew certificate manually
sudo certbot renew

# Copy new certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/

# Restart nginx
docker-compose restart nginx
```

---

## Recommended VPS Providers

| Provider | Cheapest Plan | Notes |
|----------|---------------|-------|
| DigitalOcean | $4/mo (512MB) | Easy, good docs |
| Vultr | $2.50/mo (512MB) | Cheap, Bangkok DC |
| Linode | $5/mo (1GB) | Reliable |
| Hetzner | €3.29/mo (2GB) | Best value in EU |
| Contabo | €4.99/mo (4GB) | Cheap, good specs |

For Thai market data, consider **Vultr Singapore** or **DigitalOcean Singapore** for low latency.

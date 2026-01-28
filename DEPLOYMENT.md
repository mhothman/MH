# ProFlow Deployment Guide - Ubuntu 24.04

## Prerequisites

### 1. Install Node.js 20 LTS (or 22 LTS)

**Option A: Using NodeSource (Recommended)**
```bash
# Remove old Node.js if installed
sudo apt remove nodejs npm -y

# Install Node.js 20.x LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version  # Should show v20.x.x
npm --version
```

**Option B: Using NVM (Node Version Manager)**
```bash
# Install NVM
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc

# Install and use Node 20
nvm install 20
nvm use 20
nvm alias default 20

# Verify
node --version
```

**Option C: Using Snap**
```bash
sudo snap install node --classic --channel=20
```

### 2. Install Yarn
```bash
npm install -g yarn
```

### 3. Install MongoDB 8.0
```bash
# Import MongoDB GPG key
curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor

# Add MongoDB repository
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/8.0 multiverse" | \
   sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list

# Install MongoDB
sudo apt update
sudo apt install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### 4. Install Python 3.11+ and dependencies
```bash
sudo apt install -y python3 python3-pip python3-venv
```

## Application Setup

### 1. Clone the repository
```bash
git clone <your-repo-url> /app
cd /app
```

### 2. Backend Setup
```bash
cd /app/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # or create .env with required variables
# Edit .env with your production values:
# - MONGO_URL
# - JWT_SECRET (use a strong random string)
# - RESEND_API_KEY (for emails)
```

### 3. Frontend Setup
```bash
cd /app/frontend

# Install dependencies
yarn install

# Configure environment
# Edit .env with your production backend URL:
# REACT_APP_BACKEND_URL=https://your-domain.com
```

### 4. Build Frontend for Production
```bash
cd /app/frontend
yarn build
```

## Running the Application

### Option A: Using PM2 (Recommended for Production)
```bash
# Install PM2
npm install -g pm2

# Start backend
cd /app/backend
source venv/bin/activate
pm2 start "uvicorn server:app --host 0.0.0.0 --port 8001" --name proflow-backend

# Start frontend (production build with serve)
npm install -g serve
pm2 start "serve -s /app/frontend/build -l 3000" --name proflow-frontend

# Save PM2 configuration
pm2 save
pm2 startup
```

### Option B: Using Systemd Services
Create `/etc/systemd/system/proflow-backend.service`:
```ini
[Unit]
Description=ProFlow Backend
After=network.target mongodb.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/app/backend
Environment=PATH=/app/backend/venv/bin
ExecStart=/app/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/proflow-frontend.service`:
```ini
[Unit]
Description=ProFlow Frontend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/app/frontend
ExecStart=/usr/bin/serve -s /app/frontend/build -l 3000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable proflow-backend proflow-frontend
sudo systemctl start proflow-backend proflow-frontend
```

## Nginx Reverse Proxy (Optional but Recommended)
```bash
sudo apt install -y nginx

# Create site configuration
sudo nano /etc/nginx/sites-available/proflow
```

Add configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Ensure proper MIME types for static files
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Frontend (serve static build files directly for better performance)
    location / {
        root /app/frontend/build;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # For file uploads
        client_max_body_size 50M;
    }
    
    # WebSocket support for real-time notifications
    location /api/notifications/ws {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/proflow /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL with Let's Encrypt (Production)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Environment Variables Reference

### Backend (.env)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=proflow_production
JWT_SECRET=your-secure-random-string-here
RESEND_API_KEY=your-resend-api-key
SENDER_EMAIL=noreply@your-domain.com
APP_URL=https://your-domain.com
FRONTEND_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=https://your-domain.com
```

## Troubleshooting

### Node.js Version Issues
```bash
# Check Node version
node --version

# If using nvm, ensure correct version
nvm use 20

# If Node is too old, reinstall using instructions above
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R $USER:$USER /app

# Fix MongoDB data directory
sudo chown -R mongodb:mongodb /var/lib/mongodb
```

### Port Already in Use
```bash
# Find process using port
sudo lsof -i :8001
sudo lsof -i :3000

# Kill process
sudo kill -9 <PID>
```

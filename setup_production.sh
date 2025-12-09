#!/bin/bash
# Setup script for production deployment
# Installs all required dependencies and configures the environment

set -e  # Exit on error

echo "╭─────────────────────────────────────────────────────────────╮"
echo "│  Live Validation Dashboard - Production Setup              │"
echo "╰─────────────────────────────────────────────────────────────╯"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo -e "${RED}❌ Unsupported OS: $OSTYPE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Detected OS: $OS${NC}"
echo ""

# Step 1: Update system packages
echo -e "${YELLOW}📦 Step 1: Updating system packages${NC}"
if [ "$OS" == "linux" ]; then
    if [ "$DISTRO" == "ubuntu" ] || [ "$DISTRO" == "debian" ]; then
        sudo apt-get update
        sudo apt-get install -y curl wget git build-essential python3-dev python3-pip python3-venv
    fi
elif [ "$OS" == "macos" ]; then
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    brew update
    brew install python3 git
fi
echo -e "${GREEN}✅ System packages updated${NC}"
echo ""

# Step 2: Install PostgreSQL
echo -e "${YELLOW}📦 Step 2: Installing PostgreSQL${NC}"
if [ "$OS" == "linux" ]; then
    if [ "$DISTRO" == "ubuntu" ] || [ "$DISTRO" == "debian" ]; then
        sudo apt-get install -y postgresql postgresql-contrib
        sudo service postgresql start
    fi
elif [ "$OS" == "macos" ]; then
    brew install postgresql@15
    brew services start postgresql@15
fi
echo -e "${GREEN}✅ PostgreSQL installed${NC}"
echo ""

# Step 3: Install Redis
echo -e "${YELLOW}📦 Step 3: Installing Redis${NC}"
if [ "$OS" == "linux" ]; then
    if [ "$DISTRO" == "ubuntu" ] || [ "$DISTRO" == "debian" ]; then
        sudo apt-get install -y redis-server
        sudo service redis-server start
    fi
elif [ "$OS" == "macos" ]; then
    brew install redis
    brew services start redis
fi
echo -e "${GREEN}✅ Redis installed${NC}"
echo ""

# Step 4: Install Nginx
echo -e "${YELLOW}📦 Step 4: Installing Nginx${NC}"
if [ "$OS" == "linux" ]; then
    if [ "$DISTRO" == "ubuntu" ] || [ "$DISTRO" == "debian" ]; then
        sudo apt-get install -y nginx
        sudo systemctl start nginx
    fi
elif [ "$OS" == "macos" ]; then
    brew install nginx
    brew services start nginx
fi
echo -e "${GREEN}✅ Nginx installed${NC}"
echo ""

# Step 5: Create database and user
echo -e "${YELLOW}🗄️  Step 5: Creating PostgreSQL database and user${NC}"

read -p "Enter PostgreSQL database name [live_validation_dashboard]: " DB_NAME
DB_NAME=${DB_NAME:-live_validation_dashboard}

read -p "Enter PostgreSQL username [dashboard_user]: " DB_USER
DB_USER=${DB_USER:-dashboard_user}

read -sp "Enter PostgreSQL password: " DB_PASSWORD
echo ""

if [ "$OS" == "macos" ]; then
    # macOS with brew
    psql -U $(whoami) -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
    psql -U $(whoami) -c "CREATE DATABASE $DB_NAME;"
    psql -U $(whoami) -c "CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    psql -U $(whoami) -c "ALTER USER $DB_USER CREATEDB;"
    psql -U $(whoami) -d $DB_NAME -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
elif [ "$OS" == "linux" ]; then
    # Linux with sudo
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;"
    sudo -u postgres psql -d $DB_NAME -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
fi

echo -e "${GREEN}✅ Database and user created${NC}"
echo ""

# Step 6: Create .env file
echo -e "${YELLOW}⚙️  Step 6: Creating .env file${NC}"

read -p "Enter Flask environment [production]: " FLASK_ENV
FLASK_ENV=${FLASK_ENV:-production}

read -p "Enter app URL [http://localhost]: " APP_URL
APP_URL=${APP_URL:-http://localhost}

read -p "Enter email for SMTP [noreply@example.com]: " MAIL_USERNAME
MAIL_USERNAME=${MAIL_USERNAME:-noreply@example.com}

read -sp "Enter SMTP password: " MAIL_PASSWORD
echo ""

cat > .env << EOF
# Flask Configuration
FLASK_ENV=$FLASK_ENV
FLASK_APP=run.py
DEBUG=False

# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=$MAIL_USERNAME
MAIL_PASSWORD=$MAIL_PASSWORD

# JWT Configuration
JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

# Application Configuration
APP_URL=$APP_URL
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
EOF

echo -e "${GREEN}✅ .env file created${NC}"
cat .env
echo ""

# Step 7: Setup Python virtual environment
echo -e "${YELLOW}🐍 Step 7: Setting up Python virtual environment${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo -e "${GREEN}✅ Virtual environment created and dependencies installed${NC}"
echo ""

# Step 8: Initialize database
echo -e "${YELLOW}🗄️  Step 8: Initializing database${NC}"

python3 migrate_to_postgres.py

echo -e "${GREEN}✅ Database initialized${NC}"
echo ""

# Step 9: Copy Nginx configuration
echo -e "${YELLOW}⚙️  Step 9: Configuring Nginx${NC}"

if [ "$OS" == "linux" ]; then
    sudo cp nginx.conf /etc/nginx/sites-available/live-validation-dashboard
    sudo ln -sf /etc/nginx/sites-available/live-validation-dashboard /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    sudo nginx -t
    sudo systemctl reload nginx
elif [ "$OS" == "macos" ]; then
    echo "⚠️  Manual Nginx configuration needed on macOS"
    echo "   Copy nginx.conf to $(brew --prefix nginx)/etc/nginx/nginx.conf"
fi

echo -e "${GREEN}✅ Nginx configured${NC}"
echo ""

# Step 10: Create systemd service (Linux only)
if [ "$OS" == "linux" ]; then
    echo -e "${YELLOW}⚙️  Step 10: Creating systemd service${NC}"
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
    
    sudo tee /etc/systemd/system/live-dashboard.service > /dev/null << EOF
[Unit]
Description=Live Validation Dashboard
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$SCRIPT_DIR/venv/bin"
ExecStart=$SCRIPT_DIR/venv/bin/gunicorn --config gunicorn_config.py 'app:create_app()'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable live-dashboard
    
    echo -e "${GREEN}✅ Systemd service created${NC}"
    echo ""
fi

# Summary
echo "╭─────────────────────────────────────────────────────────────╮"
echo "│  ✅ Setup Complete!                                         │"
echo "╰─────────────────────────────────────────────────────────────╯"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Verify services are running:"
echo "   - PostgreSQL: psql -U $DB_USER -d $DB_NAME -c 'SELECT 1;'"
echo "   - Redis: redis-cli ping"
echo ""
echo "2. Start the application:"
if [ "$OS" == "linux" ]; then
    echo "   - Using systemd: sudo systemctl start live-dashboard"
    echo "   - Using Gunicorn: gunicorn --config gunicorn_config.py 'app:create_app()'"
else
    echo "   - source venv/bin/activate"
    echo "   - gunicorn --config gunicorn_config.py 'app:create_app()'"
fi
echo ""
echo "3. Test the application:"
echo "   - http://localhost/ (with Nginx)"
echo "   - http://127.0.0.1:8000/ (direct Gunicorn)"
echo ""
echo "4. Monitor logs:"
if [ "$OS" == "linux" ]; then
    echo "   - Application: journalctl -u live-dashboard -f"
    echo "   - Nginx: tail -f /var/log/nginx/live_dashboard_access.log"
else
    echo "   - Application logs will appear in terminal"
fi
echo ""
echo "5. Load test:"
echo "   - python3 test_scalability.py"
echo ""

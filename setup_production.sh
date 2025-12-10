#!/bin/bash
# Setup script for production deployment
# Installs all required dependencies and configures the environment

echo ""
echo "╭─────────────────────────────────────────────────────────────╮"
echo "│  Live Validation Dashboard - Production Setup              │"
echo "╰─────────────────────────────────────────────────────────────╯"
echo ""

# Detect OS
OS=""
DISTRO=""

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        DISTRO="$ID"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

echo "✅ Detected OS: $OS"
echo ""

# Step 1: Check Homebrew
echo "📦 Step 1: Checking Homebrew"
if [[ "$OS" == "macos" ]]; then
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    echo "✅ Homebrew ready"
fi
echo ""

# Step 2: Install PostgreSQL
echo "📦 Step 2: Installing PostgreSQL"
if [[ "$OS" == "linux" ]]; then
    if [[ "$DISTRO" == "ubuntu" ]] || [[ "$DISTRO" == "debian" ]]; then
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
        sudo service postgresql start
    fi
elif [[ "$OS" == "macos" ]]; then
    if ! command -v psql &> /dev/null; then
        brew install postgresql@15
    fi
    brew services start postgresql@15
fi
echo "✅ PostgreSQL installed"
echo ""

# Step 3: Install Redis
echo "📦 Step 3: Installing Redis"
if [[ "$OS" == "linux" ]]; then
    if [[ "$DISTRO" == "ubuntu" ]] || [[ "$DISTRO" == "debian" ]]; then
        sudo apt-get install -y redis-server
        sudo service redis-server start
    fi
elif [[ "$OS" == "macos" ]]; then
    if ! command -v redis-cli &> /dev/null; then
        brew install redis
    fi
    brew services start redis
fi
echo "✅ Redis installed"
echo ""

# Step 4: Install Nginx
echo "📦 Step 4: Installing Nginx"
if [[ "$OS" == "linux" ]]; then
    if [[ "$DISTRO" == "ubuntu" ]] || [[ "$DISTRO" == "debian" ]]; then
        sudo apt-get install -y nginx
        sudo systemctl start nginx
    fi
elif [[ "$OS" == "macos" ]]; then
    if ! command -v nginx &> /dev/null; then
        brew install nginx
    fi
    brew services start nginx
fi
echo "✅ Nginx installed"
echo ""

# Step 5: Create database and user
echo "🗄️  Step 5: Creating PostgreSQL database and user"
echo ""

read -p "Enter PostgreSQL database name [live_validation_dashboard]: " DB_NAME
DB_NAME=${DB_NAME:-live_validation_dashboard}

read -p "Enter PostgreSQL username [dashboard_user]: " DB_USER
DB_USER=${DB_USER:-dashboard_user}

read -sp "Enter PostgreSQL password: " DB_PASSWORD
echo ""
echo ""

if [[ "$OS" == "macos" ]]; then
    # macOS with brew - uses postgres user
    psql -U postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" 2>/dev/null || true
    psql -U postgres -c "CREATE DATABASE \"$DB_NAME\";" 2>/dev/null || true
    psql -U postgres -c "CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    psql -U postgres -c "ALTER USER $DB_USER CREATEDB;" 2>/dev/null || true
    psql -U postgres -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO $DB_USER;" 2>/dev/null || true
    
    echo "✅ Database and user created"
    
    # Test connection
    echo ""
    echo "Testing connection..."
    if psql -U $DB_USER -d "$DB_NAME" -c "SELECT 1;" 2>/dev/null; then
        echo "✅ Connection successful"
    else
        echo "⚠️  Connection test - you may need to configure PostgreSQL authentication"
    fi
elif [[ "$OS" == "linux" ]]; then
    # Linux with sudo
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE DATABASE \"$DB_NAME\";"
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;"
    sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO $DB_USER;"
    
    echo "✅ Database and user created"
fi
echo ""

# Step 6: Create .env file
echo "⚙️  Step 6: Creating .env file"
echo ""

read -p "Enter Flask environment [production]: " FLASK_ENV
FLASK_ENV=${FLASK_ENV:-production}

read -p "Enter app URL [http://localhost]: " APP_URL
APP_URL=${APP_URL:-http://localhost}

read -p "Enter email for SMTP [noreply@example.com]: " MAIL_USERNAME
MAIL_USERNAME=${MAIL_USERNAME:-noreply@example.com}

read -sp "Enter SMTP password: " MAIL_PASSWORD
echo ""
echo ""

JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))' 2>/dev/null || echo "change-this-secret-key")
SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))' 2>/dev/null || echo "change-this-key")

cat > .env << EOF
# Flask Configuration
FLASK_ENV=$FLASK_ENV
FLASK_APP=run.py
DEBUG=False
SECRET_KEY=$SECRET

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
JWT_SECRET_KEY=$JWT_SECRET

# Application Configuration
APP_URL=$APP_URL
EOF

echo "✅ .env file created"
echo ""

# Step 7: Setup Python virtual environment
echo "🐍 Step 7: Setting up Python virtual environment"
echo ""

if [[ ! -d "venv" ]]; then
    python3 -m venv venv
fi

source venv/bin/activate

pip install --upgrade pip setuptools wheel 2>/dev/null
pip install -r requirements.txt

echo "✅ Virtual environment created and dependencies installed"
echo ""

# Step 8: Run migration
echo "🗄️  Step 8: Running database migration"
echo ""

if [[ -f "migrate_to_postgres.py" ]]; then
    python3 migrate_to_postgres.py
    echo "✅ Database initialized"
else
    echo "⚠️  Migration script not found at migrate_to_postgres.py"
fi
echo ""

# Summary
echo ""
echo "╭─────────────────────────────────────────────────────────────╮"
echo "│  ✅ Setup Complete!                                         │"
echo "╰─────────────────────────────────────────────────────────────╯"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Verify services are running:"
echo "   psql -U $DB_USER -d $DB_NAME -c 'SELECT 1;'"
echo "   redis-cli ping"
echo ""
echo "2. Start the application:"
echo "   source venv/bin/activate"
echo "   python run.py"
echo ""
echo "3. In another terminal, test Gunicorn:"
echo "   gunicorn --config gunicorn_config.py 'app:create_app()'"
echo ""
echo "4. Run load tests:"
echo "   python test_load.py"
echo ""
echo "5. Review documentation:"
echo "   open SCALABILITY_DOCS_INDEX.md"
echo ""

# Live Event Validation Dashboard

A real-time event log validation system with user authentication and live monitoring capabilities.

## Features

- **User Authentication**: Secure login system (prototype: username==password)
- **App Management**: Manage multiple applications and their validation rules
- **CSV Validation Rules**: Upload and manage validation rules via CSV files
- **Live Log Monitoring**: Real-time validation of incoming logs
- **REST API**: Endpoint for mobile apps to send logs (`/api/logs/{app_id}`)
- **WebSocket Support**: Real-time updates to dashboard
- **SOLID Architecture**: Clean separation of concerns

## Project Structure

```
live_validation_dashboard/
├── app/
│   ├── __init__.py           # Flask app initialization
│   ├── models/               # Database models (Entity)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── app.py
│   │   ├── validation_rule.py
│   │   └── log_entry.py
│   ├── repositories/         # Data access layer (Repository pattern)
│   │   ├── __init__.py
│   │   ├── base_repository.py
│   │   ├── user_repository.py
│   │   ├── app_repository.py
│   │   ├── validation_rule_repository.py
│   │   └── log_repository.py
│   ├── services/             # Business logic (Service layer)
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── app_service.py
│   │   ├── validation_service.py
│   │   └── log_service.py
│   ├── validators/           # Validation logic
│   │   ├── __init__.py
│   │   ├── event_validator.py
│   │   └── csv_parser.py
│   ├── controllers/          # Route handlers
│   │   ├── __init__.py
│   │   ├── auth_controller.py
│   │   ├── dashboard_controller.py
│   │   ├── api_controller.py
│   │   └── websocket_controller.py
│   ├── templates/            # HTML templates
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   └── app_detail.html
│   └── static/               # Static files
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── dashboard.js
├── config/
│   ├── __init__.py
│   ├── config.py            # Configuration classes
│   └── database.py          # Database initialization
├── migrations/              # Database migrations
├── tests/                   # Unit tests
│   ├── __init__.py
│   ├── test_auth_service.py
│   ├── test_validation_service.py
│   └── test_repositories.py
├── .env.example            # Environment variables template
├── .gitignore
├── requirements.txt
├── run.py                  # Application entry point
└── README.md
```

## Installation

1. **Clone the repository**
```bash
cd /path/to/live_validation_dashboard
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
python run.py init-db
```

## Usage

### Development Server

```bash
python run.py
```

The application will be available at `http://localhost:5000`

### Production Deployment

```bash
gunicorn -k eventlet -w 1 --bind 0.0.0.0:5000 run:app
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout

### Dashboard
- `GET /dashboard` - Main dashboard
- `GET /dashboard/app/<app_id>` - App details
- `POST /dashboard/upload-rules` - Upload validation rules CSV

### API (for mobile apps)
- `POST /api/logs/<app_id>` - Send logs for validation

### WebSocket Events
- `connect` - Client connects
- `disconnect` - Client disconnects
- `validation_update` - Real-time validation results

## Authentication (Prototype)

For the prototype phase, authentication follows the rule: `username == password`

Example:
- Username: `testuser`
- Password: `testuser`

## CSV Validation Rules Format

The CSV file should have the following columns:
- `eventName` - Name of the event
- `eventPayload` - Field name in the payload
- `dataType` - Expected data type (text, integer, float, date, boolean)
- `required` - Whether the field is required (true/false)
- `condition` - Optional conditional validation rules (JSON)

Example:
```csv
eventName,eventPayload,dataType,required,condition
user_login,user_id,integer,true,{}
user_login,timestamp,date,true,{}
purchase,amount,float,true,{}
```

## SOLID Principles Implementation

- **Single Responsibility**: Each class has one reason to change
  - Models: Only data structure
  - Repositories: Only data access
  - Services: Only business logic
  - Controllers: Only request handling

- **Open/Closed**: Services can be extended without modification
  - Validation rules are configurable via CSV
  - New validators can be added easily

- **Liskov Substitution**: Base repository can be replaced with any implementation
  
- **Interface Segregation**: Controllers depend only on required services

- **Dependency Inversion**: Controllers depend on service abstractions, not concrete implementations

## Testing

```bash
python -m pytest tests/
```

## License

MIT License

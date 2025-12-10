# Docker Deployment Instructions

## Prerequisites

You need to have Docker installed on your machine.

### macOS
1. Download Docker Desktop for Mac from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2. Open the `.dmg` file and drag Docker to your Applications folder.
3. Open Docker from Applications to start the Docker engine.
4. Wait for the Docker icon in the menu bar to stop animating.

### Windows
1. Download Docker Desktop for Windows.
2. Run the installer.
3. Restart your computer if prompted.

### Linux
Follow instructions for your distribution: [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)

## Running the Application

Once Docker is installed and running:

1. Open your terminal.
2. Navigate to the project directory.
3. Run the following command:

```bash
# For Docker Compose v2 (included in Docker Desktop)
docker compose up --build

# OR for older versions
docker-compose up --build
```

## Accessing the Application

- **Web Dashboard**: [http://localhost:5001](http://localhost:5001)
- **API Endpoint**: `http://localhost:5001/api/logs/{app_id}`

## Troubleshooting

- If you see `command not found: docker`, ensure Docker Desktop is running.
- If port 5001 is in use, edit `docker-compose.yml` and change `"5001:5000"` to `"5002:5000"`.

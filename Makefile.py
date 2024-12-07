# Makefile

.PHONY: setup start stop restart logs clean test install-dev lint update backup monitor help

# Değişkenler
DOCKER_COMPOSE = docker-compose
PYTHON = python3
PIP = pip3

setup:
   @echo "Setting up trading bot..."
   $(PIP) install -r requirements.txt
   mkdir -p data logs
   cp .env.example .env
   @echo "Setup complete! Please edit .env file with your credentials."

start:
   @echo "Starting trading bot..."
   $(DOCKER_COMPOSE) up -d
   @echo "Bot started! Dashboard: http://localhost:8050"

stop:
   @echo "Stopping trading bot..."
   $(DOCKER_COMPOSE) down
   @echo "Bot stopped successfully!"

restart: stop start

logs:
   $(DOCKER_COMPOSE) logs -f trading-bot

clean:
   @echo "Cleaning up..."
   rm -rf data/*
   rm -rf logs/*
   docker system prune -f
   @echo "Cleanup complete!"

test:
   $(PYTHON) -m pytest tests/

install-dev:
   $(PIP) install -r requirements-dev.txt

lint:
   flake8 .
   black .
   isort .

update:
   git pull
   $(MAKE) stop
   $(MAKE) start

backup:
   @echo "Creating backup..."
   tar -czf backup_$(shell date +%Y%m%d_%H%M%S).tar.gz data/ logs/
   @echo "Backup complete!"

monitor:
   @echo "Opening Grafana monitoring..."
   open http://localhost:3000

deploy:
   @echo "Deploying to production..."
   git pull
   $(MAKE) clean
   $(MAKE) setup
   $(MAKE) start

dev:
   @echo "Starting development environment..."
   $(PYTHON) main.py

check-env:
   @echo "Checking environment variables..."
   $(PYTHON) -c "from config.env_validator import EnvironmentValidator; EnvironmentValidator().load_and_validate()"

help:
   @echo "Available commands:"
   @echo "  make setup      - Initial setup"
   @echo "  make start      - Start the bot"
   @echo "  make stop       - Stop the bot"
   @echo "  make restart    - Restart the bot"
   @echo "  make logs       - View bot logs"
   @echo "  make clean      - Clean data and logs"
   @echo "  make test       - Run tests"
   @echo "  make lint       - Run linters"
   @echo "  make update     - Update and restart bot"
   @echo "  make backup     - Backup data and logs"
   @echo "  make monitor    - Open monitoring dashboard"
   @echo "  make deploy     - Deploy to production"
   @echo "  make dev        - Start development environment"
   @echo "  make check-env  - Check environment variables"

# Makefile for Django + PostgreSQL + MinIO Project
# This file provides convenient commands for managing the development environment

.PHONY: help
help: ## Show this help message
	@echo "Django Backend with PostgreSQL and MinIO - Development Commands"
	@echo "=============================================================="
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: ## Build Docker containers
	docker-compose build

.PHONY: up
up: ## Start all services in detached mode
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Services are starting up. Check status with 'make ps'"

.PHONY: down
down: ## Stop and remove all containers
	docker-compose down

.PHONY: restart
restart: down up ## Restart all services

.PHONY: ps
ps: ## Show status of all containers
	docker-compose ps

.PHONY: logs
logs: ## Show logs from all containers
	docker-compose logs -f

.PHONY: logs-web
logs-web: ## Show logs from Django web container
	docker-compose logs -f web

.PHONY: logs-db
logs-db: ## Show logs from PostgreSQL container
	docker-compose logs -f postgres

.PHONY: logs-minio
logs-minio: ## Show logs from MinIO container
	docker-compose logs -f minio

.PHONY: shell
shell: ## Open Django shell
	docker-compose exec web python manage.py shell

.PHONY: bash
bash: ## Open bash shell in web container
	docker-compose exec web bash

.PHONY: dbshell
dbshell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U django_user -d django_db

.PHONY: migrate
migrate: ## Run Django migrations
	docker-compose exec web python manage.py migrate

.PHONY: makemigrations
makemigrations: ## Create new Django migrations
	docker-compose exec web python manage.py makemigrations

.PHONY: createsuperuser
createsuperuser: ## Create Django superuser
	docker-compose exec web python manage.py createsuperuser

.PHONY: collectstatic
collectstatic: ## Collect static files
	docker-compose exec web python manage.py collectstatic --noinput

.PHONY: test
test: ## Run Django tests
	docker-compose exec web python manage.py test

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	docker-compose exec web coverage run --source='.' manage.py test
	docker-compose exec web coverage report
	docker-compose exec web coverage html

.PHONY: lint
lint: ## Run code linting (flake8)
	docker-compose exec web flake8 apps/ config/

.PHONY: format
format: ## Format code with black
	docker-compose exec web black apps/ config/

.PHONY: init-minio
init-minio: ## Initialize MinIO buckets
	docker-compose exec web python manage.py init_minio

.PHONY: clean-media
clean-media: ## Remove all media files
	docker-compose exec web rm -rf media/*

.PHONY: clean-static
clean-static: ## Remove all static files
	docker-compose exec web rm -rf staticfiles/*

.PHONY: backup-db
backup-db: ## Backup PostgreSQL database
	@mkdir -p backups
	docker-compose exec postgres pg_dump -U django_user django_db > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Database backed up to backups/backup_$(shell date +%Y%m%d_%H%M%S).sql"

.PHONY: restore-db
restore-db: ## Restore PostgreSQL database from latest backup
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore-db FILE=backups/backup_file.sql"; \
	else \
		docker-compose exec -T postgres psql -U django_user django_db < $(FILE); \
		echo "Database restored from $(FILE)"; \
	fi

.PHONY: reset-db
reset-db: ## Reset database (WARNING: Deletes all data!)
	@echo "WARNING: This will delete all data in the database!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose exec postgres psql -U django_user -c "DROP DATABASE IF EXISTS django_db;"
	docker-compose exec postgres psql -U django_user -c "CREATE DATABASE django_db;"
	$(MAKE) migrate
	@echo "Database has been reset"

.PHONY: install-deps
install-deps: ## Install Python dependencies
	docker-compose exec web pip install -r requirements.txt

.PHONY: freeze-deps
freeze-deps: ## Freeze current Python dependencies
	docker-compose exec web pip freeze > requirements.txt

.PHONY: check-deploy
check-deploy: ## Run Django deployment checklist
	docker-compose exec web python manage.py check --deploy

.PHONY: create-app
create-app: ## Create a new Django app (Usage: make create-app NAME=myapp)
	@if [ -z "$(NAME)" ]; then \
		echo "Usage: make create-app NAME=myapp"; \
	else \
		docker-compose exec web python manage.py startapp $(NAME) apps/$(NAME); \
		echo "Created new app: apps/$(NAME)"; \
	fi

.PHONY: minio-console
minio-console: ## Open MinIO console in browser
	@echo "Opening MinIO console at http://localhost:9001"
	@echo "Login with: minioadmin / minioadmin123"
	@python -m webbrowser http://localhost:9001 2>/dev/null || \
		xdg-open http://localhost:9001 2>/dev/null || \
		open http://localhost:9001 2>/dev/null || \
		echo "Please open http://localhost:9001 in your browser"

.PHONY: django-admin
django-admin: ## Open Django admin in browser
	@echo "Opening Django admin at http://localhost:8000/admin"
	@python -m webbrowser http://localhost:8000/admin 2>/dev/null || \
		xdg-open http://localhost:8000/admin 2>/dev/null || \
		open http://localhost:8000/admin 2>/dev/null || \
		echo "Please open http://localhost:8000/admin in your browser"

.PHONY: api-docs
api-docs: ## Open API documentation in browser
	@echo "Opening API docs at http://localhost:8000/api/"
	@python -m webbrowser http://localhost:8000/api/ 2>/dev/null || \
		xdg-open http://localhost:8000/api/ 2>/dev/null || \
		open http://localhost:8000/api/ 2>/dev/null || \
		echo "Please open http://localhost:8000/api/ in your browser"

.PHONY: clean
clean: ## Clean up generated files and caches
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf staticfiles/

.PHONY: setup
setup: build up migrate init-minio createsuperuser collectstatic ## Complete initial setup
	@echo "=============================================="
	@echo "Setup complete! Your Django app is ready."
	@echo "=============================================="
	@echo ""
	@echo "Access points:"
	@echo "  - Django Admin: http://localhost:8000/admin"
	@echo "  - API: http://localhost:8000/api/"
	@echo "  - MinIO Console: http://localhost:9001"
	@echo ""
	@echo "MinIO credentials: minioadmin / minioadmin123"
	@echo ""
	@echo "Run 'make help' to see all available commands"

.PHONY: dev
dev: up logs-web ## Start development environment and follow logs

.PHONY: stop
stop: ## Stop all containers without removing them
	docker-compose stop

.PHONY: start
start: ## Start stopped containers
	docker-compose start

.PHONY: status
status: ## Show detailed status of services
	@echo "Service Status:"
	@echo "==============="
	@docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "Database Status:"
	@docker-compose exec postgres pg_isready -U django_user -d django_db || echo "PostgreSQL is not ready"
	@echo ""
	@echo "MinIO Status:"
	@curl -s -o /dev/null -w "MinIO API: %{http_code}\n" http://localhost:9000/minio/health/live || echo "MinIO is not responding"
	@echo ""
	@echo "Django Status:"
	@curl -s -o /dev/null -w "Django App: %{http_code}\n" http://localhost:8000/ || echo "Django is not responding"

.PHONY: volumes
volumes: ## List Docker volumes used by the project
	@echo "Project Volumes:"
	@docker volume ls | grep django

.PHONY: prune
prune: ## Remove unused Docker resources (containers, networks, images)
	docker system prune -f

.DEFAULT_GOAL := help

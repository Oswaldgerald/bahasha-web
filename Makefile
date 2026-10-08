DOCKER_COMPOSE := docker compose
DEV_COMPOSE := $(DOCKER_COMPOSE) -f compose.yml -f compose.dev.yml

.PHONY: up dev dev-port down logs check test migrations makemigrations superuser shell

up:
	$(DOCKER_COMPOSE) up -d --build

dev:
	$(DEV_COMPOSE) up -d --build

dev-port:
	@test -n "$(PORT)" || (echo "Usage: make dev-port PORT=8000" && exit 1)
	WEB_PORT=$(PORT) $(DEV_COMPOSE) up -d --build

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f web

check:
	$(DOCKER_COMPOSE) exec -T web python manage.py check

test:
	$(DOCKER_COMPOSE) exec -T web python manage.py test --settings=config.settings_test

migrations:
	$(DOCKER_COMPOSE) exec -T web python manage.py migrate

makemigrations:
	$(DOCKER_COMPOSE) exec -T web python manage.py makemigrations

superuser:
	$(DOCKER_COMPOSE) exec web python manage.py createsuperuser

shell:
	$(DOCKER_COMPOSE) exec web python manage.py shell

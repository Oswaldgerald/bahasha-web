# Bahasha System

Bahasha is a Django application for church membership and contribution management. It includes member approval, contribution periods, annual targets, Excel contribution imports, reporting, notifications, audit logs, session authentication, and JWT API authentication.

## Architecture

- Django 6 and Django REST Framework
- PostgreSQL 17
- Gunicorn and WhiteNoise for production
- Docker Compose for local and production-like environments
- SQLite in-memory database for isolated tests

## Quick Start

Create the local environment file:

```sh
cp .env.example .env
```

Replace the placeholder secrets in `.env`, then start the production-like stack:

```sh
make up
```

The application is available at `http://localhost:${WEB_PORT}`. The default example port is `8000`; this workspace currently uses `8001` in its private `.env`.

Useful endpoints:

- `/` - sign in
- `/web/dashboard/` - application dashboard
- `/admin/` - Django administration
- `/api/auth/login/` - JWT login
- `/api/auth/me/` - current API user
- `/api/excel-uploads/` - Excel upload API
- `/health/` - application and database readiness

## Development

Start the development stack with source mounting and Django auto-reload:

```sh
make dev
```

Common commands:

```sh
make logs
make check
make test
make makemigrations
make migrations
make superuser
make shell
make down
```

Tests use an in-memory SQLite database and do not modify local PostgreSQL data. They can also run directly from the virtual environment:

```sh
venv/bin/python manage.py test --settings=config.settings_test
```

When dependencies change, rebuild the image with `make up` or `make dev`.

## Frontend Structure

The shared page shell lives in `templates/base.html`, with navigation, top bar, and footer in `templates/partials/`. Templates contain structure only; reusable presentation and behavior live under `static/`:

- `static/css/base.css` - typography, cards, buttons, and shared utilities
- `static/css/layout.css` - collapsible sidebar, mobile drawer, top bar, and page headers
- `static/css/forms.css` and `static/css/tables.css` - reusable form and table patterns
- `static/css/dashboard.css`, `reports.css`, and `notifications.css` - feature styles
- `static/css/member-card.css` - member card styles loaded only by that page
- `static/css/printing.css` - print-only behavior
- `static/js/app.js` - icons, printing, and progress bars
- `static/js/navigation.js` - persisted desktop sidebar and mobile drawer behavior
- `static/js/dropdowns.js` - reusable accessible dropdown menus and dismissal behavior
- `static/js/forms.js` - progressive enhancement for Django select fields

Lucide and Choices.js are pinned and vendored under `static/vendor/`, including their licenses. This keeps icons and enhanced dropdowns available without a runtime CDN dependency.

Use `{% block extra_css %}` and `{% block extra_js %}` in page templates when a feature needs isolated assets. Avoid inline styles and event handlers so browser issues remain easy to trace.

## Environment

`.env` contains secrets and machine-specific values and must never be committed. `.env.example` documents all supported settings.

For local HTTP development, keep secure cookies, HTTPS redirects, and HSTS disabled. Enable them in production only when the application is served behind a correctly configured HTTPS reverse proxy.

## Production Image

Log in to Docker Hub:

```sh
docker login
```

Build for a typical Ubuntu server and push both a rollback tag and `latest`:

```sh
DOCKERHUB_REPO=<dockerhub-user-or-org>/bahasha-system ./scripts/push-dockerhub.sh v1.0.0
```

For an ARM Ubuntu server:

```sh
DOCKERHUB_REPO=<dockerhub-user-or-org>/bahasha-system PLATFORM=linux/arm64 ./scripts/push-dockerhub.sh v1.0.0
```

Always deploy an immutable version tag in production. Keep `latest` as a convenience pointer, not as the only rollback reference.

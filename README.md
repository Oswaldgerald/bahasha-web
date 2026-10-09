# Bahasha System

Bahasha is a Django application for church membership and contribution management. It includes member approval, contribution periods, annual targets, Excel contribution imports, reporting, notifications, audit logs, and session authentication.

## Architecture

- Django 6
- PostgreSQL 17
- Gunicorn and WhiteNoise for production
- Docker Compose for local and production-like environments
- SQLite in-memory database for isolated tests

Web request handlers live with the Django app that owns the feature. `web/urls.py`
is the routing table only; it must not contain business or presentation logic.

- `dashboard/views.py` - dashboard aggregation
- `members/views.py` and `members/services.py` - member workflows and state changes
- `members/forms.py` - member account, photo, and church placement forms
- `users/forms.py` - reusable user profile and international phone forms
- `contributions/views.py` and `contributions/services.py` - contribution workflows
- `excel_uploads/views.py` - contribution upload workflows
- `reports/views.py` - contribution and member reports
- Each remaining feature uses its own `<app>/views.py` module

When adding a page, place its view and domain-specific forms in the owning app,
then reference its view module explicitly from `web/urls.py`. Forms shared across
multiple features remain in `web/forms.py`.

## Quick Start

Create the local environment file:

```sh
cp .env.example .env
```

Replace the placeholder secrets in `.env`, then start the production-like stack:

```sh
make up
```

The application is available at `http://localhost:${WEB_PORT}`. The default development port is `8000`; change `WEB_PORT` in the private `.env` when another port is required.

Useful routes:

- `/` - sign in
- `/password-reset/` - request a password reset email
- `/web/dashboard/` - application dashboard
- `/admin/` - Django administration
- `/health/` - application and database readiness

The project intentionally exposes no public application API at this stage. The
previous Django REST Framework and JWT endpoints were removed so a versioned,
member-scoped Django Ninja API can be designed without legacy contracts.

The proposed mobile contract, authorization boundaries, prerequisite model work,
and phased Django Ninja rollout are documented in
[`docs/API_DESIGN.md`](docs/API_DESIGN.md). This is a design artifact only; Django
Ninja and the endpoints are not implemented yet.

Contribution categories are already church-specific and configurable in the web
application. Administrators can control each mobile card's labels, icon, color,
order, visibility, payment availability, catch-up behavior, frequency, and amount
guidance. Churches created through the web interface receive the standard Ahadi,
Jengo, Uwakili, Jumuiya, and Mavuno categories as editable defaults.

## Development

Start the development stack with source mounting and Django auto-reload:

```sh
make dev
```

To run the same stack on a different web port without changing its data, use:

```sh
make dev-port PORT=8000
```

The port only controls where the Docker web container is exposed. PostgreSQL data
and uploaded media remain in the same Compose volumes. Do not start this project
with a bare `python manage.py runserver`: it does not load `.env` and may otherwise
connect to an unrelated PostgreSQL service installed on the host.

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
- `static/css/forms.css` and `static/css/tables.css` - reusable form, list toolbar, responsive table, status, and action patterns
- `static/css/dashboard.css`, `reports.css`, `notifications.css`, and `profile.css` - feature styles
- `static/css/members.css` - member list, form, and profile styles
- `static/css/users.css` - user account list, filters, responsive rows, and form styles
- `static/css/categories.css` - configurable contribution-category cards and editor
- `static/css/member-card.css` - member card styles loaded only by that page
- `static/css/printing.css` - print-only behavior
- `static/js/app.js` - icons, printing, and progress bars
- `static/js/navigation.js` - persisted desktop sidebar and mobile drawer behavior
- `static/js/dropdowns.js` - reusable accessible dropdown menus and dismissal behavior
- `static/js/forms.js` - progressive enhancement for Django select fields
- `static/js/profile.js` - profile picture preview and removal behavior
- `static/js/members.js` - member workflow confirmation and dependent selectors
- `static/js/categories.js` - live preview for configurable mobile category cards
- `static/js/lists.js` - reusable confirmation behavior for list actions

Shared form markup lives in `templates/partials/form_field.html`,
`form_toggle.html`, `form_section_header.html`, and `form_actions.html`. Use these
partials for administrative create and edit screens so labels, Swahili captions,
validation, switches, and action placement remain consistent.

Lucide and Choices.js are pinned and vendored under `static/vendor/`, including their licenses. This keeps icons and enhanced dropdowns available without a runtime CDN dependency.

Profile pictures are stored in the persistent Docker media volume and served through an authenticated route. They are not exposed by a public media directory.

Password reset emails use Django's console email backend during local development,
so reset links appear in the web container logs. Production deployments must set
the `EMAIL_*` and `DEFAULT_FROM_EMAIL` values documented in `.env.example` to a
working SMTP account.

Phone forms store normalized international numbers. Country selectors use the shared
Choices.js enhancement, with Tanzania first and searchable country names and calling codes.

Member Management supports transactional CSV import and church-scoped CSV export.
CSV files deliberately exclude usernames, passwords, profile photos, and church-group
memberships. Imported accounts receive an internal username and an unusable password
until an administrator explicitly sets one.

Use `{% block extra_css %}` and `{% block extra_js %}` in page templates when a feature needs isolated assets. Avoid inline styles and event handlers so browser issues remain easy to trace.

## Contribution Integrity

All contribution write paths must use `contributions.services.save_contribution` or `save_contributions`. The service validates domain relationships, derives the member's Bahasha number, saves atomically, and recalculates annual target totals from posted contributions. Web forms, Excel imports, future mobile APIs, and payment callbacks must not update cached target totals directly.

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

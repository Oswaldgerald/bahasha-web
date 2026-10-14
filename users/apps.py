from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Register custom users and their session-revocation signals with Django."""

    name = "users"

    def ready(self):
        """Register user and membership security signal handlers."""

        import users.signals  # noqa: F401

from django.apps import AppConfig
import os


class GeoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "geo"

    def ready(self):
        """
        Auto-configure the Google SocialApp for django-allauth using
        GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET from the environment.

        This avoids having to create the SocialApp manually in /admin/
        for development / demo deployments.
        """
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        # Only attempt setup if both values are present
        if not client_id or not client_secret:
            return

        try:
            from django.contrib.sites.models import Site
            from django.db.utils import OperationalError, ProgrammingError
            from allauth.socialaccount.models import SocialApp
        except Exception:
            # If imports fail (e.g. allauth not installed), just skip setup
            return

        try:
            # Database might not be ready during initial migrate/collectstatic
            site = Site.objects.get_current()
        except (OperationalError, ProgrammingError):
            return

        try:
            app, created = SocialApp.objects.get_or_create(
                provider="google",
                defaults={
                    "name": "Google",
                    "client_id": client_id,
                    "secret": client_secret,
                },
            )

            if not created:
                updated = False
                if app.client_id != client_id:
                    app.client_id = client_id
                    updated = True
                if app.secret != client_secret:
                    app.secret = client_secret
                    updated = True
                if updated:
                    app.save()

            # Ensure the SocialApp is linked to the current Site
            if site not in app.sites.all():
                app.sites.add(site)
        except (OperationalError, ProgrammingError):
            # Tables may not exist yet; safe to ignore
            return

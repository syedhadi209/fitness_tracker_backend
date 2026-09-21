#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def _on_railway():
    return bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    # Railway's Django detector (or a dashboard start command) often launches
    # `runserver`. That is the development server. Hand off to Gunicorn.
    if _on_railway() and len(sys.argv) > 1 and sys.argv[1] == "runserver":
        os.execvp("sh", ["sh", "entrypoint.sh"])
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

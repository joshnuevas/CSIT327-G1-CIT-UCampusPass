#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# 🌟 FINAL PATH FIX: This line adds the folder containing your apps (citu_campuspass)
# to the Python path, resolving the ModuleNotFoundError for 'campuspass' and 'staff'.
sys.path.append(os.path.join(os.path.dirname(__file__), "citu_campuspass"))
# --------------------------------------------------------------------------

def main():
    """Run administrative tasks."""
    # This line specifies the correct, full nested path for your settings file.
    # It is now correctly resolved because the outer path is added above.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'citu_campuspass.citu_campuspass.settings')
    
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
"""
Pytest configuration for SimTrade project.
"""
import os
import sys
import django

# Add project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simtrade.settings')
django.setup()

# Configure pytest plugins
pytest_plugins = [
    'pytest_django',
]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line('markers', 'slow: marks tests as slow')
    config.addinivalue_line('markers', 'integration: marks tests as integration tests')


# Add JSON_VALID function support for older SQLite versions
import sqlite3
from django.db.backends.sqlite3.base import Database

_json_valid_patched = False

def _json_valid(sql):
    """Mock JSON_VALID function for SQLite compatibility."""
    # Import json module to validate JSON strings
    import json
    try:
        json.loads(sql)
        return 1
    except (ValueError, TypeError):
        return 0

# Hook into Django's sqlite connection to add the function
original_connect = Database.connect
def custom_connect(*args, **kwargs):
    global _json_valid_patched
    conn = original_connect(*args, **kwargs)
    if not _json_valid_patched:
        try:
            conn.create_function('JSON_VALID', 1, _json_valid)
        except Exception:
            pass  # Function may already exist or SQLite version supports it natively
        _json_valid_patched = True
    return conn
Database.connect = custom_connect

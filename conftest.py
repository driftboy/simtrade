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

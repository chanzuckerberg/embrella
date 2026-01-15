"""
Constants used across process views.
"""
import os

ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')


def get_base_url():
    if ENVIRONMENT == 'staging':
        return 'http://umbrella-dev.czbiohub.org'
    elif ENVIRONMENT == 'production':
        return 'http://umbrella.czbiohub.org'
    else:  # development
        return 'http://localhost:8000'


base_url = get_base_url()

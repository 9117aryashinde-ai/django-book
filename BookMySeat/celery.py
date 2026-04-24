import os
from celery import Celery

# Tells Celery which Django project to use
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BookMySeat.settings')

# Creating celery app since Celery needs its own app instance to run
app = Celery('BookMySeat')

app.config_from_object('django.conf:settings', namespace='CELERY') # tells celery to read the configurations from settings.py and namespace means celery will only look for settings that will start with CELERY
app.autodiscover_tasks() # Finds all the tasks.py across all Django projects
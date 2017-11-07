#!/bin/bash

cd /app/

python manage.py migrate --settings fileservice.settings.docker_config
python manage.py loaddata initial_data --settings fileservice.settings.docker_config
python manage.py collectstatic --noinput --settings fileservice.settings.docker_config

/etc/init.d/nginx restart

DJANGO_SETTINGS_MODULE=fileservice.settings.docker_config gunicorn --reload fileservice.wsgi_docker:application -b 0.0.0.0:8011 --timeout 360
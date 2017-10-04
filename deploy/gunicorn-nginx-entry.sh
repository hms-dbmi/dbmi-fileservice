#!/bin/bash

cd /app/

python manage.py migrate --settings fileservice.settings.docker_config
python manage.py loaddata filemaster --settings fileservice.settings.docker_config
python manage.py collectstatic --noinput --settings fileservice.settings.docker_config

/etc/init.d/nginx restart

DJANGO_SETTINGS_MODULE=fileservice.settings.docker_config gunicorn fileservice.wsgi_docker:application -b 0.0.0.0:8003 --timeout 360
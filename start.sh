#!/bin/bash
python manage.py collectstatic --noinput
python manage.py migrate
python init_data.py
gunicorn elitebuss_final.wsgi:application --bind 0.0.0.0:8000
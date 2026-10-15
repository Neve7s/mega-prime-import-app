#!/bin/sh
# Sincroniza imágenes semilla del repo al volumen (sin pisar subidas de prod),
# aplica migraciones y levanta Gunicorn.
set -e
if [ -d /app/media_seed ]; then
  mkdir -p /app/media
  cp -rn /app/media_seed/. /app/media/ 2>/dev/null || true
fi
python manage.py migrate --noinput
exec gunicorn megra_prime.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60

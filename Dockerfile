# Mega Prime Import — Django + Gunicorn + WhiteNoise (Coolify-ready)
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Estáticos compilados en la imagen: en cada redeploy se regeneran solos.
# (El secret dummy es solo de compilación; en runtime Coolify inyecta el real.)
RUN DJANGO_SECRET_KEY=build-only-dummy-value python manage.py collectstatic --noinput

RUN useradd -m app && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/')" || exit 1

# Migraciones se aplican al arrancar (ver entrypoint).
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn megra_prime.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60"]

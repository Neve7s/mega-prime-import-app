# Mega Prime Import — Django + Gunicorn + WhiteNoise (Coolify-ready)
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Copia semilla de media: el volumen /app/media tapa esta carpeta en runtime,
# el entrypoint sincroniza lo que falte sin pisar subidas de prod.
COPY media/ /app/media_seed/
# Estáticos compilados en la imagen: en cada redeploy se regeneran solos.
# (El secret dummy es solo de compilación; en runtime Coolify inyecta el real.)
RUN DJANGO_SECRET_KEY=build-only-dummy-value python manage.py collectstatic --noinput

RUN useradd -m app && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/')" || exit 1

COPY --chown=app:app entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Migraciones se aplican al arrancar (ver entrypoint).
CMD ["/app/entrypoint.sh"]

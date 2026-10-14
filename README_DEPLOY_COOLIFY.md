# Deploy en Coolify — Sitio estático (HTML)

Ya está preparado. Es solo estático: se sirve `index.html` con nginx.

## Qué se agregó

- `index.html` — copia de `code.html` + `<title>` y meta description (es lo que sirve nginx).
- `Dockerfile` — imagen `nginx:1.27-alpine`, expone puerto `80`, con healthcheck en `/health`.
- `nginx.conf` — gzip, cache, headers básicos, ruta `/health` → `ok`.
- `docker-compose.yml` — para prueba local (`web: 8080->80`).
- `.dockerignore` — excluye `.git`, `DESIGN.md`, `screen.png`, zips.

## Probar local (requiere Docker Desktop encendido)

```powershell
docker compose up --build -d
# abrir http://localhost:8080
# health: http://localhost:8080/health  -> ok
docker compose down
```

> Si Docker Desktop está apagado verás el error `dockerDesktopLinuxEngine`. Enciéndelo y reintenta.

## Subir a Coolify

**Opción A — desde repo Git (recomendado):**

1. Sube esta carpeta a GitHub (tiene que incluir `Dockerfile`, `nginx.conf`, `index.html`).
2. Coolify → New Project → New Service → Application.
3. Source: tu repo, branch `main`.
4. Build Pack: **Dockerfile** (detecta solo el `Dockerfile`).
5. Puerto expuesto: `80`.
6. Health check path: `/health`.
7. Deploy. Tu dominio de Coolify apuntará al `index.html`.

**Opción B — con docker-compose en Coolify:**

1. En el servicio elige Build Pack **Docker Compose**.
2. Usa el `docker-compose.yml` incluido.
3. Deploy.

## Notas

- `code.html` se mantiene por compatibilidad (ruta `/code.html`), pero la ruta principal es `/` → `index.html`.
- Las imágenes de la plantilla son URLs externas (`googleusercontent`). Si alguna caduca, hay que descargarlas a una carpeta `assets/` y actualizar los `src`. Avísame y lo hago.
- Cuando quieras pasar a webapp con DB, se agrega servicio `api/` + Postgres como recursos de Coolify, sin tocar este estático.

## Rollback

Cada deploy en Coolify guarda la versión anterior: si algo falla, Redeploy del commit anterior. No hay migraciones ni estado que cuidar (estático puro).

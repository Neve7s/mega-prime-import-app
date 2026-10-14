# Coolify-ready: sitio estatico con nginx
FROM nginx:1.27-alpine

# Config custom
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Contenido estatico (index.html es el que se sirve)
COPY index.html /usr/share/nginx/html/index.html
COPY code.html /usr/share/nginx/html/code.html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:80/health || exit 1

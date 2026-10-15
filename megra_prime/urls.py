from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("accounts.urls")),
    path("catalogo/", include("catalog.urls")),
    path("carrito/", include("cart.urls")),
    path("calculadora/", include("calculator.urls")),
    path("webadmin/", include("panel.urls")),
    path("", include("core.urls")),
]

# /media/ servido por Django (static() es no-op con DEBUG=False).
# En prod los archivos viven en el volumen persistente /app/media.
urlpatterns += [path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT})]

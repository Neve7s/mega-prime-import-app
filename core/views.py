import random

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from catalog.models import Category, Product
from core.models import HeroMedia


def health(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok")


# Categorías que son complementos: no salen en el showcase del hero
# (el hero muestra los productos principales: tejas, cielo razo, paneles...).
CATEGORIAS_COMPLEMENTO = ("accesorios-y-materiales", "herramientas-y-equipos")


def _productos_hero(cantidad: int = 3) -> list:
    """Productos para el showcase del hero: destacados primero y elección al azar.

    Solo productos principales (nada de tornillos ni accesorios) y siempre
    con foto: se toman de los 40 más recientes/destacados, no de toda la base.
    """
    qs = (Product.objects.filter(activo=True)
          .exclude(categoria__slug__in=CATEGORIAS_COMPLEMENTO)
          .select_related("categoria", "tipo")
          .order_by("-destacado", "-created_at", "-pk")[:40])
    # `imagen_src` resuelve archivo o URL; filtrar aquí evita los NULL de la
    # columna (exclude(imagen="") no los deja pasar).
    candidatos = [p for p in qs if p.imagen_src]
    if not candidatos:
        return []
    return random.sample(candidatos, min(cantidad, len(candidatos)))


def home(request: HttpRequest) -> HttpResponse:
    productos = list(
        Product.objects.filter(activo=True)
        .select_related("categoria", "tipo")
        .prefetch_related("colores_producto__color")
    )
    return render(request, "core/home.html", {
        # La colección del home es una muestra, no el catálogo completo.
        "productos": productos[:8],
        "productos_total": len(productos),
        "categorias": Category.objects.all(),
        "hero_medias": list(HeroMedia.objects.filter(activo=True)),
        "hero_productos": _productos_hero(),
    })

import random

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from catalog.models import Category, Product
from core.forms import ComplaintForm
from core.models import HeroMedia, SiteSettings


def health(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok")


LEGAL_PAGES = {
    "privacidad": {
        "title": "Política de privacidad",
        "description": "Cómo tratamos los datos personales que nos compartes al utilizar este sitio.",
        "content_template": "core/legal/_privacy_content.html",
    },
    "terminos": {
        "title": "Términos y condiciones",
        "description": "Información sobre el uso del sitio, consultas, pedidos y atención comercial.",
        "content_template": "core/legal/_terms_content.html",
    },
    "cookies": {
        "title": "Política de cookies y tecnologías locales",
        "description": "Conoce qué almacenamiento técnico utiliza este sitio y cómo administrarlo.",
        "content_template": "core/legal/_cookies_content.html",
    },
}


def legal_page(request: HttpRequest, page: str) -> HttpResponse:
    content = LEGAL_PAGES[page]
    return render(request, "core/legal/page.html", {"legal_page": content})


@require_http_methods(["GET", "POST"])
def libro_reclamaciones(request: HttpRequest) -> HttpResponse:
    form = ComplaintForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reclamo = form.save()
        return render(
            request,
            "core/legal/complaint_received.html",
            {"complaint_code": reclamo.codigo},
        )
    return render(request, "core/legal/complaint_form.html", {"form": form})


# ── SEO: datos estructurados por página ──────────────────────────
def _abs(request, path: str) -> str:
    """URL absoluta con el dominio público del sitio (megaprimeimport.com)."""
    from django.conf import settings

    base = getattr(settings, "SITE_URL", "").rstrip("/")
    if not base:
        return request.build_absolute_uri(path)
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return base + (path if path.startswith("/") else "/" + path)


def _url_pagina(request, path: str) -> str:
    """URL canónica: siempre el dominio público (no el host de la petición)."""
    from django.conf import settings

    base = getattr(settings, "SITE_URL", "").rstrip("/")
    if base:
        return base + path
    return request.build_absolute_uri(path)


def _imagen_principal(producto) -> str:
    return producto.imagen_src or ""


def jsonld_negocio(request, site) -> dict:
    """LocalBusiness / Organization para el inicio."""
    datos = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": site.site_name,
        "url": _url_pagina(request, "/"),
        "description": site.meta_description,
        "telephone": "+" + site.whatsapp_number,
        "email": site.email,
        "priceRange": "$$",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": site.direccion_mostrada,
            "addressLocality": (site.cities or "Ambato").split(",")[0].strip(),
            "addressCountry": "EC",
        },
    }
    if site.logo:
        datos["logo"] = _abs(request, site.logo.url)
    if site.hero_image:
        datos["image"] = _abs(request, site.hero_image.url)
    if site.maps_link:
        datos["hasMap"] = site.maps_link
    if site.schedule:
        datos["openingHours"] = site.schedule
    return datos


def jsonld_catalogo(request, productos) -> dict:
    """CollectionPage con la lista de productos del catálogo."""
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Catálogo mayorista",
        "url": _url_pagina(request, reverse("catalog:catalogo")),
        "description": "Catálogo de productos para venta mayorista.",
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(productos),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": indice,
                    "name": producto.nombre,
                    "url": _url_pagina(request, reverse("catalog:detalle", args=[producto.slug])),
                }
                for indice, producto in enumerate(productos, start=1)
            ],
        },
    }


def jsonld_producto(request, producto, site) -> dict:
    """Product con su oferta, para que Google lo muestre en los resultados."""
    imagenes = [f.imagen_src for f in producto.imagenes.all() if f.imagen_src]
    if producto.imagen_src and producto.imagen_src not in imagenes:
        imagenes.insert(0, producto.imagen_src)
    url = _url_pagina(request, reverse("catalog:detalle", args=[producto.slug]))
    colores = [pc.color.nombre for pc in producto.colores_producto.all()]
    datos = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": producto.nombre,
        "sku": producto.sku,
        "url": url,
        "description": (producto.descripcion or producto.nombre)[:600],
        "category": producto.categoria.nombre,
        "brand": {"@type": "Brand", "name": site.site_name},
        "image": [_abs(request, i) for i in imagenes[:6]],
    }
    if colores:
        datos["color"] = ", ".join(colores)
    if producto.precio_mayor:
        datos["offers"] = {
            "@type": "Offer",
            "url": url,
            "price": f"{producto.precio_mayor:.2f}",
            "priceCurrency": producto.moneda or "USD",
            "availability": ("https://schema.org/InStock"
                             if producto.en_stock else "https://schema.org/OutOfStock"),
            "priceValidUntil": "",
            "seller": {"@type": "Organization", "name": site.site_name},
        }
        datos["offers"]["priceValidUntil"] = ""
    return datos


def jsonld_migas(request, elements) -> dict:
    """BreadcrumbList."""
    items = []
    for indice, (nombre, url) in enumerate(elements, start=1):
        item = {"@type": "ListItem", "position": indice, "name": nombre}
        if url:
            item["item"] = _abs(request, url)
        items.append(item)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": items}


# ── Vistas ───────────────────────────────────────────────────────
def _productos_hero(cantidad: int = 3) -> list:
    """Productos para el showcase del hero: destacados primero y elección al azar.

    Solo productos principales (nada de tornillos ni accesorios) y siempre
    con foto: se toman de los 40 más recientes/destacados, no de toda la base.
    """
    qs = (Product.objects.filter(activo=True)
          .exclude(categoria__slug__in=CATEGORIAS_COMPLEMENTO)
          .select_related("categoria", "tipo")
          .prefetch_related("imagenes")
          .order_by("-destacado", "-created_at", "-pk")[:40])
    # `imagen_src` resuelve archivo o URL; filtrar aquí evita los NULL de la
    # columna (exclude(imagen="") no los deja pasar).
    candidatos = []
    for producto in qs:
        imagen = producto.imagen_src
        if not imagen:
            primera_imagen = next(
                (foto.imagen_src for foto in producto.imagenes.all() if foto.imagen_src),
                "",
            )
            imagen = primera_imagen
        if imagen:
            producto.hero_image_src = imagen
            candidatos.append(producto)
    if not candidatos:
        return []
    return random.sample(candidatos, min(cantidad, len(candidatos)))


# Categorías que son complementos: no salen en el showcase del hero
# (el hero muestra los productos principales: tejas, cielo razo, paneles...).
CATEGORIAS_COMPLEMENTO = ("accesorios-y-materiales", "herramientas-y-equipos")


def home(request: HttpRequest) -> HttpResponse:
    site = SiteSettings.get_solo()
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
        "jsonld_negocio": jsonld_negocio(request, site),
        "seo_titulo": f"{site.site_name} | Acabados, Interiorismo y Maquinaria Pro",
        "seo_descripcion": site.meta_description,
        "seo_imagen": (_abs(request, site.hero_image.url)
                        if site.hero_image else
                        (_abs(request, site.logo.url) if site.logo else "")),
    })


def sitemap(request: HttpRequest) -> HttpResponse:
    """sitemap.xml con la portada, el catálogo y los productos activos."""
    from xml.sax.saxutils import escape

    entradas = [
        {"loc": _url_pagina(request, reverse("core:home")),
         "priority": "1.0", "changefreq": "daily"},
        {"loc": _url_pagina(request, reverse("catalog:catalogo")),
         "priority": "0.9", "changefreq": "weekly"},
        {"loc": _url_pagina(request, reverse("core:privacidad")),
         "priority": "0.3", "changefreq": "yearly"},
        {"loc": _url_pagina(request, reverse("core:terminos")),
         "priority": "0.3", "changefreq": "yearly"},
        {"loc": _url_pagina(request, reverse("core:cookies")),
         "priority": "0.3", "changefreq": "yearly"},
        {"loc": _url_pagina(request, reverse("core:libro_reclamaciones")),
         "priority": "0.3", "changefreq": "yearly"},
    ]
    for producto in (Product.objects.filter(activo=True)
                     .select_related("categoria")
                     .order_by("categoria__orden", "nombre")):
        entradas.append({
            "loc": _url_pagina(request, reverse("catalog:detalle", args=[producto.slug])),
            "lastmod": producto.updated_at.strftime("%Y-%m-%d"),
            "priority": "0.7", "changefreq": "weekly",
        })
    cuerpo = "".join(
        "<url><loc>{loc}</loc>{lastmod}<changefreq>{changefreq}</changefreq>"
        "<priority>{priority}</priority></url>".format(
            loc=escape(e["loc"]),
            lastmod=f"<lastmod>{e['lastmod']}</lastmod>" if e.get("lastmod") else "",
            changefreq=e["changefreq"], priority=e["priority"])
        for e in entradas)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f"{cuerpo}</urlset>")
    return HttpResponse(xml, content_type="application/xml")


def robots(request: HttpRequest) -> HttpResponse:
    lineas = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /carrito/",
        "Disallow: /webadmin/",
        f"Sitemap: {_url_pagina(request, '/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lineas) + "\n", content_type="text/plain")

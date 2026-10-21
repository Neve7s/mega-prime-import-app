"""Colores del producto: paleta del catálogo y aplicación en la ficha.

El panel manda una lista de colores (slug, nombre, hex, rol). Este módulo la
resuelve contra la tabla `Color` (creando el color si no estaba en la
paleta) y deja la ficha con esa lista, en ese orden.
"""

from django.db import transaction
from django.utils.text import slugify

from .models import Color, ProductColor

ROLES = ("", "exterior", "interior")


def _slug(nombre, usados):
    base = slugify(nombre)[:40] or "color"
    candidato = base
    numero = 2
    while candidato in usados:
        candidato = f"{base}-{numero}"
        numero += 1
    usados.add(candidato)
    return candidato


def _normaliza_rol(rol):
    valor = str(rol or "").strip().lower()
    return valor if valor in ROLES else ""


def color_de_paleta(slug):
    """Color de la paleta por slug (para el selector del panel)."""
    return Color.objects.filter(slug=slug).first()


def aplicar_colores(producto, datos):
    """Deja el producto con la lista de colores recibida.

    `datos`: [{"slug", "nombre", "hex", "rol"}]. Los que no existan en la
    paleta se crean. Los que ya no estén en la lista se eliminan.
    """
    if not producto.pk:
        raise ValueError("El producto debe estar guardado antes de asignarle colores.")
    usados = set(Color.objects.values_list("slug", flat=True))
    with transaction.atomic():
        producto.colores_producto.all().delete()
        for orden, item in enumerate(datos or []):
            if not isinstance(item, dict):
                continue
            nombre = str(item.get("nombre") or "").strip()
            slug = str(item.get("slug") or "").strip()
            hex_color = str(item.get("hex") or "").strip()
            if not nombre and not slug:
                continue
            tonalidad = None
            if slug:
                tonalidad = Color.objects.filter(slug=slug).first()
            if tonalidad is not None and nombre and tonalidad.nombre.casefold() != nombre.casefold():
                # Es un color propio con el nombre cambiado: no se toca la paleta.
                tonalidad = None
            if tonalidad is None and nombre:
                # Reutiliza el color de la paleta (con su tono) si existe.
                tonalidad = Color.objects.filter(nombre__iexact=nombre).first()
            if tonalidad is None:
                slug = _slug(nombre or slug, usados)
                tonalidad = Color.objects.create(
                    slug=slug, nombre=(nombre or slug)[:40],
                    hex=(hex_color or "#9CA3AF")[:7], orden=99)
            ProductColor.objects.get_or_create(
                producto=producto, color=tonalidad,
                rol=_normaliza_rol(item.get("rol")),
                defaults={"orden": orden})
    return producto


def colores_para_form(producto):
    """Los colores del producto como lista para el formulario del panel."""
    datos = []
    for pc in producto.colores_producto.all():
        datos.append({
            "slug": pc.color.slug,
            "nombre": pc.color.nombre,
            "hex": pc.color.hex,
            "rol": pc.rol,
        })
    return datos


def parsea_colores(texto):
    """Lee el JSON que manda el formulario del panel."""
    import json

    try:
        datos = json.loads(texto or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(datos, list):
        return []
    return [item for item in datos if isinstance(item, dict)]

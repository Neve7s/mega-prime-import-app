"""Reglas de calidad de ficha de producto y normalización de nombres.

Una sola fuente de verdad para el panel: qué le falta a un producto
(`faltantes_producto`), la clave para agrupar nombres parecidos
(`clave_nombre`) y las condiciones SQL equivalentes (`q_sin_*`) que
alimentan los conteos por categoría con `Count(filter=...)`.
"""
import re
import unicodedata
from collections import Counter

from django.db.models import Q

from .models import Product

SIN_FOTOS = "sin fotos"
SIN_CARACTERISTICAS = "sin características"
SIN_PRECIO = "sin precio"


def clave_nombre(nombre) -> str:
    """Clave de comparación: 'Teja  Roma' y 'teja roma' dan lo mismo.

    Quita tildes, pasa a minúsculas y colapsa todo lo que no sea
    letra o dígito en un solo espacio.
    """
    texto = unicodedata.normalize("NFKD", str(nombre or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z]+", " ", texto)).strip()


def faltantes_producto(producto) -> list:
    """Etiquetas de lo que le falta a la ficha. Lista vacía = ficha completa."""
    faltan = []
    if not (getattr(producto, "imagen", None)
            or (getattr(producto, "imagen_url", "") or "").strip()):
        faltan.append(SIN_FOTOS)
    if not producto.caracteristicas:
        faltan.append(SIN_CARACTERISTICAS)
    if producto.precio_mayor is None or producto.precio_mayor <= 0:
        faltan.append(SIN_PRECIO)
    return faltan


def q_sin_fotos(prefijo="") -> Q:
    return ((Q(**{f"{prefijo}imagen__isnull": True})
             | Q(**{f"{prefijo}imagen": ""}))
            & Q(**{f"{prefijo}imagen_url": ""}))


def q_sin_caracteristicas(prefijo="") -> Q:
    return (Q(**{f"{prefijo}caracteristicas": []})
            | Q(**{f"{prefijo}caracteristicas__isnull": True}))


def q_sin_precio(prefijo="") -> Q:
    return Q(**{f"{prefijo}precio_mayor__lte": 0})


def q_incompleto(prefijo="") -> Q:
    """Cualquiera de los tres faltantes. `prefijo` = 'productos__' desde Category."""
    return (q_sin_fotos(prefijo) | q_sin_caracteristicas(prefijo)
            | q_sin_precio(prefijo))


def grupos_duplicados() -> list:
    """Grupos de ≥2 productos con el mismo nombre normalizado en la misma categoría.

    Ordenados por categoría (orden, nombre) y luego por nombre.
    """
    grupos = {}
    productos = (Product.objects.select_related("categoria", "tipo")
                 .order_by("categoria__orden", "categoria__nombre", "nombre", "pk"))
    for producto in productos:
        grupos.setdefault((producto.categoria_id, clave_nombre(producto.nombre)),
                          []).append(producto)
    duplicados = [g for g in grupos.values() if len(g) > 1]
    duplicados.sort(key=lambda g: (g[0].categoria.orden, g[0].categoria.nombre,
                                   g[0].nombre.lower()))
    return duplicados


def contar_grupos_duplicados() -> int:
    """Número de grupos con productos repetidos (para el badge del encabezado)."""
    conteo = Counter()
    for cat_id, nombre in Product.objects.values_list("categoria_id", "nombre"):
        conteo[(cat_id, clave_nombre(nombre))] += 1
    return sum(1 for n in conteo.values() if n > 1)

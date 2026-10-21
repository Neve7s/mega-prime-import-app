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


def _frases_de_color():
    """Nombres de la paleta (y sus sinónimos) ya normalizados."""
    from .models import Color

    frases = set()
    for color in Color.objects.all():
        frases.add(clave_nombre(color.nombre))
    return {f for f in frases if f}


def clave_modelo(nombre, colores_extra=(), paleta=None) -> str:
    """Clave del modelo: el nombre sin los colores.

    'Teja Español PVC Negro/Blanco 2.5 mm' y 'Teja Español PVC Verde/Blanco
    2.5 mm' dan la misma clave: son el mismo modelo en otro color.
    """
    if paleta is None:
        paleta = _frases_de_color()
    return _clave_modelo_con_paleta(nombre, colores_extra, paleta)


RE_MEDIDAS = re.compile(
    r"\d+(?:[.,*×]\d+)*\s*(?:mm|cm|kg|ml)\b|\d+(?:[.,*×]\d+)*\s*m(?![a-záéíóúñ])",
    re.IGNORECASE)


def sin_medidas(texto):
    """Quita las medidas: '2.5 mm', '0.25*5.95*0.08 mm'…"""
    return RE_MEDIDAS.sub(" ", str(texto or ""))


def clave_modelo_medidas(nombre, colores_extra=(), contexto="") -> str:
    """Clave del modelo usando las medidas del nombre o de la categoría.

    Si la categoría ya fija el espesor (p. ej. "Teja PVC tipo Roma colonial
    2.5 mm."), las medidas del producto no se usan en la clave: así las
    fichas de un mismo modelo caen juntas aunque unas las escriban y otras
    no.
    """
    base = clave_modelo(nombre, colores_extra)
    medidas = _normaliza_medidas("".join(RE_MEDIDAS.findall(base)))
    if not medidas:
        medidas = _normaliza_medidas("".join(RE_MEDIDAS.findall(contexto or "")))
    return sin_medidas(base).replace(" ", "") + medidas


def _normaliza_medidas(texto):
    """'2.5 mm' y '2 5 mm' son la misma medida."""
    return re.sub(r"[^0-9a-z]", "", str(texto or "").lower())


def _clave_modelo_con_paleta(nombre, colores_extra, paleta) -> str:
    texto = clave_nombre(nombre)
    frases = set(paleta)
    for color in colores_extra or ():
        frase = clave_nombre(color)
        if frase:
            frases.add(frase)
    # Las frases más largas primero: "blanco opal" antes que "blanco".
    # Sin \b al final: el color puede ir pegado a un número ("Terracota2.5mm").
    for frase in sorted(frases, key=len, reverse=True):
        texto = re.sub(rf"\b{re.escape(frase)}", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def grupos_mismo_modelo(paleta=None) -> list:
    """Productos que son el mismo modelo en distinto color.

    Agrupa por (categoría, tipo, modelo) y devuelve solo los grupos con
    nombres distintos: los colores son la única diferencia.
    """
    if paleta is None:
        paleta = _frases_de_color()
    grupos = {}
    productos = (Product.objects.filter(activo=True)
                 .select_related("categoria", "tipo")
                 .prefetch_related("colores_producto__color")
                 .order_by("categoria__orden", "categoria__nombre", "nombre", "pk"))
    for producto in productos:
        extras = [pc.color.nombre for pc in producto.colores_producto.all()]
        clave = _clave_modelo_con_paleta(producto.nombre, extras, paleta)
        if not clave:
            continue
        grupos.setdefault(
            (producto.categoria_id, producto.tipo_id, clave), []).append(producto)
    candidatos = [g for g in grupos.values() if len(g) > 1]
    # Solo si además el nombre difiere (si no, es un duplicado exacto).
    distintos = []
    for grupo in candidatos:
        nombres = {clave_nombre(p.nombre) for p in grupo}
        if len(nombres) > 1:
            distintos.append(grupo)
    distintos.sort(key=lambda g: (g[0].categoria.orden, g[0].categoria.nombre,
                                   g[0].nombre.lower()))
    return distintos


def fusionar_variantes(principal, variantes) -> dict:
    """Junta las variantes de color en un solo producto.

    Los colores y las fotos de las variantes pasan al principal; las
    variantes se desactivan (no se borran, por si acaso).
    """
    from .models import ProductColor

    movidos = {"colores": 0, "fotos": 0}
    orden = principal.colores_producto.count()
    vistos = {(pc.color_id, pc.rol) for pc in principal.colores_producto.all()}
    for variante in variantes:
        if variante.pk == principal.pk:
            continue
        for pc in variante.colores_producto.all():
            if (pc.color_id, pc.rol) in vistos:
                continue
            ProductColor.objects.create(
                producto=principal, color=pc.color, orden=orden, rol=pc.rol)
            vistos.add((pc.color_id, pc.rol))
            orden += 1
            movidos["colores"] += 1
        for foto in variante.imagenes.all():
            foto.producto = principal
            foto.orden = principal.imagenes.count()
            foto.save(update_fields=["producto", "orden"])
            movidos["fotos"] += 1
        # La foto principal de la variante pasa al principal si este no tiene.
        if not principal.imagen_src and variante.imagen_src:
            principal.imagen = variante.imagen
            principal.imagen_url = variante.imagen_url
            principal.save(update_fields=["imagen", "imagen_url"])
        variante.activo = False
        variante.save(update_fields=["activo"])
    return movidos


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

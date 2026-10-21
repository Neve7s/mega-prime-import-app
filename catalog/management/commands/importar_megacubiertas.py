"""Importa el catálogo de megacubiertasimportaciones.com.

El panel de ese sitio guarda todo en Supabase (`site_content.data`). Este
comando lee ese JSON (descargado desde el navegador) y crea/actualiza los
productos del catálogo: descripción, características, ficha técnica, fotos y
colores.

Uso:
    python manage.py importar_megacubiertas ruta/mc_data.json

Reglas:
· Los productos que solo difieren en el color se vuelven UN producto con
  varios colores (igual que en la plantilla de poductos.md).
· Los accesorios van a su propia categoría ("Accesorios y Materiales").
· Es idempotente: se puede volver a ejecutar sin duplicar nada.
"""

import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from catalog.calidad import clave_modelo, clave_modelo_medidas
from catalog.colores import aplicar_colores
from catalog.models import Category, Color, Product, ProductColor, ProductImage, TipoProducto
from catalog.sku import siguiente_sku

# Categoría del sitio -> (slug de la categoría, nombre)
CATEGORIAS = {
    "cubiertas": ("tejas-y-cubiertas", "Tejas y Cubiertas"),
    "teja trapezoidal": ("tejas-y-cubiertas", "Tejas y Cubiertas"),
    "teja pvc tipo roma": ("tejas-y-cubiertas", "Tejas y Cubiertas"),
    "cielo razo": ("cielorrasos-y-techos", "Cielorrasos y Techos"),
    "piso": ("pisos", "Pisos"),
    "policarbonato": ("cielorrasos-y-techos", "Cielorrasos y Techos"),
    "wall panel": ("revestimientos-y-paneles", "Revestimientos y Paneles"),
}

# Categoría de accesorios -> (slug de la categoría, slug del tipo de producto)
ACCESORIOS = {
    "accesorios para teja": ("accesorios-y-materiales", "cumbreros"),
    "tornillos": ("accesorios-y-materiales", "tornilleria"),
    "canal": ("accesorios-y-materiales", "canales"),
    "accesorios y mucho": ("accesorios-y-materiales", "perfiles"),
}

# Filtros del sitio -> tipo de producto (el primero que coincide manda)
FILTROS = [
    ("cielo razo pvc", "cielo-razo", "Cielo Razo"),
    ("trapezoidal", "teja-trapezoidal", "Teja Trapezoidal"),
    ("piso", "spc", "SPC"),
    ("policarbonato", "policarbonato-alveolar", "Policarbonato Alveolar"),
    ("pvc", "teja-pvc", "Teja PVC"),
    ("wall panel", "wall-panel-wpc", "Wall Panel WPC"),
]

# Tonos que no están en la paleta general
TONOS = {
    "Abedul Miel": "#C9A876",
    "Alamo Natural": "#D9C7A7",
    "Álamo Natural": "#D9C7A7",
    "Forest Grey": "#6B7A72",
    "Forest Nut": "#6B4A2F",
    "Café": "#7A4A24",
    "Cafe": "#7A4A24",
}


def _texto(valor):
    return " ".join(str(valor or "").split())


def _slug_limpio(texto, usados):
    base = slugify(texto)[:150] or "producto"
    candidato = base
    numero = 2
    while candidato in usados:
        candidato = f"{base}-{numero}"
        numero += 1
    usados.add(candidato)
    return candidato


class Command(BaseCommand):
    help = "Importa el catálogo de megacubiertasimportaciones.com (JSON del panel)."

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="Ruta del JSON con la data del sitio.")

    def handle(self, *args, **opciones):
        ruta = Path(opciones["archivo"])
        if not ruta.exists():
            self.stderr.write(f"No existe el archivo: {ruta}")
            return
        datos = json.loads(ruta.read_text(encoding="utf-8"))

        categorias = self._asegurar_categorias()
        tipos = self._asegurar_tipos(categorias)
        productos = self._productos_del_sitio(datos)
        # La paleta se actualiza con los colores del sitio (son la fuente real).
        self._asegura_colores(productos)
        lineas = self._agrupar_por_modelo(productos)

        creados = actualizados = 0
        for linea in lineas:
            if self._guarda(linea, categorias, tipos):
                creados += 1
            else:
                actualizados += 1
        self.stdout.write(self.style.SUCCESS(
            f"Catálogo importado: {creados} productos nuevos, {actualizados} "
            f"actualizados ({len(lineas)} fichas en total)."))

    # ── Estructura ───────────────────────────────────────────
    def _asegurar_categorias(self):
        mapa = {}
        for slug, (nombre, descripcion) in {
            "tejas-y-cubiertas": ("Tejas y Cubiertas",
                                   "Tejas y cubiertas: perfil español, romano y trapezoidal."),
            "cielorrasos-y-techos": ("Cielorrasos y Techos",
                                      "Cielorrasos y placas de policarbonato para iluminación natural."),
            "pisos": ("Pisos", "Pisos de alto tráfico: SPC y porcelanato."),
            "revestimientos-y-paneles": ("Revestimientos y Paneles",
                                        "Paneles decorativos WPC y acústicos para revestimiento interior."),
            "accesorios-y-materiales": ("Accesorios y Materiales",
                                        "Cumbreros, tornillería, perfiles y canales."),
        }.items():
            categoria, _ = Category.objects.get_or_create(
                slug=slug, defaults={"nombre": nombre, "descripcion": descripcion})
            mapa[slug] = categoria
        return mapa

    def _asegurar_tipos(self, categorias):
        mapa = {}
        for slug, (categoria_slug, nombre) in {
            "teja-pvc": ("tejas-y-cubiertas", "Teja PVC"),
            "teja-trapezoidal": ("tejas-y-cubiertas", "Teja Trapezoidal"),
            "cielo-razo": ("cielorrasos-y-techos", "Cielo Razo"),
            "policarbonato-alveolar": ("cielorrasos-y-techos", "Policarbonato Alveolar"),
            "spc": ("pisos", "SPC"),
            "wall-panel-wpc": ("revestimientos-y-paneles", "Wall Panel WPC"),
            "cumbreros": ("accesorios-y-materiales", "Cumbreros"),
            "tornilleria": ("accesorios-y-materiales", "Tornillería"),
            "perfiles": ("accesorios-y-materiales", "Perfiles"),
            "canales": ("accesorios-y-materiales", "Canales"),
        }.items():
            tipo, _ = TipoProducto.objects.get_or_create(
                slug=slug, defaults={"nombre": nombre,
                                     "categoria": categorias[categoria_slug]})
            mapa[slug] = tipo
        return mapa

    # ── Lectura del JSON ─────────────────────────────────────
    def _productos_del_sitio(self, datos):
        """Aplana el JSON del sitio a una lista de fichas."""
        fichas = []
        for categoria in datos.get("categoriasProducto") or []:
            nombre_cat = _texto(categoria.get("nombre")).lower()
            destino = next((v for k, v in CATEGORIAS.items() if nombre_cat.startswith(k)), None)
            if destino is None:
                self.stderr.write(f"Categoría sin mapeo, se omite: {nombre_cat}")
                continue
            for item in categoria.get("items") or []:
                ficha = self._ficha(item, destino[0], tipo_slug=None)
                ficha["categoria_contexto"] = categoria.get("nombre") or ""
                fichas.append(ficha)
        for categoria in datos.get("accesorios") or []:
            nombre_cat = _texto(categoria.get("nombre")).lower()
            destino = next((v for k, v in ACCESORIOS.items() if nombre_cat.startswith(k)), None)
            if destino is None:
                self.stderr.write(f"Categoría de accesorios sin mapeo: {nombre_cat}")
                continue
            for item in categoria.get("items") or []:
                fichas.append(self._ficha(item, destino[0], tipo_slug=destino[1]))
        return fichas

    def _ficha(self, item, categoria_slug, tipo_slug):
        nombre = _texto(item.get("nombre"))
        colores = []
        for color in item.get("colores") or []:
            nombre_color = _texto(color.get("nombre"))
            if not nombre_color:
                continue
            colores.append({"nombre": nombre_color,
                            "hex": _texto(color.get("hex")).upper(),
                            "rol": _texto(color.get("rol"))})
        # El color puede venir solo en el nombre (piso, policarbonato...).
        if not colores:
            detectada = self._color_en_nombre(nombre)
            if detectada:
                colores.append(detectada)
        tipo = tipo_slug or self._tipo_por_nombre(nombre)
        return {
            "id": item.get("id"),
            "nombre": nombre,
            "descripcion": _texto(item.get("descripcion")),
            "caracteristicas": [_texto(c) for c in (item.get("caracteristicas") or []) if _texto(c)],
            "ficha": self._ficha_tecnica(item.get("ficha")),
            "fotos": [f for f in (item.get("fotos") or []) if f],
            "imagen": item.get("imagen") or "",
            "colores": colores,
            "categoria": categoria_slug,
            "tipo": tipo,
        }

    def _ficha_tecnica(self, pares):
        """[[clave, valor]] -> {clave: valor} (sin los valores de color)."""
        datos = {}
        for par in pares or []:
            if not isinstance(par, (list, tuple)) or len(par) < 2:
                continue
            clave = _texto(par[0])
            valor = _texto(par[1])
            if not clave or not valor:
                continue
            if clave.casefold() in ("color", "tono", "tono / diseño", "tono / diseno"):
                continue
            datos[clave] = valor
        return datos

    def _color_en_nombre(self, nombre):
        """Detecta el color/tono en el nombre (para los productos sin color)."""
        from catalog.calidad import clave_nombre

        texto = clave_nombre(nombre)
        for tono, hex_color in TONOS.items():
            if clave_nombre(tono) in texto:
                return {"nombre": tono, "hex": hex_color, "rol": ""}
        # Los nombres más largos primero: "Alamo Natural" antes que "Natural".
        for color in sorted(Color.objects.all(), key=lambda c: -len(c.nombre)):
            if clave_nombre(color.nombre) in texto:
                return {"nombre": color.nombre, "hex": color.hex, "rol": ""}
        return None

    def _tipo_por_nombre(self, nombre):
        texto = nombre.lower()
        for filtro, slug, _ in FILTROS:
            if filtro in texto:
                return slug
        return None

    def _asegura_colores(self, fichas):
        """Crea/actualiza la paleta con los colores que usa el sitio."""
        from catalog.calidad import clave_nombre

        usados = set(Color.objects.values_list("slug", flat=True))
        for ficha in fichas:
            for color in ficha["colores"]:
                nombre = color["nombre"]
                hex_color = color.get("hex") or TONOS.get(nombre, "")
                if not hex_color:
                    continue
                existente = None
                for color_paleta in Color.objects.all():
                    if clave_nombre(color_paleta.nombre) == clave_nombre(nombre):
                        existente = color_paleta
                        break
                if existente is None:
                    slug = _slug_limpio(nombre, usados)
                    Color.objects.create(slug=slug, nombre=nombre[:40],
                                         hex=hex_color[:7], orden=99)
                elif existente.hex != hex_color[:7]:
                    existente.hex = hex_color[:7]
                    existente.save(update_fields=["hex"])

    # ── Agrupación por modelo ────────────────────────────────
    def _agrupar_por_modelo(self, fichas):
        """Las fichas que solo difieren en el color se vuelven una."""
        grupos = {}
        for ficha in fichas:
            colores = [c["nombre"] for c in ficha["colores"]]
            clave = clave_modelo_medidas(ficha["nombre"], colores,
                                        ficha.get("categoria_contexto", ""))
            if not clave:
                clave = slugify(ficha["nombre"])
            if clave not in grupos:
                grupos[clave] = {"ficha": dict(ficha), "colores": [], "fotos": [],
                                 "nombre": self._nombre_sin_color(ficha["nombre"], colores)}
            grupo = grupos[clave]
            grupo["fotos"].extend(ficha["fotos"])
            for color in ficha["colores"]:
                if color["nombre"] not in [c["nombre"] for c in grupo["colores"]]:
                    grupo["colores"].append(color)
            # La descripción y las características más largas son las mejores.
            if len(ficha["descripcion"]) > len(grupo["ficha"]["descripcion"]):
                grupo["ficha"]["descripcion"] = ficha["descripcion"]
            if len(ficha["caracteristicas"]) > len(grupo["ficha"]["caracteristicas"]):
                grupo["ficha"]["caracteristicas"] = ficha["caracteristicas"]
            for clave_ficha, valor in ficha["ficha"].items():
                grupo["ficha"]["ficha"].setdefault(clave_ficha, valor)
        lineas = []
        for clave, grupo in grupos.items():
            ficha = grupo["ficha"]
            ficha["nombre"] = grupo["nombre"]
            ficha["clave"] = clave
            ficha["colores"] = grupo["colores"]
            ficha["fotos"] = list(dict.fromkeys(grupo["fotos"]))
            if not ficha["fotos"] and ficha.get("imagen"):
                ficha["fotos"] = [ficha["imagen"]]
            lineas.append(ficha)
        return lineas

    def _nombre_sin_color(self, nombre, colores):
        """El nombre del modelo sin el color.

        'Teja Español PVC Negro/Blanco 2.5 mm.' → 'Teja Español PVC 2.5 mm.'
        (se quita el color y su pareja, no las demás barras).
        """
        texto = nombre
        paleta = [c.nombre for c in Color.objects.all()]
        for color in colores:
            alterno = "|".join(re.escape(n) for n in paleta)
            texto = re.sub(rf"{re.escape(color)}(/({alterno}))?", " ", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\s*/\s*", " ", texto)
        texto = re.sub(r"\s+", " ", texto).strip(" .-")
        return texto or nombre

    # ── Guardado ─────────────────────────────────────────────
    def _busca_producto(self, categoria, slug, clave):
        """El producto que ya existe para este modelo (por slug o por clave)."""
        producto = Product.objects.filter(slug=slug).first()
        if producto is not None:
            return producto
        if not clave:
            return None
        for otro in Product.objects.filter(categoria=categoria):
            colores = [pc.color.nombre for pc in otro.colores_producto.all()]
            if clave_modelo_medidas(otro.nombre, colores) == clave:
                return otro
        return None

    def _guarda(self, ficha, categorias, tipos):
        nombre = ficha["nombre"]
        slug = slugify(nombre)[:50] or "producto"
        categoria = categorias[ficha["categoria"]]
        producto = self._busca_producto(categoria, slug, ficha.get("clave"))
        nuevo = producto is None
        if nuevo:
            producto = Product(slug=slug, sku=siguiente_sku())
        producto.nombre = nombre
        producto.categoria = categoria
        producto.tipo = tipos.get(ficha["tipo"]) if ficha.get("tipo") else None
        producto.descripcion = ficha["descripcion"]
        producto.caracteristicas = ficha["caracteristicas"]
        producto.ficha_tecnica = ficha["ficha"]
        producto.activo = True
        if not producto.precio_mayor:
            producto.precio_mayor = 0
        producto.save()
        # Colores
        aplicar_colores(producto, [
            {"slug": "", "nombre": c["nombre"], "hex": c.get("hex") or "", "rol": c.get("rol") or ""}
            for c in ficha["colores"]])
        # Galería: la primera foto es la portada
        fotos = list(producto.imagenes.all())
        for foto in fotos:
            if foto.imagen_url in ficha["fotos"]:
                foto.delete()
        orden = 0
        for url in ficha["fotos"]:
            ProductImage.objects.create(producto=producto, imagen_url=url[:500],
                                        alt=producto.nombre[:160], orden=orden)
            orden += 1
        if not producto.imagen_src and ficha["fotos"]:
            producto.imagen_url = ficha["fotos"][0][:500]
            producto.save(update_fields=["imagen_url"])
        return nuevo

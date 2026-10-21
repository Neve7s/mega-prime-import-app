"""Carga el catálogo desde `poductos.md` (categorías, tipos y productos).

Uso:
    python manage.py cargar_catalogo_md [ruta/poductos.md]

El Markdown trae el color dentro del nombre del producto ("Teja Español PVC
Negro/Blanco 2.5 mm"). Como el color es una variable, las fichas que solo
difieren en el color se juntan en un solo producto con varios colores.

Es idempotente: se puede volver a ejecutar sin duplicar nada.
"""

import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from catalog.calidad import clave_modelo
from catalog.colores import aplicar_colores
from catalog.models import Category, Color, Product, ProductImage, TipoProducto
from catalog.sku import siguiente_sku

BASE = Path(__file__).resolve().parents[3]

# Categoría del Markdown -> (categoría del catálogo, tipo de producto)
MAPA_CATEGORIAS = {
    "cubiertas": ("tejas-y-cubiertas", "Teja Española"),
    "teja trapezoidal": ("tejas-y-cubiertas", "Teja Trapezoidal"),
    "teja pvc tipo roma": ("tejas-y-cubiertas", "Teja Roma"),
    "teja pvc tipo roma colonial": ("tejas-y-cubiertas", "Teja Roma"),
    "cielo razo": ("cielorrasos-y-techos", "Cielo Razo"),
    "piso": ("pisos", "SPC"),
    "policarbonato": ("cielorrasos-y-techos", "Policarbonato Alveolar"),
    "wall panel": ("revestimientos-y-paneles", "Wall Panel WPC"),
}

CATEGORIAS_NUEVAS = {
    "tejas-y-cubiertas": ("Tejas y Cubiertas",
                           "Tejas y cubiertas: perfil español, romano y trapezoidal."),
    "cielorrasos-y-techos": ("Cielorrasos y Techos",
                              "Cielorrasos y placas de policarbonato para iluminación natural."),
    "pisos": ("Pisos", "Pisos de alto tráfico: SPC y porcelanato."),
    "revestimientos-y-paneles": ("Revestimientos y Paneles",
                                 "Paneles decorativos WPC y acústicos para revestimiento interior."),
    "accesorios-y-materiales": ("Accesorios y Materiales",
                                "Cumbreros, tornillería, selladores y perfiles."),
    "herramientas-y-equipos": ("Herramientas y Equipos",
                                "Herramientas y maquinaria para corte e instalación."),
}

# Tonos propios del catálogo (no están en la paleta general).
TONOS_CATALOGO = {
    "Abedul Miel": "#C9A876",
    "Álamo Natural": "#D9C7A7",
    "Alamo Natural": "#D9C7A7",
    "Forest Grey": "#6B7A72",
    "Forest Nut": "#6B4A2F",
    "Gris Perla": "#C9CDD3",
    "Cristal": "#E8F1F5",
    "Verde Oliva": "#6B7A3A",
}

RE_CATEGORIA = re.compile(r"^##\s+\d+\.\s+(?P<titulo>.+?)\s*$")
RE_DESCRIPCION = re.compile(r"\*\*Descripci[oó]n de la categor[ií]a:\*\*\s*(?P<texto>.+)")
RE_PRODUCTO = re.compile(r"^\d+\.\s+\*\*(?P<nombre>.+?)\*\*")
RE_FICHA = re.compile(r"\*\*Caracter[ií]sticas t[eé]cnicas:\*\*\s*(?P<texto>.+)")
RE_FOTO = re.compile(r"\*\s*\[Ver fotograf[ií]a \d+\]\((?P<url>[^)]+)\)")
RE_DIMENSION = re.compile(r"\d+(?:[.,*×]\d+)*\s*(?:mm|cm|kg|ml)\b|\d+(?:[.,*×]\d+)*\s*m(?![a-záéíóúñ])",
                          re.IGNORECASE)


class Command(BaseCommand):
    help = "Carga el catálogo del Markdown (categorías, tipos, productos y colores)."

    def add_arguments(self, parser):
        parser.add_argument("archivo", nargs="?", default=str(BASE / "poductos.md"),
                            help="Ruta del Markdown con el catálogo.")

    def handle(self, *args, **opciones):
        ruta = Path(opciones["archivo"])
        if not ruta.exists():
            self.stderr.write(f"No existe el archivo: {ruta}")
            return
        texto = ruta.read_text(encoding="utf-8")
        categorias = self._parsear(texto)
        if not categorias:
            self.stderr.write("No se encontró ninguna categoría en el Markdown.")
            return

        # 1) Categorías y tipos del catálogo
        mapa = self._asegurar_categorias()

        creadas = actualizadas = 0
        for categoria_md, productos in categorias.items():
            destino = self._destino(categoria_md, mapa)
            if destino is None:
                self.stderr.write(f"Categoría sin mapeo, se omite: {categoria_md}")
                continue
            categoria, tipo = destino
            for _clave, ficha in self._agrupar(productos, categoria_md).items():
                if self._guardar(categoria, tipo, ficha):
                    creadas += 1
                else:
                    actualizadas += 1
        self.stdout.write(self.style.SUCCESS(
            f"Catálogo cargado: {creadas} productos nuevos, {actualizadas} actualizados, "
            f"{len(categorias)} categorías del Markdown."))

    # ── Parsing ──────────────────────────────────────────────
    def _parsear(self, texto):
        """{categoría_md: [ {nombre, ficha, fotos} ]}"""
        categorias = {}
        categoria_actual = None
        for linea in texto.splitlines():
            match = RE_CATEGORIA.match(linea)
            if match:
                categoria_actual = match.group("titulo").strip()
                categorias.setdefault(categoria_actual, [])
                continue
            if categoria_actual is None:
                continue
            match = RE_PRODUCTO.match(linea)
            if match:
                nombre = re.sub(r"\s*\*\(.*?\)\*\s*$", "", match.group("nombre")).strip()
                categorias[categoria_actual].append({"nombre": nombre, "ficha": "",
                                                    "fotos": []})
                continue
            if not categorias[categoria_actual]:
                continue
            ficha = categorias[categoria_actual][-1]
            match = RE_FICHA.search(linea)
            if match:
                ficha["ficha"] = match.group("texto").strip()
                continue
            match = RE_FOTO.search(linea)
            if match:
                ficha["fotos"].append(match.group("url"))
        return categorias

    def _atributos(self, ficha_texto):
        """'Espesor: 2.5 mm | Material: PVC' -> {'Espesor': '2.5 mm', …}"""
        datos = {}
        for parte in str(ficha_texto or "").split("|"):
            if ":" not in parte:
                continue
            clave, _, valor = parte.partition(":")
            clave = clave.strip()
            valor = valor.strip()
            if clave and valor:
                datos[clave] = valor
        return datos

    def _colores_de(self, nombre, atributos):
        """Colores del producto: primero los de la ficha, si no los del nombre.

        'Blanco Opal (difusor de luz)' -> 'Blanco Opal';
        'Azul exterior / Gris interior' -> Azul (exterior) y Gris (interior);
        'Negro / Blanco' -> Negro (exterior) y Blanco (interior);
        'Tono / Diseño: Abedul Miel' -> Abedul Miel (tono).
        """
        nombres = []
        roles = {}
        texto = (atributos.get("Color") or atributos.get("Tono / Diseño")
                 or atributos.get("Tono") or "")
        partes = [p.strip() for p in texto.split("/") if p.strip()]
        for indice, parte in enumerate(partes):
            nombre_color = parte
            rol = ""
            if "(" in nombre_color:
                nombre_color = nombre_color.split("(")[0].strip()
            for palabra in ("exterior", "interior"):
                if nombre_color.casefold().endswith(" " + palabra):
                    nombre_color = nombre_color[: -len(palabra)].strip()
                    rol = palabra
            if not rol and len(partes) > 1:
                # Pareja exterior/interior (convención del Excel de costos).
                rol = "exterior" if indice == 0 else "interior"
            if nombre_color.casefold() in ("transparente", "cristal"):
                nombre_color = "Transparente"
            if nombre_color and nombre_color not in nombres:
                nombres.append(nombre_color)
                roles[nombre_color] = rol
        if not nombres:
            nombres = self._colores_en_nombre(nombre)
            roles = {color: "" for color in nombres}
        return nombres, roles

    def _colores_en_nombre(self, nombre):
        """Busca en el nombre los colores de la paleta ('Negro/Blanco')."""
        from django.db.models.functions import Length

        texto = str(nombre or "")
        encontrados = []
        paleta = Color.objects.annotate(largo=Length("nombre")).order_by("-largo")
        for color in paleta:
            if color.nombre.casefold() in texto.casefold():
                encontrados.append(color.nombre)
        return encontrados

    def _agrupar(self, productos, contexto=""):
        """Junta las fichas que solo difieren en el color -> {modelo: ficha}."""
        grupos = {}
        for producto in productos:
            atributos = self._atributos(producto["ficha"])
            colores, roles = self._colores_de(producto["nombre"], atributos)
            clave = self._clave_agrupacion(producto["nombre"], colores, contexto)
            nombre_modelo = self._nombre_sin_color(producto["nombre"], colores)
            if clave not in grupos:
                grupos[clave] = {"nombre": nombre_modelo, "atributos": {},
                                 "colores": [], "roles": {}, "fotos": []}
            grupo = grupos[clave]
            for clave_attr, valor in atributos.items():
                if clave_attr.casefold() == "color":
                    continue
                grupo["atributos"].setdefault(clave_attr, valor)
            for color in colores:
                if color not in grupo["colores"]:
                    grupo["colores"].append(color)
                    grupo["roles"][color] = roles.get(color, "")
            grupo["fotos"].extend(producto["fotos"])
        # El color queda como "exterior/interior" solo si el modelo tiene dos
        # colores; con más, son los colores disponibles y el interior se omite.
        for grupo in grupos.values():
            if len(grupo["colores"]) > 2:
                grupo["colores"] = [c for c in grupo["colores"]
                                    if grupo["roles"].get(c) != "interior"]
                grupo["roles"] = {c: "" for c in grupo["colores"]}
            else:
                for color in grupo["colores"]:
                    if not grupo["roles"].get(color):
                        grupo["roles"][color] = ""
        return grupos

    def _clave_agrupacion(self, nombre, colores, contexto=""):
        """Clave del modelo: el nombre sin colores y con las medidas de la categoría.

        Así '2.5 mm' y '2.5mm' caen en la misma ficha, y las medidas que solo
        aparecen en el título de la categoría (p. ej. la teja Roma) se
        agregan a todas sus fichas.
        """
        texto = self._sin_medidas(nombre)
        clave = clave_modelo(texto, colores).replace(" ", "")
        return clave + self._sin_medidas(contexto).replace(" ", "")

    def _sin_medidas(self, texto):
        """Quita las medidas: '2.5 mm', '0.25*5.95*0.08 mm'…"""
        return RE_DIMENSION.sub(" ", str(texto or ""))

    def _nombre_sin_color(self, nombre, colores):
        """Quita del nombre los colores: 'Teja PVC Negro/Blanco 2.5 mm'."""
        texto = str(nombre or "")
        for color in colores:
            texto = re.sub(re.escape(color), " ", texto, flags=re.IGNORECASE)
        texto = re.sub(r"[\/,]", " ", texto)
        texto = re.sub(r"\s+", " ", texto).strip(" .-")
        return texto

    # ── Alta en la base ─────────────────────────────────────
    def _asegurar_categorias(self):
        mapa = {}
        for slug, (nombre, descripcion) in CATEGORIAS_NUEVAS.items():
            categoria, _ = Category.objects.get_or_create(
                slug=slug, defaults={"nombre": nombre, "descripcion": descripcion})
            mapa[slug] = categoria
        return mapa

    def _destino(self, categoria_md, mapa):
        clave = slugify(categoria_md)
        for prefijo, (slug_categoria, nombre_tipo) in MAPA_CATEGORIAS.items():
            if clave.startswith(slugify(prefijo)):
                categoria = mapa[slug_categoria]
                tipo, _ = TipoProducto.objects.get_or_create(
                    slug=slugify(nombre_tipo),
                    defaults={"nombre": nombre_tipo,
                              "descripcion": f"Familia {nombre_tipo.lower()}."})
                return categoria, tipo
        return None

    def _guardar(self, categoria, tipo, ficha):
        nombre = ficha["nombre"]
        slug = slugify(nombre)[:150] or "producto"
        # Busca dentro de la categoría: no toca productos de otra categoría.
        existente = Product.objects.filter(categoria=categoria, slug=slug).first()
        if existente is None and Product.objects.filter(slug=slug).exists():
            slug = f"{slug}-{categoria.slug}"[:150]
            existente = Product.objects.filter(categoria=categoria, slug=slug).first()
        creado = existente is None
        if creado:
            producto = Product(categoria=categoria, tipo=tipo, sku=siguiente_sku(),
                               nombre=nombre, slug=slug)
        else:
            producto = existente
            producto.categoria = categoria
            producto.tipo = tipo
        if not producto.descripcion:
            producto.descripcion = ""
        if not producto.precio_mayor:
            producto.precio_mayor = 0
        if creado:
            # Solo los productos nuevos reciben la ficha del Markdown.
            producto.ficha_tecnica = ficha["atributos"]
            producto.caracteristicas = [f"{k}: {v}" for k, v in ficha["atributos"].items()]
            producto.activo = True
        producto.save()
        # Colores del modelo: solo si el producto es nuevo o no tiene colores
        # (no se pisa lo que el usuario ajustó en el panel).
        if creado or not producto.colores_producto.exists():
            aplicar_colores(producto, [
                {"slug": "", "nombre": color,
                 "hex": TONOS_CATALOGO.get(color, ""), "rol": ficha["roles"].get(color, "")}
                for color in ficha["colores"]])
        # Fotos: solo si el enlace es real (el Markdown trae enlaces de ejemplo)
        orden = producto.imagenes.count()
        for url in ficha["fotos"]:
            if not url or "administrador.html" in url:
                continue
            if producto.imagenes.filter(imagen_url=url).exists():
                continue
            ProductImage.objects.create(producto=producto, imagen_url=url,
                                        alt=producto.nombre[:160], orden=orden)
            orden += 1
        return creado

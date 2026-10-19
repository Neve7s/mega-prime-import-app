from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from PIL import Image

from .models import Category, Product, TipoProducto

import shutil
import tempfile


class ProductTest(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(nombre="Porcelanatos", slug="porcelanato")

    def test_sku_unico_y_str(self):
        p = Product.objects.create(
            categoria=self.cat, sku="MPG-CALA-120", nombre="Calacatta Imperial",
            slug="calacatta-imperial", precio_mayor=Decimal("68.50"),
        )
        self.assertEqual(str(p), "MPG-CALA-120 — Calacatta Imperial")
        with self.assertRaises(Exception):
            Product.objects.create(
                categoria=self.cat, sku="MPG-CALA-120", nombre="Duplicado",
                slug="duplicado", precio_mayor=Decimal("10"),
            )

    def test_imagen_src_prefiere_archivo(self):
        p = Product.objects.create(
            categoria=self.cat, sku="MPG-X", nombre="X", slug="x",
            precio_mayor=Decimal("1"), imagen_url="https://ejemplo.com/x.jpg",
        )
        self.assertEqual(p.imagen_src, "https://ejemplo.com/x.jpg")

    def test_catalogo_completo_con_filtros(self):
        Product.objects.create(
            categoria=self.cat, sku="MPG-CALA-120", nombre="Calacatta Imperial",
            slug="calacatta-imperial", precio_mayor=Decimal("68.50"),
        )
        resp = self.client.get("/catalogo/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Catálogo completo")
        resp = self.client.get("/catalogo/", {"q": "CALA"})
        self.assertContains(resp, "MPG-CALA-120")
        resp = self.client.get("/catalogo/", {"categoria": "porcelanato"})
        self.assertContains(resp, "MPG-CALA-120")

    def test_seed_lineas_y_tipos(self):
        for slug in ("tejas", "accesorios"):
            self.assertTrue(Category.objects.filter(slug=slug).exists())
        for slug in ("teja-roma", "teja-espanola", "teja-pvc", "cumbreros",
                     "tornilleria", "perfiles", "selladores"):
            self.assertTrue(TipoProducto.objects.filter(slug=slug).exists())

    def test_filtro_y_busqueda_por_tipo_y_badge(self):
        tipo = TipoProducto.objects.get(slug="teja-roma")
        Product.objects.create(
            categoria=self.cat, tipo=tipo, sku="MPG-R", nombre="Roma 7.2",
            slug="roma-72", precio_mayor=Decimal("50"), badge="MÁS VENDIDO",
        )
        Product.objects.create(
            categoria=self.cat, sku="MPG-X2", nombre="Otro",
            slug="otro", precio_mayor=Decimal("10"),
        )
        resp = self.client.get("/catalogo/", {"tipo": "teja-roma"})
        self.assertContains(resp, "MPG-R")
        self.assertNotContains(resp, "MPG-X2")
        resp = self.client.get("/catalogo/", {"q": "roma"})
        self.assertContains(resp, "MPG-R")
        html = self.client.get("/catalogo/").content.decode()
        self.assertIn("Teja Roma", html)  # filtro automático
        self.assertIn("MÁS VENDIDO", html)  # badge visible
        det = self.client.get("/catalogo/producto/roma-72/").content.decode()
        self.assertIn("Teja Roma", det)

    def test_grid_htmx_devuelve_parcial(self):
        Product.objects.create(
            categoria=self.cat, sku="MPG-NERO-160", nombre="Titanium Nero",
            slug="titanium-nero", precio_mayor=Decimal("124.00"),
        )
        resp = self.client.get("/catalogo/", {"q": "NERO"}, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "MPG-NERO-160")
        self.assertNotContains(resp, "Catálogo completo")

    def test_detalle_usa_mismo_header_que_index(self):
        p = Product.objects.create(
            categoria=self.cat, sku="MPG-D", nombre="D", slug="d",
            precio_mayor=Decimal("5"),
        )
        home = self.client.get("/").content.decode()
        det = self.client.get(f"/catalogo/producto/{p.slug}/")
        self.assertEqual(det.status_code, 200)
        self.assertContains(det, p.nombre)
        # mismo header que el index (marca del sitio)
        self.assertIn("MEGA PRIME", home)
        self.assertContains(det, "MEGA PRIME")

    def test_upload_png_se_convierte_a_webp(self):
        tmp = tempfile.mkdtemp()
        try:
            with override_settings(MEDIA_ROOT=tmp):
                buf = BytesIO()
                Image.new("RGB", (2000, 1000), "red").save(buf, "PNG")
                p = Product(
                    categoria=self.cat, sku="MPG-W", nombre="W", slug="w",
                    precio_mayor=Decimal("1"),
                )
                p.imagen.save("foto.png", ContentFile(buf.getvalue()), save=True)
                p.refresh_from_db()
                self.assertTrue(p.imagen.name.endswith(".webp"))
                with Image.open(p.imagen.path) as img:
                    self.assertEqual(img.format, "WEBP")
                    self.assertLessEqual(max(img.size), 1600)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ExcelProductosTest(TestCase):
    """Plantilla y lector de Excel para alta masiva (Task D1)."""

    def setUp(self):
        self.cat = Category.objects.create(nombre="Tejas Excel", slug="tejas-x")
        self.tipo = TipoProducto.objects.create(nombre="Cumbreros Excel", slug="cumbreros-x")

    def _libro_con_filas(self, filas):
        from openpyxl import load_workbook

        from catalog.excel_productos import build_productos_xlsx

        workbook = load_workbook(BytesIO(build_productos_xlsx()))
        sheet = workbook.active
        for fila in filas:
            sheet.append(fila)
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output

    def test_encabezados_de_la_plantilla_coinciden_con_el_lector(self):
        from openpyxl import load_workbook

        from catalog.excel_productos import HEADERS, build_productos_xlsx

        workbook = load_workbook(BytesIO(build_productos_xlsx()), read_only=True)
        self.assertEqual([c.value for c in workbook.active[1]], HEADERS)

    def test_lee_fila_valida_y_normaliza(self):
        from catalog.excel_productos import read_productos_xlsx

        rows = read_productos_xlsx(self._libro_con_filas([[
            "TEJ-1", "Teja Excel Uno", "Tejas Excel", "Cumbreros Excel",
            12.5, "M²", 30, "NUEVO", "EC", "https://example.com/a.jpg", "Una teja",
        ]]))

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["fila"], 2)
        self.assertEqual(row["sku"], "TEJ-1")
        self.assertEqual(row["nombre"], "Teja Excel Uno")
        self.assertEqual(row["categoria"], self.cat)
        self.assertEqual(row["tipo"], self.tipo)
        self.assertEqual(str(row["precio_mayor"]), "12.50")
        self.assertEqual(row["unidad"], "m2")
        self.assertEqual(str(row["stock_cantidad"]), "30.00")
        self.assertEqual(row["badge"], "NUEVO")
        self.assertEqual(row["origen"], "EC")
        self.assertEqual(row["descripcion"], "Una teja")

    def test_ignora_filas_vacias_y_usa_defaults(self):
        from catalog.excel_productos import read_productos_xlsx

        rows = read_productos_xlsx(self._libro_con_filas([
            [None] * 11,
            ["TEJ-2", "Sólo lo mínimo", "tejas-x", None, 5, None, None, None, None, None, None],
            ["TEJ-3", "Sin categoría", None, None, 5, None, None, None, None, None, None],
        ]))

        self.assertEqual(len(rows), 2)
        row = rows[0]
        self.assertEqual(row["sku"], "TEJ-2")
        self.assertEqual(row["categoria"], self.cat)  # resuelto por slug
        self.assertIsNone(row["tipo"])
        self.assertEqual(row["unidad"], "m2")  # default
        self.assertEqual(str(row["stock_cantidad"]), "0.00")
        self.assertIsNone(rows[1]["categoria"])  # sin categoría: la decide el importador

    def test_errores_legibles_por_fila(self):
        from catalog.excel_productos import read_productos_xlsx

        casos = [
            (["", "Sin SKU", "Tejas Excel", None, 1, None, None, None, None, None, None], "SKU"),
            (["TEJ-3", "", "Tejas Excel", None, 1, None, None, None, None, None, None], "nombre"),
            (["TEJ-4", "Cat mala", "No Existe", None, 1, None, None, None, None, None, None], "No Existe"),
            (["TEJ-5", "Precio malo", "Tejas Excel", None, "abc", None, None, None, None, None, None], "precio"),
            (["TEJ-6", "Unidad mala", "Tejas Excel", None, 1, "cajas", None, None, None, None, None], "Unidad no válida"),
        ]
        for fila, esperado in casos:
            with self.subTest(esperado=esperado):
                with self.assertRaises(ValueError) as ctx:
                    read_productos_xlsx(self._libro_con_filas([fila]))
                self.assertIn(esperado, str(ctx.exception))
                self.assertIn("fila 2", str(ctx.exception))

    def test_sku_duplicado_en_el_archivo_es_error(self):
        from catalog.excel_productos import read_productos_xlsx

        with self.assertRaises(ValueError) as ctx:
            read_productos_xlsx(self._libro_con_filas([
                ["TEJ-7", "Uno", "Tejas Excel", None, 1, None, None, None, None, None, None],
                ["TEJ-7", "Dos", "Tejas Excel", None, 2, None, None, None, None, None, None],
            ]))
        self.assertIn("TEJ-7", str(ctx.exception))

    def test_archivo_ilegible_es_error_legible(self):
        from catalog.excel_productos import read_productos_xlsx

        with self.assertRaises(ValueError):
            read_productos_xlsx(BytesIO(b"no soy un excel"))


class CalidadProductosTest(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(nombre="CalidadX", slug="calidad-x")

    def _producto(self, sku, nombre, slug, **kwargs):
        datos = {"categoria": kwargs.pop("categoria", self.cat), "sku": sku,
                 "nombre": nombre, "slug": slug,
                 "precio_mayor": kwargs.pop("precio_mayor", Decimal("10.00"))}
        datos.update(kwargs)
        return Product.objects.create(**datos)

    def test_clave_nombre_ignora_tildes_mayusculas_y_espacios(self):
        from catalog.calidad import clave_nombre

        self.assertEqual(clave_nombre("Teja  Roma"), clave_nombre("teja roma"))
        self.assertEqual(clave_nombre("Grifería"), "griferia")
        self.assertEqual(clave_nombre("Panel WPC LK-8125"), "panel wpc lk 8125")
        self.assertEqual(clave_nombre(None), "")

    def test_faltantes_detecta_ficha_vacia_y_completa(self):
        from catalog.calidad import (SIN_CARACTERISTICAS, SIN_FOTOS, SIN_PRECIO,
                                     faltantes_producto)

        vacio = self._producto("CAL-VAC", "Calidad Vacía", "cal-vac",
                               precio_mayor=Decimal("0"))
        self.assertEqual(faltantes_producto(vacio),
                         [SIN_FOTOS, SIN_CARACTERISTICAS, SIN_PRECIO])

        completo = self._producto("CAL-OK", "Calidad OK", "cal-ok",
                                  imagen_url="https://example.com/a.jpg",
                                  precio_mayor=Decimal("5.00"),
                                  caracteristicas=["Resistente UV"])
        self.assertEqual(faltantes_producto(completo), [])

    def test_los_q_coinciden_con_la_regla_de_faltantes(self):
        from catalog.calidad import (SIN_CARACTERISTICAS, SIN_FOTOS, SIN_PRECIO,
                                     faltantes_producto, q_sin_caracteristicas,
                                     q_sin_fotos, q_sin_precio)

        self._producto("CAL-1", "Sin nada", "cal-1", precio_mayor=Decimal("0"))
        self._producto("CAL-2", "Completo", "cal-2",
                       imagen_url="https://example.com/b.jpg",
                       caracteristicas=["Peso ligero"])
        self._producto("CAL-3", "Con foto", "cal-3",
                       imagen_url="https://example.com/c.jpg")
        self._producto("CAL-4", "Con caract", "cal-4",
                       caracteristicas=["Resistente"], precio_mayor=Decimal("0"))

        def por_regla(etiqueta):
            return {p.pk for p in Product.objects.all()
                    if etiqueta in faltantes_producto(p)}

        def por_q(condicion):
            return set(Product.objects.filter(condicion).values_list("pk", flat=True))

        self.assertEqual(por_q(q_sin_fotos()), por_regla(SIN_FOTOS))
        self.assertEqual(por_q(q_sin_caracteristicas()), por_regla(SIN_CARACTERISTICAS))
        self.assertEqual(por_q(q_sin_precio()), por_regla(SIN_PRECIO))

    def test_agrupa_duplicados_por_categoria_y_nombre_normalizado(self):
        from catalog.calidad import contar_grupos_duplicados, grupos_duplicados

        otra = Category.objects.create(nombre="OtraCatX", slug="otra-cat-x")
        self._producto("DUP-1", "Teja Roma PVC", "dup-1")
        self._producto("DUP-2", "TEJA  roma pvc", "dup-2")
        self._producto("DUP-3", "Grifería Alta", "dup-3")
        self._producto("DUP-4", "griferia alta", "dup-4")
        # Mismo nombre pero en otra categoría: no es duplicado
        self._producto("DUP-5", "Teja Roma PVC", "dup-5", categoria=otra)

        grupos = grupos_duplicados()
        self.assertEqual(len(grupos), 2)
        self.assertEqual(contar_grupos_duplicados(), 2)
        for grupo in grupos:
            self.assertEqual(len(grupo), 2)
            self.assertEqual({p.categoria_id for p in grupo}, {self.cat.pk})
        skus = sorted(p.sku for grupo in grupos for p in grupo)
        self.assertEqual(skus, ["DUP-1", "DUP-2", "DUP-3", "DUP-4"])

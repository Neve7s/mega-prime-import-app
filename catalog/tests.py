from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from PIL import Image

from .models import Category, Product

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

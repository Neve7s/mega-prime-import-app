from decimal import Decimal

from django.test import TestCase

from .models import Category, Product


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

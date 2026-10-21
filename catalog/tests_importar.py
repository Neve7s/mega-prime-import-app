"""Test del importador del catálogo de megacubiertasimportaciones.com."""

import json
import tempfile
from pathlib import Path

from django.test import TestCase

from .models import Category, Product, ProductColor, ProductImage, TipoProducto

# Un recorte fiel del JSON del panel del sitio (2 productos + 1 accesorio).
DATOS = {
    "categoriasProducto": [
        {
            "id": "c1", "nombre": "Teja PVC tipo Roma colonial 2.5 mm.",
            "descripcion": "Perfiles de PVC",
            "items": [
                {
                    "id": "pi-1", "nombre": "Teja Roma PVC Terracota/Terracota 2.5 mm.",
                    "descripcion": "La teja de PVC es una de las soluciones mas eficientes.",
                    "caracteristicas": ["Livieza estructural: Reduce el peso."],
                    "ficha": [["Marca", " MG 1050."], ["Color", "Terracota"], ["Espesor", " 2.5mm."]],
                    "fotos": ["https://ejemplo.com/roma-terracota.png"],
                    "imagen": "https://ejemplo.com/roma-terracota.png",
                    "colores": [{"hex": "#C0392B", "nombre": "Terracota"}],
                },
                {
                    "id": "pi-2", "nombre": "Teja Roma PVC Negro/Negro.",
                    "descripcion": "La teja de PVC en negro.",
                    "caracteristicas": ["Livieza estructural: Reduce el peso."],
                    "ficha": [["Marca", " MG 1050."], ["Espesor", " 2.5mm."]],
                    "fotos": ["https://ejemplo.com/roma-negro.png"],
                    "imagen": "https://ejemplo.com/roma-negro.png",
                    "colores": [{"hex": "#1A1A1A", "nombre": "Negro"}],
                },
            ],
        },
        {
            "id": "c2", "nombre": "Pisos SPC Alto trafico 5 mm.",
            "descripcion": "Pisos de composite",
            "items": [
                {
                    "id": "pi-3", "nombre": "Piso SPC Abedul Miel",
                    "descripcion": "El diseno Abedul Miel destaca por su tonalidad calida.",
                    "caracteristicas": ["100% Resistente al agua"],
                    "ficha": [["Espesor total", " 5 mm."]],
                    "fotos": ["https://ejemplo.com/spc.png"],
                    "imagen": "https://ejemplo.com/spc.png",
                    "colores": [],
                },
            ],
        },
    ],
    "accesorios": [
        {
            "id": "a1", "nombre": "Tornillos y capuchones",
            "descripcion": "Fijaciones",
            "items": [
                {
                    "id": "acc-1", "nombre": "Tornillo Autoperforante 5.5*75 mm.",
                    "descripcion": "Tornillo especial.",
                    "caracteristicas": [],
                    "ficha": [["Material", " Acero inoxidable"]],
                    "fotos": ["https://ejemplo.com/tornillo.png"],
                    "imagen": "https://ejemplo.com/tornillo.png",
                    "colores": [],
                },
            ],
        },
    ],
    "productoCategorias": [],
}


class ImportarMegacubiertasTest(TestCase):
    def setUp(self):
        self.archivo = Path(tempfile.mkdtemp()) / "mc_data.json"
        self.archivo.write_text(json.dumps(DATOS), encoding="utf-8")

    def _importa(self):
        from django.core.management import call_command

        call_command("importar_megacubiertas", str(self.archivo), verbosity=0)

    def test_importa_productos_agrupando_por_modelo(self):
        self._importa()
        # Las dos tejas romanas (distinto color) quedan en UNA ficha.
        roma = Product.objects.get(nombre__icontains="Teja Roma PVC")
        self.assertEqual(roma.colores_producto.count(), 2)
        self.assertEqual(roma.imagenes.count(), 2)
        self.assertEqual(roma.categoria.slug, "tejas-y-cubiertas")
        self.assertEqual(roma.tipo.slug, "teja-pvc")
        self.assertEqual(roma.ficha_tecnica.get("Espesor"), "2.5mm.")
        self.assertNotIn("Color", roma.ficha_tecnica)
        self.assertTrue(roma.caracteristicas)

    def test_importa_el_tono_del_piso_detectado_en_el_nombre(self):
        self._importa()
        piso = Product.objects.get(nombre__icontains="Piso SPC")
        self.assertEqual(piso.categoria.slug, "pisos")
        self.assertEqual([pc.color.nombre for pc in piso.colores_producto.all()],
                         ["Abedul Miel"])

    def test_importa_los_accesorios_en_su_categoria(self):
        self._importa()
        tornillo = Product.objects.get(nombre__icontains="Tornillo")
        self.assertEqual(tornillo.categoria.slug, "accesorios-y-materiales")
        self.assertEqual(tornillo.tipo.slug, "tornilleria")

    def test_es_idempotente(self):
        self._importa()
        self._importa()
        self.assertEqual(Product.objects.count(), 3)
        roma = Product.objects.get(nombre__icontains="Teja Roma PVC")
        self.assertEqual(roma.colores_producto.count(), 2)
        self.assertEqual(roma.imagenes.count(), 2)

    def test_los_sku_son_correlativos_cod(self):
        self._importa()
        skus = sorted(Product.objects.values_list("sku", flat=True))
        self.assertEqual(skus, ["COD-0001", "COD-0002", "COD-0003"])

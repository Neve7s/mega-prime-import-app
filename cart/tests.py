from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from cart.models import Order, SaleCode
from cart.services import crear_pedido, validar_codigo
from catalog.models import Category, Product


class VentaTest(TestCase):
    def setUp(self):
        cat = Category.objects.create(nombre="Porcelanatos", slug="porcelanato")
        self.p = Product.objects.create(
            categoria=cat, sku="MPG-T", nombre="Test", slug="t",
            precio_mayor=Decimal("100"),
        )
        self.sale = SaleCode.objects.create(cliente_nombre="Juan Pérez")

    def test_codigo_vigente_y_uso_unico(self):
        sale, err = validar_codigo(self.sale.codigo.lower())
        self.assertEqual(err, "")
        self.assertTrue(sale.vigente)
        sale.registrar_uso()
        sale2, err2 = validar_codigo(self.sale.codigo)
        self.assertIsNone(sale2)
        self.assertIn("vencido o ya utilizado", err2)

    def test_codigo_inexistente(self):
        sale, err = validar_codigo("MPI-XXXXXX")
        self.assertIsNone(sale)
        self.assertIn("no válido", err)

    def test_crear_pedido_ok_con_snapshot(self):
        datos = {"nombre_completo": "Juan Pérez López", "documento_identidad": "0912345678",
                 "email": "juan@mail.com", "telefono": "+593963796222", "ciudad": "Ambato"}
        pedido, err = crear_pedido(datos, [{"sku": "MPG-T", "cantidad": 2}], self.sale)
        self.assertEqual(err, "")
        self.assertEqual(pedido.total, Decimal("200"))
        self.assertEqual(pedido.items.count(), 1)
        self.assertEqual(Order.objects.count(), 1)
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.estado, SaleCode.USADO)

    def test_checkout_rechaza_datos_malos(self):
        datos = {"nombre_completo": "Ana", "documento_identidad": "x",
                 "email": "mal", "telefono": "1"}
        pedido, err = crear_pedido(datos, [{"sku": "MPG-T", "cantidad": 1}], self.sale)
        self.assertIsNone(pedido)
        self.assertTrue(err)
        self.assertEqual(Order.objects.count(), 0)

    def test_codigo_vencido(self):
        self.sale.expira_en = timezone.now() - timezone.timedelta(hours=1)
        self.sale.save()
        sale, err = validar_codigo(self.sale.codigo)
        self.assertIsNone(sale)
        self.assertIn("vencido", err)

    def test_checkout_endpoint_crea_pedido(self):
        resp = self.client.post(
            "/carrito/checkout/",
            data={
                "codigo": self.sale.codigo,
                "datos": {"nombre_completo": "María Torres Vega", "documento_identidad": "1701234567",
                          "email": "maria@mail.com", "telefono": "0987654321"},
                "items": [{"sku": "MPG-T", "cantidad": 1}],
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["ok"])
        self.assertEqual(Order.objects.count(), 1)

    def test_checkout_sin_codigo_falla(self):
        resp = self.client.post(
            "/carrito/checkout/",
            data={"codigo": "MPI-XXXXXX", "datos": {}, "items": []},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])

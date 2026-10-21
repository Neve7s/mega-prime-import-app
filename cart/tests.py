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


class PedidoConColorTest(TestCase):
    """El color elegido en la ficha llega al pedido."""

    def setUp(self):
        from catalog.models import Color, ProductColor

        cat = Category.objects.create(nombre="Tejas", slug="tejas-color")
        self.p = Product.objects.create(
            categoria=cat, sku="COD-0001", nombre="Teja Español PVC 2.5 mm",
            slug="teja-espanol", precio_mayor=Decimal("18.5"),
        )
        rojo = Color.objects.get(slug="rojo")
        negro = Color.objects.get(slug="negro")
        ProductColor.objects.create(producto=self.p, color=rojo, orden=0)
        ProductColor.objects.create(producto=self.p, color=negro, orden=1)
        self.sale = SaleCode.objects.create(cliente_nombre="Cliente")

    DATOS = {"nombre_completo": "Juan Pérez López", "documento_identidad": "0912345678",
              "email": "juan@mail.com", "telefono": "+593963796222"}

    def test_el_color_se_guarda_en_el_item(self):
        pedido, err = crear_pedido(
            self.DATOS, [{"sku": "COD-0001", "cantidad": 3, "color": "Negro"}], self.sale)
        self.assertEqual(err, "")
        item = pedido.items.get()
        self.assertEqual(item.color_snapshot, "Negro")
        self.assertEqual(item.cantidad, 3)

    def test_color_que_no_es_del_producto_se_rechaza(self):
        pedido, err = crear_pedido(
            self.DATOS, [{"sku": "COD-0001", "cantidad": 1, "color": "Fucsia"}], self.sale)
        self.assertIsNone(pedido)
        self.assertIn("Color no disponible", err)
        self.assertEqual(Order.objects.count(), 0)

    def test_producto_sin_colores_acepta_cualquier_color(self):
        cat = Category.objects.create(nombre="Otros", slug="otros")
        p = Product.objects.create(categoria=cat, sku="COD-0002", nombre="Cumbrero",
                                   slug="cumbrero", precio_mayor=Decimal("9"))
        pedido, err = crear_pedido(
            self.DATOS, [{"sku": "COD-0002", "cantidad": 1, "color": "Terracota"}], self.sale)
        self.assertEqual(err, "")
        self.assertEqual(pedido.items.get().color_snapshot, "Terracota")
        self.assertTrue(p)

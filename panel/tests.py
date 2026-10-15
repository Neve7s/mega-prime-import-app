from django.test import TestCase


class PanelTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.staff = User.objects.create_user("webadmin", password="x", is_staff=True)
        self.plain = User.objects.create_user("nadie", password="x")

    def test_anonimo_va_a_login(self):
        resp = self.client.get("/webadmin/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/webadmin/login/", resp["Location"])

    def test_sin_staff_no_entra(self):
        self.client.force_login(self.plain)
        resp = self.client.get("/webadmin/")
        self.assertEqual(resp.status_code, 302)

    def test_staff_ve_tablero_y_productos(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/webadmin/").status_code, 200)
        self.assertEqual(self.client.get("/webadmin/productos/").status_code, 200)
        self.assertEqual(self.client.get("/webadmin/pedidos/").status_code, 200)
        self.assertEqual(self.client.get("/webadmin/codigos/").status_code, 200)
        self.assertEqual(self.client.get("/webadmin/ajustes/").status_code, 200)
        self.assertEqual(self.client.get("/webadmin/calculadora/").status_code, 200)

    def test_staff_crea_producto_desde_panel(self):
        from catalog.models import Category, Product

        cat = Category.objects.create(nombre="Porcelanatos", slug="porcelanato")
        self.client.force_login(self.staff)
        resp = self.client.post("/webadmin/productos/nuevo/", data={
            "categoria": cat.pk, "sku": "MPG-PANEL", "nombre": "Panel test",
            "slug": "panel-test", "descripcion": "", "precio_mayor": "10.00",
            "unidad": "m2", "stock_cantidad": "5", "origen": "", "imagen_url": "",
            "en_stock": "on", "activo": "on",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Product.objects.filter(sku="MPG-PANEL").exists())

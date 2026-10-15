from django.test import TestCase


class PanelTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.staff = User.objects.create_user("webadmin", password="x", is_staff=True)
        self.plain = User.objects.create_user("nadie", password="x")

    def test_anonimo_va_a_login(self):
        resp = self.client.get("/panel/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/panel/login/", resp["Location"])

    def test_sin_staff_no_entra(self):
        self.client.force_login(self.plain)
        resp = self.client.get("/panel/")
        self.assertEqual(resp.status_code, 302)

    def test_staff_ve_tablero_y_productos(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/panel/").status_code, 200)
        self.assertEqual(self.client.get("/panel/productos/").status_code, 200)
        self.assertEqual(self.client.get("/panel/pedidos/").status_code, 200)
        self.assertEqual(self.client.get("/panel/codigos/").status_code, 200)
        self.assertEqual(self.client.get("/panel/ajustes/").status_code, 200)
        self.assertEqual(self.client.get("/panel/calculadora/").status_code, 200)

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

    def test_ajustes_subtabs_y_guardado(self):
        self.client.force_login(self.staff)
        html = self.client.get("/webadmin/ajustes/").content.decode()
        for tab in ("marca", "portada", "contacto", "redes", "seo", "pie", "tema"):
            self.assertIn('data-tab="%s"' % tab, html)
        self.assertIn("Paletas predefinidas", html)
        self.assertIn('data-drop', html)  # dropzones de imagen
        resp = self.client.post("/webadmin/ajustes/", data={
            "site_name": "MP", "meta_title": "T", "tagline": "S",
            "company_legal": "E", "hero_city": "C", "hero_title": "HT",
            "hero_cta_primary": "A", "hero_cta_secondary": "B",
            "whatsapp_number": "593900000000", "phone_display": "+593",
            "email": "v@v.com", "address": "D", "cities": "C",
            "schedule": "H", "footer_text": "F",
            "color_primario": "#D4AF37", "color_secundario": "#0A0A0B",
            "color_fondo": "#FAFAF8", "color_tarjetas": "#FFFFFF",
            "color_texto": "#131313", "color_acento": "#15803D",
            "fuente_cuerpo": "Inter", "fuente_titulos": "Montserrat",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Guardado", resp.content.decode())
        from core.models import SiteSettings
        site = SiteSettings.get_solo()
        self.assertEqual(site.fuente_titulos, "Montserrat")
        self.assertEqual(site.color_primario, "#D4AF37")

    def test_ajustes_sube_logo(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (100, 60), (212, 175, 55)).save(buf, "PNG")
        logo = SimpleUploadedFile("logo-test.png", buf.getvalue(), "image/png")
        self.client.force_login(self.staff)
        resp = self.client.post("/webadmin/ajustes/", data={
            "site_name": "MP", "meta_title": "T", "tagline": "S",
            "company_legal": "E", "hero_city": "C", "hero_title": "HT",
            "hero_cta_primary": "A", "hero_cta_secondary": "B",
            "whatsapp_number": "593900000000", "phone_display": "+593",
            "email": "v@v.com", "address": "D", "cities": "C",
            "schedule": "H", "footer_text": "F",
            "color_primario": "#D4AF37", "color_secundario": "#0A0A0B",
            "color_fondo": "#FAFAF8", "color_tarjetas": "#FFFFFF",
            "color_texto": "#131313", "color_acento": "#15803D",
            "fuente_cuerpo": "Inter", "fuente_titulos": "Inter",
            "logo": logo,
        })
        self.assertEqual(resp.status_code, 200)
        from core.models import SiteSettings
        site = SiteSettings.get_solo()
        self.assertTrue(bool(site.logo))
        self.assertIn("logo-test", site.logo.name)

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

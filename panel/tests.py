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
        import shutil
        import tempfile

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from PIL import Image

        tmp = tempfile.mkdtemp()
        try:
            with override_settings(MEDIA_ROOT=tmp):
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
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_categorias_crud_y_filtro_automatico(self):
        from catalog.models import Category

        self.client.force_login(self.staff)
        # Crear
        r = self.client.post("/webadmin/categorias/nueva/", data={
            "nombre": "Grifería", "slug": "griferia",
            "descripcion": "", "orden": "3",
        })
        self.assertEqual(r.status_code, 302)
        cat = Category.objects.get(slug="griferia")
        # Aparece sola en el filtro del catálogo público
        html = self.client.get("/catalogo/").content.decode()
        self.assertIn('value="griferia"', html)
        self.assertIn("Grifería", html)
        # Y en el selector del formulario de producto
        html_p = self.client.get("/webadmin/productos/nuevo/").content.decode()
        self.assertIn("Grifería", html_p)
        # Editar
        r = self.client.post(f"/webadmin/categorias/{cat.pk}/", data={
            "nombre": "Griferías Finas", "slug": "griferia",
            "descripcion": "", "orden": "1",
        })
        self.assertEqual(r.status_code, 302)
        cat.refresh_from_db()
        self.assertEqual(cat.nombre, "Griferías Finas")
        # Eliminar vacía
        r = self.client.post(f"/webadmin/categorias/{cat.pk}/eliminar/")
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Category.objects.filter(slug="griferia").exists())

    def test_producto_guarda_colores_y_caracteristicas(self):
        import json

        from catalog.models import Category, Product

        self.client.force_login(self.staff)
        cat = Category.objects.create(nombre="Tejas", slug="tejas-t")
        base = {"categoria": cat.pk, "sku": "MPG-COL", "nombre": "Con color",
                "slug": "con-color", "descripcion": "", "precio_mayor": "10.00",
                "unidad": "m2", "stock_cantidad": "1", "imagen_url": "",
                "en_stock": "on", "activo": "on",
                "colores_json": json.dumps([
                    {"nombre": "Rojo Teja", "hex": "#8B2500"},
                    {"nombre": "Malo", "hex": "zzz"},
                    {"nombre": "", "hex": "#FFFFFF"}]),
                "caracteristicas_json": json.dumps(
                    ["Resistente UV", "  ", "Peso ligero"])}
        r = self.client.post("/webadmin/productos/nuevo/", data=base)
        self.assertEqual(r.status_code, 302)
        p = Product.objects.get(sku="MPG-COL")
        self.assertEqual(p.colores, [{"nombre": "Rojo Teja", "hex": "#8B2500"}])
        self.assertEqual(p.caracteristicas, ["Resistente UV", "Peso ligero"])
        det = self.client.get("/catalogo/producto/con-color/").content.decode()
        self.assertIn("Rojo Teja", det)
        self.assertIn("Resistente UV", det)
        self.assertIn("#8B2500", det)

    def test_tipos_crud_y_proteccion(self):
        from catalog.models import TipoProducto

        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/webadmin/tipos/").status_code, 200)
        r = self.client.post("/webadmin/tipos/nuevo/", data={
            "nombre": "Teja Colonial", "slug": "teja-colonial",
            "descripcion": "", "orden": "9",
        })
        self.assertEqual(r.status_code, 302)
        tipo = TipoProducto.objects.get(slug="teja-colonial")
        html = self.client.get("/catalogo/").content.decode()
        self.assertIn("Teja Colonial", html)
        # Con producto no se elimina
        from catalog.models import Category, Product
        cat = Category.objects.create(nombre="T", slug="t")
        Product.objects.create(
            categoria=cat, tipo=tipo, sku="P-T", nombre="PT", slug="pt",
            precio_mayor="5", stock_cantidad="1")
        r = self.client.post(f"/webadmin/tipos/{tipo.pk}/eliminar/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("No se puede eliminar", r.content.decode())
        self.assertTrue(TipoProducto.objects.filter(slug="teja-colonial").exists())

    def test_producto_con_tipo_y_badge_desde_panel(self):
        from catalog.models import Category, Product, TipoProducto

        self.client.force_login(self.staff)
        cat = Category.objects.create(nombre="Tejas", slug="tejas-p")
        tipo = TipoProducto.objects.create(nombre="Roma", slug="roma-p")
        r = self.client.post("/webadmin/productos/nuevo/", data={
            "categoria": cat.pk, "tipo": tipo.pk, "sku": "MPG-TP",
            "nombre": "Teja panel", "slug": "teja-panel", "descripcion": "",
            "badge": "MÁS VENDIDO", "precio_mayor": "20.00", "unidad": "m2",
            "stock_cantidad": "3", "origen": "", "imagen_url": "",
            "en_stock": "on", "activo": "on",
        })
        self.assertEqual(r.status_code, 302)
        p = Product.objects.get(sku="MPG-TP")
        self.assertEqual(p.tipo, tipo)
        self.assertEqual(p.badge, "MÁS VENDIDO")

    def test_categoria_con_productos_no_se_elimina(self):
        from catalog.models import Category, Product

        self.client.force_login(self.staff)
        cat = Category.objects.create(nombre="Pisos", slug="pisos")
        Product.objects.create(
            categoria=cat, sku="P-1", nombre="Piso test", slug="piso-test",
            precio_mayor="10.00", stock_cantidad="5")
        r = self.client.post(f"/webadmin/categorias/{cat.pk}/eliminar/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("No se puede eliminar", r.content.decode())
        self.assertTrue(Category.objects.filter(slug="pisos").exists())

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

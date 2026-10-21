from decimal import Decimal

from django.test import TestCase

from catalog.models import Category, Product

from .models import HeroMedia, HeroStat, SiteSettings


class SiteSettingsTest(TestCase):
    def test_singleton_and_home_renders_branding(self):
        s = SiteSettings.get_solo()
        self.assertEqual(s.pk, 1)
        self.assertIn("593", s.whatsapp_number)
        HeroStat.objects.create(value="+15 Años", label="Importación Directa", orden=0)
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, s.site_name)
        self.assertContains(resp, s.whatsapp_number)


class HeroMediaTest(TestCase):
    """Fondos del hero: hasta 3 imágenes, GIF o videos, desde el panel."""

    def setUp(self):
        from django.contrib.auth.models import User

        self.staff = User.objects.create_user("hero-staff", password="x", is_staff=True)
        self.client.force_login(self.staff)

    def test_agregar_fondo_por_url(self):
        resp = self.client.post("/webadmin/ajustes/hero-media/", {
            "hero_tipo": "imagen", "hero_url": "https://ejemplo.com/fondo.gif",
            "hero_alt": "Obra en Ambato",
        })
        self.assertEqual(resp.status_code, 302)
        fondo = HeroMedia.objects.get()
        self.assertEqual(fondo.url, "https://ejemplo.com/fondo.gif")
        self.assertEqual(fondo.tipo, "imagen")
        self.assertTrue(fondo.activo)
        # Y sale en la portada
        html = self.client.get("/").content.decode()
        self.assertIn("https://ejemplo.com/fondo.gif", html)

    def test_sin_archivo_ni_enlace_no_se_crea(self):
        self.client.post("/webadmin/ajustes/hero-media/", {"hero_tipo": "imagen"})
        self.assertEqual(HeroMedia.objects.count(), 0)

    def test_maximo_tres_fondos(self):
        for i in range(3):
            HeroMedia.objects.create(url=f"https://ejemplo.com/{i}.jpg")
        self.client.post("/webadmin/ajustes/hero-media/", {
            "hero_tipo": "imagen", "hero_url": "https://ejemplo.com/cuarto.jpg"})
        self.assertEqual(HeroMedia.objects.count(), 3)

    def test_cambiar_un_fondo_existente(self):
        fondo = HeroMedia.objects.create(url="https://ejemplo.com/viejo.jpg", alt="Viejo")
        self.client.post("/webadmin/ajustes/hero-media/", {
            "hero_pk": fondo.pk, "hero_tipo": "imagen",
            "hero_url": "https://ejemplo.com/nuevo.jpg", "hero_alt": "Nuevo"})
        fondo.refresh_from_db()
        self.assertEqual(fondo.url, "https://ejemplo.com/nuevo.jpg")
        self.assertEqual(fondo.alt, "Nuevo")
        self.assertEqual(HeroMedia.objects.count(), 1)

    def test_borrar_un_fondo(self):
        fondo = HeroMedia.objects.create(url="https://ejemplo.com/x.jpg")
        self.client.post("/webadmin/ajustes/hero-media/", {"borrar_pk": fondo.pk})
        self.assertEqual(HeroMedia.objects.count(), 0)

    def test_el_video_se_muestra_como_video(self):
        HeroMedia.objects.create(tipo="video", url="https://ejemplo.com/fondo.mp4")
        html = self.client.get("/").content.decode()
        self.assertIn("<video", html)
        self.assertIn("https://ejemplo.com/fondo.mp4", html)


class PortadaTest(TestCase):
    """El hero muestra productos del catálogo y la colección es una muestra."""

    def setUp(self):
        self.cat = Category.objects.create(nombre="Tejas", slug="tejas-home")
        for i in range(12):
            Product.objects.create(
                categoria=self.cat, sku=f"HOME-{i:02d}", nombre=f"Producto {i}",
                slug=f"producto-{i}", precio_mayor=Decimal("10"),
                imagen_url=f"https://ejemplo.com/{i}.jpg",
            )

    def test_la_coleccion_del_portal_es_una_muestra(self):
        html = self.client.get("/").content.decode()
        self.assertEqual(html.count('class="product-item'), 8)
        self.assertIn("Ver los 12 productos del catálogo", html)

    def test_el_hero_muestra_un_producto_del_catalogo(self):
        html = self.client.get("/").content.decode()
        self.assertIn("data-hero-producto", html)
        self.assertIn("/catalogo/producto/producto-", html)

    def test_el_hero_cae_a_la_imagen_por_defecto_sin_productos(self):
        Product.objects.all().delete()
        html = self.client.get("/").content.decode()
        self.assertEqual(html.count("data-hero-producto"), 0)
        # Sin productos, el showcase muestra la imagen por defecto configurada.
        self.assertIn("data-alt=", html)

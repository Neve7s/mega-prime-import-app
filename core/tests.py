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


class SeoTest(TestCase):
    """SEO por template: canonical, Open Graph, JSON-LD, sitemap y robots."""

    def setUp(self):
        self.cat = Category.objects.create(nombre="Tejas", slug="tejas-seo")
        self.producto = Product.objects.create(
            categoria=self.cat, sku="SEO-1", nombre="Teja SEO", slug="teja-seo",
            precio_mayor=Decimal("18.50"), imagen_url="https://ejemplo.com/teja.jpg",
            descripcion="Teja de prueba para el SEO.", activo=True)

    def test_el_portal_declara_canonical_y_open_graph(self):
        html = self.client.get("/").content.decode()
        self.assertIn('<link rel="canonical" href="https://megaprimeimport.com/"', html)
        self.assertIn('property="og:title"', html)
        self.assertIn('property="og:description"', html)
        self.assertIn('name="twitter:card"', html)
        self.assertIn("jsonld-negocio", html)
        # El JSON-LD del negocio es LocalBusiness
        self.assertIn('"@type": "LocalBusiness"', html)

    def test_el_producto_declara_product_con_sku_y_precio(self):
        html = self.client.get("/catalogo/producto/teja-seo/").content.decode()
        self.assertIn('property="og:type" content="product"', html)
        self.assertIn('"@type": "Product"', html)
        self.assertIn('"sku": "SEO-1"', html)
        self.assertIn('"price": "18.50"', html)
        self.assertIn('"@type": "BreadcrumbList"', html)

    def test_el_catalogo_declara_la_coleccion(self):
        html = self.client.get("/catalogo/").content.decode()
        self.assertIn('"@type": "CollectionPage"', html)
        self.assertIn('"@type": "ItemList"', html)

    def test_el_carrito_no_se_indexa(self):
        html = self.client.get("/carrito/").content.decode()
        self.assertIn('name="robots" content="noindex, nofollow"', html)

    def test_el_panel_no_se_indexa(self):
        from django.contrib.auth.models import User

        User.objects.create_user("seo-staff", password="x", is_staff=True)
        self.client.login(username="seo-staff", password="x")
        html = self.client.get("/webadmin/").content.decode()
        self.assertIn('name="robots" content="noindex, nofollow"', html)

    def test_sitemap_y_robots(self):
        xml = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("<urlset", xml)
        self.assertIn("https://megaprimeimport.com/", xml)
        self.assertIn("https://megaprimeimport.com/catalogo/producto/teja-seo/", xml)
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /webadmin/", robots)
        self.assertIn("Sitemap: https://megaprimeimport.com/sitemap.xml", robots)


class DireccionFisicaTest(TestCase):
    """La dirección del panel sale en el pie con su enlace a Maps."""

    def test_se_arma_el_enlace_a_maps_con_la_direccion(self):
        from core.models import SiteSettings

        site = SiteSettings.get_solo()
        site.direccion_fisica = "Av. Principal 123, Ambato"
        site.save()
        self.assertIn("maps/search", site.maps_link)
        self.assertIn("Ambato", site.maps_link)

    def test_el_enlace_configurado_gana(self):
        from core.models import SiteSettings

        site = SiteSettings.get_solo()
        site.direccion_fisica = "Av. Principal 123"
        site.enlace_maps = "https://maps.app.goo.gl/ejemplo"
        site.save()
        self.assertEqual(site.maps_link, "https://maps.app.goo.gl/ejemplo")

    def test_el_pie_muestra_la_direccion_y_el_boton_de_maps(self):
        from core.models import SiteSettings

        site = SiteSettings.get_solo()
        site.direccion_fisica = "Av. Principal 123, Ambato"
        site.save()
        html = self.client.get("/").content.decode()
        self.assertIn("Av. Principal 123, Ambato", html)
        self.assertIn("Ver en Google Maps", html)
        self.assertIn("maps/search", html)
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

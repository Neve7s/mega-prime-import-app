from decimal import Decimal
from unittest.mock import patch

from django.db import OperationalError
from django.test import RequestFactory, TestCase

from catalog.models import Category, Product

from .models import HeroMedia, HeroStat, SiteSettings


class SiteSettingsTest(TestCase):
    def test_singleton_and_home_renders_branding(self):
        s = SiteSettings.get_solo()
        self.assertEqual(s.pk, 1)
        self.assertIn("593", s.whatsapp_number)
        HeroStat.objects.create(value="+15 Años", label="Importación Directa", orden=0)
        s.x_url = "https://x.com/megaprime"
        s.youtube_url = "https://youtube.com/@megaprime"
        s.save()
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, s.site_name)
        self.assertContains(resp, s.whatsapp_number)
        self.assertContains(resp, "Síguenos en nuestras redes")
        self.assertContains(resp, "https://x.com/megaprime")
        self.assertContains(resp, "https://youtube.com/@megaprime")
        self.assertContains(resp, "Misión")
        self.assertContains(resp, "Visión")
        self.assertContains(resp, "Escríbenos por WhatsApp")


class LegalPagesTest(TestCase):
    def test_paginas_legales_publicas_y_enlazadas(self):
        urls = (
            ("/terminos-y-condiciones/", "Términos y condiciones"),
            ("/privacidad/", "Política de privacidad"),
            ("/cookies/", "Política de cookies"),
            ("/libro-de-reclamaciones/", "Libro de reclamaciones"),
        )
        for url, title in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, title)

        claims = self.client.get("/libro-de-reclamaciones/")
        for field in (
            "tipo_identificacion", "identificacion", "correo", "telefono",
            "direccion", "provincia", "producto_servicio", "numero_pedido",
            "fecha_incidente", "monto_reclamado", "detalle", "solicitud",
            "acepta_privacidad",
        ):
            self.assertContains(claims, f'name="{field}"')
        self.assertContains(claims, 'href="/privacidad/"')

        home = self.client.get("/").content.decode()
        self.assertIn('href="/terminos-y-condiciones/"', home)
        self.assertIn('href="/privacidad/"', home)
        self.assertIn('href="/cookies/"', home)
        self.assertIn('href="/libro-de-reclamaciones/"', home)

    def test_libro_registra_reclamacion_y_devuelve_codigo(self):
        from core.models import Complaint

        response = self.client.post("/libro-de-reclamaciones/", {
            "tipo": "reclamo",
            "nombres": "Ana",
            "apellidos": "Pérez",
            "tipo_identificacion": "cedula",
            "identificacion": "1800000000",
            "empresa": "Constructora Ejemplo",
            "correo": "ana@example.com",
            "telefono": "0990000000",
            "direccion": "Av. Central 123",
            "provincia": "Tungurahua",
            "producto_servicio": "Porcelanato",
            "numero_pedido": "PED-1024",
            "fecha_incidente": "2026-10-20",
            "monto_reclamado": "120.50",
            "detalle": "El producto recibido no coincide con la orden.",
            "solicitud": "Solicito que revisen el pedido.",
            "canal_respuesta": "correo",
            "acepta_privacidad": "on",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/legal/complaint_received.html")
        self.assertEqual(Complaint.objects.count(), 1)
        reclamo = Complaint.objects.get()
        self.assertEqual(reclamo.identificacion, "1800000000")
        self.assertEqual(reclamo.numero_pedido, "PED-1024")
        self.assertContains(response, reclamo.codigo)

    def test_libro_exige_privacidad_y_no_guarda_sin_aceptacion(self):
        from core.models import Complaint

        data = {
            "tipo": "queja",
            "nombres": "Ana",
            "apellidos": "Pérez",
            "tipo_identificacion": "cedula",
            "identificacion": "1800000000",
            "correo": "ana@example.com",
            "telefono": "0990000000",
            "direccion": "Av. Central 123",
            "provincia": "Tungurahua",
            "producto_servicio": "Atención",
            "detalle": "Solicito revisar la atención.",
            "solicitud": "Contactarme.",
            "canal_respuesta": "correo",
        }
        response = self.client.post("/libro-de-reclamaciones/", data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Complaint.objects.count(), 0)
        self.assertContains(response, "Debes aceptar el aviso de privacidad")


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


class SiteLocationMapsTest(TestCase):
    def test_renderiza_un_mapa_por_cada_ubicacion(self):
        from core.models import SiteLocation, SiteSettings

        site = SiteSettings.get_solo()
        SiteLocation.objects.create(
            sitio=site, nombre="Sede Ambato", direccion="Av. Cevallos, Ambato"
        )
        SiteLocation.objects.create(
            sitio=site, nombre="Showroom Quito", direccion="Av. Amazonas, Quito",
            enlace_maps="https://maps.app.goo.gl/quito",
        )

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'title="Mapa de Sede Ambato"')
        self.assertContains(response, 'title="Mapa de Showroom Quito"')
        self.assertContains(response, "maps?q=Av.%20Cevallos%2C%20Ambato&amp;output=embed")
        self.assertContains(response, "https://maps.app.goo.gl/quito")
        self.assertEqual(response.content.decode().count("<iframe"), 2)

    def test_fallo_al_leer_sedes_no_invalida_los_ajustes_del_sitio(self):
        from core.context_processors import site_settings
        from core.models import SiteLocation

        with patch.object(
            SiteLocation.objects, "all", side_effect=OperationalError("tabla no disponible")
        ), self.assertLogs("core.context_processors", level="ERROR"):
            context = site_settings(RequestFactory().get("/"))

        self.assertIsNotNone(context["site_settings"])
        self.assertEqual(context["site_locations"], [])


class HeroRotationTest(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(nombre="Tejas", slug="tejas-rotacion")

    def test_actualiza_nombre_y_muestra_solo_la_primera_foto(self):
        from catalog.models import ProductImage

        producto = Product.objects.create(
            categoria=self.cat, sku="HERO-FOTOS", nombre="Producto galería",
            slug="producto-galeria", precio_mayor=Decimal("10"),
        )
        ProductImage.objects.create(
            producto=producto, imagen_url="https://ejemplo.com/primera.jpg", orden=0
        )
        ProductImage.objects.create(
            producto=producto, imagen_url="https://ejemplo.com/segunda.jpg", orden=1
        )

        with patch("core.views.random.sample", side_effect=lambda items, count: items[:count]):
            response = self.client.get("/")
        html = response.content.decode()
        self.assertEqual(response.context["hero_productos"][0].pk, producto.pk)
        self.assertEqual(
            response.context["hero_productos"][0].hero_image_src,
            "https://ejemplo.com/primera.jpg",
        )
        self.assertIn('src="https://ejemplo.com/primera.jpg"', html)
        self.assertNotIn("https://ejemplo.com/segunda.jpg", html)
        self.assertIn('data-producto-nombre="Producto galería"', html)
        self.assertIn("nombre.textContent = productoActivo.dataset.productoNombre", html)
        self.assertIn("categoria.textContent = productoActivo.dataset.productoCategoria", html)


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
        self.assertIn("data-producto-nombre=", html)
        self.assertIn("nombre.textContent = productoActivo.dataset.productoNombre", html)

    def test_el_hero_cae_a_la_imagen_por_defecto_sin_productos(self):
        Product.objects.all().delete()
        html = self.client.get("/").content.decode()
        self.assertEqual(html.count("data-hero-producto"), 0)
        # Sin productos, el showcase muestra la imagen por defecto configurada.
        self.assertIn("data-alt=", html)


class InteractiveExperienceTest(TestCase):
    """Experiencia 3D (Three.js) + GSAP ScrollTrigger + Didáctica Ecuador."""

    def test_base_landing_carga_gsap_three_y_mpi_experience_sin_fuentes_duplicadas(self):
        html = self.client.get("/").content.decode()
        # No debe cargar dos veces Material Symbols Outlined
        self.assertEqual(html.count("family=Material+Symbols+Outlined"), 1)
        # Carga diferida de GSAP, ScrollTrigger, Three.js y el motor propio
        self.assertIn("gsap.min.js", html)
        self.assertIn("ScrollTrigger.min.js", html)
        self.assertIn("three.min.js", html)
        self.assertIn("mpi-experience", html)

    def test_home_incluye_canvas_3d_parallax_y_anatomia_didactica_ecuador(self):
        html = self.client.get("/").content.decode()
        self.assertIn('id="mpi-hero-3d"', html)
        self.assertIn('data-animate="title"', html)
        self.assertIn("data-parallax=", html)
        self.assertIn("data-didactic-tab=", html)
        self.assertIn("data-import-step=", html)
        # Referencias reales a los productos y logística de importación en Ecuador
        self.assertIn("Teja", html)
        self.assertIn("Wall Panel WPC", html)
        self.assertIn("Ambato", html)


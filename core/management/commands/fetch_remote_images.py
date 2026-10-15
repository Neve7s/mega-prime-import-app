"""Descarga imágenes remotas (landing + imagen_url de productos) a media/ en WebP.

Fuentes desde index.html: logo del footer -> SiteSettings.logo,
foto hero lobby -> SiteSettings.hero_image, y cada Product.imagen_url -> imagen.
Idempotente: omite lo que ya está localizado.
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from catalog.models import Product
from core.image_utils import fetch_url_into_field
from core.models import SiteSettings


class Command(BaseCommand):
    help = "Localiza imágenes remotas en WebP (logo, hero, productos)."

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        html = (base / "index.html").read_text(encoding="utf-8")
        site = SiteSettings.get_solo()
        done = 0

        m = re.search(r'alt="MEGA PRIME IMPORT LGM Logo"[^>]*src="([^"]+)"', html)
        if m and not site.logo:
            if fetch_url_into_field(site, "logo", m.group(1), "logo", max_dim=800):
                done += 1
                self.stdout.write("logo OK")

        hero = re.search(
            r'data-alt="Close-up architectural photograph[^"]*" src="([^"]+)"', html
        )
        if hero and not site.hero_image:
            if fetch_url_into_field(site, "hero_image", hero.group(1), "hero", max_dim=1920):
                done += 1
                self.stdout.write("hero OK")

        for p in Product.objects.filter(imagen="", imagen_url__startswith="http"):
            if fetch_url_into_field(p, "imagen", p.imagen_url, p.slug):
                done += 1
                self.stdout.write(f"{p.sku} OK")

        self.stdout.write(self.style.SUCCESS(f"Localizadas: {done}"))

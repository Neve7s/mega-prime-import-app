import logging

from django.conf import settings
from django.db import DatabaseError
from django.http import HttpRequest

logger = logging.getLogger(__name__)


def site_settings(request: HttpRequest) -> dict:
    from .models import HeroStat, SiteLocation, SiteSettings

    settings_obj = SiteSettings.get_solo()
    stats = list(HeroStat.objects.filter(activo=True)[:4])
    try:
        locations = list(SiteLocation.objects.all())
    except DatabaseError:
        logger.exception(
            "No se pudieron cargar las ubicaciones del sitio. "
            "Verifica que las migraciones de core estén aplicadas."
        )
        locations = []
    return {
        "site_settings": settings_obj,
        "hero_stats": stats,
        "site_locations": locations,
        # Dominio público (megaprimeimport.com) para canonical, og:url y sitemap.
        "site_url": getattr(settings, "SITE_URL", "").rstrip("/"),
    }

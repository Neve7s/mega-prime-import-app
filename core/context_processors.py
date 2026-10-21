from django.conf import settings
from django.http import HttpRequest


def site_settings(request: HttpRequest) -> dict:
    try:
        from .models import HeroStat, SiteSettings

        settings_obj = SiteSettings.get_solo()
        stats = list(HeroStat.objects.filter(activo=True)[:4])
    except Exception:
        settings_obj = None
        stats = []
    return {
        "site_settings": settings_obj,
        "hero_stats": stats,
        # Dominio público (megaprimeimport.com) para canonical, og:url y sitemap.
        "site_url": getattr(settings, "SITE_URL", "").rstrip("/"),
    }

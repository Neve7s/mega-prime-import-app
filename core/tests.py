from django.test import TestCase

from .models import HeroStat, SiteSettings


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

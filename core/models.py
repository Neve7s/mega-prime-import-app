from django.db import models


class SiteSettings(models.Model):
    """Singleton: branding + slogans + contacto. Editable desde /admin/."""

    site_name = models.CharField(max_length=120, default="MEGA PRIME IMPORT LGM")
    meta_title = models.CharField(
        max_length=160, default="MEGA PRIME IMPORT | Acabados, Interiorismo y Maquinaria Pro"
    )
    meta_description = models.CharField(
        max_length=255,
        default="Importadores directos de porcelanatos gran formato, interiorismo contract y maquinaria pro. Cotización B2B en 48h.",
        blank=True,
    )
    tagline = models.CharField(
        max_length=255,
        default="Hub Logístico & Distribución Mayorista",
        help_text="Slogan corto (overline del hero, header, pestaña).",
    )
    hero_city = models.CharField(max_length=80, default="Ambato, Ecuador")
    hero_title = models.CharField(
        max_length=255, default="Excelencia en Cada Acabado, Potencia en Cada Herramienta."
    )
    hero_subtitle = models.TextField(
        default="Importadores directos de revestimientos porcelánicos de gran formato, perfiles arquitectónicos, grifería de autor y maquinaria de corte con precisión milimétrica para contratistas, arquitectos y constructoras de alto rendimiento.",
        blank=True,
    )
    hero_cta_primary = models.CharField(max_length=80, default="Explorar Catálogo 2025")
    hero_cta_secondary = models.CharField(max_length=80, default="Cotizar Proyecto por Mayor")
    hero_spec_label = models.CharField(
        max_length=80, default="Placa Sinterizada 3200x1600x12mm", blank=True
    )
    hero_telemetry_1_value = models.CharField(max_length=40, default="+1,200", blank=True)
    hero_telemetry_1_label = models.CharField(max_length=80, default="Obras Suministradas", blank=True)
    hero_telemetry_2_value = models.CharField(max_length=40, default="40,000 m²", blank=True)
    hero_telemetry_2_label = models.CharField(max_length=80, default="Stock en Bodega Ambato", blank=True)

    whatsapp_number = models.CharField(
        max_length=20,
        default="593963796222",
        help_text="Solo dígitos con código país, ej 593963796222. Se usa en checkout del carrito.",
    )
    whatsapp_default_message = models.CharField(
        max_length=255,
        default="Hola MEGA PRIME, deseo cotizar un proyecto por mayor",
        blank=True,
    )
    phone_display = models.CharField(max_length=40, default="+593 96 379 6222", blank=True)
    email = models.EmailField(default="ventas@megaprimeimport.com", blank=True)
    address = models.CharField(max_length=255, default="Bodega Ambato — Ambato, Ecuador", blank=True)
    cities = models.CharField(max_length=120, default="Ambato, Ecuador", blank=True)
    schedule = models.CharField(
        max_length=120, default="Lunes a Sábado 8:00 AM – 6:30 PM (Ambato, Ecuador)", blank=True
    )
    company_legal = models.CharField(
        max_length=160, default="Ecuatoriana | MEGA PRIME IMPORT", blank=True
    )

    facebook_url = models.URLField(blank=True, default="")
    instagram_url = models.URLField(blank=True, default="")
    tiktok_url = models.URLField(blank=True, default="")

    logo = models.ImageField(upload_to="branding/", blank=True, null=True)
    hero_image = models.ImageField(upload_to="branding/", blank=True, null=True)

    footer_text = models.TextField(
        default="Importación directa, homologación de materiales de alto tránsito y distribución mayorista de revestimientos de gran formato, perfiles arquitectónicos y maquinaria de precisión para proyectos corporativos y residenciales de lujo.",
        blank=True,
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ajustes del sitio"
        verbose_name_plural = "Ajustes del sitio"

    def __str__(self) -> str:
        return f"Ajustes: {self.site_name}"

    @classmethod
    def get_solo(cls) -> "SiteSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        from .image_utils import optimize_field_file

        changed = []
        if optimize_field_file(self.logo, max_dim=800):
            changed.append("logo")
        if optimize_field_file(self.hero_image, max_dim=1920):
            changed.append("hero_image")
        if changed:
            super().save(update_fields=changed)

    @property
    def whatsapp_link(self) -> str:
        return f"https://wa.me/{self.whatsapp_number}"


class HeroStat(models.Model):
    """Cifras del hero (+15 años, 48h, stock, B2B). Ordenables y activables."""

    value = models.CharField(max_length=40)
    label = models.CharField(max_length=80)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Cifra hero"
        verbose_name_plural = "Cifras hero"

    def __str__(self) -> str:
        return f"{self.value} — {self.label}"

from django.contrib import admin

from .models import HeroStat, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Branding / Logo", {"fields": ("site_name", "tagline", "logo", "hero_image", "company_legal")}),
        ("SEO", {"fields": ("meta_title", "meta_description")}),
        (
            "Hero / Slogans",
            {
                "fields": (
                    "hero_city",
                    "hero_title",
                    "hero_subtitle",
                    "hero_cta_primary",
                    "hero_cta_secondary",
                    "hero_spec_label",
                    "hero_telemetry_1_value",
                    "hero_telemetry_1_label",
                    "hero_telemetry_2_value",
                    "hero_telemetry_2_label",
                )
            },
        ),
        (
            "Contacto / WhatsApp",
            {
                "fields": (
                    "whatsapp_number",
                    "whatsapp_default_message",
                    "phone_display",
                    "email",
                    "address",
                    "cities",
                    "schedule",
                )
            },
        ),
        ("Redes", {"fields": ("facebook_url", "instagram_url", "tiktok_url")}),
        ("Footer", {"fields": ("footer_text",)}),
    )

    def has_add_permission(self, request):
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HeroStat)
class HeroStatAdmin(admin.ModelAdmin):
    list_display = ("value", "label", "orden", "activo")
    list_editable = ("orden", "activo")

from django.contrib import admin

from .models import Complaint, HeroStat, SiteLocation, SiteSettings


class SiteLocationInline(admin.TabularInline):
    model = SiteLocation
    extra = 1


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    inlines = (SiteLocationInline,)
    fieldsets = (
        ("Branding / Logo", {"fields": (
            "site_name", "tagline", "logo", "hero_image", "company_legal", "company_ruc",
        )}),
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
        ("Misión y visión", {"fields": ("mision", "vision")}),
        ("Redes", {"fields": (
            "facebook_url", "instagram_url", "tiktok_url", "x_url",
            "youtube_url", "pinterest_url", "linkedin_url",
        )}),
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


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("codigo", "tipo", "creado_en", "estado")
    list_filter = ("tipo", "estado", "creado_en")
    search_fields = ("codigo", "nombres", "apellidos", "identificacion", "correo")
    readonly_fields = (
        "codigo", "tipo", "nombres", "apellidos", "tipo_identificacion",
        "identificacion", "empresa", "correo", "telefono", "direccion",
        "provincia", "producto_servicio", "numero_pedido", "fecha_incidente",
        "monto_reclamado", "detalle", "solicitud", "canal_respuesta",
        "acepta_privacidad", "creado_en", "actualizado_en",
    )
    fields = readonly_fields + ("estado", "respuesta_interna")
    date_hierarchy = "creado_en"
    list_per_page = 25


admin.site.site_header = "MEGA PRIME IMPORT — Administración"
admin.site.site_title = "Mega Prime Admin"
admin.site.index_title = "Gestión del sitio megaprimeimport.com"

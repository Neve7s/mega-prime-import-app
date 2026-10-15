from django.contrib import admin
from django.utils.html import format_html

from .models import Order, OrderItem, SaleCode


@admin.register(SaleCode)
class SaleCodeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "cliente_nombre", "cliente_telefono", "estado", "usos", "max_usos", "expira_en")
    list_filter = ("estado",)
    search_fields = ("codigo", "cliente_nombre", "cliente_telefono")
    readonly_fields = ("codigo", "usos", "created_at")

    @admin.action(description="Marcar como anulados")
    def anular(self, request, queryset):
        queryset.update(estado=SaleCode.ANULADO)

    actions = ["anular"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("sku_snapshot", "nombre_snapshot", "cantidad", "precio_snapshot")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre_completo", "telefono", "total", "estado", "sale_code", "created_at")
    list_filter = ("estado",)
    search_fields = ("codigo", "nombre_completo", "documento_identidad", "telefono", "email")
    readonly_fields = ("codigo", "sale_code", "subtotal", "total", "created_at")
    inlines = [OrderItemInline]

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ("codigo", "created_at")
        return self.readonly_fields

    def wa_link(self, obj):
        from urllib.parse import quote

        msg = f"Hola {obj.nombre_completo}, tu pedido {obj.codigo} está {obj.get_estado_display()}."
        return format_html('<a target="_blank" href="https://wa.me/{}?text={}">WhatsApp</a>',
                           obj.telefono, quote(msg))

    wa_link.short_description = "WhatsApp"

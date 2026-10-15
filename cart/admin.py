from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "updated_at")
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("sku_snapshot", "nombre_snapshot", "cantidad", "precio_snapshot")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre_cliente", "telefono", "total", "estado", "created_at")
    list_filter = ("estado",)
    search_fields = ("codigo", "nombre_cliente", "telefono")
    inlines = [OrderItemInline]

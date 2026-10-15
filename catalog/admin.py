from django.contrib import admin

from .models import Category, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden")
    list_editable = ("orden",)
    prepopulated_fields = {"slug": ("nombre",)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "nombre", "categoria", "precio_mayor", "stock_cantidad", "en_stock", "activo")
    list_filter = ("categoria", "en_stock", "activo", "destacado")
    search_fields = ("sku", "nombre")
    list_editable = ("precio_mayor", "stock_cantidad", "en_stock", "activo")
    prepopulated_fields = {"slug": ("nombre",)}
    inlines = [ProductImageInline]

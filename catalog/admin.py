from django.contrib import admin

from .models import Category, Product, ProductImage, TipoProducto


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden")
    list_editable = ("orden",)
    prepopulated_fields = {"slug": ("nombre",)}


@admin.register(TipoProducto)
class TipoProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden")
    list_editable = ("orden",)
    prepopulated_fields = {"slug": ("nombre",)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "nombre", "categoria", "tipo", "precio_mayor", "stock_cantidad", "en_stock", "activo")
    list_filter = ("categoria", "tipo", "en_stock", "activo", "destacado")
    search_fields = ("sku", "nombre")
    list_editable = ("precio_mayor", "stock_cantidad", "en_stock", "activo")
    prepopulated_fields = {"slug": ("nombre",)}
    inlines = [ProductImageInline]
    actions = ["descargar_imagen_url"]

    @admin.action(description="Descargar imagen desde URL al servidor (WebP)")
    def descargar_imagen_url(self, request, queryset):
        from core.image_utils import fetch_url_into_field

        ok = 0
        for product in queryset:
            if product.imagen_url and fetch_url_into_field(
                product, "imagen", product.imagen_url, product.slug
            ):
                ok += 1
        self.message_user(request, f"{ok} imágenes localizadas en WebP.")

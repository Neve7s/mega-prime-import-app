from django.db import models


class Category(models.Model):
    nombre = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self) -> str:
        return self.nombre


class TipoProducto(models.Model):
    """Familia del producto (Teja Roma, Cumbreros, Tornillería…).

    Eje de filtro y búsqueda junto a Categoría. Gestionable en el panel.
    """

    nombre = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Tipo de producto"
        verbose_name_plural = "Tipos de producto"

    def __str__(self) -> str:
        return self.nombre


class Product(models.Model):
    UNIDAD_M2 = "m2"
    UNIDAD_UNID = "unid"
    UNIDAD_SET = "set"
    UNIDADES = [(UNIDAD_M2, "m²"), (UNIDAD_UNID, "Unidad"), (UNIDAD_SET, "Set")]

    categoria = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="productos")
    tipo = models.ForeignKey(TipoProducto, on_delete=models.PROTECT,
                             related_name="productos", null=True, blank=True)
    sku = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    badge = models.CharField(
        max_length=40, blank=True, default="",
        help_text="Etiqueta destacada, ej MÁS VENDIDO. Vacío = sin etiqueta.")
    colores = models.JSONField(
        default=list, blank=True,
        help_text="Lista de {nombre, hex}, ej [{nombre: Rojo, hex: #8B2500}].")
    caracteristicas = models.JSONField(
        default=list, blank=True,
        help_text="Lista de textos destacados del producto.")
    descripcion = models.TextField(blank=True)
    precio_mayor = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default="USD")
    unidad = models.CharField(max_length=8, choices=UNIDADES, default=UNIDAD_M2)
    stock_cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    en_stock = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)
    origen = models.CharField(max_length=40, blank=True)
    imagen = models.ImageField(upload_to="productos/", blank=True, null=True)
    imagen_url = models.URLField(max_length=500, blank=True, default="", help_text="Temporal: URL externa hasta subir imagen propia.")
    ficha_tecnica = models.JSONField(default=dict, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria__orden", "nombre"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self) -> str:
        return f"{self.sku} — {self.nombre}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from core.image_utils import optimize_field_file

        if optimize_field_file(self.imagen, max_dim=1600):
            super().save(update_fields=["imagen"])

    @property
    def imagen_src(self) -> str:
        if self.imagen:
            return self.imagen.url
        return self.imagen_url


class ProductImage(models.Model):
    producto = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="imagenes")
    imagen = models.ImageField(upload_to="productos/galeria/", blank=True, null=True)
    imagen_url = models.URLField(max_length=500, blank=True, default="")
    alt = models.CharField(max_length=160, blank=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"

    def __str__(self) -> str:
        return f"{self.producto.sku} #{self.orden}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from core.image_utils import optimize_field_file

        if optimize_field_file(self.imagen, max_dim=1600):
            super().save(update_fields=["imagen"])

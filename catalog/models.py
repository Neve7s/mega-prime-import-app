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

    Eje de filtro y búsqueda junto a Categoría. Si tiene categoría propia,
    al elegir el tipo la categoría se rellena sola: una sola decisión.
    """

    nombre = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    categoria = models.ForeignKey(Category, on_delete=models.PROTECT,
                                 related_name="tipos", null=True, blank=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Tipo de producto"
        verbose_name_plural = "Tipos de producto"

    def __str__(self) -> str:
        return self.nombre


class Color(models.Model):
    """Paleta de colores del catálogo (rojo, verde, naranja, negro, plomo…)."""

    nombre = models.CharField(max_length=40)
    slug = models.SlugField(max_length=40, unique=True)
    hex = models.CharField(max_length=7, default="#000000")
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Color"
        verbose_name_plural = "Colores"

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

    @property
    def lista_colores(self):
        """Colores del producto en orden (relación, no JSON)."""
        return [pc.color for pc in self.colores_producto.all()]


class ProductColor(models.Model):
    """Un color disponible de un producto (con su orden y su rol).

    `rol` sirve para las fichas con dos colores (exterior/interior):
    Teja Española Negro/Blanco = Negro(exterior) + Blanco(interior).
    """

    ROL_EXTERIOR = "exterior"
    ROL_INTERIOR = "interior"
    ROLES = [(ROL_EXTERIOR, "Exterior"), (ROL_INTERIOR, "Interior")]

    producto = models.ForeignKey(Product, on_delete=models.CASCADE,
                                 related_name="colores_producto")
    color = models.ForeignKey(Color, on_delete=models.PROTECT, related_name="usos")
    orden = models.PositiveIntegerField(default=0)
    rol = models.CharField(max_length=20, blank=True, default="", choices=ROLES)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Color del producto"
        verbose_name_plural = "Colores del producto"
        constraints = [
            models.UniqueConstraint(fields=["producto", "color", "rol"],
                                    name="uniq_color_producto_rol"),
        ]

    def __str__(self) -> str:
        return f"{self.producto.sku} · {self.color.nombre}"


class ProductImage(models.Model):
    producto = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="imagenes")
    imagen = models.ImageField(upload_to="productos/galeria/", blank=True, null=True)
    imagen_url = models.URLField(max_length=500, blank=True, default="")
    alt = models.CharField(max_length=160, blank=True)
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="fotos")
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

    @property
    def imagen_src(self) -> str:
        """URL de la foto: archivo propio si existe, si no la externa."""
        if self.imagen:
            return self.imagen.url
        return self.imagen_url

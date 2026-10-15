from django.conf import settings
from django.db import models


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="carts"
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Carrito"
        verbose_name_plural = "Carritos"

    def __str__(self) -> str:
        owner = self.user.username if self.user else f"sesión {self.session_key}"
        return f"Carrito {self.pk} ({owner})"

    @property
    def total(self):
        return sum((i.subtotal for i in self.items.all()), start=0)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="cart_items")
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cart", "product"], name="unique_cart_product")]
        verbose_name = "Ítem de carrito"
        verbose_name_plural = "Ítems de carrito"

    def __str__(self) -> str:
        return f"{self.product.sku} x{self.cantidad}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class Order(models.Model):
    PENDING_WHATSAPP = "pending_wa"
    SENT = "sent"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    ESTADOS = [
        (PENDING_WHATSAPP, "Pendiente WhatsApp"),
        (SENT, "Enviada"),
        (CONFIRMED, "Confirmada"),
        (CANCELLED, "Cancelada"),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    nombre_cliente = models.CharField(max_length=120)
    telefono = models.CharField(max_length=30)
    ciudad = models.CharField(max_length=80, blank=True)
    notas = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=12, choices=ESTADOS, default=PENDING_WHATSAPP)
    mensaje_wa = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self) -> str:
        return f"{self.codigo} — {self.nombre_cliente}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, on_delete=models.SET_NULL, related_name="order_items"
    )
    sku_snapshot = models.CharField(max_length=40)
    nombre_snapshot = models.CharField(max_length=160)
    cantidad = models.PositiveIntegerField()
    precio_snapshot = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Ítem de pedido"
        verbose_name_plural = "Ítems de pedido"

    def __str__(self) -> str:
        return f"{self.sku_snapshot} x{self.cantidad}"

"""Venta sin pasarela: el admin emite códigos por WhatsApp y el cliente
los usa en el checkout junto a sus datos. El carrito vive en localStorage;
aquí solo persisten códigos y pedidos."""

import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def new_sale_code() -> str:
    alphabet = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
    return "MPI-" + "".join(secrets.choice(alphabet) for _ in range(6))


class SaleCode(models.Model):
    """Código que el admin genera y comparte por WhatsApp para autorizar un pedido web."""

    EMITIDO = "emitido"
    USADO = "usado"
    ANULADO = "anulado"
    ESTADOS = [(EMITIDO, "Emitido"), (USADO, "Usado"), (ANULADO, "Anulado")]

    codigo = models.CharField(max_length=12, unique=True, default=new_sale_code)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sale_codes",
    )
    cliente_nombre = models.CharField(max_length=120, blank=True)
    cliente_telefono = models.CharField(max_length=30, blank=True)
    max_usos = models.PositiveIntegerField(default=1)
    usos = models.PositiveIntegerField(default=0)
    expira_en = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default=EMITIDO)
    notas = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Código de venta"
        verbose_name_plural = "Códigos de venta"

    def __str__(self) -> str:
        return f"{self.codigo} ({self.get_estado_display()})"

    def save(self, *args, **kwargs):
        if not self.expira_en:
            self.expira_en = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def vigente(self) -> bool:
        if self.estado != self.EMITIDO:
            return False
        if self.usos >= self.max_usos:
            return False
        if self.expira_en and timezone.now() > self.expira_en:
            return False
        return True

    def registrar_uso(self) -> None:
        self.usos += 1
        if self.usos >= self.max_usos:
            self.estado = self.USADO
        self.save(update_fields=["usos", "estado"])


class Order(models.Model):
    """Pedido web creado desde el carrito localStorage + código WhatsApp."""

    RECIBIDO = "recibido"
    PREPARACION = "preparacion"
    LISTO = "listo"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"
    ESTADOS = [
        (RECIBIDO, "Recibido"),
        (PREPARACION, "En preparación"),
        (LISTO, "Listo"),
        (ENTREGADO, "Entregado"),
        (CANCELADO, "Cancelado"),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    sale_code = models.ForeignKey(
        SaleCode, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    nombre_completo = models.CharField(max_length=160)
    documento_identidad = models.CharField(max_length=20)
    email = models.EmailField()
    telefono = models.CharField(max_length=30)
    ciudad = models.CharField(max_length=80, blank=True)
    notas = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=12, choices=ESTADOS, default=RECIBIDO)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos (Punto de venta)"

    def __str__(self) -> str:
        return f"{self.codigo} — {self.nombre_completo}"


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

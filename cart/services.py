"""Lógica de venta: validar código, crear pedido desde el carrito localStorage."""

import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from django.conf import settings

from catalog.models import Product

from .models import Order, OrderItem, SaleCode

DOCUMENTO_RE = re.compile(r"^[A-Za-z0-9-]{5,20}$")


def validar_codigo(codigo: str) -> tuple[SaleCode | None, str]:
    """Devuelve (SaleCode vigente, '') o (None, mensaje de error)."""
    codigo = (codigo or "").strip().upper()
    if not codigo:
        return None, "Ingresa el código que te compartimos por WhatsApp."
    try:
        sale = SaleCode.objects.get(codigo=codigo)
    except SaleCode.DoesNotExist:
        return None, "Código no válido. Revisa el mensaje de WhatsApp."
    if not sale.vigente:
        return None, "Código vencido o ya utilizado. Solicita uno nuevo por WhatsApp."
    return sale, ""


def crear_pedido(datos: dict, items: list[dict], sale: SaleCode) -> tuple[Order | None, str]:
    """Crea Order + OrderItems con snapshots de precio. Retorna (pedido, error)."""
    nombre = (datos.get("nombre_completo") or "").strip()
    doc = (datos.get("documento_identidad") or "").strip().upper()
    email = (datos.get("email") or "").strip()
    telefono = (datos.get("telefono") or "").strip()
    if len(nombre) < 5:
        return None, "Ingresa tu nombre completo."
    if not DOCUMENTO_RE.match(doc):
        return None, "Documento de identidad no válido."
    if "@" not in email or "." not in email:
        return None, "Correo electrónico no válido."
    if len(re.sub(r"\D", "", telefono)) < 7:
        return None, "Número de teléfono no válido."
    if not items:
        return None, "Tu carrito está vacío."

    lineas = []
    subtotal = Decimal("0")
    for it in items:
        try:
            product = Product.objects.get(sku=str(it.get("sku", "")), activo=True)
        except Product.DoesNotExist:
            return None, f"Producto no disponible: {it.get('sku', '?')}"
        try:
            cantidad = int(it.get("cantidad", 0))
        except (TypeError, ValueError):
            return None, f"Cantidad no válida para {product.sku}."
        if cantidad < 1 or cantidad > 9999:
            return None, f"Cantidad no válida para {product.sku}."
        precio = product.precio_mayor
        subtotal += precio * cantidad
        lineas.append((product, cantidad, precio))

    try:
        numero = Order.objects.count() + 1
        codigo = f"PED-{numero:06d}"
        pedido = Order.objects.create(
            codigo=codigo, sale_code=sale, nombre_completo=nombre,
            documento_identidad=doc, email=email, telefono=telefono,
            ciudad=(datos.get("ciudad") or "").strip()[:80],
            notas=(datos.get("notas") or "").strip(),
            subtotal=subtotal, descuento=Decimal("0"), total=subtotal,
            raw_payload={"items": items},
        )
        for product, cantidad, precio in lineas:
            OrderItem.objects.create(
                order=pedido, product=product, sku_snapshot=product.sku,
                nombre_snapshot=product.nombre, cantidad=cantidad, precio_snapshot=precio,
            )
    except (InvalidOperation, ValueError):
        return None, "No se pudo procesar el pedido. Intenta de nuevo."
    sale.registrar_uso()
    return pedido, ""


def wa_compartir_codigo(sale: SaleCode) -> str:
    """Link wa.me para enviar el código al cliente."""
    numero = getattr(settings, "WHATSAPP_NUMBER", "")
    msg = (
        f"Hola, tu código de compra MEGA PRIME es *{sale.codigo}*.\n"
        f"Úsalo en tu carrito web junto a tus datos para procesar el pedido.\n"
        f"Coordinamos pago y entrega por aquí."
    )
    return f"https://wa.me/{numero}?text={quote(msg)}" if numero else ""

from decimal import Decimal

from django.test import TestCase

from cart.models import Cart, CartItem
from catalog.models import Category, Product


class CartTest(TestCase):
    def setUp(self):
        cat = Category.objects.create(nombre="Porcelanatos", slug="porcelanato")
        self.p = Product.objects.create(
            categoria=cat, sku="MPG-T", nombre="Test", slug="t",
            precio_mayor=Decimal("100"),
        )

    def test_snapshot_y_total(self):
        cart = Cart.objects.create(session_key="abc123")
        CartItem.objects.create(cart=cart, product=self.p, cantidad=2, precio_unitario=self.p.precio_mayor)
        self.p.precio_mayor = Decimal("999")
        self.p.save()
        item = cart.items.get()
        self.assertEqual(item.subtotal, Decimal("200"))
        self.assertEqual(cart.total, Decimal("200"))

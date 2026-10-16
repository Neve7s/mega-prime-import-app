from django import forms

from calculator.models import HSCode
from cart.models import Order, SaleCode
from catalog.models import Category, Product, TipoProducto
from core.models import SiteSettings


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["categoria", "tipo", "sku", "nombre", "slug", "descripcion", "badge",
                  "precio_mayor", "unidad", "stock_cantidad", "en_stock", "destacado",
                  "origen", "imagen", "imagen_url", "activo"]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["nombre", "slug", "descripcion", "orden"]
        help_texts = {
            "slug": "Se genera solo desde el nombre. Úsalo sin espacios ni tildes.",
            "orden": "Menor número = aparece primero en filtros y catálogo.",
        }


class TipoForm(forms.ModelForm):
    class Meta:
        model = TipoProducto
        fields = ["nombre", "slug", "descripcion", "orden"]
        help_texts = {
            "slug": "Se genera solo desde el nombre. Úsalo sin espacios ni tildes.",
            "orden": "Menor número = aparece primero en filtros y catálogo.",
        }


class OrderEstadoForm(forms.Form):
    estado = forms.ChoiceField(choices=Order.ESTADOS)


class SaleCodeForm(forms.ModelForm):
    class Meta:
        model = SaleCode
        fields = ["cliente_nombre", "cliente_telefono", "max_usos", "notas"]


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        exclude = ["updated_at"]


class CalculadoraForm(forms.Form):
    valor_fob = forms.DecimalField(max_digits=12, decimal_places=2, label="Valor FOB (USD)")
    flete = forms.DecimalField(max_digits=12, decimal_places=2, initial=0)
    seguro = forms.DecimalField(max_digits=12, decimal_places=2, initial=0)
    hs_code = forms.ModelChoiceField(queryset=HSCode.objects.all(), required=False, label="Partida")

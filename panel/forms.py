from django import forms
from django.contrib.auth import get_user_model, password_validation

from calculator.models import HSCode
from cart.models import Order, SaleCode
from catalog.models import Category, Product, TipoProducto
from core.models import SiteSettings

from .models import AccesoPanel


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


class ColaboradorForm(forms.Form):
    SECCIONES = ("calculadora", "pedidos", "codigos", "productos")
    CHECK = {"class": "mt-0.5 h-4 w-4 shrink-0 accent-[#0A0A0B]"}

    username = forms.CharField(max_length=150, label="Usuario")
    first_name = forms.CharField(max_length=150, required=False, label="Nombre")
    password = forms.CharField(
        required=False, label="Contraseña", widget=forms.PasswordInput(render_value=False),
        help_text="Mínimo 8 caracteres. Al editar, déjala vacía para no cambiarla.")
    calculadora = forms.BooleanField(required=False, label="Calculadora", widget=forms.CheckboxInput(attrs=CHECK))
    pedidos = forms.BooleanField(required=False, label="Punto de venta", widget=forms.CheckboxInput(attrs=CHECK))
    codigos = forms.BooleanField(required=False, label="Códigos WhatsApp", widget=forms.CheckboxInput(attrs=CHECK))
    productos = forms.BooleanField(required=False, label="Productos", widget=forms.CheckboxInput(attrs=CHECK))
    activo = forms.BooleanField(required=False, label="Activo", widget=forms.CheckboxInput(attrs=CHECK))

    def __init__(self, *args, colaborador=None, **kwargs):
        self.colaborador = colaborador
        super().__init__(*args, **kwargs)
        if colaborador:
            usuario = colaborador.usuario
            self.fields["username"].initial = usuario.username
            self.fields["first_name"].initial = usuario.first_name
            for clave in self.SECCIONES:
                self.fields[clave].initial = getattr(colaborador, clave)
            self.fields["activo"].initial = colaborador.activo
        else:
            self.fields["activo"].initial = True

    def clean_username(self):
        username = (self.cleaned_data["username"] or "").strip()
        if not username:
            raise forms.ValidationError("Escribe un usuario.")
        existentes = get_user_model().objects.filter(username__iexact=username)
        if self.colaborador:
            existentes = existentes.exclude(pk=self.colaborador.usuario_id)
        if existentes.exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get("password") or ""
        if not password and not self.colaborador:
            raise forms.ValidationError("La contraseña es obligatoria.")
        if password:
            password_validation.validate_password(password)
        return password

    def clean(self):
        datos = super().clean()
        if not any(datos.get(clave) for clave in self.SECCIONES):
            raise forms.ValidationError("Marca al menos una sección para el colaborador.")
        return datos

    def save(self):
        datos = self.cleaned_data
        if self.colaborador:
            perfil = self.colaborador
            usuario = perfil.usuario
        else:
            perfil = AccesoPanel()
            usuario = get_user_model()()
        usuario.username = datos["username"]
        usuario.first_name = datos["first_name"]
        usuario.is_staff = False
        activo = bool(datos.get("activo"))
        usuario.is_active = activo
        if datos["password"]:
            usuario.set_password(datos["password"])
        usuario.save()
        perfil.usuario = usuario
        for clave in self.SECCIONES:
            setattr(perfil, clave, bool(datos.get(clave)))
        perfil.activo = activo
        perfil.save()
        return perfil

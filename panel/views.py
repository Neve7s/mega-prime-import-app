from urllib.parse import quote

from django.contrib.auth import logout
from django.shortcuts import get_object_or_404, redirect, render

from calculator.models import HSCode, TaxRule
from calculator.services import estimate
from cart.models import Order, SaleCode
from catalog.models import Product
from core.models import SiteSettings

from .auth import staff_only
from .forms import CalculadoraForm, OrderEstadoForm, ProductForm, SaleCodeForm, SiteSettingsForm


@staff_only
def dashboard(request):
    ctx = {
        "n_productos": Product.objects.filter(activo=True).count(),
        "n_pedidos_abiertos": Order.objects.exclude(estado__in=[Order.ENTREGADO, Order.CANCELADO]).count(),
        "n_codigos": SaleCode.objects.filter(estado=SaleCode.EMITIDO).count(),
        "ultimos": Order.objects.all()[:5],
    }
    return render(request, "panel/dashboard.html", ctx)


@staff_only
def productos(request):
    q = (request.GET.get("q") or "").strip()
    prods = Product.objects.select_related("categoria").all()
    if q:
        prods = prods.filter(nombre__icontains=q) | prods.filter(sku__icontains=q)
    return render(request, "panel/productos.html", {"productos": prods[:100], "q": q})


@staff_only
def producto_editar(request, pk=None):
    obj = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel:productos")
    return render(request, "panel/producto_form.html", {"form": form, "obj": obj})


@staff_only
def pedidos(request):
    estado = request.GET.get("estado", "")
    qs = Order.objects.select_related("sale_code").all()
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, "panel/pedidos.html",
                  {"pedidos": qs[:100], "estado": estado, "estados": Order.ESTADOS})


@staff_only
def pedido_detalle(request, codigo):
    pedido = get_object_or_404(Order, codigo=codigo)
    form = OrderEstadoForm(request.POST or None, initial={"estado": pedido.estado})
    if request.method == "POST" and form.is_valid():
        pedido.estado = form.cleaned_data["estado"]
        pedido.save(update_fields=["estado"])
        return redirect("panel:pedido_detalle", codigo=pedido.codigo)
    tel = "".join(c for c in pedido.telefono if c.isdigit())
    wa = f"https://wa.me/{tel}?text={quote(f'Hola {pedido.nombre_completo}, tu pedido {pedido.codigo} está {pedido.get_estado_display()}.')}" if tel else ""
    return render(request, "panel/pedido_detalle.html",
                  {"pedido": pedido, "form": form, "wa_cliente": wa})


@staff_only
def codigos(request):
    return render(request, "panel/codigos.html", {"codigos": SaleCode.objects.all()[:100]})


@staff_only
def codigo_crear(request):
    form = SaleCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        sale = form.save(commit=False)
        sale.creado_por = request.user
        sale.save()
        return redirect("panel:codigo_detalle", codigo=sale.codigo)
    return render(request, "panel/codigo_form.html", {"form": form})


@staff_only
def codigo_detalle(request, codigo):
    sale = get_object_or_404(SaleCode, codigo=codigo)
    tel = "".join(c for c in sale.cliente_telefono if c.isdigit())
    wa = (f"https://wa.me/{tel}?text={quote(f'Hola {sale.cliente_nombre or ''}, tu código de compra MEGA PRIME es *{sale.codigo}*. Úsalo en tu carrito web.')}"
          if tel else "")
    if request.method == "POST":
        sale.estado = SaleCode.ANULADO
        sale.save(update_fields=["estado"])
        return redirect("panel:codigos")
    return render(request, "panel/codigo_detalle.html", {"sale": sale, "wa": wa})


@staff_only
def ajustes(request):
    site = SiteSettings.get_solo()
    form = SiteSettingsForm(request.POST or None, request.FILES or None, instance=site)
    ok = False
    if request.method == "POST" and form.is_valid():
        form.save()
        ok = True
    return render(request, "panel/ajustes.html", {"form": form, "ok": ok})


@staff_only
def calculadora(request):
    form = CalculadoraForm(request.GET or None)
    resultado = None
    rule = TaxRule.get_active()
    if form.is_valid():
        hs = form.cleaned_data["hs_code"]
        resultado = estimate(
            form.cleaned_data["valor_fob"], form.cleaned_data["flete"], form.cleaned_data["seguro"],
            hs.ad_valorem_pct if hs else 0,
            rule.fodinfa_pct if rule else 0, rule.iva_pct if rule else 0,
        )
    return render(request, "panel/calculadora.html",
                  {"form": form, "resultado": resultado, "rule": rule})


def salir(request):
    logout(request)
    return redirect("panel:login")

from urllib.parse import quote

from django.contrib.auth import logout
from django.shortcuts import get_object_or_404, redirect, render

from calculator.models import HSCode, TaxRule
from calculator.services import estimate
from cart.models import Order, OrderItem, SaleCode
from catalog.models import Product
from core.models import SiteSettings

from .auth import staff_only
from .forms import CalculadoraForm, OrderEstadoForm, ProductForm, SaleCodeForm, SiteSettingsForm


@staff_only
def dashboard(request):
    from datetime import timedelta
    from django.db.models import Count, Sum
    from django.utils import timezone

    hoy = timezone.now().date()
    ultimos7 = [(hoy - timedelta(days=i)) for i in range(6, -1, -1)]
    por_dia = []
    max_dia = 0
    for d in ultimos7:
        n = Order.objects.filter(created_at__date=d).exclude(estado=Order.CANCELADO).count()
        max_dia = max(max_dia, n)
        por_dia.append({"dia": d.strftime("%d/%m"), "n": n})

    por_estado_qs = Order.objects.values("estado").annotate(n=Count("id"))
    total_ped = sum(r["n"] for r in por_estado_qs) or 1
    colores = {Order.RECIBIDO: "#D4AF37", Order.PREPARACION: "#b45309",
               Order.LISTO: "#0ea5e9", Order.ENTREGADO: "#16a34a", Order.CANCELADO: "#9ca3af"}
    labels = dict(Order.ESTADOS)
    por_estado = [{"label": labels[r["estado"]], "n": r["n"],
                   "pct": round(r["n"] * 100 / total_ped),
                   "color": colores.get(r["estado"], "#6b7280")} for r in por_estado_qs]
    segmentos = []
    acc = 0
    for s in por_estado:
        segmentos.append(f"{s['color']} {acc}% {acc + s['pct']}%")
        acc += s["pct"]

    top_productos = (OrderItem.objects.exclude(order__estado=Order.CANCELADO)
                     .values("sku_snapshot", "nombre_snapshot")
                     .annotate(qty=Count("id")).order_by("-qty")[:5])
    ingresos = (Order.objects.exclude(estado=Order.CANCELADO)
                .aggregate(t=Sum("total"))["t"] or 0)
    ctx = {
        "n_productos": Product.objects.filter(activo=True).count(),
        "n_pedidos_abiertos": Order.objects.exclude(estado__in=[Order.ENTREGADO, Order.CANCELADO]).count(),
        "n_codigos": SaleCode.objects.filter(estado=SaleCode.EMITIDO).count(),
        "ingresos": ingresos,
        "por_dia": por_dia, "max_dia": max_dia or 1,
        "por_estado": por_estado, "dona": ", ".join(segmentos) or "#e5e7eb 0% 100%",
        "top_productos": top_productos,
        "stock_bajo": Product.objects.filter(activo=True, stock_cantidad__lt=100).order_by("stock_cantidad")[:5],
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
    sections = [
        {"wide": True, "title": "Datos básicos", "fields": ["categoria", "sku", "nombre", "slug", "descripcion"], "full": ["descripcion"]},
        {"wide": False, "title": "Precio y stock", "fields": ["precio_mayor", "unidad", "stock_cantidad", "en_stock"], "full": []},
        {"wide": False, "title": "Origen y visibilidad", "fields": ["origen", "destacado", "activo"], "full": []},
        {"wide": True, "title": "Imagen", "fields": ["imagen", "imagen_url"], "full": ["imagen", "imagen_url"]},
    ]
    return render(request, "panel/producto_form.html", {"form": form, "obj": obj, "sections": sections})


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
    sections = [
        {"wide": False, "title": "Cliente", "fields": ["cliente_nombre", "cliente_telefono", "notas"], "full": ["notas"]},
        {"wide": False, "title": "Uso", "fields": ["max_usos"], "full": []},
    ]
    return render(request, "panel/codigo_form.html", {"form": form, "sections": sections})


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
    sections = [
        {"wide": False, "title": "Branding", "fields": ["site_name", "tagline", "logo", "hero_image", "company_legal"], "full": ["logo", "hero_image"]},
        {"wide": False, "title": "SEO", "fields": ["meta_title", "meta_description"], "full": ["meta_description"]},
        {"wide": True, "title": "Hero", "fields": ["hero_city", "hero_title", "hero_subtitle", "hero_cta_primary", "hero_cta_secondary", "hero_spec_label", "hero_telemetry_1_value", "hero_telemetry_1_label", "hero_telemetry_2_value", "hero_telemetry_2_label"], "full": ["hero_subtitle"]},
        {"wide": True, "title": "Contacto / WhatsApp", "fields": ["whatsapp_number", "whatsapp_default_message", "phone_display", "email", "address", "cities", "schedule"], "full": ["whatsapp_default_message"]},
        {"wide": False, "title": "Redes", "fields": ["facebook_url", "instagram_url", "tiktok_url"], "full": []},
        {"wide": False, "title": "Footer", "fields": ["footer_text"], "full": ["footer_text"]},
    ]
    return render(request, "panel/ajustes.html", {"form": form, "ok": ok, "sections": sections})


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
    return redirect("core:home")

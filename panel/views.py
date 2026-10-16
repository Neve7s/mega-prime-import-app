from urllib.parse import quote

from django.contrib.auth import logout
from django.shortcuts import get_object_or_404, redirect, render

from calculator.models import TaxRule
from cart.models import Order, OrderItem, SaleCode
from catalog.models import Category, Product, TipoProducto
from core.models import SiteSettings

from django.views.decorators.csrf import ensure_csrf_cookie

from .auth import staff_only
from .forms import (CategoryForm, OrderEstadoForm, ProductForm, SaleCodeForm,
                    SiteSettingsForm, TipoForm)


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


def _parse_colores(raw):
    """Lista [{nombre, hex}] saneada (máx 20). Lo inválido se descarta."""
    import json as _json
    import re as _re

    try:
        data = _json.loads(raw or "[]")
    except (ValueError, TypeError):
        return []
    out = []
    if not isinstance(data, list):
        return []
    for it in data[:20]:
        if not isinstance(it, dict):
            continue
        nombre = str(it.get("nombre") or "").strip()[:40]
        hexv = str(it.get("hex") or "").strip()
        if not nombre:
            continue
        if not _re.fullmatch(r"#[0-9a-fA-F]{6}", hexv):
            continue
        out.append({"nombre": nombre, "hex": hexv.upper()})
    return out


def _parse_caracteristicas(raw):
    """Lista de textos saneada (máx 30, c/u máx 120)."""
    import json as _json

    try:
        data = _json.loads(raw or "[]")
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(t).strip()[:120] for t in data[:30] if str(t or "").strip()]


@staff_only
def producto_editar(request, pk=None):
    import json as _json

    obj = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        prod = form.save()
        prod.colores = _parse_colores(request.POST.get("colores_json", "[]"))
        prod.caracteristicas = _parse_caracteristicas(
            request.POST.get("caracteristicas_json", "[]"))
        prod.save(update_fields=["colores", "caracteristicas"])
        return redirect("panel:productos")
    sections = [
        {"wide": True, "title": "Datos básicos", "fields": ["categoria", "tipo", "sku", "nombre", "slug", "badge", "descripcion"], "full": ["descripcion"]},
        {"wide": False, "title": "Precio y stock", "fields": ["precio_mayor", "unidad", "stock_cantidad", "en_stock"], "full": []},
        {"wide": False, "title": "Origen y visibilidad", "fields": ["origen", "destacado", "activo"], "full": []},
        {"wide": True, "title": "Imagen", "fields": ["imagen", "imagen_url"], "full": ["imagen", "imagen_url"]},
    ]
    if request.method == "POST":
        # Re-pinta lo enviado (ya saneado) para no perder lo editado.
        # Ojo: se pasan objetos, json_script serializa (no pre-serializar).
        colores_init = _parse_colores(
            request.POST.get("colores_json", "[]"))
        caracteristicas_init = _parse_caracteristicas(
            request.POST.get("caracteristicas_json", "[]"))
    else:
        colores_init = list(getattr(obj, "colores", None) or [])
        caracteristicas_init = list(
            getattr(obj, "caracteristicas", None) or [])
    ctx = {"form": form, "obj": obj, "sections": sections,
           "colores_init": colores_init,
           "caracteristicas_init": caracteristicas_init}
    return render(request, "panel/producto_form.html", ctx)


@staff_only
def categorias(request):
    from django.db.models import Count

    cats = Category.objects.annotate(n_productos=Count("productos")).all()
    return render(request, "panel/categorias.html", {"categorias": cats})


@staff_only
def categoria_editar(request, pk=None):
    obj = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel:categorias")
    return render(request, "panel/categoria_form.html", {"form": form, "obj": obj})


@staff_only
def categoria_eliminar(request, pk):
    from django.db.models import ProtectedError

    obj = get_object_or_404(Category, pk=pk)
    error = ""
    if request.method == "POST":
        try:
            obj.delete()
            return redirect("panel:categorias")
        except ProtectedError:
            error = ("No se puede eliminar: tiene %d producto(s) asociados. "
                     "Muévelos a otra categoría primero."
                     % obj.productos.count())
    return render(request, "panel/categoria_eliminar.html",
                  {"obj": obj, "error": error})


@staff_only
def tipos(request):
    from django.db.models import Count

    tipos = TipoProducto.objects.annotate(n_productos=Count("productos")).all()
    return render(request, "panel/tipos.html", {"tipos": tipos})


@staff_only
def tipo_editar(request, pk=None):
    obj = get_object_or_404(TipoProducto, pk=pk) if pk else None
    form = TipoForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel:tipos")
    return render(request, "panel/tipo_form.html", {"form": form, "obj": obj})


@staff_only
def tipo_eliminar(request, pk):
    from django.db.models import ProtectedError

    obj = get_object_or_404(TipoProducto, pk=pk)
    error = ""
    if request.method == "POST":
        try:
            obj.delete()
            return redirect("panel:tipos")
        except ProtectedError:
            error = ("No se puede eliminar: tiene %d producto(s) asociados. "
                     "Muévelos a otro tipo primero."
                     % obj.productos.count())
    return render(request, "panel/tipo_eliminar.html",
                  {"obj": obj, "error": error})


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


AJUSTES_TABS = [
    {"key": "marca", "icon": "🏷", "title": "Marca",
     "desc": "Nombre, slogan, logo y razón social. Aparecen en el header y el footer de toda la web.",
     "fields": ["site_name", "tagline", "logo", "company_legal"], "full": ["logo"]},
    {"key": "portada", "icon": "🖼", "title": "Portada",
     "desc": "La pantalla principal: ciudad, titular, botones, foto y cifras destacadas.",
     "fields": ["hero_city", "hero_title", "hero_subtitle", "hero_cta_primary",
                "hero_cta_secondary", "hero_spec_label", "hero_image",
                "hero_telemetry_1_value", "hero_telemetry_1_label",
                "hero_telemetry_2_value", "hero_telemetry_2_label"],
     "full": ["hero_subtitle", "hero_image"]},
    {"key": "contacto", "icon": "📞", "title": "Contacto",
     "desc": "WhatsApp, teléfono, correo, dirección, ciudades y horario de atención.",
     "fields": ["whatsapp_number", "whatsapp_default_message", "phone_display",
                "email", "address", "cities", "schedule"],
     "full": ["whatsapp_default_message", "address"]},
    {"key": "redes", "icon": "🔗", "title": "Redes",
     "desc": "Enlaces de los iconos de redes sociales del pie de página.",
     "fields": ["facebook_url", "instagram_url", "tiktok_url"], "full": []},
    {"key": "seo", "icon": "🔍", "title": "SEO",
     "desc": "Título y descripción con los que la web aparece en Google.",
     "fields": ["meta_title", "meta_description"], "full": ["meta_description"]},
    {"key": "pie", "icon": "🧾", "title": "Pie de página",
     "desc": "Texto descriptivo largo del footer.",
     "fields": ["footer_text"], "full": ["footer_text"]},
    {"key": "tema", "icon": "🎨", "title": "Tema",
     "desc": "Colores, fondos y fuentes de toda la página. Elige una paleta o personaliza.",
     "fields": ["color_primario", "color_secundario", "color_fondo",
                "color_tarjetas", "color_texto", "color_acento",
                "fuente_cuerpo", "fuente_titulos"], "full": []},
]

PALETAS_TEMA = [
    {"nombre": "Dorado & Negro",
     "colores": {"color_primario": "#D4AF37", "color_secundario": "#0A0A0B",
                 "color_fondo": "#FAFAF8", "color_tarjetas": "#FFFFFF",
                 "color_texto": "#131313", "color_acento": "#15803D"},
     "fuentes": {"fuente_cuerpo": "IBM Plex Sans", "fuente_titulos": "Libre Franklin"}},
    {"nombre": "Verde & Negro",
     "colores": {"color_primario": "#16A34A", "color_secundario": "#0A0A0B",
                 "color_fondo": "#F7FAF7", "color_tarjetas": "#FFFFFF",
                 "color_texto": "#131313", "color_acento": "#0E7C66"},
     "fuentes": {"fuente_cuerpo": "Inter", "fuente_titulos": "Montserrat"}},
    {"nombre": "Azul & Negro",
     "colores": {"color_primario": "#2563EB", "color_secundario": "#0A0A0B",
                 "color_fondo": "#F7F9FC", "color_tarjetas": "#FFFFFF",
                 "color_texto": "#131313", "color_acento": "#0E7490"},
     "fuentes": {"fuente_cuerpo": "Inter", "fuente_titulos": "Inter"}},
    {"nombre": "Rojo & Negro",
     "colores": {"color_primario": "#DC2626", "color_secundario": "#0A0A0B",
                 "color_fondo": "#FBF7F7", "color_tarjetas": "#FFFFFF",
                 "color_texto": "#131313", "color_acento": "#B45309"},
     "fuentes": {"fuente_cuerpo": "Barlow", "fuente_titulos": "Oswald"}},
    {"nombre": "Oscuro & Blanco",
     "colores": {"color_primario": "#D4AF37", "color_secundario": "#000000",
                 "color_fondo": "#111214", "color_tarjetas": "#1C1E21",
                 "color_texto": "#F5F5F4", "color_acento": "#34D399"},
     "fuentes": {"fuente_cuerpo": "Inter", "fuente_titulos": "Montserrat"}},
    {"nombre": "Café & Marrón",
     "colores": {"color_primario": "#B45309", "color_secundario": "#1C1410",
                 "color_fondo": "#FAF7F2", "color_tarjetas": "#FFFFFF",
                 "color_texto": "#1C1410", "color_acento": "#047857"},
     "fuentes": {"fuente_cuerpo": "Poppins", "fuente_titulos": "Playfair Display"}},
]

AJUSTES_HINTS = {
    "site_name": "Header, footer y título de la pestaña del navegador.",
    "tagline": "Slogan bajo el nombre, en el header.",
    "logo": "Logo del header y footer. Recomendado: PNG sin fondo. Vacío = emblema dorado.",
    "company_legal": "Línea “Empresa: …” del footer.",
    "hero_city": "Línea superior de la portada.",
    "hero_title": "Titular grande de la portada.",
    "hero_subtitle": "Párrafo bajo el titular de la portada.",
    "hero_cta_primary": "Botón principal de la portada.",
    "hero_cta_secondary": "Botón secundario de la portada.",
    "hero_spec_label": "Etiqueta técnica pequeña de la portada.",
    "hero_image": "Foto grande de la portada.",
    "hero_telemetry_1_value": "Cifra destacada 1 de la portada.",
    "hero_telemetry_1_label": "Etiqueta de la cifra 1.",
    "hero_telemetry_2_value": "Cifra destacada 2 de la portada.",
    "hero_telemetry_2_label": "Etiqueta de la cifra 2.",
    "whatsapp_number": "Todos los botones de WhatsApp. Solo dígitos con código país (ej 593963796222).",
    "whatsapp_default_message": "Mensaje que llega pre-llenado en el chat.",
    "phone_display": "“Línea Directa” del header.",
    "email": "Botón de correo y sección de contacto.",
    "address": "Dirección en contacto y pie del sitio.",
    "cities": "Ciudades en header y contacto.",
    "schedule": "Horario en contacto y CTA.",
    "facebook_url": "Icono Facebook del footer. Vacío = se oculta.",
    "instagram_url": "Icono Instagram del footer. Vacío = se oculta.",
    "tiktok_url": "Icono TikTok del footer. Vacío = se oculta.",
    "meta_title": "Título azul en resultados de Google.",
    "meta_description": "Descripción gris bajo el título en Google.",
    "footer_text": "Párrafo descriptivo del pie de página.",
    "color_primario": "Botones dorados y textos destacados.",
    "color_secundario": "Botones oscuros, secciones oscuras y titulares.",
    "color_fondo": "Fondo principal de la página.",
    "color_tarjetas": "Fondo de tarjetas y secciones.",
    "color_texto": "Texto principal de la página.",
    "color_acento": "Botones de WhatsApp y estados.",
    "fuente_cuerpo": "Tipografía del texto general.",
    "fuente_titulos": "Tipografía de títulos.",
}


@staff_only
def ajustes(request):
    site = SiteSettings.get_solo()
    form = SiteSettingsForm(request.POST or None, request.FILES or None, instance=site)
    ok = False
    if request.method == "POST" and form.is_valid():
        form.save()
        ok = True
    # Pestaña activa: la pedida, o la primera con errores de validación.
    active_tab = request.GET.get("tab", "marca")
    if form.errors:
        for tab in AJUSTES_TABS:
            if any(f in form.errors for f in tab["fields"]):
                active_tab = tab["key"]
                break
    if active_tab not in [t["key"] for t in AJUSTES_TABS]:
        active_tab = "marca"
    return render(request, "panel/ajustes.html",
                  {"form": form, "ok": ok, "tabs": AJUSTES_TABS,
                   "hints": AJUSTES_HINTS, "active_tab": active_tab,
                   "paletas": PALETAS_TEMA})


@staff_only
@ensure_csrf_cookie
def calculadora(request):
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    from calculator.seed_embarques import EMBARQUES
    from calculator.services import calculate_shipment

    def _num(v, default=0):
        try:
            s = str(v).strip().replace(",", "")
            return Decimal(s) if s not in ("", None) else Decimal(str(default))
        except (InvalidOperation, ValueError, TypeError, AttributeError):
            return Decimal(str(default))

    def _q2(v):
        return str(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    # Datos para el selector de embarques (gastos redondeados a 2 dec. para mostrar).
    embarques_ui = {
        key: {"nombre": e["nombre"], "tasas": e["tasas"],
              "gastos": {k: _q2(v) for k, v in e["gastos"].items()},
              "items": e["items"]}
        for key, e in EMBARQUES.items()
    }
    sel = request.GET.get("embarque", "roma")
    if sel not in EMBARQUES and sel != "nuevo":
        sel = "roma"
    if sel == "nuevo":
        # Embarque en blanco: tasas generales, gastos en 0 y una fila vacía.
        defaults_tasas = {"seguro_pct": "1", "advalorem_pct": "20",
                          "fondinfa_pct": "0.5", "iva_pct": "15", "iva_pvp_pct": "15"}
        defaults_gastos = {k: "0" for k in
                           ("flete_intl", "flete_local", "gasto_admin", "bodegaje",
                            "devolucion", "comision_banco", "descarga", "agente",
                            "otros_unit")}
        defaults_items = [{"nombre": "", "cant": "1", "cant_caja": "1",
                           "valor_unit": "0", "margen_pct": "35",
                           "compet1": "", "compet2": "", "compet3": "",
                           "seguro_pct": "", "advalorem_pct": "",
                           "fondinfa_pct": "", "iva_pct": ""}]
    else:
        seed = EMBARQUES[sel]
        defaults_tasas = dict(seed["tasas"])
        defaults_gastos = {k: _q2(v) for k, v in seed["gastos"].items()}
        defaults_items = seed["items"]
    override_keys = ("seguro_pct", "advalorem_pct", "fondinfa_pct", "iva_pct")

    if request.method == "POST":
        tasas = {k: _num(request.POST.get(k, v), v) for k, v in defaults_tasas.items()}
        gastos = {k: _num(request.POST.get(k, v), v) for k, v in defaults_gastos.items()}
        nombres = request.POST.getlist("nombre")
        posted = {k: request.POST.getlist(k) for k in
                  ("cant", "cant_caja", "valor_unit", "margen_pct", "compet1",
                   "compet2", "compet3") + tuple(f"ov_{k}" for k in override_keys)}

        def _raw(key, i, d=""):
            lst = posted.get(key, [])
            if key.startswith("ov_"):
                lst = request.POST.getlist(key)
            return lst[i] if i < len(lst) else d

        def _ov(key, i):
            s = _raw(f"ov_{key}", i, "").strip()
            return s if s != "" else None

        items = []
        for i, nombre in enumerate(nombres):
            if not (nombre.strip() or _raw("cant", i).strip() or _raw("valor_unit", i).strip()):
                continue
            items.append({
                "nombre": nombre.strip() or f"Producto {i+1}",
                "cant": _num(_raw("cant", i), 0),
                "cant_caja": _num(_raw("cant_caja", i), 1) or 1,
                "valor_unit": _num(_raw("valor_unit", i), 0),
                "margen_pct": _num(_raw("margen_pct", i), 35),
                "compet1": _num(_raw("compet1", i), 0),
                "compet2": _num(_raw("compet2", i), 0),
                "compet3": _num(_raw("compet3", i), 0),
                # Override por producto: None/vacío = usa tasa general.
                "seguro_pct": _ov("seguro_pct", i),
                "advalorem_pct": _ov("advalorem_pct", i),
                "fondinfa_pct": _ov("fondinfa_pct", i),
                "iva_pct": _ov("iva_pct", i),
            })
        # valores para repintar el form
        tasas_raw = {k: request.POST.get(k, v) for k, v in defaults_tasas.items()}
        gastos_raw = {k: request.POST.get(k, v) for k, v in defaults_gastos.items()}

        def _rl(key, i):
            lst = request.POST.getlist(key)
            return lst[i] if i < len(lst) else ""

        items_raw = [{"nombre": n,
                      "cant": _rl("cant", i),
                      "cant_caja": _rl("cant_caja", i),
                      "valor_unit": _rl("valor_unit", i),
                      "margen_pct": _rl("margen_pct", i),
                      "compet1": _rl("compet1", i),
                      "compet2": _rl("compet2", i),
                      "compet3": _rl("compet3", i),
                      "seguro_pct": _rl("ov_seguro_pct", i),
                      "advalorem_pct": _rl("ov_advalorem_pct", i),
                      "fondinfa_pct": _rl("ov_fondinfa_pct", i),
                      "iva_pct": _rl("ov_iva_pct", i)}
                     for i, n in enumerate(nombres)]
        calc = calculate_shipment(items, gastos, tasas)
        return render(request, "panel/calculadora.html",
                      {"tasas": tasas_raw, "gastos": gastos_raw, "items_raw": items_raw,
                       "calc": calc, "rule": TaxRule.get_active(),
                       "embarques_ui": embarques_ui, "embarque_sel": sel})
    rule = TaxRule.get_active()
    return render(request, "panel/calculadora.html",
                  {"tasas": defaults_tasas, "gastos": defaults_gastos,
                   "items_raw": defaults_items, "calc": None, "rule": rule,
                   "embarques_ui": embarques_ui, "embarque_sel": sel})


@staff_only
def calculadora_reporte(request):
    """Descarga el reporte del embarque en .xlsx presentable.

    Recibe el estado actual de la calculadora como JSON (el cálculo en vivo
    corre en el navegador; aquí se recalcula en el servidor como fuente única
    de verdad antes de generar el archivo).
    """
    import json as _json
    from datetime import datetime
    from decimal import Decimal, InvalidOperation
    from django.http import HttpResponse, JsonResponse

    from calculator.reports import build_reporte_xlsx
    from calculator.services import calculate_shipment

    if request.method != "POST":
        return JsonResponse({"error": "Solo POST."}, status=405)
    try:
        payload = _json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "JSON inválido."}, status=400)

    def _num(v, default=0):
        try:
            s = str(v).strip().replace(",", ".")
            return Decimal(s) if s not in ("", None) else Decimal(str(default))
        except (InvalidOperation, ValueError, TypeError, AttributeError):
            return Decimal(str(default))

    def _ov(v):
        s = str(v or "").strip()
        return s if s != "" else None

    t = payload.get("tasas", {})
    tasas = {"seguro_pct": _num(t.get("seguro_pct"), 1),
             "advalorem_pct": _num(t.get("advalorem_pct"), 20),
             "fondinfa_pct": _num(t.get("fondinfa_pct"), "0.5"),
             "iva_pct": _num(t.get("iva_pct"), 15),
             "iva_pvp_pct": _num(t.get("iva_pvp_pct"), 15)}
    g = payload.get("gastos", {})
    gastos = {"flete_intl": _num(g.get("flete_intl"), 0),
              "flete_local": _num(g.get("flete_local"), 0),
              "gasto_admin": _num(g.get("gasto_admin"), 0),
              "bodegaje": _num(g.get("bodegaje"), 0),
              "devolucion": _num(g.get("devolucion"), 0),
              "comision_banco": _num(g.get("comision_banco"), 0),
              "descarga": _num(g.get("descarga"), 0),
              "agente": _num(g.get("agente"), 0),
              "otros_unit": _num(g.get("otros_unit"), 0)}
    items = []
    for i, it in enumerate(payload.get("items", [])):
        nombre = str(it.get("nombre") or "").strip()
        if not (nombre or str(it.get("cant") or "").strip()
                or str(it.get("valor_unit") or "").strip()):
            continue
        items.append({
            "nombre": nombre or f"Producto {i + 1}",
            "cant": _num(it.get("cant"), 0),
            "cant_caja": _num(it.get("cant_caja"), 1) or Decimal(1),
            "valor_unit": _num(it.get("valor_unit"), 0),
            "margen_pct": _num(it.get("margen_pct"), 35),
            "compet1": _num(it.get("compet1"), 0),
            "compet2": _num(it.get("compet2"), 0),
            "compet3": _num(it.get("compet3"), 0),
            "seguro_pct": _ov(it.get("seguro_pct")),
            "advalorem_pct": _ov(it.get("advalorem_pct")),
            "fondinfa_pct": _ov(it.get("fondinfa_pct")),
            "iva_pct": _ov(it.get("iva_pct")),
        })
    if not items:
        return JsonResponse({"error": "Sin productos."}, status=400)
    calc = calculate_shipment(items, gastos, tasas)
    if calc["error"]:
        return JsonResponse({"error": calc["error"]}, status=400)
    nombre = str(payload.get("embarque") or "Embarque").strip()[:60]
    data = build_reporte_xlsx(calc, tasas, gastos, nombre)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    resp = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="reporte-embarque-{stamp}.xlsx"'
    return resp


def salir(request):
    logout(request)
    return redirect("core:home")

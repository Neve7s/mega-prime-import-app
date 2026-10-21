from urllib.parse import quote, urlencode

from django.contrib.auth import logout
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from calculator.models import SavedShipment, TaxRule
from cart.models import Order, OrderItem, SaleCode
from catalog.calidad import (contar_grupos_duplicados, faltantes_producto,
                             grupos_duplicados, q_incompleto)
from catalog.models import Category, Color, Product, TipoProducto
from core.models import HeroMedia, SiteSettings

from django.views.decorators.csrf import ensure_csrf_cookie

from .auth import (SECCIONES_URL, es_dueno, primera_seccion,
                   seccion_requerida, staff_only, tiene_panel)
from .forms import (CategoryForm, ColaboradorForm, HeroMediaForm, OrderEstadoForm,
                    ProductForm, SaleCodeForm, SiteSettingsForm, TipoForm)
from .models import AccesoPanel


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("panel:login")
    if not tiene_panel(request.user):
        return redirect("panel:login")
    if not es_dueno(request.user):
        seccion = primera_seccion(request.user)
        if seccion:
            return redirect(SECCIONES_URL[seccion])
        return render(request, "panel/sin_acceso.html", {"seccion": ""}, status=403)

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


BULK_MAX = 200

AVISOS = {
    "eliminados": ("ok", "producto eliminado", "productos eliminados"),
    "precios": ("ok", "ficha actualizada", "fichas actualizadas"),
    "fusionados": ("ok", "variante de color fusionada", "variantes de color fusionadas"),
    "datos_invalidos": ("error",
                        "Revisa precio y stock: deben ser números mayores o iguales a 0.",
                        ""),
}


def _entero(valor, default=0):
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return default


def _todas(request):
    """`?todas=1`: buscar en todas las categorías en vez de la activa."""
    return (request.GET.get("todas") or "").strip().lower() in ("1", "on", "true", "si", "sí")


def _aviso_desde_request(request):
    """Los avisos viajan por querystring: `?msg=<codigo>&n=<cantidad>&cat=<nombre>`."""
    codigo = (request.GET.get("msg") or "").strip()
    if codigo not in AVISOS:
        return None
    tipo, singular, plural = AVISOS[codigo]
    n = _entero(request.GET.get("n"))
    if plural:
        texto = f"{_plural(n, singular, plural)}."
    else:
        texto = singular
    return {"tipo": tipo, "texto": texto}


def _url_productos(cat_slug="", q="", todas=False):
    """URL de la lista preservando el contexto (categoría, búsqueda, global)."""
    params = {}
    if cat_slug:
        params["categoria"] = cat_slug
    if q:
        params["q"] = q
    if todas:
        params["todas"] = "1"
    base = reverse("panel:productos")
    return f"{base}?{urlencode(params)}" if params else base


def _url_productos_desde_post(request):
    return _url_productos(
        (request.POST.get("volver_categoria") or "").strip(),
        (request.POST.get("volver_q") or "").strip(),
        (request.POST.get("volver_todas") or "").strip().lower() in ("1", "on", "true"))


def _con_msg(url, codigo, n=0, cat=""):
    extra = {"msg": codigo}
    if n:
        extra["n"] = n
    if cat:
        extra["cat"] = cat
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urlencode(extra)}"


def _ids_seleccionados(valores):
    """Enteros válidos de la selección (máx BULK_MAX), sin duplicados."""
    ids = []
    for valor in valores[:BULK_MAX]:
        numero = _entero(valor, None)
        if numero is not None and numero not in ids:
            ids.append(numero)
    return ids


def _ctx_productos(request, categoria_slug=None, import_result=None, import_error=""):
    from django.db.models import Count, Q

    q = (request.GET.get("q") or "").strip()
    todas = _todas(request)
    if categoria_slug is not None:
        cat_slug = categoria_slug.strip()
    else:
        cat_slug = "" if todas else (request.GET.get("categoria") or "").strip()
    categorias = (Category.objects.annotate(
        n_productos=Count("productos"),
        n_incompletos=Count("productos", filter=q_incompleto("productos__")),
    ).order_by("orden", "nombre"))
    categoria_activa = Category.objects.filter(slug=cat_slug).first() if cat_slug else None
    prods = Product.objects.select_related("categoria", "tipo")
    if categoria_activa is not None:
        prods = prods.filter(categoria=categoria_activa)
    if q:
        prods = prods.filter(Q(nombre__icontains=q) | Q(sku__icontains=q))
    productos = list(prods[:100])
    for producto in productos:
        producto.faltantes = faltantes_producto(producto)
    return {
        "productos": productos, "q": q, "todas": todas,
        "categorias": categorias, "categoria_activa": categoria_activa,
        "n_total": Product.objects.count(),
        "n_duplicados": contar_grupos_duplicados(),
        "aviso": _aviso_desde_request(request),
        "import_result": import_result, "import_error": import_error,
    }


@seccion_requerida("productos")
def productos(request):
    return render(request, "panel/productos.html", _ctx_productos(request))


@seccion_requerida("productos")
def productos_precios(request):
    """Edición inline de precio y stock en la lista."""
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    if request.method != "POST":
        return redirect("panel:productos")
    volver = _url_productos_desde_post(request)
    ids = _ids_seleccionados(request.POST.getlist("ids_precio"))
    if not ids:
        return redirect(_con_msg(volver, "datos_invalidos"))

    def _decimal(pk, campo):
        raw = str(request.POST.get(f"{campo}_{pk}", "")).strip().replace(",", ".")
        if not raw:
            raise InvalidOperation
        valor = Decimal(raw)
        if not valor.is_finite() or valor < 0:
            raise InvalidOperation
        return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    cambios = []
    for pk in ids:
        producto = Product.objects.filter(pk=pk).first()
        if producto is None:
            continue
        try:
            precio = _decimal(pk, "precio")
            stock = _decimal(pk, "stock")
        except (InvalidOperation, ValueError):
            return redirect(_con_msg(volver, "datos_invalidos"))
        cambios.append((producto.pk, precio, stock))
    if not cambios:
        return redirect(_con_msg(volver, "datos_invalidos"))
    for pk, precio, stock in cambios:
        Product.objects.filter(pk=pk).update(
            precio_mayor=precio, stock_cantidad=stock)
    return redirect(_con_msg(volver, "precios", len(cambios)))


@seccion_requerida("productos")
def productos_duplicados(request):
    grupos = grupos_duplicados()
    from catalog.calidad import grupos_mismo_modelo

    modelos = grupos_mismo_modelo()
    return render(request, "panel/productos_duplicados.html",
                  {"grupos": grupos, "n_grupos": len(grupos),
                   "n_productos": sum(len(g) for g in grupos),
                   "grupos_modelo": modelos,
                   "n_grupos_modelo": len(modelos),
                   "n_productos_modelo": sum(len(g) for g in modelos)})


@seccion_requerida("productos")
def productos_fusionar(request):
    """Junta en un solo producto las fichas que son el mismo modelo."""
    from catalog.calidad import fusionar_variantes, grupos_mismo_modelo

    if request.method != "POST":
        return redirect("panel:productos_duplicados")
    try:
        principal = get_object_or_404(Product, pk=int(request.POST.get("principal")))
    except (TypeError, ValueError):
        return redirect("panel:productos_duplicados")
    ids = []
    for valor in request.POST.getlist("variantes"):
        try:
            ids.append(int(valor))
        except (TypeError, ValueError):
            continue
    ids = [i for i in ids if i != principal.pk]
    if not ids:
        return redirect("panel:productos_duplicados")
    # Solo se fusionan fichas del MISMO grupo de "mismo modelo".
    grupo = next((g for g in grupos_mismo_modelo()
                  if any(p.pk == principal.pk for p in g)), None)
    if grupo is None:
        return redirect(_con_msg(reverse("panel:productos_duplicados"),
                                "datos_invalidos"))
    pks_grupo = {p.pk for p in grupo}
    variantes = [p for p in Product.objects.filter(pk__in=ids)
                 if p.pk in pks_grupo]
    if not variantes:
        return redirect("panel:productos_duplicados")
    with transaction.atomic():
        fusionar_variantes(principal, variantes)
    return redirect(_con_msg(
        reverse("panel:productos_duplicados"), "fusionados", len(variantes)))


@seccion_requerida("productos")
def producto_eliminar(request, pk):
    obj = get_object_or_404(Product, pk=pk)
    volver_slug = (request.POST.get("volver_categoria")
                   or request.GET.get("categoria") or "").strip()
    if request.method == "POST":
        obj.delete()
        return redirect(_con_msg(_url_productos(volver_slug), "eliminados", 1))
    return render(request, "panel/producto_eliminar.html",
                  {"obj": obj, "volver_categoria": volver_slug})



@seccion_requerida("productos")
def productos_plantilla(request):
    from catalog.excel_productos import build_productos_xlsx

    resp = HttpResponse(
        build_productos_xlsx(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="productos-plantilla.xlsx"'
    return resp


def _slug_producto(nombre, sku):
    from django.utils.text import slugify

    base = slugify(nombre) or slugify(sku) or "producto"
    candidato = base
    numero = 2
    while Product.objects.filter(slug=candidato).exists():
        candidato = f"{base}-{numero}"
        numero += 1
    return candidato


def _plural(cantidad, singular, plural):
    return f"{cantidad} {singular if cantidad == 1 else plural}"


@seccion_requerida("productos")
def productos_importar(request):
    from catalog.excel_productos import read_productos_xlsx

    if request.method != "POST":
        return redirect("panel:productos")

    cat_slug = (request.POST.get("categoria") or "").strip()
    cat_defecto = Category.objects.filter(slug=cat_slug).first() if cat_slug else None

    def fallo(mensaje):
        return render(request, "panel/productos.html",
                      _ctx_productos(request, categoria_slug=cat_slug,
                                     import_error=mensaje))

    archivo = request.FILES.get("archivo")
    if archivo is None:
        return fallo("Adjunta un archivo Excel (.xlsx).")
    if archivo.size > 5 * 1024 * 1024:
        return fallo("El archivo supera los 5 MB. Divídelo en partes más pequeñas.")
    try:
        filas = read_productos_xlsx(archivo)
    except ValueError as exc:
        return fallo(str(exc))

    creados = actualizados = 0
    campos = ("nombre", "tipo", "precio_mayor", "unidad", "stock_cantidad",
              "badge", "origen", "imagen_url", "descripcion")
    from catalog.sku import siguiente_sku

    # 1) Validación ANTES de escribir nada: si algo falla, no queda nada a medias.
    for fila in filas:
        if (fila["categoria"] or cat_defecto) is None:
            return fallo(f"Falta la categoría en la fila {fila['fila']} "
                        "y no hay una categoría seleccionada como valor por defecto.")

    # Los SKUs que trae el archivo y los que se generen aquí no pueden pisarse
    # entre sí ni repetir uno ya existente en la base.
    reservados = {f["sku"] for f in filas if f["sku"]}
    with transaction.atomic():
        for fila in filas:
            categoria = fila["categoria"] or cat_defecto
            valores = {campo: fila[campo] for campo in campos}
            sku = fila["sku"]
            generado = not sku
            if generado:
                # Sin SKU en el Excel: se asigna el siguiente correlativo COD-000X.
                sku = siguiente_sku(reservados=reservados)
                while Product.objects.filter(sku__iexact=sku).exists():
                    sku = siguiente_sku(reservados=reservados)
                reservados.add(sku)
            existente = Product.objects.filter(sku=sku).first()
            if existente is None:
                producto = Product.objects.create(
                    sku=sku, slug=_slug_producto(fila["nombre"], sku),
                    categoria=categoria, **valores)
                creados += 1
            elif generado:
                # Un SKU generado nunca pisa un producto existente.
                producto = Product.objects.create(
                    sku=sku, slug=_slug_producto(fila["nombre"], sku),
                    categoria=categoria, **valores)
                creados += 1
            else:
                for campo, valor in valores.items():
                    setattr(existente, campo, valor)
                existente.categoria = categoria
                existente.save()
                producto = existente
                actualizados += 1
            # Colores (uno por modelo) y galería con las fotos del Excel.
            if fila["colores"]:
                from catalog.colores import aplicar_colores

                aplicar_colores(producto, [
                    {"slug": "", "nombre": c["nombre"], "hex": "", "rol": c["rol"]}
                    for c in fila["colores"]])
            if fila["galeria"]:
                from catalog.models import ProductImage

                orden = producto.imagenes.count()
                for url in fila["galeria"]:
                    if producto.imagenes.filter(imagen_url=url).exists():
                        continue
                    ProductImage.objects.create(
                        producto=producto, imagen_url=url[:500],
                        alt=producto.nombre[:160], orden=orden)
                    orden += 1

    return render(request, "panel/productos.html", _ctx_productos(
        request, categoria_slug=cat_slug,
        import_result={"creados": creados, "actualizados": actualizados,
                       "total": len(filas)}))


def _parse_colores(raw):
    """Lista [{slug, nombre, hex, rol}] saneada (máx 20). Lo inválido se descarta."""
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
        slug = str(it.get("slug") or "").strip()[:40]
        rol = str(it.get("rol") or "").strip().lower()
        if not nombre and not slug:
            continue
        if hexv and not _re.fullmatch(r"#[0-9a-fA-F]{6}", hexv):
            hexv = ""
        if not slug and not hexv:
            # Color propio sin tono válido: se descarta.
            continue
        if rol not in ("", "exterior", "interior"):
            rol = ""
        out.append({"slug": slug, "nombre": nombre, "hex": hexv.upper(), "rol": rol})
    return out


def _parse_galeria_urls(raw):
    """Lista de enlaces de la galería (uno por línea)."""
    import re as _re

    urls = []
    for linea in str(raw or "").splitlines():
        url = linea.strip()
        if not url or not _re.match(r"^https?://\S+$", url):
            continue
        if url not in urls:
            urls.append(url)
    return urls[:20]


def _imagen_valida(archivo, max_bytes=8 * 1024 * 1024):
    """Solo imágenes reales (y no tan grandes) para la galería."""
    if archivo is None:
        return False
    try:
        if archivo.size > max_bytes:
            return False
    except (TypeError, ValueError):
        return False
    tipo = (getattr(archivo, "content_type", "") or "").lower()
    if tipo and not tipo.startswith("image/"):
        return False
    # Comprobación real: si Pillow no la abre, no es una imagen.
    try:
        from PIL import Image

        archivo.seek(0)
        with Image.open(archivo) as imagen:
            imagen.verify()
        archivo.seek(0)
    except Exception:
        return False
    return True


def _guardar_galeria(request, producto):
    """Aplica la galería del formulario: borra, agrega enlaces y sube archivos."""
    from catalog.models import ProductImage

    # 1) Fotos marcadas para quitar
    for pk in request.POST.getlist("galeria_borrar"):
        try:
            numero = int(pk)
        except (TypeError, ValueError):
            continue
        producto.imagenes.filter(pk=numero).delete()

    # 2) Enlaces nuevos (al final de la galería, sin repetir)
    orden = producto.imagenes.count()
    for url in _parse_galeria_urls(request.POST.get("galeria_urls", "")):
        if producto.imagenes.filter(imagen_url=url).exists():
            continue
        ProductImage.objects.create(
            producto=producto, imagen_url=url[:500], alt=producto.nombre[:160],
            orden=orden)
        orden += 1

    # 3) Archivos subidos (solo imágenes válidas)
    for archivo in request.FILES.getlist("galeria_archivos"):
        if not _imagen_valida(archivo):
            continue
        try:
            ProductImage.objects.create(
                producto=producto, imagen=archivo, alt=producto.nombre[:160],
                orden=orden)
        except Exception:
            continue
        orden += 1


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


@seccion_requerida("productos")
def producto_editar(request, pk=None):
    import json as _json

    obj = get_object_or_404(Product, pk=pk) if pk else None
    # Alta "dentro de una categoría": llega desde el listado filtrado.
    volver_slug = (request.POST.get("volver_categoria")
                   or request.GET.get("categoria") or "").strip()
    volver_categoria = (Category.objects.filter(slug=volver_slug).first()
                        if volver_slug else None)
    # Alta "dentro de una categoría": la categoría queda fijada y sin select.
    categoria_ctx = volver_categoria if obj is None else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=obj)
    if categoria_ctx is not None and request.method != "POST":
        form.initial["categoria"] = categoria_ctx.pk
    if request.method == "POST" and form.is_valid():
        prod = form.save()
        from catalog.colores import aplicar_colores

        aplicar_colores(prod, _parse_colores(request.POST.get("colores_json", "[]")))
        prod.caracteristicas = _parse_caracteristicas(
            request.POST.get("caracteristicas_json", "[]"))
        prod.save(update_fields=["caracteristicas"])
        _guardar_galeria(request, prod)
        if volver_categoria is not None:
            return redirect(f"{reverse('panel:productos')}?categoria={volver_categoria.slug}")
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
        from catalog.colores import colores_para_form

        colores_init = colores_para_form(obj) if obj is not None else []
        caracteristicas_init = list(
            getattr(obj, "caracteristicas", None) or [])
    ctx = {"form": form, "obj": obj, "sections": sections,
           "colores_init": colores_init,
           "paleta": Color.objects.all(),
           "tipos_categoria": {
               str(t.pk): {"categoria": t.categoria_id,
                           "nombre": t.categoria.nombre if t.categoria else ""}
               for t in TipoProducto.objects.select_related("categoria")},
           "caracteristicas_init": caracteristicas_init,
           "categoria_ctx": categoria_ctx,
           "volver_categoria": volver_categoria,
           "en_modal": False}
    # El listado pide la ficha dentro de un <dialog>: devolvemos sólo el
    # fragmento y dejamos la URL normal como respaldo sin JavaScript.
    if obj is not None and request.method == "GET" and request.GET.get("modal") == "1":
        base = reverse("panel:producto_editar", args=[obj.pk])
        ctx["form_action"] = (f"{base}?categoria={volver_categoria.slug}"
                              if volver_categoria else base)
        ctx["en_modal"] = True
        return render(request, "panel/producto_form_modal.html", ctx)
    return render(request, "panel/producto_form.html", ctx)


@seccion_requerida("productos")
def categorias(request):
    from django.db.models import Count

    cats = Category.objects.annotate(n_productos=Count("productos")).all()
    return render(request, "panel/categorias.html", {"categorias": cats})


@seccion_requerida("productos")
def categoria_editar(request, pk=None):
    obj = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel:categorias")
    return render(request, "panel/categoria_form.html", {"form": form, "obj": obj})


@seccion_requerida("productos")
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


@seccion_requerida("productos")
def tipos(request):
    from django.db.models import Count

    tipos = TipoProducto.objects.annotate(n_productos=Count("productos")).all()
    return render(request, "panel/tipos.html", {"tipos": tipos})


@seccion_requerida("productos")
def tipo_editar(request, pk=None):
    obj = get_object_or_404(TipoProducto, pk=pk) if pk else None
    form = TipoForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel:tipos")
    return render(request, "panel/tipo_form.html", {"form": form, "obj": obj})


@seccion_requerida("productos")
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


def _alta_rapida(request, form_class):
    """Alta desde modal: JSON con el objeto creado o los errores del form.

    Sólo exige el nombre; el slug se deriva y el orden cae al final.
    """
    from django.http import JsonResponse
    from django.utils.text import slugify

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Solo POST."}, status=405)
    data = request.POST.copy()
    if not (data.get("slug") or "").strip():
        data["slug"] = slugify(data.get("nombre") or "")
    data.setdefault("orden", "0")
    form = form_class(data)
    if not form.is_valid():
        errores = {field: [str(e) for e in errors]
                   for field, errors in form.errors.items()}
        if "slug" in errores:
            errores["slug"] = ["Ya existe un registro con ese nombre."]
        return JsonResponse({"ok": False, "errors": errores}, status=400)
    obj = form.save()
    return JsonResponse({"ok": True, "id": obj.pk,
                         "nombre": obj.nombre, "slug": obj.slug})


@seccion_requerida("productos")
def categoria_crear_rapida(request):
    return _alta_rapida(request, CategoryForm)


@seccion_requerida("productos")
def tipo_crear_rapido(request):
    return _alta_rapida(request, TipoForm)


@seccion_requerida("pedidos")
def pedidos(request):
    estado = request.GET.get("estado", "")
    qs = Order.objects.select_related("sale_code").all()
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, "panel/pedidos.html",
                  {"pedidos": qs[:100], "estado": estado, "estados": Order.ESTADOS})


@seccion_requerida("pedidos")
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


@seccion_requerida("codigos")
def codigos(request):
    return render(request, "panel/codigos.html", {"codigos": SaleCode.objects.all()[:100]})


@seccion_requerida("codigos")
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


@seccion_requerida("codigos")
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
                "email", "address", "direccion_fisica", "enlace_maps", "cities", "schedule"],
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
    # Pesta��a activa: la pedida, o la primera con errores de validaci��n.
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
                   "paletas": PALETAS_TEMA,
                   "hero_medias": HeroMedia.objects.all(),
                   "hero_media_form": HeroMediaForm(),
                   "n_hero_medias": HeroMedia.objects.count()})


@seccion_requerida("productos")
def ajustes_hero_media(request):
    """Alta / cambio / borrado de los fondos del hero (máx. 3)."""
    from django.shortcuts import redirect

    borrar_pk = request.POST.get("borrar_pk")
    if borrar_pk:
        HeroMedia.objects.filter(pk=borrar_pk).delete()
        return redirect(f"{reverse('panel:ajustes')}#tab-portada")
    instancia = HeroMedia.objects.filter(pk=request.POST.get("hero_pk") or 0).first()
    datos = {
        "tipo": request.POST.get("hero_tipo") or HeroMedia.TIPO_IMAGEN,
        "url": (request.POST.get("hero_url") or "").strip()[:300],
        "alt": (request.POST.get("hero_alt") or "").strip()[:160],
        "activo": True,
    }
    archivo = request.FILES.get("hero_imagen")
    form = HeroMediaForm(datos, {"imagen": archivo} if archivo else None,
                         instance=instancia)
    if not form.is_valid():
        return redirect(f"{reverse('panel:ajustes')}#tab-portada")
    media = form.save(commit=False)
    if not media.pk and HeroMedia.objects.count() >= HeroMedia.MAX_MEDIOS:
        return redirect(f"{reverse('panel:ajustes')}#tab-portada")
    media.orden = HeroMedia.objects.count()
    media.save()
    return redirect(f"{reverse('panel:ajustes')}#tab-portada")


@seccion_requerida("calculadora")
@ensure_csrf_cookie
def calculadora(request):
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    from calculator.seed_embarques import EMBARQUES
    from calculator.services import calculate_shipment

    embarques = dict(EMBARQUES)
    saved_embarques = SavedShipment.objects.all()
    for saved in saved_embarques:
        embarques[f"guardado-{saved.pk}"] = {
            "nombre": saved.nombre,
            "tasas": saved.tasas,
            "gastos": saved.gastos,
            "items": saved.items,
        }

    def _num(v, default=0):
        try:
            s = str(v).strip().replace(",", "")
            return Decimal(s) if s not in ("", None) else Decimal(str(default))
        except (InvalidOperation, ValueError, TypeError, AttributeError):
            return Decimal(str(default))

    def _q2(v):
        return str(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def _pricing_items(items):
        normalized = []
        for item in items:
            item = dict(item)
            legacy_margin = item.pop("margen_pct", None)
            item.pop("cant_caja", None)
            for key in ("compet1", "compet2", "compet3"):
                if legacy_margin not in (None, ""):
                    item[key] = str(legacy_margin)
                elif item.get(key) in (None, ""):
                    # Los márgenes se dejan sin rellenar: el cálculo usa la
                    # tasa general cuando el campo está vacío.
                    item[key] = ""
                else:
                    item[key] = str(item[key])
            normalized.append(item)
        return normalized

    # Datos para el selector de embarques (gastos redondeados a 2 dec. para mostrar).
    embarques_ui = {
        key: {"nombre": e["nombre"], "tasas": e["tasas"],
              "gastos": {k: _q2(v) for k, v in e["gastos"].items()},
              "items": e["items"]}
        for key, e in embarques.items()
    }
    sel = request.GET.get("embarque", "roma")
    if sel not in embarques and sel != "nuevo":
        sel = "roma"
    if sel == "nuevo":
        # Embarque en blanco: tasas generales, gastos en 0 y una fila vacía.
        defaults_tasas = {"seguro_pct": "1", "advalorem_pct": "20",
                          "fondinfa_pct": "0.5", "iva_pct": "15", "iva_pvp_pct": "15"}
        defaults_gastos = {k: "0" for k in
                           ("flete_intl", "flete_local", "gasto_admin", "bodegaje",
                            "devolucion", "comision_banco", "descarga", "agente",
                            "otros_unit")}
        defaults_items = [{"nombre": "", "cant": "1", "valor_unit": "",
                           "compet1": "", "compet2": "", "compet3": "",
                           "seguro_pct": "", "advalorem_pct": "",
                           "fondinfa_pct": "", "iva_pct": ""}]
    else:
        seed = embarques[sel]
        defaults_tasas = dict(seed["tasas"])
        defaults_gastos = {k: _q2(v) for k, v in seed["gastos"].items()}
        defaults_items = _pricing_items(seed["items"]) or [{
            "nombre": "", "cant": "1", "valor_unit": "",
            "compet1": "", "compet2": "", "compet3": "",
            "seguro_pct": "", "advalorem_pct": "", "fondinfa_pct": "", "iva_pct": "",
        }]
    override_keys = ("seguro_pct", "advalorem_pct", "fondinfa_pct", "iva_pct")

    if request.method == "POST":
        tasas = {k: _num(request.POST.get(k, v), v) for k, v in defaults_tasas.items()}
        gastos = {k: _num(request.POST.get(k, v), v) for k, v in defaults_gastos.items()}
        nombres = request.POST.getlist("nombre")
        posted = {k: request.POST.getlist(k) for k in
                  ("cant", "valor_unit", "compet1", "compet2", "compet3")
                  + tuple(f"ov_{k}" for k in override_keys)}

        def _raw(key, i, d=""):
            lst = posted.get(key, [])
            if key.startswith("ov_"):
                lst = request.POST.getlist(key)
            return lst[i] if i < len(lst) else d

        def _ov(key, i):
            s = _raw(f"ov_{key}", i, "").strip()
            return s if s != "" else None

        def _margen(key, i):
            """El margen se guarda tal cual, pero solo si es numérico."""
            s = _raw(key, i).strip()
            if s == "":
                return ""
            try:
                float(s.replace(",", "."))
            except ValueError:
                return ""
            return s

        items = []
        for i, nombre in enumerate(nombres):
            if not (nombre.strip() or _raw("cant", i).strip() or _raw("valor_unit", i).strip()):
                continue
            items.append({
                "nombre": nombre.strip() or f"Producto {i+1}",
                "cant": _num(_raw("cant", i), 0),
                "valor_unit": _num(_raw("valor_unit", i), 0),
                "compet1": _margen("compet1", i),
                "compet2": _margen("compet2", i),
                "compet3": _margen("compet3", i),
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
                      "valor_unit": _rl("valor_unit", i),
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
                       "embarques_ui": embarques_ui, "embarque_sel": sel,
                       "embarques_opciones": embarques_ui.items(),
                       "embarque_nombre": ("Nuevo embarque" if sel == "nuevo"
                                           else embarques[sel]["nombre"] if sel in embarques else "")})
    rule = TaxRule.get_active()
    return render(request, "panel/calculadora.html",
                  {"tasas": defaults_tasas, "gastos": defaults_gastos,
                   "items_raw": defaults_items, "calc": None, "rule": rule,
                   "embarques_ui": embarques_ui, "embarque_sel": sel,
                   "embarques_opciones": embarques_ui.items(),
                   "embarque_nombre": ("Nuevo embarque" if sel == "nuevo"
                                       else embarques[sel]["nombre"] if sel in embarques else "")})


@seccion_requerida("calculadora")
def calculadora_guardar(request):
    import json
    from decimal import Decimal, InvalidOperation
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"error": "Solo POST."}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "JSON inválido."}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Los datos del embarque no son válidos."}, status=400)

    def clean_number(value, label, default="0", allow_blank=False):
        raw = str(value if value is not None else "").strip()
        if not raw and allow_blank:
            return ""
        raw = raw or str(default)
        try:
            number = Decimal(raw.replace(",", "."))
        except (InvalidOperation, ValueError):
            raise ValueError(f"{label} debe ser numérico.") from None
        if not number.is_finite() or number < 0:
            raise ValueError(f"{label} no puede ser negativo.")
        return format(number, "f")

    try:
        rates_input = payload.get("tasas", {})
        expenses_input = payload.get("gastos", {})
        if not isinstance(rates_input, dict) or not isinstance(expenses_input, dict):
            raise ValueError("Las tasas y los gastos no son válidos.")
        rate_defaults = {"seguro_pct": "1", "advalorem_pct": "20",
                         "fondinfa_pct": "0.5", "iva_pct": "15", "iva_pvp_pct": "15"}
        expense_defaults = {"flete_intl": "0", "flete_local": "0", "gasto_admin": "0",
                            "bodegaje": "0", "devolucion": "0", "comision_banco": "0",
                            "descarga": "0", "agente": "0", "otros_unit": "0"}
        tasas = {key: clean_number(rates_input.get(key), key, default)
                 for key, default in rate_defaults.items()}
        gastos = {key: clean_number(expenses_input.get(key), key, default)
                  for key, default in expense_defaults.items()}
        items_input = payload.get("items", [])
        if not isinstance(items_input, list) or len(items_input) > 500:
            raise ValueError("El embarque admite hasta 500 productos.")
        items = []
        numeric_defaults = {"cant": "0", "valor_unit": "",
                            "compet1": "", "compet2": "", "compet3": "",
                            "seguro_pct": "", "advalorem_pct": "", "fondinfa_pct": "",
                            "iva_pct": ""}
        for row_number, item in enumerate(items_input, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Los datos del producto {row_number} no son válidos.")
            name = str(item.get("nombre") or "").strip()[:200]
            clean_item = {"nombre": name}
            for key, default in numeric_defaults.items():
                clean_item[key] = clean_number(item.get(key), f"{key} del producto {row_number}",
                                               default, allow_blank=default == "")
            items.append(clean_item)
        name = str(payload.get("nombre") or "").strip()[:100]
        if not name:
            raise ValueError("Ingrese un nombre para el embarque.")
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    key = str(payload.get("embarque_key") or "")
    numero = key[9:] if key.startswith("guardado-") else ""
    if numero.isascii() and numero.isdigit():
        shipment = get_object_or_404(SavedShipment, pk=int(numero))
        shipment.nombre = name
        shipment.tasas = tasas
        shipment.gastos = gastos
        shipment.items = items
        shipment.save()
    else:
        shipment = SavedShipment.objects.create(
            nombre=name, tasas=tasas, gastos=gastos, items=items)
    return JsonResponse({
        "key": f"guardado-{shipment.pk}",
        "nombre": shipment.nombre,
        "message": "Embarque guardado correctamente.",
    })


def _embarque_guardado(payload):
    """Devuelve el SavedShipment de la clave 'guardado-<id>' o un error."""
    from django.http import Http404

    key = str(payload.get("embarque_key") or "")
    numero = key[9:] if key.startswith("guardado-") else ""
    if not (numero.isascii() and numero.isdigit()):
        raise ValueError("Solo se pueden modificar los embarques guardados.")
    try:
        return get_object_or_404(SavedShipment, pk=int(numero)), key
    except Http404:
        raise ValueError("El embarque no existe.") from None


@seccion_requerida("calculadora")
def calculadora_renombrar(request):
    """Cambia el nombre de un embarque guardado (sin tocar sus datos)."""
    import json
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"error": "Solo POST."}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "JSON inválido."}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Los datos no son válidos."}, status=400)
    nombre = str(payload.get("nombre") or "").strip()[:100]
    if not nombre:
        return JsonResponse({"error": "Ingrese un nombre para el embarque."}, status=400)
    try:
        shipment, key = _embarque_guardado(payload)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    shipment.nombre = nombre
    shipment.save()
    return JsonResponse({
        "key": key,
        "nombre": shipment.nombre,
        "message": "Embarque renombrado correctamente.",
    })


@seccion_requerida("calculadora")
def calculadora_eliminar(request):
    """Elimina un embarque guardado."""
    import json
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"error": "Solo POST."}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "JSON inválido."}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Los datos no son válidos."}, status=400)
    try:
        shipment, key = _embarque_guardado(payload)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    nombre = shipment.nombre
    shipment.delete()
    return JsonResponse({
        "key": key,
        "message": f"Embarque «{nombre}» eliminado.",
    })


@seccion_requerida("calculadora")
def calculadora_plantilla(request):
    from django.http import HttpResponse

    if request.method != "GET":
        return HttpResponse("Solo GET.", status=405)
    from calculator.excel_templates import build_plantilla_xlsx

    response = HttpResponse(
        build_plantilla_xlsx(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="plantilla-embarque.xlsx"'
    return response


@seccion_requerida("calculadora")
def calculadora_importar(request):
    from django.http import JsonResponse
    from calculator.excel_templates import read_plantilla_xlsx

    if request.method != "POST":
        return JsonResponse({"error": "Solo POST."}, status=405)
    upload = request.FILES.get("archivo")
    if upload is None:
        return JsonResponse({"error": "Seleccione una plantilla Excel."}, status=400)
    if upload.size > 5 * 1024 * 1024:
        return JsonResponse({"error": "El archivo no puede superar 5 MB."}, status=400)
    if not upload.name.lower().endswith(".xlsx"):
        return JsonResponse({"error": "Suba un archivo .xlsx."}, status=400)
    try:
        imported = read_plantilla_xlsx(upload)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(imported)


@seccion_requerida("calculadora")
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
        item = {
            "nombre": nombre or f"Producto {i + 1}",
            "cant": _num(it.get("cant"), 0),
            "valor_unit": _num(it.get("valor_unit"), 0),
            "compet1": _num(it.get("compet1"), 35),
            "compet2": _num(it.get("compet2"), 35),
            "compet3": _num(it.get("compet3"), 35),
            "seguro_pct": _ov(it.get("seguro_pct")),
            "advalorem_pct": _ov(it.get("advalorem_pct")),
            "fondinfa_pct": _ov(it.get("fondinfa_pct")),
            "iva_pct": _ov(it.get("iva_pct")),
        }
        if it.get("margen_pct") not in (None, ""):
            item["margen_pct"] = _num(it.get("margen_pct"), 35)
        items.append(item)
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


@staff_only
def colaboradores(request):
    perfiles = (AccesoPanel.objects.select_related("usuario")
                .order_by("usuario__username"))
    return render(request, "panel/colaboradores.html", {"colaboradores": perfiles})


@staff_only
def colaborador_editar(request, pk=None):
    perfil = get_object_or_404(AccesoPanel, pk=pk) if pk else None
    form = ColaboradorForm(request.POST or None, colaborador=perfil)
    if request.method == "POST" and form.is_valid():
        perfil = form.save()
        return redirect("panel:colaboradores")
    return render(request, "panel/colaborador_form.html",
                  {"form": form, "obj": perfil})


@staff_only
def colaborador_estado(request, pk):
    perfil = get_object_or_404(AccesoPanel, pk=pk)
    if request.method == "POST":
        perfil.activo = not perfil.activo
        perfil.save(update_fields=["activo", "actualizado"])
        perfil.usuario.is_active = perfil.activo
        perfil.usuario.save(update_fields=["is_active"])
    return redirect("panel:colaboradores")


@staff_only
def colaborador_eliminar(request, pk):
    perfil = get_object_or_404(AccesoPanel, pk=pk)
    if request.method == "POST":
        usuario = perfil.usuario
        usuario.delete()
        return redirect("panel:colaboradores")
    return render(request, "panel/colaborador_eliminar.html", {"obj": perfil})


def salir(request):
    logout(request)
    return redirect("core:home")

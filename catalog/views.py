from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product, TipoProducto


def filtrar(request):
    qs = (Product.objects.filter(activo=True)
          .select_related("categoria", "tipo")
          .prefetch_related("colores_producto__color"))
    q = (request.GET.get("q") or "").strip()
    categoria = request.GET.get("categoria", "")
    tipo = request.GET.get("tipo", "")
    stock = request.GET.get("stock", "")
    orden = request.GET.get("orden", "")
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(sku__icontains=q)
                       | Q(categoria__nombre__icontains=q)
                       | Q(tipo__nombre__icontains=q))
    if categoria:
        qs = qs.filter(categoria__slug=categoria)
    if tipo:
        qs = qs.filter(tipo__slug=tipo)
    if stock == "si":
        qs = qs.filter(en_stock=True, stock_cantidad__gt=0)
    if orden == "precio_asc":
        qs = qs.order_by("precio_mayor")
    elif orden == "precio_desc":
        qs = qs.order_by("-precio_mayor")
    elif orden == "nombre":
        qs = qs.order_by("nombre")
    else:
        qs = qs.order_by("-destacado", "categoria__orden", "nombre")
    return qs, q, categoria, tipo, stock, orden


def detalle(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("categoria", "tipo")
        .prefetch_related("imagenes", "colores_producto__color"),
        slug=slug, activo=True)
    relacionados = (Product.objects.filter(activo=True, categoria=product.categoria)
                    .exclude(pk=product.pk)[:4])
    ordenados = list(Product.objects.filter(activo=True)
                     .order_by("categoria__orden", "nombre").values_list("slug", flat=True))
    idx = ordenados.index(product.slug)
    anterior = ordenados[idx - 1] if idx > 0 else None
    siguiente = ordenados[idx + 1] if idx < len(ordenados) - 1 else None
    galeria = [f for f in product.imagenes.all() if f.imagen_src]
    return render(request, "catalog/detalle.html",
                  {"product": product, "relacionados": relacionados,
                   "galeria": galeria,
                   "anterior": anterior, "siguiente": siguiente})


def catalogo(request):
    productos, q, categoria, tipo, stock, orden = filtrar(request)
    # En el sitio público solo las categorías que tienen productos activos.
    categorias = (Category.objects.filter(productos__activo=True)
                  .distinct().order_by("orden", "nombre"))
    # Los tipos van agrupados por línea; si hay línea elegida, solo los suyos.
    tipos_qs = (TipoProducto.objects.select_related("categoria")
                .order_by("categoria__orden", "orden", "nombre"))
    if categoria:
        tipos_qs = tipos_qs.filter(Q(categoria__slug=categoria) | Q(slug=tipo))
    grupos = {}
    for t in tipos_qs:
        etiqueta = t.categoria.nombre if t.categoria else "Otros"
        grupos.setdefault(etiqueta, {"slug": t.categoria.slug if t.categoria else "",
                                     "tipos": []})
        grupos[etiqueta]["tipos"].append((t.slug, t.nombre))
    tipos_agrupados = [{"etiqueta": etiqueta, "slug": datos["slug"],
                        "tipos": datos["tipos"]} for etiqueta, datos in grupos.items()]
    ctx = {"productos": productos, "categorias": categorias,
           "tipos": TipoProducto.objects.filter(productos__activo=True).distinct(),
           "tipos_agrupados": tipos_agrupados,
           "q": q, "categoria": categoria, "tipo": tipo,
           "stock": stock, "orden": orden}
    if getattr(request, "htmx", False):
        return render(request, "catalog/_grid.html", ctx)
    return render(request, "catalog/catalogo.html", ctx)

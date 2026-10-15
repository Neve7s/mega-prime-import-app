from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product


def filtrar(request):
    qs = Product.objects.filter(activo=True).select_related("categoria")
    q = (request.GET.get("q") or "").strip()
    categoria = request.GET.get("categoria", "")
    stock = request.GET.get("stock", "")
    orden = request.GET.get("orden", "")
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(sku__icontains=q))
    if categoria:
        qs = qs.filter(categoria__slug=categoria)
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
    return qs, q, categoria, stock, orden


def detalle(request, slug):
    product = get_object_or_404(Product, slug=slug, activo=True)
    relacionados = (Product.objects.filter(activo=True, categoria=product.categoria)
                    .exclude(pk=product.pk)[:4])
    return render(request, "catalog/detalle.html",
                  {"product": product, "relacionados": relacionados})


def catalogo(request):
    productos, q, categoria, stock, orden = filtrar(request)
    ctx = {"productos": productos, "categorias": Category.objects.all(),
           "q": q, "categoria": categoria, "stock": stock, "orden": orden}
    if getattr(request, "htmx", False):
        return render(request, "catalog/_grid.html", ctx)
    return render(request, "catalog/catalogo.html", ctx)

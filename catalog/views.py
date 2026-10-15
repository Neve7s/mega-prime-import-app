from django.shortcuts import get_object_or_404, render

from .models import Product


def detalle(request, slug):
    product = get_object_or_404(Product, slug=slug, activo=True)
    relacionados = (Product.objects.filter(activo=True, categoria=product.categoria)
                    .exclude(pk=product.pk)[:4])
    return render(request, "catalog/detalle.html",
                  {"product": product, "relacionados": relacionados})

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from catalog.models import Category, Product


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "core/home.html", {
        "productos": Product.objects.filter(activo=True).select_related("categoria"),
        "categorias": Category.objects.all(),
    })

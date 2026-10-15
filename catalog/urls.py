from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.catalogo, name="catalogo"),
    path("producto/<slug:slug>/", views.detalle, name="detalle"),
]

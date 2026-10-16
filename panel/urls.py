from django.urls import path

from . import views
from .auth import PanelLoginView

app_name = "panel"

urlpatterns = [
    path("login/", PanelLoginView.as_view(), name="login"),
    path("salir/", views.salir, name="salir"),
    path("", views.dashboard, name="dashboard"),
    path("productos/", views.productos, name="productos"),
    path("productos/nuevo/", views.producto_editar, name="producto_nuevo"),
    path("productos/<int:pk>/", views.producto_editar, name="producto_editar"),
    path("categorias/", views.categorias, name="categorias"),
    path("categorias/nueva/", views.categoria_editar, name="categoria_nueva"),
    path("categorias/<int:pk>/", views.categoria_editar, name="categoria_editar"),
    path("categorias/<int:pk>/eliminar/", views.categoria_eliminar, name="categoria_eliminar"),
    path("tipos/", views.tipos, name="tipos"),
    path("tipos/nuevo/", views.tipo_editar, name="tipo_nuevo"),
    path("tipos/<int:pk>/", views.tipo_editar, name="tipo_editar"),
    path("tipos/<int:pk>/eliminar/", views.tipo_eliminar, name="tipo_eliminar"),
    path("pedidos/", views.pedidos, name="pedidos"),
    path("pedidos/<str:codigo>/", views.pedido_detalle, name="pedido_detalle"),
    path("codigos/", views.codigos, name="codigos"),
    path("codigos/nuevo/", views.codigo_crear, name="codigo_crear"),
    path("codigos/<str:codigo>/", views.codigo_detalle, name="codigo_detalle"),
    path("ajustes/", views.ajustes, name="ajustes"),
    path("calculadora/", views.calculadora, name="calculadora"),
    path("calculadora/reporte/", views.calculadora_reporte, name="calculadora_reporte"),
    path("calculadora/guardar/", views.calculadora_guardar, name="calculadora_guardar"),
    path("calculadora/plantilla/", views.calculadora_plantilla, name="calculadora_plantilla"),
    path("calculadora/importar/", views.calculadora_importar, name="calculadora_importar"),
]

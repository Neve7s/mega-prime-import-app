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
    path("pedidos/", views.pedidos, name="pedidos"),
    path("pedidos/<str:codigo>/", views.pedido_detalle, name="pedido_detalle"),
    path("codigos/", views.codigos, name="codigos"),
    path("codigos/nuevo/", views.codigo_crear, name="codigo_crear"),
    path("codigos/<str:codigo>/", views.codigo_detalle, name="codigo_detalle"),
    path("ajustes/", views.ajustes, name="ajustes"),
    path("calculadora/", views.calculadora, name="calculadora"),
    path("calculadora/reporte/", views.calculadora_reporte, name="calculadora_reporte"),
]

from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.carrito, name="carrito"),
    path("checkout/", views.checkout, name="checkout"),
    path("confirmacion/<str:codigo>/", views.confirmacion, name="confirmacion"),
]

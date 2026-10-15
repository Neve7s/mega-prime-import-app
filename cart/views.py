import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Order
from .services import crear_pedido, validar_codigo


def carrito(request):
    return render(request, "cart/checkout.html")


@require_POST
def checkout(request):
    """Recibe {datos, items} del carrito localStorage, valida código y crea el pedido."""
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Solicitud no válida."}, status=400)
    sale, err = validar_codigo(payload.get("codigo", ""))
    if not sale:
        return JsonResponse({"ok": False, "error": err}, status=400)
    pedido, err = crear_pedido(payload.get("datos", {}), payload.get("items", []), sale)
    if not pedido:
        return JsonResponse({"ok": False, "error": err}, status=400)
    return JsonResponse({"ok": True, "pedido": pedido.codigo,
                         "confirm_url": f"/carrito/confirmacion/{pedido.codigo}/"})


def confirmacion(request, codigo):
    pedido = get_object_or_404(Order, codigo=codigo)
    return render(request, "cart/confirmacion.html", {"pedido": pedido})

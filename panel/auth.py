from functools import wraps

from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .models import AccesoPanel

SECCIONES = (
    ("calculadora", "Calculadora"),
    ("pedidos", "Punto de venta"),
    ("codigos", "Códigos WhatsApp"),
    ("productos", "Productos"),
)

SECCIONES_URL = {
    "calculadora": "panel:calculadora",
    "pedidos": "panel:pedidos",
    "codigos": "panel:codigos",
    "productos": "panel:productos",
}


def es_dueno(user):
    return bool(getattr(user, "is_authenticated", False)
                and (user.is_superuser or user.is_staff))


def acceso(user):
    if not getattr(user, "is_authenticated", False) or es_dueno(user):
        return None
    try:
        perfil = user.acceso_panel
    except AccesoPanel.DoesNotExist:
        return None
    return perfil if perfil.activo else None


def tiene_panel(user):
    return es_dueno(user) or acceso(user) is not None


def puede(user, seccion):
    if es_dueno(user):
        return True
    perfil = acceso(user)
    return bool(perfil and getattr(perfil, seccion, False))


def primera_seccion(user):
    perfil = acceso(user)
    if not perfil:
        return ""
    for clave, _ in SECCIONES:
        if getattr(perfil, clave, False):
            return clave
    return ""


def seccion_requerida(seccion):
    def decorador(view):
        @wraps(view)
        def inner(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("panel:login")
            if not tiene_panel(request.user):
                return redirect("panel:login")
            if not puede(request.user, seccion):
                return render(request, "panel/sin_acceso.html",
                              {"seccion": dict(SECCIONES).get(seccion, seccion)},
                              status=403)
            return view(request, *args, **kwargs)

        return inner

    return decorador


def staff_only(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("panel:login")
        if not es_dueno(request.user):
            return redirect("panel:login")
        return view(request, *args, **kwargs)

    return inner


class PanelLoginView(LoginView):
    template_name = "panel/login.html"

    def form_valid(self, form):
        user = form.get_user()
        if not tiene_panel(user):
            form.add_error(None, "Esta cuenta no tiene acceso al panel.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return "/webadmin/"

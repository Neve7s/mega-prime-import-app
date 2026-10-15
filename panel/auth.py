from functools import wraps

from django.contrib.auth.views import LoginView
from django.shortcuts import redirect


def staff_only(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("panel:login")
        if not (request.user.is_staff or request.user.is_superuser):
            return redirect("panel:login")
        return view(request, *args, **kwargs)

    return inner


class PanelLoginView(LoginView):
    template_name = "panel/login.html"

    def form_valid(self, form):
        user = form.get_user()
        if not (user.is_staff or user.is_superuser):
            form.add_error(None, "Esta cuenta no tiene acceso al panel.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return "/panel/"

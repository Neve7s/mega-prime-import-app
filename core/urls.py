from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("sitemap.xml", views.sitemap, name="sitemap"),
    path("robots.txt", views.robots, name="robots"),
    path("privacidad/", views.legal_page, {"page": "privacidad"}, name="privacidad"),
    path("terminos-y-condiciones/", views.legal_page, {"page": "terminos"}, name="terminos"),
    path("cookies/", views.legal_page, {"page": "cookies"}, name="cookies"),
    path("libro-de-reclamaciones/", views.libro_reclamaciones, name="libro_reclamaciones"),
    path("", views.home, name="home"),
]

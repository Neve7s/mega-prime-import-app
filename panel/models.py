from django.conf import settings
from django.db import models


class AccesoPanel(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acceso_panel",
    )
    calculadora = models.BooleanField(default=False)
    pedidos = models.BooleanField(default=False)
    codigos = models.BooleanField(default=False)
    productos = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "acceso al panel"
        verbose_name_plural = "accesos al panel"
        ordering = ["usuario__username"]

    def __str__(self):
        return "Acceso de %s" % self.usuario.username

    def secciones(self):
        from .auth import SECCIONES

        return [etiqueta for clave, etiqueta in SECCIONES if getattr(self, clave)]

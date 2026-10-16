from django.db import models


class HSCode(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.CharField(max_length=255)
    ad_valorem_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Arancel ad-valorem % sobre CIF. Ajustar según arancel SENAE vigente.",
    )

    class Meta:
        ordering = ["codigo"]
        verbose_name = "Partida arancelaria"
        verbose_name_plural = "Partidas arancelarias"

    def __str__(self) -> str:
        return f"{self.codigo} ({self.ad_valorem_pct}%)"


class TaxRule(models.Model):
    nombre = models.CharField(max_length=120)
    fodinfa_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.50)
    iva_pct = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)
    isd_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tasa_control_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    vigencia_desde = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-vigencia_desde", "-id"]
        verbose_name = "Regla de impuestos"
        verbose_name_plural = "Reglas de impuestos"

    def __str__(self) -> str:
        return f"{self.nombre} (IVA {self.iva_pct}%)"

    @classmethod
    def get_active(cls) -> "TaxRule | None":
        return cls.objects.filter(activo=True).first()


class QuoteLog(models.Model):
    user = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="quotes"
    )
    session_key = models.CharField(max_length=40, blank=True)
    valor_fob = models.DecimalField(max_digits=12, decimal_places=2)
    flete = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    seguro = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hs_code = models.ForeignKey(HSCode, null=True, blank=True, on_delete=models.SET_NULL)
    ad_valorem_calc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fodinfa_calc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    base_iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva_calc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Cotización calculadora"
        verbose_name_plural = "Cotizaciones calculadora"


class SavedShipment(models.Model):
    nombre = models.CharField(max_length=100)
    tasas = models.JSONField(default=dict)
    gastos = models.JSONField(default=dict)
    items = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        verbose_name = "Embarque guardado"
        verbose_name_plural = "Embarques guardados"

    def __str__(self) -> str:
        return self.nombre

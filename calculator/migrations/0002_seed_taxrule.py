# Semilla idempotente: crea la regla general solo si no existe una con ese nombre.
# No toca ni borra ningún otro dato (seguro correrlo en prod con migrate).
from django.db import migrations


def seed_taxrule(apps, schema_editor):
    TaxRule = apps.get_model("calculator", "TaxRule")
    TaxRule.objects.get_or_create(
        nombre="Régimen general 2026",
        defaults={"fodinfa_pct": "0.50", "iva_pct": "15.00",
                  "isd_pct": "0", "tasa_control_usd": "0", "activo": True},
    )


def unseed_taxrule(apps, schema_editor):
    apps.get_model("calculator", "TaxRule").objects.filter(
        nombre="Régimen general 2026").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("calculator", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_taxrule, unseed_taxrule),
    ]

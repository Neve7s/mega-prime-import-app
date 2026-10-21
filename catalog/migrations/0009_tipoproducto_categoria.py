"""El tipo de producto pasa a saber su categoría.

Así, al elegir el tipo en el panel la categoría se rellena sola (una sola
decisión para quien da de alta el producto).
"""

from django.db import migrations, models
import django.db.models.deletion

# Tipo -> categoría final (las mismas seis del catálogo)
TIPOS_CATEGORIA = {
    "teja-espanola": "tejas-y-cubiertas",
    "teja-roma": "tejas-y-cubiertas",
    "teja-trapezoidal": "tejas-y-cubiertas",
    "teja-pvc": "tejas-y-cubiertas",
    "cielo-razo": "cielorrasos-y-techos",
    "policarbonato-alveolar": "cielorrasos-y-techos",
    "spc": "pisos",
    "porcelanato": "pisos",
    "wall-panel-wpc": "revestimientos-y-paneles",
    "paneles-decorativos": "revestimientos-y-paneles",
    "cumbreros": "accesorios-y-materiales",
    "tornilleria": "accesorios-y-materiales",
    "perfiles": "accesorios-y-materiales",
    "selladores": "accesorios-y-materiales",
    "cortadoras": "herramientas-y-equipos",
}


def asigna_categorias(apps, schema_editor):
    TipoProducto = apps.get_model("catalog", "TipoProducto")
    Category = apps.get_model("catalog", "Category")
    for slug_tipo, slug_categoria in TIPOS_CATEGORIA.items():
        tipo = TipoProducto.objects.filter(slug=slug_tipo).first()
        categoria = Category.objects.filter(slug=slug_categoria).first()
        if tipo is None or categoria is None:
            continue
        tipo.categoria = categoria
        tipo.save(update_fields=["categoria"])


def revierte(apps, schema_editor):
    apps.get_model("catalog", "TipoProducto").objects.update(categoria=None)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_consolida_categorias'),
    ]

    operations = [
        migrations.AddField(
            model_name='tipoproducto',
            name='categoria',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tipos', to='catalog.category'),
        ),
        migrations.RunPython(asigna_categorias, revierte),
    ]

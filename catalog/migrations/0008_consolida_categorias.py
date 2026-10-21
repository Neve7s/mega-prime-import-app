"""Consolida las categorías del catálogo en seis ejes claros.

Antes convivían las categorías viejas (Tejas, Accesorios, Porcelanatos,
Paneles y Decor, Herramientas Pro) con las nuevas del catálogo importado
(Tejas y Cubiertas, Cielorrasos y Techos, Pisos, …). Aquí se dejan solo las
seis definitivas, moviendo los productos a su categoría final y completando
el tipo de producto de los que estaban sin tipo.
"""

from django.db import migrations

CATEGORIAS_FINALES = [
    ("Tejas y Cubiertas", "tejas-y-cubiertas",
     "Tejas y cubiertas: perfil español, romano y trapezoidal.", 1),
    ("Cielorrasos y Techos", "cielorrasos-y-techos",
     "Cielorrasos y placas de policarbonato para iluminación natural.", 2),
    ("Pisos", "pisos", "Pisos de alto tráfico: SPC y porcelanato.", 3),
    ("Revestimientos y Paneles", "revestimientos-y-paneles",
     "Paneles decorativos WPC y acústicos para revestimiento interior.", 4),
    ("Accesorios y Materiales", "accesorios-y-materiales",
     "Cumbreros, tornillería, selladores y perfiles.", 5),
    ("Herramientas y Equipos", "herramientas-y-equipos",
     "Herramientas y maquinaria para corte e instalación.", 6),
]

# Categoría vieja -> categoría final
FUSIONES = {
    "tejas": "tejas-y-cubiertas",
    "porcelanato": "pisos",
    "interiorismo": "revestimientos-y-paneles",
    "paneles-y-decor": "revestimientos-y-paneles",
    "accesorios": "accesorios-y-materiales",
    "maquinaria": "herramientas-y-equipos",
    "herramientas-pro": "herramientas-y-equipos",
    "herramientas": "herramientas-y-equipos",
}

# Tipo de producto para los productos que venían sin tipo
TIPOS = {
    "pisos": ("Porcelanato", "porcelanato", "Revestimientos porcelánicos."),
    "revestimientos-y-paneles": ("Paneles Decorativos", "paneles-decorativos",
                                 "Paneles acústicos y decorativos."),
    "herramientas-y-equipos": ("Cortadoras", "cortadoras",
                               "Cortadoras y maquinaria de corte."),
}


def consolida(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    TipoProducto = apps.get_model("catalog", "TipoProducto")

    for nombre, slug, descripcion, orden in CATEGORIAS_FINALES:
        Category.objects.update_or_create(
            slug=slug,
            defaults={"nombre": nombre, "descripcion": descripcion, "orden": orden})

    for slug_viejo, slug_final in FUSIONES.items():
        vieja = Category.objects.filter(slug=slug_viejo).first()
        if vieja is None:
            continue
        final = Category.objects.filter(slug=slug_final).first()
        if final is None:
            continue
        Product.objects.filter(categoria=vieja).update(categoria=final)
        if vieja.pk != final.pk:
            vieja.delete()

    # Tipo de producto para los que estaban sin tipo
    for slug_categoria, (nombre_tipo, slug_tipo, descripcion) in TIPOS.items():
        categoria = Category.objects.filter(slug=slug_categoria).first()
        if categoria is None:
            continue
        tipo, _ = TipoProducto.objects.get_or_create(
            slug=slug_tipo,
            defaults={"nombre": nombre_tipo, "descripcion": descripcion,
                      "orden": 90})
        Product.objects.filter(categoria=categoria, tipo__isnull=True).update(tipo=tipo)


def revierte(apps, schema_editor):
    """No deshace: mover productos entre categorías no tiene vuelta atrás."""
    Category = apps.get_model("catalog", "Category")
    Category.objects.filter(slug__in=[c[1] for c in CATEGORIAS_FINALES]).update(
        orden=0)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0007_remove_product_colores'),
    ]

    operations = [
        migrations.RunPython(consolida, revierte),
    ]

# Semilla idempotente de líneas y tipos (estructura del negocio, como la
# referencia Megacubiertas: familias de tejas + accesorios). No toca ni
# borra ningún otro dato.
from django.db import migrations


CATEGORIAS = [
    ("Tejas", "tejas", "Cubiertas: teja Roma, Española y PVC.", 1),
    ("Accesorios", "accesorios", "Cumbreros, tornillería, perfiles y selladores.", 2),
]

TIPOS = [
    ("Teja Roma", "teja-roma", "Tejas perfil Roma.", 1),
    ("Teja Española", "teja-espanola", "Tejas perfil español.", 2),
    ("Teja PVC", "teja-pvc", "Tejas de PVC.", 3),
    ("Cumbreros", "cumbreros", "Remates superiores para cubiertas.", 4),
    ("Tornillería", "tornilleria", "Fijaciones y tornillos.", 5),
    ("Perfiles", "perfiles", "Perfiles de aluminio y PVC.", 6),
    ("Selladores", "selladores", "Selladores y cintas.", 7),
]


def seed(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    TipoProducto = apps.get_model("catalog", "TipoProducto")
    for nombre, slug, desc, orden in CATEGORIAS:
        Category.objects.get_or_create(
            slug=slug, defaults={"nombre": nombre, "descripcion": desc,
                                 "orden": orden})
    for nombre, slug, desc, orden in TIPOS:
        TipoProducto.objects.get_or_create(
            slug=slug, defaults={"nombre": nombre, "descripcion": desc,
                                 "orden": orden})


def unseed(apps, schema_editor):
    apps.get_model("catalog", "Category").objects.filter(
        slug__in=[c[1] for c in CATEGORIAS]).delete()
    apps.get_model("catalog", "TipoProducto").objects.filter(
        slug__in=[t[1] for t in TIPOS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_tipoproducto_product_badge_product_tipo"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]

import django.db.models.deletion
from django.db import migrations, models
from django.utils.text import slugify

# Paleta base del catálogo: los colores que se repiten entre productos.
PALETA = [
    ("Blanco", "#F5F5F4"),
    ("Negro", "#1F2937"),
    ("Gris", "#9CA3AF"),
    ("Plomo", "#6B7280"),
    ("Terracota", "#B4532A"),
    ("Marrón", "#7A4A24"),
    ("Rojo", "#A32020"),
    ("Naranja", "#E2762B"),
    ("Amarillo", "#EAB308"),
    ("Verde", "#2F6B3A"),
    ("Azul", "#1F4E79"),
    ("Celeste", "#7DD3FC"),
    ("Bronce", "#8C6A4A"),
    ("Beige", "#E7D8C9"),
    ("Blanco Opal", "#F0F4F7"),
    ("Transparente", "#E8F1F5"),
]


def _slug_color(nombre, usados):
    base = slugify(nombre)[:40] or "color"
    candidato = base
    numero = 2
    while candidato in usados:
        candidato = f"{base}-{numero}"
        numero += 1
    usados.add(candidato)
    return candidato


def migra_colores_json(apps, schema_editor):
    """El JSON `colores` pasa a la tabla Color/ProductColor."""
    Product = apps.get_model("catalog", "Product")
    Color = apps.get_model("catalog", "Color")
    ProductColor = apps.get_model("catalog", "ProductColor")

    usados = set(Color.objects.values_list("slug", flat=True))
    for producto in Product.objects.all():
        for orden, color in enumerate(producto.colores or []):
            if not isinstance(color, dict):
                continue
            nombre = str(color.get("nombre") or "").strip()
            if not nombre:
                continue
            hex_color = str(color.get("hex") or "").strip()
            # Un color con el mismo nombre es el mismo color: se reutiliza.
            tonalidad = Color.objects.filter(nombre__iexact=nombre).first()
            if tonalidad is None:
                slug = _slug_color(nombre, usados)
                tonalidad = Color.objects.create(
                    slug=slug, nombre=nombre[:40], hex=(hex_color or "#9CA3AF")[:7],
                    orden=99)
            ProductColor.objects.get_or_create(
                producto=producto, color=tonalidad, rol="",
                defaults={"orden": orden})


def revierte_colores_json(apps, schema_editor):
    """Deja la tabla vacía antes de borrarla.

    En PostgreSQL los triggers de las claves foráneas quedan 'pendientes'
    hasta el commit y bloquean el DROP TABLE: hay que cerrarlos antes.
    """
    from django.db import connection

    ProductColor = apps.get_model("catalog", "ProductColor")
    ProductColor.objects.all().delete()
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def siembra_paleta(apps, schema_editor):
    """Crea la paleta de colores usada por el panel.

    Si el color ya existe (lo creó la migración del JSON), se reaprovecha:
    solo se le pone su tono y su posición en la paleta.
    """
    Color = apps.get_model("catalog", "Color")
    usados = set(Color.objects.values_list("slug", flat=True))
    for orden, (nombre, hex_color) in enumerate(PALETA, start=1):
        existente = Color.objects.filter(nombre__iexact=nombre).first()
        if existente is not None:
            existente.hex = hex_color
            existente.orden = orden
            existente.save(update_fields=["hex", "orden"])
            continue
        slug = _slug_color(nombre, usados)
        Color.objects.create(
            slug=slug, nombre=nombre, hex=hex_color, orden=orden)


def revierte_paleta(apps, schema_editor):
    """Quita solo los colores de la paleta que nadie usa."""
    Color = apps.get_model("catalog", "Color")
    nombres = [nombre for nombre, _ in PALETA]
    Color.objects.filter(nombre__in=nombres, usos__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_product_caracteristicas_product_colores'),
    ]

    operations = [
        migrations.CreateModel(
            name='Color',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=40)),
                ('slug', models.SlugField(max_length=40, unique=True)),
                ('hex', models.CharField(default='#000000', max_length=7)),
                ('orden', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Color',
                'verbose_name_plural': 'Colores',
                'ordering': ['orden', 'nombre'],
            },
        ),
        migrations.CreateModel(
            name='ProductColor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('orden', models.PositiveIntegerField(default=0)),
                ('rol', models.CharField(blank=True, choices=[('exterior', 'Exterior'), ('interior', 'Interior')], default='', max_length=20)),
                ('color', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='usos', to='catalog.color')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='colores_producto', to='catalog.product')),
            ],
            options={
                'verbose_name': 'Color del producto',
                'verbose_name_plural': 'Colores del producto',
                'ordering': ['orden', 'id'],
            },
        ),
        migrations.AddField(
            model_name='productimage',
            name='color',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fotos', to='catalog.color'),
        ),
        migrations.AddConstraint(
            model_name='productcolor',
            constraint=models.UniqueConstraint(fields=('producto', 'color', 'rol'), name='uniq_color_producto_rol'),
        ),
        migrations.RunPython(migra_colores_json, revierte_colores_json),
        migrations.RunPython(siembra_paleta, revierte_paleta),
    ]

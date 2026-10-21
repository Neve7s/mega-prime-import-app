from django.db import migrations


class Migration(migrations.Migration):
    """Quita el JSON `colores` de Product: ahora vive en la tabla Color."""

    dependencies = [
        ('catalog', '0006_color_remove_product_colores_productimage_color_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='colores',
        ),
    ]

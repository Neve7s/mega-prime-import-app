"""Seed idempotente del catálogo con los 4 productos reales de index.html."""

from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Category, Product

CATEGORIES = [
    ("porcelanato", "Porcelanatos", 0),
    ("interiorismo", "Paneles y Decor", 1),
    ("maquinaria", "Herramientas Pro", 2),
]

PRODUCTS = [
    {
        "cat": "porcelanato", "sku": "MPG-CALA-120", "nombre": "Calacatta Imperial Gold Honed",
        "slug": "calacatta-imperial-gold-honed", "precio": "68.50", "unidad": "m2",
        "stock": "4800", "origen": "España",
        "img": "https://lh3.googleusercontent.com/aida-public/AB6AXuCgOvaXrnQ5fMfGLl3uFq__S3qQts1r6_XFXQq8VEWtsUZerwtjoJFL_EggxmL83f1-Mlj4ZXKMtPSmKN-0Twu12ukLGHNDGRocHtIn-90XVa9TrxEHNGpq6NCRQIccbmEy7c9qmu3xnHaa2zZ1_axO7_iOgRbIEurmjaw-MB48HucuUoCaZ4M_uZdUIOLc-rIJOO2biGiN-XLKCjHbapp_6xohF6KaoKmZczZpmBXmWJJZaP0JeV_v",
        "ficha": {"Formato": "120 x 240 x 9 mm", "Superficie": "Satinado Mate Anti-huella", "Tráfico": "PEI V (Comercial Pesado)"},
    },
    {
        "cat": "porcelanato", "sku": "MPG-NERO-160", "nombre": "Titanium Nero Sintered Slab",
        "slug": "titanium-nero-sintered-slab", "precio": "124.00", "unidad": "m2",
        "stock": "2400", "origen": "Italia",
        "img": "https://lh3.googleusercontent.com/aida-public/AB6AXuBcOwi241mkoSaKNWoxeO_OAQAiOW_hRddtjUJhZ2eKnwB09syHXVebEWAoYiZ8C0BrB6YuntFA7SvGwAB34LdP7seePUT73o3X2CsV5-XeEmGNZcnKvJgaImZEiSPzTHPV9zxo1VaEw_KOaJu1f8D2QHm4Xy4ldcRE6KmF4Pdx1F03Dt7lO80-smaOYCIgnrjtAi_MEcJAj03_Ikz06LLQxJMpMUbOtQ39eyVHU7mHFA527tyUxOzU",
        "ficha": {"Formato": "160 x 320 x 12 mm", "Superficie": "Texturizado Flamed Touch", "Tráfico": "Inalterable Térmico (Mesadas)"},
    },
    {
        "cat": "interiorismo", "sku": "MPG-ACOU-WNL", "nombre": "Panel Acústico Walnut 3D Pro",
        "slug": "panel-acustico-walnut-3d-pro", "precio": "89.00", "unidad": "unid",
        "stock": "850", "origen": "Alemania",
        "img": "https://lh3.googleusercontent.com/aida-public/AB6AXuAcZRB4tlah-4eMmFxURQOCFFw0H4vBbN6FRaC02fCAqDFgMR4CImyNBAD1GOKt0wDb26IVr1aN8KdVKaTTP87TOTCHAiC3cavQqX5CxdUaTUOoOTbOZfjCIKr3pspPquhwquqGv7yd65QzIKJpwB_MpsmD37qzIzUcNGM8N9afhXj6SVrEWDRKQRqAtq9jWW4YpKTIimBsyLFY8ZvaJPb3TQmxjow5fqxbRO3Uquw-jE319jzsb8pR",
        "ficha": {"Formato": "600 x 2800 x 21 mm", "Base": "Fieltro PET Reciclado 9mm", "Fuego": "Norma Retardante B-s1,d0"},
    },
    {
        "cat": "maquinaria", "sku": "MPG-CUT-3600", "nombre": "Cortadora de Riel Guiado 3.6m",
        "slug": "cortadora-riel-guiado-36m", "precio": "1250.00", "unidad": "set",
        "stock": "120", "origen": "Alemania",
        "img": "https://lh3.googleusercontent.com/aida-public/AB6AXuBWyBV1SXurBRiP3I3PJ4kPBb7M9WAxQXWay3Vhm-DvEurAlOMZDpS_L3vZ1f_Un_5mx_oNiTGno16fhYzisA5gXYLIEDP9EVIUmiiVgo_5GQ5_KVtS-mZeE6z8avGW-IteoWsC71veYrp1MliJFkb4eMHDHz6WM_u6XpUdo9OwMseEETvyZ9s3zHNHNtO3L3qUxKF4GLRzJ6mr2MeyxC35LlogtQQYTUKIkSEhWismsh6Ou8GcwzVL",
        "ficha": {"Capacidad": "Corte continuo hasta 360 cm", "Espesor": "De 3 mm a 20 mm con prensa", "Incluye": "3 Rieles + Ventosas Bombeo"},
    },
]


class Command(BaseCommand):
    help = "Carga categorías y productos iniciales (idempotente por slug/sku)."

    def handle(self, *args, **options):
        cats = {}
        for slug, nombre, orden in CATEGORIES:
            cats[slug], _ = Category.objects.update_or_create(
                slug=slug, defaults={"nombre": nombre, "orden": orden}
            )
        for p in PRODUCTS:
            Product.objects.update_or_create(
                sku=p["sku"],
                defaults={
                    "categoria": cats[p["cat"]], "nombre": p["nombre"], "slug": p["slug"],
                    "precio_mayor": Decimal(p["precio"]), "unidad": p["unidad"],
                    "stock_cantidad": Decimal(p["stock"]), "origen": p["origen"],
                    "imagen_url": p["img"], "ficha_tecnica": p["ficha"], "destacado": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(
            f"Categorías: {Category.objects.count()}, Productos: {Product.objects.count()}"
        ))

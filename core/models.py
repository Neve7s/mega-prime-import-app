from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from urllib.parse import quote

COLOR_HEX = RegexValidator(
    regex=r"^#[0-9a-fA-F]{6}$",
    message="Usa formato hexadecimal, ej #D4AF37.",
)

FUENTES = [
    ("IBM Plex Sans", "IBM Plex Sans (actual texto)"),
    ("Libre Franklin", "Libre Franklin (actual títulos)"),
    ("Inter", "Inter"),
    ("Barlow", "Barlow"),
    ("Montserrat", "Montserrat"),
    ("Poppins", "Poppins"),
    ("Playfair Display", "Playfair Display"),
    ("Oswald", "Oswald"),
]


class SiteSettings(models.Model):
    """Singleton: branding + slogans + contacto. Editable desde /admin/."""

    site_name = models.CharField(max_length=120, default="MEGA PRIME IMPORT LGM")
    meta_title = models.CharField(
        max_length=160, default="MEGA PRIME IMPORT | Acabados, Interiorismo y Maquinaria Pro"
    )
    meta_description = models.CharField(
        max_length=255,
        default="Importadores directos de porcelanatos gran formato, interiorismo contract y maquinaria pro. Cotización B2B en 48h.",
        blank=True,
    )
    tagline = models.CharField(
        max_length=255,
        default="Hub Logístico & Distribución Mayorista",
        help_text="Slogan corto (overline del hero, header, pestaña).",
    )
    hero_city = models.CharField(max_length=80, default="Ambato, Ecuador")
    hero_title = models.CharField(
        max_length=255, default="Excelencia en Cada Acabado, Potencia en Cada Herramienta."
    )
    hero_subtitle = models.TextField(
        default="Importadores directos de revestimientos porcelánicos de gran formato, perfiles arquitectónicos, grifería de autor y maquinaria de corte con precisión milimétrica para contratistas, arquitectos y constructoras de alto rendimiento.",
        blank=True,
    )
    hero_cta_primary = models.CharField(max_length=80, default="Explorar Catálogo 2025")
    hero_cta_secondary = models.CharField(max_length=80, default="Cotizar Proyecto por Mayor")
    hero_spec_label = models.CharField(
        max_length=80, default="Placa Sinterizada 3200x1600x12mm", blank=True
    )
    hero_telemetry_1_value = models.CharField(max_length=40, default="+1,200", blank=True)
    hero_telemetry_1_label = models.CharField(max_length=80, default="Obras Suministradas", blank=True)
    hero_telemetry_2_value = models.CharField(max_length=40, default="40,000 m²", blank=True)
    hero_telemetry_2_label = models.CharField(max_length=80, default="Stock en Bodega Ambato", blank=True)

    whatsapp_number = models.CharField(
        max_length=20,
        default="593963796222",
        help_text="Solo dígitos con código país, ej 593963796222. Se usa en checkout del carrito.",
    )
    whatsapp_default_message = models.CharField(
        max_length=255,
        default="Hola MEGA PRIME, deseo cotizar un proyecto por mayor",
        blank=True,
    )
    phone_display = models.CharField(max_length=40, default="+593 96 379 6222", blank=True)
    email = models.EmailField(default="ventas@megaprimeimport.com", blank=True)
    address = models.CharField(max_length=255, default="Bodega Ambato — Ambato, Ecuador", blank=True)
    direccion_fisica = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Dirección de la bodega/oficina. Aparece en el pie con un enlace a Google Maps.",
    )
    enlace_maps = models.URLField(
        max_length=300, blank=True, default="",
        help_text="Enlace a Google Maps. Si lo dejas vacío se arma con la dirección física.",
    )
    cities = models.CharField(max_length=120, default="Ambato, Ecuador", blank=True)
    schedule = models.CharField(
        max_length=120, default="Lunes a Sábado 8:00 AM – 6:30 PM (Ambato, Ecuador)", blank=True
    )
    company_legal = models.CharField(
        max_length=160, default="Ecuatoriana | MEGA PRIME IMPORT", blank=True
    )
    company_ruc = models.CharField(
        max_length=13,
        blank=True,
        default="",
        help_text="RUC de la empresa. Se muestra en la información legal pública si se completa.",
    )

    mision = models.TextField(
        default="Ofrecer materiales, acabados y herramientas de calidad que impulsen proyectos de construcción e interiorismo en todo el Ecuador.",
        blank=True,
    )
    vision = models.TextField(
        default="Ser un aliado confiable para profesionales y empresas, reconocido por la calidad de sus productos y un servicio cercano.",
        blank=True,
    )

    facebook_url = models.URLField(blank=True, default="")
    instagram_url = models.URLField(blank=True, default="")
    tiktok_url = models.URLField(blank=True, default="")
    x_url = models.URLField(blank=True, default="")
    youtube_url = models.URLField(blank=True, default="")
    pinterest_url = models.URLField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")

    logo = models.ImageField(upload_to="branding/", blank=True, null=True)
    hero_image = models.ImageField(upload_to="branding/", blank=True, null=True)

    footer_text = models.TextField(
        default="Importación directa, homologación de materiales de alto tránsito y distribución mayorista de revestimientos de gran formato, perfiles arquitectónicos y maquinaria de precisión para proyectos corporativos y residenciales de lujo.",
        blank=True,
    )

    color_primario = models.CharField(
        max_length=7, default="#D4AF37", validators=[COLOR_HEX],
        help_text="Dorado / acento principal: botones dorados y textos destacados.",
    )
    color_secundario = models.CharField(
        max_length=7, default="#0A0A0B", validators=[COLOR_HEX],
        help_text="Base oscura: botones negros, secciones oscuras y titulares.",
    )
    color_fondo = models.CharField(
        max_length=7, default="#FAFAF8", validators=[COLOR_HEX],
        help_text="Fondo principal de la página.",
    )
    color_tarjetas = models.CharField(
        max_length=7, default="#FFFFFF", validators=[COLOR_HEX],
        help_text="Fondo de tarjetas y secciones.",
    )
    color_texto = models.CharField(
        max_length=7, default="#131313", validators=[COLOR_HEX],
        help_text="Color del texto principal.",
    )
    color_acento = models.CharField(
        max_length=7, default="#15803D", validators=[COLOR_HEX],
        help_text="Acento verde: botones de WhatsApp y estados.",
    )
    fuente_cuerpo = models.CharField(
        max_length=40, choices=FUENTES, default="IBM Plex Sans",
        help_text="Tipografía del texto general.",
    )
    fuente_titulos = models.CharField(
        max_length=40, choices=FUENTES, default="Libre Franklin",
        help_text="Tipografía de títulos y encabezados.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ajustes del sitio"
        verbose_name_plural = "Ajustes del sitio"

    def __str__(self) -> str:
        return f"Ajustes: {self.site_name}"

    @classmethod
    def get_solo(cls) -> "SiteSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        from .image_utils import optimize_field_file

        changed = []
        if optimize_field_file(self.logo, max_dim=800):
            changed.append("logo")
        if optimize_field_file(self.hero_image, max_dim=1920):
            changed.append("hero_image")
        if changed:
            super().save(update_fields=changed)

    @property
    def whatsapp_link(self) -> str:
        return f"https://wa.me/{self.whatsapp_number}"

    @property
    def direccion_mostrada(self) -> str:
        """Dirección física que se muestra (con su enlace a Maps)."""
        return (self.direccion_fisica or self.address or "").strip()

    @property
    def maps_link(self) -> str:
        """Enlace a Google Maps: el configurado o el que se arma con la dirección."""
        if (self.enlace_maps or "").strip():
            return self.enlace_maps.strip()
        direccion = self.direccion_mostrada
        if not direccion:
            return ""
        return "https://www.google.com/maps/search/?api=1&query=" + quote(direccion)

    @property
    def fuentes_google_href(self) -> str:
        """URL de Google Fonts con las 2 tipografías elegidas (sin duplicar)."""
        fams = []
        for f in (self.fuente_cuerpo, self.fuente_titulos):
            if f and f not in fams:
                fams.append(f)
        qs = "&family=".join(
            f.replace(" ", "+") + ":wght@400;500;600;700;800" for f in fams
        )
        return f"https://fonts.googleapis.com/css2?family={qs}&display=swap"


class SiteLocation(models.Model):
    sitio = models.ForeignKey(
        SiteSettings, on_delete=models.CASCADE, related_name="ubicaciones"
    )
    nombre = models.CharField(max_length=100, default="Sede")
    direccion = models.CharField(max_length=255)
    enlace_maps = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="Enlace para abrir esta sede en Google Maps (opcional).",
    )
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Ubicación del sitio"
        verbose_name_plural = "Ubicaciones del sitio"

    def __str__(self) -> str:
        return self.nombre

    @property
    def maps_link(self) -> str:
        if self.enlace_maps.strip():
            return self.enlace_maps.strip()
        return "https://www.google.com/maps/search/?api=1&query=" + quote(self.direccion)

    @property
    def maps_embed_link(self) -> str:
        return "https://www.google.com/maps?q=" + quote(self.direccion) + "&output=embed"


class Complaint(models.Model):
    RECLAMO = "reclamo"
    QUEJA = "queja"
    TIPOS = [(RECLAMO, "Reclamo"), (QUEJA, "Queja")]
    IDENTIFICACIONES = [
        ("cedula", "Cédula"),
        ("ruc", "RUC"),
        ("pasaporte", "Pasaporte"),
        ("otro", "Otro"),
    ]
    CANALES_RESPUESTA = [
        ("correo", "Correo electrónico"),
        ("telefono", "Teléfono"),
        ("whatsapp", "WhatsApp"),
    ]

    ESTADOS = [
        ("recibido", "Recibido"),
        ("revision", "En revisión"),
        ("respondido", "Respondido"),
        ("cerrado", "Cerrado"),
    ]

    codigo = models.CharField(max_length=14, unique=True, editable=False)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    nombres = models.CharField(max_length=120)
    apellidos = models.CharField(max_length=120)
    tipo_identificacion = models.CharField(max_length=20, choices=IDENTIFICACIONES)
    identificacion = models.CharField(max_length=30)
    empresa = models.CharField(max_length=160, blank=True)
    correo = models.EmailField()
    telefono = models.CharField(max_length=30)
    direccion = models.CharField(max_length=255)
    provincia = models.CharField(max_length=80)
    producto_servicio = models.CharField(max_length=180)
    numero_pedido = models.CharField(max_length=60, blank=True)
    fecha_incidente = models.DateField(null=True, blank=True)
    monto_reclamado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    detalle = models.TextField()
    solicitud = models.TextField()
    canal_respuesta = models.CharField(
        max_length=20, choices=CANALES_RESPUESTA, default="correo"
    )
    acepta_privacidad = models.BooleanField(default=False)
    estado = models.CharField(max_length=12, choices=ESTADOS, default="recibido")
    respuesta_interna = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en", "-id"]
        verbose_name = "Reclamo o queja"
        verbose_name_plural = "Reclamos y quejas"

    def __str__(self) -> str:
        return f"{self.codigo} — {self.get_tipo_display()}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            import secrets

            self.codigo = f"MP-{secrets.token_hex(5).upper()}"
        super().save(*args, **kwargs)


class HeroMedia(models.Model):
    """Fondos del hero: hasta 3 imágenes, GIF o videos.

    Se administran desde el panel (Ajustes → Portada). Si no hay ninguno,
    el hero usa su fondo por defecto.
    """

    TIPO_IMAGEN = "imagen"
    TIPO_VIDEO = "video"
    TIPOS = [(TIPO_IMAGEN, "Imagen o GIF"), (TIPO_VIDEO, "Video (mp4)")]

    MAX_MEDIOS = 3

    tipo = models.CharField(max_length=10, choices=TIPOS, default=TIPO_IMAGEN)
    imagen = models.ImageField(
        upload_to="branding/hero/", blank=True, null=True,
        help_text="Sube la foto o el GIF (se optimiza a 1920px).")
    url = models.CharField(
        max_length=300, blank=True, default="",
        help_text="Enlace externo (video mp4 o GIF). Si subes archivo, gana el archivo.")
    alt = models.CharField(max_length=160, blank=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Fondo del hero"
        verbose_name_plural = "Fondos del hero"

    def __str__(self) -> str:
        return self.alt or f"Fondo {self.pk}"

    @property
    def src(self) -> str:
        return self.imagen.url if self.imagen else (self.url or "")

    @property
    def tiene_fuente(self) -> bool:
        return bool(self.src)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from .image_utils import optimize_field_file

        if optimize_field_file(self.imagen, max_dim=1920):
            super().save(update_fields=["imagen"])


class HeroStat(models.Model):
    """Cifras del hero (+15 años, 48h, stock, B2B). Ordenables y activables."""

    value = models.CharField(max_length=40)
    label = models.CharField(max_length=80)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Cifra hero"
        verbose_name_plural = "Cifras hero"

    def __str__(self) -> str:
        return f"{self.value} — {self.label}"

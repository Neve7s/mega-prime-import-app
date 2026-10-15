"""Pipeline de imágenes: resize + conversión a WebP + descarga desde URL.

PNG/JPG de varios MB -> WebP optimizado. Usado en save() de
Product/ProductImage (max 1600px), SiteSettings.hero_image (1920px) y logo (800px).
"""

import urllib.request
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image

MAX_BYTES = 15 * 1024 * 1024


def process_to_webp(path: Path, max_dim: int = 1600, quality: int = 82) -> Path:
    """Reescribe la imagen en WebP optimizada. Devuelve la ruta final."""
    img = Image.open(path)
    img.load()
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    webp_path = path.with_suffix(".webp")
    img.save(webp_path, "WEBP", quality=quality, method=6)
    if webp_path != path:
        path.unlink(missing_ok=True)
    return webp_path


def optimize_field_file(field_file, max_dim: int = 1600, quality: int = 82) -> bool:
    """Optimiza un FieldFile ya guardado en disco. Devuelve True si cambió el nombre."""
    if not field_file or not field_file.name:
        return False
    path = Path(field_file.path)
    if not path.exists():
        return False
    final = process_to_webp(path, max_dim=max_dim, quality=quality)
    # Forward slashes: lo que Django espera en DB/URLs (no backslashes de Windows).
    new_name = str(final.relative_to(Path(field_file.storage.base_location))).replace("\\", "/")
    if new_name != field_file.name.replace("\\", "/"):
        # Escribir en la instancia: FieldFile.save() deja un str en __dict__
        # y el objeto FieldFile previo queda huérfano.
        field_file.instance.__dict__[field_file.field.name] = new_name
        return True
    return False


def download_image(url: str, timeout: int = 25) -> tuple[bytes, str] | None:
    """Descarga una imagen y devuelve (bytes, extensión). None si falla."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type", "")
        if not ctype.startswith("image/"):
            return None
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or not data:
        return None
    ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(
        ctype.split(";")[0].strip(), ".jpg"
    )
    return data, ext


def fetch_url_into_field(instance, field_name: str, url: str, filename: str,
                          max_dim: int = 1600, quality: int = 82) -> bool:
    """Descarga URL al ImageField y lo optimiza a WebP. Guarda la instancia."""
    got = download_image(url)
    if not got:
        return False
    data, ext = got
    field = getattr(instance, field_name)
    field.save(f"{filename}{ext}", ContentFile(data), save=False)
    optimize_field_file(field, max_dim=max_dim, quality=quality)
    instance.save(update_fields=[field_name])
    return True

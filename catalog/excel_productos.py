"""Plantilla y lectura de Excel para el alta masiva de productos.

La idea es la misma que en la calculadora: se descarga una plantilla, se
llena en Excel y se sube. `build_productos_xlsx` y `read_productos_xlsx`
comparten `HEADERS`, así que la plantilla y el lector nunca se desincronizan.
"""

from decimal import Decimal, InvalidOperation
from io import BytesIO
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils.exceptions import InvalidFileException

from .models import Category, Product, TipoProducto

HEADERS = [
    "SKU", "Nombre", "Categoría", "Tipo", "Precio mayor USD",
    "Unidad", "Stock", "Badge", "Origen", "Imagen URL", "Descripción",
]

ANCHOS = (18, 40, 22, 22, 16, 10, 10, 16, 12, 38, 50)

MAX_FILAS = 1000

UNIDADES = {
    "m2": Product.UNIDAD_M2, "m²": Product.UNIDAD_M2,
    "metro": Product.UNIDAD_M2, "metros": Product.UNIDAD_M2,
    "metro cuadrado": Product.UNIDAD_M2, "metros cuadrados": Product.UNIDAD_M2,
    "unid": Product.UNIDAD_UNID, "unidad": Product.UNIDAD_UNID,
    "unidades": Product.UNIDAD_UNID, "u": Product.UNIDAD_UNID,
    "set": Product.UNIDAD_SET, "sets": Product.UNIDAD_SET,
    "juego": Product.UNIDAD_SET, "juegos": Product.UNIDAD_SET,
}

INSTRUCCIONES = (
    "Cómo llenar la plantilla de productos",
    "",
    "· Una fila por producto. Deje la fila en blanco para ignorarla.",
    "· SKU y Nombre son obligatorios. El SKU identifica el producto: si ya existe, se actualiza.",
    "· Categoría: nombre o slug de una categoría existente (obligatorio).",
    "· Tipo: nombre o slug del tipo de producto (opcional).",
    "· Precio mayor USD: número mayor o igual a 0 (obligatorio).",
    "· Unidad: m2, unid o set. Vacío = m2.",
    "· Stock: número mayor o igual a 0. Vacío = 0.",
    "· Badge: etiqueta destacada, ej MÁS VENDIDO (opcional).",
    "· Imagen URL: enlace http(s) de la foto (opcional).",
)


def _texto(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _numero(value, etiqueta, fila, obligatorio):
    texto = _texto(value)
    if not texto:
        if obligatorio:
            raise ValueError(f"Falta {etiqueta} en la fila {fila}.")
        return Decimal("0.00")
    try:
        numero = Decimal(texto)
    except (InvalidOperation, ArithmeticError):
        raise ValueError(f"{etiqueta} debe ser un número (fila {fila}).") from None
    if numero < 0:
        raise ValueError(f"{etiqueta} no puede ser negativo (fila {fila}).")
    return numero.quantize(Decimal("0.01"))


def build_productos_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Productos"
    sheet.append(HEADERS)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for columna, ancho in zip("ABCDEFGHIJK", ANCHOS):
        sheet.column_dimensions[columna].width = ancho
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0A0A0B")

    notas = workbook.create_sheet("Instrucciones")
    notas.column_dimensions["A"].width = 110
    for linea in INSTRUCCIONES:
        notas.append([linea])

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _indice_catalogo(modelo):
    """Nombre y slug apuntan al mismo objeto (el usuario escribe lo que ve)."""
    indice = {}
    for obj in modelo.objects.all():
        indice[obj.nombre.casefold()] = obj
        indice[obj.slug.casefold()] = obj
    return indice


def read_productos_xlsx(uploaded_file):
    """Devuelve filas normalizadas y listas para guardar (una por producto)."""
    try:
        workbook = load_workbook(uploaded_file, read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, OSError, ValueError) as exc:
        raise ValueError("No se pudo leer el archivo Excel. Use la plantilla descargada.") from exc

    if "Productos" not in workbook.sheetnames:
        raise ValueError("El archivo debe incluir la hoja Productos.")

    sheet = workbook["Productos"]
    if [sheet.cell(1, col).value for col in range(1, len(HEADERS) + 1)] != HEADERS:
        raise ValueError("La hoja Productos debe conservar los encabezados de la plantilla.")
    if sheet.max_row > MAX_FILAS + 1:
        raise ValueError(f"La plantilla admite hasta {MAX_FILAS} productos.")

    categorias = _indice_catalogo(Category)
    tipos = _indice_catalogo(TipoProducto)

    filas = []
    skus = set()
    for fila, values in enumerate(
            sheet.iter_rows(min_row=2, max_row=sheet.max_row, values_only=True), start=2):
        valores = list(values) + [None] * (len(HEADERS) - len(values))
        if all(_texto(valor) == "" for valor in valores):
            continue
        (sku, nombre, categoria_txt, tipo_txt, precio, unidad_txt, stock,
         badge, origen, imagen, descripcion) = valores[:len(HEADERS)]

        sku = _texto(sku)
        if not sku:
            raise ValueError(f"Falta SKU en la fila {fila}.")
        if sku.casefold() in skus:
            raise ValueError(f"El SKU {sku} está repetido en el archivo (fila {fila}).")
        skus.add(sku.casefold())

        nombre = _texto(nombre)
        if not nombre:
            raise ValueError(f"Falta nombre en la fila {fila}.")

        categoria = None
        if _texto(categoria_txt):
            categoria = categorias.get(_texto(categoria_txt).casefold())
            if categoria is None:
                raise ValueError(
                    f"Categoría no encontrada: {_texto(categoria_txt)} (fila {fila}).")

        tipo = None
        if _texto(tipo_txt):
            tipo = tipos.get(_texto(tipo_txt).casefold())
            if tipo is None:
                raise ValueError(f"Tipo no encontrado: {_texto(tipo_txt)} (fila {fila}).")

        unidad = Product.UNIDAD_M2
        if _texto(unidad_txt):
            unidad = UNIDADES.get(_texto(unidad_txt).casefold())
            if unidad is None:
                raise ValueError(
                    f"Unidad no válida ({_texto(unidad_txt)}) en la fila {fila}. "
                    "Use m2, unid o set.")

        filas.append({
            "fila": fila,
            "sku": sku,
            "nombre": nombre,
            "categoria": categoria,
            "tipo": tipo,
            "precio_mayor": _numero(precio, "precio", fila, obligatorio=True),
            "unidad": unidad,
            "stock_cantidad": _numero(stock, "stock", fila, obligatorio=False),
            "badge": _texto(badge)[:40],
            "origen": _texto(origen)[:40],
            "imagen_url": _texto(imagen)[:500],
            "descripcion": _texto(descripcion)[:1000],
        })

    workbook.close()
    return filas

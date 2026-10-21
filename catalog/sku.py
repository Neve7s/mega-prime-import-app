"""SKU incremental de los productos: COD-0001, COD-0002, …

El prefijo vive en `PREFIJO_SKU`; se puede cambiar (o hacerlo por categoría)
sin tocar el resto del código. El número es correlativo y siempre se entrega
libre: si alguien borró el COD-0007, el siguiente alta usa el 0008.
"""

import re

PREFIJO_SKU = "COD"
LARGO_NUMERO = 4

_SUFIJO = re.compile(r"^\d+$")


def _numeros_usados(prefijo: str) -> list:
    from .models import Product

    numeros = []
    # .order_by() vacío: sin el JOIN al orden de la categoría.
    for sku in (Product.objects.filter(sku__startswith=f"{prefijo}-")
                .order_by().values_list("sku", flat=True)):
        sufijo = sku[len(prefijo) + 1:]
        if _SUFIJO.match(sufijo):
            numeros.append(int(sufijo))
    return numeros


def siguiente_sku(prefijo: str = PREFIJO_SKU, largo: int = LARGO_NUMERO,
                   reservados=()) -> str:
    """Devuelve el siguiente SKU libre con el formato `COD-0001`.

    `reservados`: SKUs que ya se van a usar en la misma operación (por
    ejemplo las filas de un Excel) y que no deben repetirse.
    """
    from .models import Product

    tomados = {str(s).casefold() for s in reservados}
    numeros = _numeros_usados(prefijo)
    numero = (max(numeros) if numeros else 0) + 1
    while True:
        candidato = f"{prefijo}-{numero:0{largo}d}"
        if candidato.casefold() not in tomados and not Product.objects.filter(
                sku__iexact=candidato).exists():
            return candidato
        numero += 1

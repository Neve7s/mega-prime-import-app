"""Estimación de impuestos de importación Ecuador (función pura, testeable)."""

from decimal import Decimal, ROUND_HALF_UP

TWOPLACES = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def estimate(
    valor_fob: Decimal,
    flete: Decimal = Decimal("0"),
    seguro: Decimal = Decimal("0"),
    ad_valorem_pct: Decimal = Decimal("0"),
    fodinfa_pct: Decimal = Decimal("0.50"),
    iva_pct: Decimal = Decimal("15"),
) -> dict:
    """CIF = FOB + flete + seguro; ad-valorem y FODINFA sobre CIF; IVA sobre CIF+aranceles."""
    cif = valor_fob + flete + seguro
    ad_valorem = cif * ad_valorem_pct / Decimal("100")
    fodinfa = cif * fodinfa_pct / Decimal("100")
    base_iva = cif + ad_valorem + fodinfa
    iva = base_iva * iva_pct / Decimal("100")
    total = cif + ad_valorem + fodinfa + iva
    return {
        "cif": _q(cif),
        "ad_valorem": _q(ad_valorem),
        "fodinfa": _q(fodinfa),
        "base_iva": _q(base_iva),
        "iva": _q(iva),
        "total": _q(total),
    }

"""Estimación de impuestos de importación Ecuador (función pura, testeable)."""

from decimal import Decimal, ROUND_HALF_UP

TWOPLACES = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _to_pct(value, default):
    """None/vacío → default (usa tasa general). Si no, Decimal del %."""
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == "":
        return default
    return Decimal(str(value))


def calculate_shipment(items, gastos, tasas) -> dict:
    """Réplica exacta de COSTOS ROMA.xlsx (hojas Teja Roma / Español).

    items: [{nombre, cant, valor_unit, compet1, compet2, compet3,
             seguro_pct?, advalorem_pct?, fondinfa_pct?, iva_pct?}]
      - compet1/2/3 son recargos (%) para mayorista, frecuente y eventual.
        Se calculan sobre el costo unitario: precio sin IVA = costo * (1 + recargo).
      - margen_pct solo se reconoce al leer embarques antiguos; esos datos usaban
        compet1/2/3 como precios de referencia y un margen único.
      - Los 4 *_pct por item son OVERRIDES opcionales: None/""/ausente = usa
        la tasa general. Permite que un producto tenga su propio arancel
        (ej. ad-valorem 0% por partida exonerada) sin afectar al resto.
    gastos: {flete_intl, flete_local, gasto_admin, bodegaje, devolucion,
             comision_banco, descarga, agente, otros_unit}
    tasas: {seguro_pct, advalorem_pct, fondinfa_pct, iva_pct, iva_pvp_pct}
      - porcentajes en % (ej. 20 = 20%). seguro por defecto 1.0, advalorem 20,
        fondinfa 0.5, iva 15, iva_pvp 15.

    Fórmulas Excel (generalizadas por item):
      total_fob = Σ cant*valor_unit
      flete_i = flete_intl * ratio_i            (ratio_i = cant_i / total_cant)
      seguro_i = (fob_i + flete_i) * seguro_pct_i
      advalorem_i = (fob_i + seguro_i) * advalorem_pct_i   (NO incluye flete, como el Excel)
      fondinfa_i = (fob_i + flete_i + seguro_i) * fondinfa_pct_i
      iva_i = (fob_i + flete_i + seguro_i + advalorem_i + fondinfa_i) * iva_pct_i
      Los totales del resumen son la SUMA de los rubros por item.
      Sin overrides, el resultado es idéntico al cálculo global anterior.
      valor_total_i = fob_i + tributos_i + locales prorrateados_i
      costo_unit_i = valor_total_i / cant_i
      precio_sin_iva = costo_unit_i * (1 + recargo_pct / 100)
      precio_con_iva = precio_sin_iva * (1 + iva_pvp / 100)
    """
    def D(v):
        return Decimal(str(v)) if not isinstance(v, Decimal) else v

    seguro_pct = D(tasas.get("seguro_pct", 1))
    advalorem_pct = D(tasas.get("advalorem_pct", 20))
    fondinfa_pct = D(tasas.get("fondinfa_pct", Decimal("0.5")))
    iva_pct = D(tasas.get("iva_pct", 15))
    iva_pvp_pct = D(tasas.get("iva_pvp_pct", 15))

    flete_intl = D(gastos.get("flete_intl", 0))
    flete_local = D(gastos.get("flete_local", 0))
    gasto_admin = D(gastos.get("gasto_admin", 0))
    bodegaje = D(gastos.get("bodegaje", 0))
    devolucion = D(gastos.get("devolucion", 0))
    comision_banco = D(gastos.get("comision_banco", 0))
    descarga = D(gastos.get("descarga", 0))
    agente = D(gastos.get("agente", 0))
    otros_unit = D(gastos.get("otros_unit", 0))

    norm = []
    total_cant = Decimal("0")
    total_fob = Decimal("0")
    for it in items:
        cant = D(it.get("cant", 0))
        valor_unit = D(it.get("valor_unit", 0))
        fob = cant * valor_unit
        legacy_margin = it.get("margen_pct")
        def _client_margin(key):
            value = legacy_margin if legacy_margin is not None else it.get(key)
            return _to_pct(value, Decimal("35"))
        total_cant += cant
        total_fob += fob
        norm.append({
            "nombre": (it.get("nombre") or "").strip() or "Producto",
            "cant": cant, "valor_unit": valor_unit,
            "fob": fob,
            "compet1": _client_margin("compet1"),
            "compet2": _client_margin("compet2"),
            "compet3": _client_margin("compet3"),
            # Overrides por item (None = usa tasa general). Se resuelven abajo.
            "seguro_pct_raw": it.get("seguro_pct", None),
            "advalorem_pct_raw": it.get("advalorem_pct", None),
            "fondinfa_pct_raw": it.get("fondinfa_pct", None),
            "iva_pct_raw": it.get("iva_pct", None),
        })

    if total_cant <= 0:
        return {"items": [], "resumen": None, "error": "Ingrese cantidades > 0."}

    out_items = []
    seguro_total = Decimal("0")
    advalorem_total = Decimal("0")
    fondinfa_total = Decimal("0")
    iva_total = Decimal("0")
    # Primera pasada: tributos por item con su tasa efectiva.
    for it in norm:
        ratio = it["cant"] / total_cant if total_cant else Decimal("0")
        fob_i = it["fob"]
        flete_i = flete_intl * ratio
        s_pct = _to_pct(it["seguro_pct_raw"], seguro_pct)
        a_pct = _to_pct(it["advalorem_pct_raw"], advalorem_pct)
        f_pct = _to_pct(it["fondinfa_pct_raw"], fondinfa_pct)
        v_pct = _to_pct(it["iva_pct_raw"], iva_pct)
        seguro_i = (fob_i + flete_i) * s_pct / Decimal("100")
        advalorem_i = (fob_i + seguro_i) * a_pct / Decimal("100")
        fondinfa_i = (fob_i + flete_i + seguro_i) * f_pct / Decimal("100")
        iva_i = (fob_i + flete_i + seguro_i + advalorem_i + fondinfa_i) * v_pct / Decimal("100")
        it["_ratio"] = ratio
        it["_flete"] = flete_i
        it["_seguro"] = seguro_i
        it["_advalorem"] = advalorem_i
        it["_fondinfa"] = fondinfa_i
        it["_iva"] = iva_i
        it["_s_pct"] = s_pct
        it["_a_pct"] = a_pct
        it["_f_pct"] = f_pct
        it["_v_pct"] = v_pct
        def _hay_override(raw):
            if raw is None:
                return False
            if isinstance(raw, str) and raw.strip() == "":
                return False
            return True
        it["_especial"] = any(
            _hay_override(raw)
            for raw in (it["seguro_pct_raw"], it["advalorem_pct_raw"],
                        it["fondinfa_pct_raw"], it["iva_pct_raw"])
        )
        seguro_total += seguro_i
        advalorem_total += advalorem_i
        fondinfa_total += fondinfa_i
        iva_total += iva_i

    total_tributos = total_fob + flete_intl + seguro_total + advalorem_total + fondinfa_total + iva_total

    otros_total = otros_unit * total_cant
    locales_total = (comision_banco + agente + flete_local + bodegaje
                     + devolucion + gasto_admin + descarga + otros_total)
    gran_total = total_tributos + locales_total

    for it in norm:
        ratio = it["_ratio"]
        fob_i = it["fob"]
        flete_i = it["_flete"]
        seguro_i = it["_seguro"]
        advalorem_i = it["_advalorem"]
        fondinfa_i = it["_fondinfa"]
        isd_i = comision_banco * ratio
        agente_i = agente * ratio
        flete_local_i = flete_local * ratio
        bodegaje_i = bodegaje * ratio
        devolucion_i = devolucion * ratio
        admin_i = gasto_admin * ratio
        descarga_i = descarga * ratio
        otros_i = otros_unit * it["cant"]
        adicionales_i = (isd_i + agente_i + flete_local_i + bodegaje_i
                         + devolucion_i + admin_i + descarga_i + otros_i)
        iva_i = it["_iva"]
        valor_total = (fob_i + advalorem_i + flete_i + seguro_i + fondinfa_i
                       + iva_i + adicionales_i)
        costo_unit = valor_total / it["cant"] if it["cant"] else Decimal("0")
        precios = {}
        for index in range(1, 4):
            precio_sin = costo_unit * (Decimal("1") + it[f"compet{index}"] / Decimal("100"))
            precios[f"comp{index}_sin"] = _q(precio_sin)
            precios[f"comp{index}_con"] = _q(
                precio_sin * (Decimal("1") + iva_pvp_pct / Decimal("100")))
        out_items.append({
            **{k: v for k, v in it.items() if not k.startswith("_")},
            "seguro_pct_raw": None, "advalorem_pct_raw": None,
            "fondinfa_pct_raw": None, "iva_pct_raw": None,
            "seguro_pct_eff": _q(it["_s_pct"]), "advalorem_pct_eff": _q(it["_a_pct"]),
            "fondinfa_pct_eff": _q(it["_f_pct"]), "iva_pct_eff": _q(it["_v_pct"]),
            "especial": it["_especial"],
            "ratio": _q(ratio * 100),
            "advalorem": _q(advalorem_i), "flete": _q(flete_i), "seguro": _q(seguro_i),
            "fondinfa": _q(fondinfa_i), "iva_item": _q(it["_iva"]),
            "isd": _q(isd_i), "agente": _q(agente_i),
            "flete_local": _q(flete_local_i), "bodegaje": _q(bodegaje_i),
            "devolucion": _q(devolucion_i), "admin": _q(admin_i),
            "descarga": _q(descarga_i), "otros": _q(otros_i),
            "adicionales": _q(adicionales_i),
            "valor_total": _q(valor_total),
            "costo_unit": _q(costo_unit),
            **precios,
        })

    resumen = {
        "total_cant": _q(total_cant),
        "fob": _q(total_fob), "flete_intl": _q(flete_intl),
        "seguro": _q(seguro_total), "advalorem": _q(advalorem_total),
        "fondinfa": _q(fondinfa_total), "iva": _q(iva_total),
        "total_tributos": _q(total_tributos),
        "comision_banco": _q(comision_banco), "agente": _q(agente),
        "flete_local": _q(flete_local), "bodegaje": _q(bodegaje),
        "devolucion": _q(devolucion), "gasto_admin": _q(gasto_admin),
        "descarga": _q(descarga), "otros": _q(otros_total),
        "locales_total": _q(locales_total),
        "gran_total": _q(gran_total),
        "impuesto_iva_sum": _q(advalorem_total + fondinfa_total + iva_total),
    }
    return {"items": out_items, "resumen": resumen, "error": None}


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

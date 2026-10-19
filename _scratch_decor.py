import io
import re

RUTA = "panel/views.py"

SECCION = {
    "productos": [
        "productos", "productos_precios", "productos_duplicados",
        "producto_eliminar", "productos_importar", "productos_plantilla",
        "producto_editar", "categorias", "categoria_editar",
        "categoria_eliminar", "categoria_crear_rapida", "tipos",
        "tipo_editar", "tipo_eliminar", "tipo_crear_rapido",
    ],
    "pedidos": ["pedidos", "pedido_detalle"],
    "codigos": ["codigos", "codigo_crear", "codigo_detalle"],
    "calculadora": [
        "calculadora", "calculadora_guardar", "calculadora_plantilla",
        "calculadora_importar", "calculadora_reporte",
    ],
}

MAPA = {}
for seccion, funciones in SECCION.items():
    for fn in funciones:
        MAPA[fn] = seccion

lineas = io.open(RUTA, encoding="utf-8").read().split("\n")
cambios = []
for i, linea in enumerate(lineas):
    if linea.strip() != "@staff_only":
        continue
    siguiente = lineas[i + 1] if i + 1 < len(lineas) else ""
    m = re.match(r"def ([a-zA-Z_0-9]+)\(", siguiente)
    if not m:
        continue
    nombre = m.group(1)
    if nombre in MAPA:
        lineas[i] = '@seccion_requerida("%s")' % MAPA[nombre]
        cambios.append((nombre, MAPA[nombre]))

io.open(RUTA, "w", encoding="utf-8", newline="").write("\n".join(lineas))
print(len(cambios), "cambios")
for nombre, seccion in cambios:
    print(" ", nombre, "->", seccion)

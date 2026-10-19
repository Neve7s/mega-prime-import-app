# Spec: Gestión de productos — calidad, búsqueda global, acciones masivas, duplicados y edición inline

## Objective

Cerrar la brecha entre el panel Django (`/webadmin/productos/`) y el admin actual del cliente
(Supabase) en cinco frentes, manteniendo la organización **por categoría dentro de Productos**
(ya implementada, no se separa en pantallas nuevas de primer nivel):

1. **Señales de calidad** — badges por producto que faltan (`sin fotos`, `sin características`,
   `sin precio`) y conteo de incompletos por categoría, para detectar fichas a medio hacer.
2. **Búsqueda global** — poder buscar en **todas** las categorías sin perder el filtro por categoría.
3. **Acciones masivas** — activar / desactivar / mover a categoría / eliminar varios productos de una vez.
4. **Detector de duplicados** — agrupar productos con el mismo nombre normalizado dentro de una
   categoría, para limpiar datos repetidos.
5. **Edición inline** — editar `precio_mayor` y `stock_cantidad` directamente en la lista, sin
   entrar al formulario completo.

**Usuario:** staff del panel (`is_staff`), un operador de tienda con prisa que quiere pocos clics.
**Éxito:** puede responder "¿qué productos están incompletos?", "buscar en todo el catálogo",
"apagar 20 productos de un golpe", "encontrar los repetidos" y "corregir un precio" sin salir de Productos.

## Tech Stack

- Django 5.2.18, templates de Django + JS vanilla, Tailwind por CDN (sin build).
- Postgres. **Sin HTMX, sin nuevas dependencias** (decisión previa respetada).
- Sin framework de mensajes: los avisos viajan por querystring y los pinta `_ctx_productos`.
- Formularios: `ModelForm` existentes (`ProductForm`, `CategoryForm`, `TipoForm`).

## Commands

```
Tests (app):     & ".venv\Scripts\python.exe" manage.py test panel catalog
Tests (todo):    & ".venv\Scripts\python.exe" manage.py test
Check:           & ".venv\Scripts\python.exe" manage.py check
Servidor manual: & ".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8009
```

> Nota: `calculator.tests.SavedShipmentViewTest.test_guarda_y_carga_embarque_vacio` falla por un
> rename de etiquetas previo (`b56e718`), **ajeno a este trabajo**. El criterio de éxito son
> `panel` + `catalog` en verde y `check` limpio.

## Project Structure

```
panel/views.py                     → vistas del panel (productos, acciones masivas, duplicados, precios)
panel/urls.py                      → rutas nuevas bajo productos/
panel/forms.py                     → (sin cambios salvo que el spec lo pida)
panel/templates/panel/productos.html        → lista: badges, búsqueda global, acciones masivas, edición inline
panel/templates/panel/productos_duplicados.html  → (nuevo) grupos de duplicados
panel/templates/panel/producto_eliminar.html     → (nuevo) confirmación de borrado de 1 producto
panel/tests.py                     → tests A1..F2
catalog/calidad.py                 → (nuevo) reglas de "faltantes" + normalización de nombres
catalog/tests.py                   → tests unitarios de calidad/normalización
tasks/spec-productos-v2.md         → este spec
tasks/plan.md / tasks/todo.md      → plan y tareas de esta fase
```

## Code Style

Estilo actual del repo: helpers privados con `_`, imports locales dentro de la vista cuando son
pesados, español en UI, JSON sin `_json` salvo colisión.

```python
def _ctx_productos(request, categoria_slug=None, import_result=None, import_error=""):
    ...
    return {"productos": prods[:100], "q": q, "categorias": categorias, ...}

@staff_only
def productos_acciones(request):
    if request.method != "POST":
        return redirect("panel:productos")
    ...
```

Reglas:
- Toda vista nueva de productos: `@staff_only`, mutaciones **solo por POST**, CSRF obligatorio.
- Nada de `!important` ni CSS nuevo si Tailwind lo cubre.
- Español en textos visibles, identificadores en inglés/español como ya hace el módulo.

## Testing Strategy

- Framework: `django.test.TestCase` (patrón `PanelTest`), `self.client`, `force_login`.
- Tests de vista (comportamiento HTTP + HTML) en `panel/tests.py`.
- Tests unitarios puros (faltantes/normalización) en `catalog/tests.py`.
- Nivel: integración de vista + unitario de helper. Sin tests de JS (se verifica en navegador).
- Cobertura exigida: cada endpoint nuevo tiene caso **ok**, caso **inválido** y caso **permiso**.
- Slugs de test únicos (`*-x`, `*-imp`) para no chocar con la migración semilla (`tejas`).

## Boundaries

- **Always**
  - `@staff_only` + POST-only + CSRF en cada vista que crea/edita/borra.
  - Validar y acotar listas de `ids` (enteros, máx 200) antes de tocar la BD.
  - Preservar el contexto (categoría activa, `q`, `todas`) en cada redirect de vuelta a la lista.
  - `manage.py check` + `test panel catalog` antes de dar por terminada una tarea.
- **Ask first**
  - Cambios de esquema/migraciones (`catalog`).
  - Añadir dependencias (por ahora: ninguna).
  - Cambiar comportamiento de tests existentes.
- **Never**
  - Guardar/alterar nada en el admin remoto del cliente.
  - Borrar productos sin confirmación explícita del usuario en la UI.
  - Dejar un botón destructivo fuera del `require POST` / sin staff.

## Design decisions (defaults propuestos)

| Tema | Decisión | Razón |
|------|----------|-------|
| "Faltante" = | `sin fotos` (`imagen` y `imagen_url` vacíos), `sin características` (`caracteristicas == []`), `sin precio` (`precio_mayor <= 0`) | Sólo señales accionables y verificables hoy |
| Badges por categoría | `⚠ N` en el pill si la categoría tiene ≥1 incompleto | Describe sin ruido; el detalle va en cada fila |
| Búsqueda global | Checkbox `todas=1` junto a "Buscar"; por defecto **no** (filtro por categoría se respeta) | No rompe el comportamiento actual ni sus tests |
| Acciones masivas | Un `<form id="acciones-masivas">` + checkboxes asociados con el atributo `form="acciones-masivas"` | Evita formularios anidados; HTML5 estándar |
| Destructivas | `eliminar` exige `confirm()` en el cliente; `mover` exige categoría destino | Fricción mínima en lo reversible, máxima en lo irreversible |
| Edición inline | Form único `#precios` con botón "Guardar precios" (server-side, **sin JS**) | Accesible, testeable, sin estados parciales |
| Duplicados | Agrupar por (categoría, nombre normalizado: sin tildes/mayúsculas/espacios) | Evita falsos positivos entre categorías |
| Dónde vive | Todo dentro de `/webadmin/productos/` (+ sub-página `productos/duplicados/` enlazada desde ahí, no en el nav) | Respeta "dentro de producto, no separado" |

## Success Criteria

1. En `/webadmin/productos/` cada fila muestra los badges de faltantes y cada pill de categoría
   muestra `⚠ N` cuando aplica. **Testeable:** el HTML contiene los textos de badge esperados.
2. `?q=...&todas=1` busca en todas las categorías; `?q=...` sin `todas` mantiene el filtro
   por categoría. **Testeable:** dos GET con aserciones cruzadas.
3. Un POST a `productos/acciones/` con `accion=desactivar` y `ids` desactiva sólo esos productos
   y redirige a la lista con aviso; `accion=eliminar` los borra; `accion=mover` los cambia de
   categoría; no-staff no cambia nada. **Testeable:** 4 casos + permiso.
4. `/webadmin/productos/duplicados/` lista grupos con ≥2 productos del mismo nombre normalizado
   en la misma categoría, con enlace a editar/eliminar cada uno. **Testeable:** HTML con ambos SKU.
5. Un POST a `productos/precios/` con `precio_<pk>`/`stock_<pk>` actualiza los valores y redirige
   con aviso; valores negativos/no numéricos → error sin cambios. **Testeable:** estado en BD.
6. `manage.py check` limpio y `test panel catalog` en verde (sin contar el fallo preexistente de `calculator`).

## Open Questions

1. ¿Basta el checkbox "Buscar en todas las categorías" o se prefiere que buscar siempre sea global?
2. ¿La edición inline se acepta como formulario con botón "Guardar precios" (sin JS) o se quiere
   autoguardado por fila con `fetch`?
3. Duplicados: ¿agrupar por (categoría + nombre normalizado) o sólo por nombre normalizado?
4. ¿"Mover a categoría" debe ofrecer crear categoría nueva ahí mismo (reusando el modal de alta rápida)?

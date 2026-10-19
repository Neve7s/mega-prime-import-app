# Implementation Plan: Mega Prime Import ECU → Django + HTMX Webapp

## Overview
Convertir `code.html` (landing de 8 secciones, Tailwind CDN + Material Symbols) a webapp Django con solo Django Templates + HTMX, sin SPA/React. Los cambios en DB (productos, precios, stock) se reflejan en el frontend vía fragmentos HTMX. 4 apps: `core` (landing), `catalog` (gestión productos), `cart` (carrito → checkout WhatsApp, sin pasarela), `calculator` (calculadora impuestos importación Ecuador), `accounts` (login usuario/contraseña).

Stack: Django 5.x, SQLite dev / Postgres prod (Coolify), Django auth por defecto, HTMX 1.9 CDN + `django-htmx` middleware, Tailwind vía CSS ya extraído de `code.html` (no CDN en prod), Pillow para imágenes, WhiteNoise + Gunicorn + Nginx (reusar `Dockerfile`/`nginx.conf` existentes).

## Architecture Decisions
- **Solo Django Templates + HTMX, cero DRF/React:** cada sección dinámica de `code.html` se parte en `*_partial.html` que responde a `HX-Request`. Decisión para mantener deploy simple en Coolify y SEO server-side.
- **Estructura por apps desacopladas:** `core` no depende de nada; `cart` depende de `catalog` solo por FK; `calculator` es independiente y reusable en landing (Sección 5) y en ficha producto.
- **Carrito en sesión para anónimos + DB para autenticados:** `Cart/CartItem` en DB ligado a `User` o `session_key`. Checkout no cobra: genera `Order` en estado `PENDING_WHATSAPP` y construye link `wa.me` con resumen. Sin pagos.
- **Auth estándar Django:** `User` built-in + `Userena? No` — solo `LoginView/LogoutView`, `@login_required` para gestión. Sin registro público en v1 (usuarios creados por admin), evita abuso.
- **Impuestos Ecuador como datos, no hardcode:** modelo `TaxRule` (ad_valorem %, fodinfa 0.5%, ice, iva 15%, isd, tasa_control) + `HSCode` editable desde admin. Calculadora = función pura `calculator/services.py::estimate()` testeable.
- **Conversión `code.html` por secciones:** `base.html` (head, Tailwind, HTMX, header/footer) + `core/home.html` que incluye 8 `{% include %}`; secciones 3 (catálogo) y 5 (calculadora) se vuelven dinámicas primero, resto estáticas en fase 1.

## Mapeo code.html → Templates
```
templates/base.html          ← <head>, tailwind config, HTMX script, nav + footer (extraer de code.html)
core/templates/core/home.html ← contenedor de las 8 secciones
  ├─ partials/_hero.html            ← SECTION 1 (estático)
  ├─ partials/_pillars.html         ← SECTION 2 (estático)
  ├─ catalog/partials/_grid.html    ← SECTION 3 (DINÁMICO HTMX: filtro + spec matrix)
  ├─ partials/_advantages.html      ← SECTION 4 (estático)
  ├─ calculator/partials/_widget.html ← SECTION 5 (DINÁMICO HTMX: form → resultado)
  ├─ partials/_certs.html           ← SECTION 6 (estático)
  ├─ partials/_testimonials.html    ← SECTION 7 (estático)
  └─ partials/_cta.html             ← SECTION 8 (estático + botón WhatsApp carrito)
cart/templates/cart/…        ← drawer/widget flotante HTMX (hx-get / hx-post, hx-swap outerHTML, hx-trigger)
```

Patrón HTMX global: cada `hx-post` incluye `{% csrf_token %}`, respuestas parciales sin `base.html` (detectar con `request.htmx` o `HX-Request`), `hx-target="#id"` + `hx-swap="outerHTML"`, `hx-push-url="false"` en filtros.

## Modelos propuestos

### catalog (gestión productos)
- `Category(slug, nombre, descripcion, orden)`
- `Product(sku único, nombre, slug, categoria FK, descripcion, precio_mayor, precio_menor?, moneda=COP/USD, unidad=m2/pza, stock_m2, stock_minimo, en_stock bool, destacado bool, imagen, ficha_tecnica JSON {pei, antideslizante, grosor_mm, formato}, origen, activo, created/updated)`
- `ProductImage(producto FK, imagen, orden)` — para galería ficha.

### cart (sin pago, solo WhatsApp)
- `Cart(user FK null, session_key, created/updated)` + constraint único por user/session.
- `CartItem(cart FK, product FK, cantidad, precio_unitario_snapshot)` — snapshot congela precio al agregar.
- `Order(codigo único MPI-XXXX, user FK null, nombre_cliente, telefono, ciudad, notas, subtotal, descuento, total, whatsapp_number, mensaje_wa TEXT, estado=PENDING_WHATSAPP/SENT/CONFIRMED/CANCELLED, raw_payload JSON)` + `OrderItem(order FK, product FK null, sku_snapshot, nombre_snapshot, cantidad, precio_snapshot)`.

### calculator (impuestos importación)
- `HSCode(codigo, descripcion, ad_valorem_pct)` — partida arancelaria.
- `TaxRule(nombre, fodinfa_pct=0.5, iva_pct=15, isd_pct, tasa_control_usd, activo, vigencia_desde)` — un registro activo a la vez.
- `QuoteLog(user FK null, session_key, valor_fob, flete, seguro, hs_code FK, ad_valorem_calc, fodinfa_calc, base_iva, iva_calc, total_estimado, created)` — historial, no es orden.

### accounts
- Sin modelo custom en v1: `django.contrib.auth.User` + `Group(gestor_catalogo, vendedor)` + `Profile(user OneToOne, telefono, empresa, rol)` si se necesita teléfono/empresa. Login con `AuthenticationForm`.

## Task List

### Phase 1: Fundación
- [ ] Task 1: Scaffold proyecto `megra_prime/` + settings base/dev/prod, static/media, HTMX + Tailwind local, Dockerfile/Coolify reuse
- [ ] Task 2: Auth `accounts/` — login/logout, `@login_required`, grupos, templates login, redirect next
- [ ] Task 3: `base.html` + `home.html` estática (las 8 secciones tal cual, sin dinámica) — deploy verde

### Checkpoint: Fundación
- [ ] `python manage.py test` pasa, `runserver` renderiza `/` idéntico a `code.html`, login/logout funciona

### Phase 2: Catálogo dinámico HTMX (Sección 3)
- [ ] Task 4: Modelos `catalog` + admin + migraciones + fixtures iniciales (3-5 productos reales)
- [ ] Task 5: Grid HTMX con filtro por categoría/búsqueda/stock (`hx-get`, `hx-trigger="keyup changed delay:300ms"`, paginación)
- [ ] Task 6: CRUD gestión productos (solo staff) con parciales HTMX + validación stock/precio

### Checkpoint: Catálogo
- [ ] Cambiar precio/stock en admin se refleja en `/` sin reload completo; filtros no recargan página

### Phase 3: Carrito → WhatsApp
- [ ] Task 7: Modelos `cart/order` + add/remove/update qty vía HTMX (drawer + badge contador con `hx-swap-oob`)
- [ ] Task 8: Checkout → crea `Order` + genera `https://wa.me/<NUM>?text=<resumen urlencode>` + vista confirmación; vacía carrito

### Checkpoint: Carrito
- [ ] Flujo anónimo completo: agregar → ver drawer → checkout → abre WhatsApp con mensaje correcto; orden queda en DB

### Phase 4: Calculadora impuestos (Sección 5)
- [ ] Task 9: Modelos `HSCode/TaxRule/QuoteLog` + `services.estimate(fob,flete,seguro,hs)` + widget HTMX (`hx-post` → parcial resultado con desglose CIF, ad-valorem, fodinfa, IVA, total)
- [ ] Task 10: Conectar "Agregar cotización al carrito/WhatsApp" desde resultado calculadora

### Checkpoint: Completo
- [ ] End-to-end: filtrar → agregar → calcular impuestos → checkout WhatsApp; tests + build Docker ok; review humano

### Phase 5: Polish (post-MVP)
- [ ] Task 11: Imágenes (Pillow, thumbnails), SEO meta, sitemap, rate-limit calculadora, tests e2e Playwright opcional

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Tailwind CDN en `code.html` no apto prod | Med | Extraer CSS compilado a `static/css/` en Task 1; purgar clases no usadas |
| Reglas impuestos EC cambian (IVA/ISD) | Med | `TaxRule` versionado por vigencia, nunca hardcode; test unitario de `estimate()` |
| Número WhatsApp / formato mensaje rompe URL | Baja | Centralizar en `cart/services.py::build_wa_link()` + test con urlencode |
| Carrito sesión vs usuario duplica items al loguearse | Med | Merge en `user_logged_in` signal (suma cantidades, conserva snapshot menor) |
| Imágenes externas `lh3.googleusercontent` caen | Baja | Descargar a `media/` en Task 4; fallback placeholder |

## Open Questions
- ¿DB prod: Postgres Coolify (recomendado) o seguir SQLite? ¿Nombre proyecto Django?
- ¿Número WhatsApp destino (con código país) y mensaje plantilla?
- ¿IVA vigente a usar (15%) y flete/seguro por defecto en calculadora? ¿Partidas HS iniciales?
- ¿Registro público de usuarios o solo login con cuentas creadas por admin?
- ¿Moneda principal (USD) y si precios llevan IVA incluido o +IVA?

---

# Feature Plan: Catálogo por categoría + alta rápida de categoría/tipo en modales

## Intent (confirmado con el usuario)
- **Outcome:** que el alta de productos esté ordenada por categoría y que categoría/tipo se creen en contexto, sin salir del formulario de producto.
- **Usuario:** el staff/operador del panel (`/webadmin/`).
- **Éxito:** entrar a una categoría, ver sólo sus productos y registrar uno ya dentro de esa categoría; crear categoría/tipo desde un modal y quedar seleccionada al instante.
- **Restricción:** sin agregar dependencias (nada de HTMX al panel ni SPA).
- **Imagen:** basta con **URL** (`Product.imagen_url`); subir archivo es opcional.
- **Extra (al final, nice-to-have):** alta masiva por **Excel**.
- **Fuera de alcance:** editar/eliminar categoría o tipo desde el modal (sólo alta rápida); filtrar por tipo; cambios al catálogo público.

## Overview
Reorganizar la gestión del catálogo en el panel: la **lista de productos** se navega/filtra por categoría y el alta nace dentro de la categoría activa. **Categoría** y **tipo de producto** se crean sin salir del formulario de producto, con modales (`<dialog>` nativo + `fetch`). Las pantallas sueltas `Categorías` y `Tipos` se mantienen como administración completa (listar/editar/eliminar).

## Architecture Decisions
- **Sin HTMX en el panel:** hoy el panel renderiza Django templates + Tailwind CDN + JS vanilla. Los modales usan `<dialog>` nativo + `fetch` contra endpoints JSON nuevos. No se agrega dependencia.
- **Filtro por categoría en servidor (querystring):** `?categoria=<slug>` combinable con `?q=`. La vista arma `categorias` (con conteo de productos), `categoria_activa` y la lista filtrada.
- **Alta en contexto por querystring:** `+ Nuevo en {Categoría}` apunta a `/webadmin/productos/nuevo/?categoria=<slug>`; `ProductForm` llega con `initial["categoria"]` y, al guardar, redirige de vuelta a `/webadmin/productos/?categoria=<slug>` para no perder el contexto.
- **Endpoints JSON de alta rápida reusan `CategoryForm` / `TipoForm`** (misma validación y unicidad de slug ya existentes).
- **El modal sólo crea.** Editar/eliminar sigue en `/webadmin/categorias/` y `/webadmin/tipos/`.

## Contrato JSON (alta rápida)
```
POST /webadmin/categorias/rapida/     (staff)
POST /webadmin/tipos/rapido/          (staff)
CSRF: header X-CSRFToken (token del form de producto)
Body: application/x-www-form-urlencoded  (nombre, slug, descripcion, orden)

200 {"ok": true,  "id": 12, "nombre": "Grifería", "slug": "griferia"}
400 {"ok": false, "errors": {"nombre": ["Ya existe una categoría con este nombre."]}}
```

## Task List

### Fase A: Lista de productos por categoría
- [ ] Task A1: `productos` acepta `?categoria=<slug>` (combinable con `?q=`) + contexto de categorías con conteo y categoría activa; banda de categorías (pills/sidebar) en `productos.html`.
- [ ] Task A2: `+ Nuevo en {Categoría}` → `/webadmin/productos/nuevo/?categoria=<slug>`; `producto_editar` preselecciona la categoría y al guardar vuelve a `?categoria=<slug>`.

### Checkpoint: Fase A
- [ ] Filtrar por categoría muestra sólo sus productos y conserva la búsqueda; "Todas" muestra todo.
- [ ] Registrar desde una categoría deja el producto visible en esa misma categoría tras guardar.

### Fase B: Modales de alta rápida (categoría/tipo) dentro del formulario de producto
- [ ] Task B1: Endpoints JSON `categoria_crear_rapida` / `tipo_crear_rapido` (staff, reusan `CategoryForm`/`TipoForm`, responden 200/400 según contrato).
- [ ] Task B2: Botones `+ Nuevo` junto a los selects `categoria` y `tipo`; modal `<dialog>` con el form; `fetch` POST; al éxito agrega la `<option>` y la selecciona; errores inline sin cerrar el modal.

### Checkpoint: Fase B
- [ ] Crear una categoría desde el modal la deja seleccionada sin recargar la página.
- [ ] Un nombre/slug duplicado muestra el error dentro del modal y no pierde lo escrito.

### Fase C: Verificación
- [ ] Task C1: Tests en `panel/tests.py` (filtro por categoría, alta en contexto, endpoints JSON ok/error, permiso staff).

### Fase D (nice-to-have): Importación masiva por Excel
- [ ] Task D1: `catalog/excel_productos.py` con `build_productos_xlsx()` / `read_productos_xlsx()` siguiendo el patrón de `calculator/excel_templates.py` (openpyxl). Columnas: SKU, nombre, categoría (slug o nombre), tipo, precio_mayor, unidad, stock_cantidad, badge, origen, imagen_url, descripción. Valida encabezados, categorías/tipos existentes y SKU no duplicados; devuelve filas normalizadas.
- [ ] Task D2: Vista + URL `productos/importar/` (POST staff) con resumen "X creados / Y actualizados" y errores por fila; botones "Importar Excel" y "Descargar plantilla" en la lista, con la categoría activa como valor por defecto de las filas.

### Checkpoint: Complete
- [ ] `python manage.py test` en verde.
- [ ] Flujo manual: entrar a categoría → alta → guardar → ver producto en la categoría; crear categoría y tipo desde el modal del formulario.
- [ ] (Fase D) Importar un Excel de prueba y ver los productos creados en su categoría.
- [ ] Review humano del diff.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Slug/nombre duplicado al crear desde modal | Med | Responder 400 con `errors` del ModelForm y pintarlos inline; no cerrar el modal |
| CSRF faltante en `fetch` | Med | Enviar `X-CSRFToken` tomado del `{% csrf_token %}` del formulario de producto |
| Perder el contexto de categoría al guardar | Baja | Mantener `?categoria=<slug>` en el `action`/redirect y en "Cancelar" |
| `<dialog>` con UX pobre en móvil | Baja | Ancho fluido, `max-h` con scroll interno, cerrar con Escape/Cancelar |

## Open Questions
- Al crear desde el modal, ¿basta con `orden=0` (se agrega al final) o el usuario quiere fijar el orden ahí mismo?
- ¿Se quiere color/ícono por categoría más adelante? (fuera de alcance por ahora.)
- Excel (Fase D): ¿la columna "categoría" viene por slug, por nombre, o ambas? ¿SKU repetido = actualizar o error?
- Excel (Fase D): ¿descarga la plantilla con la categoría activa ya puesta en las filas?

---

# Plan (v2): Calidad de fichas, búsqueda global, acciones masivas, duplicados y edición inline

Spec: `tasks/spec-productos-v2.md`. Todo vive dentro de `/webadmin/productos/`
(sin pestañas nuevas de primer nivel). Sin dependencias nuevas; sin JS salvo el modal de alta rápida.

## Architecture Decisions
- **Faltantes = regla pura en `catalog/calidad.py`** (`faltantes_producto`, `clave_nombre`, `q_sin_*`).
  Una sola fuente de verdad; los conteos por categoría se resuelven con `Count(filter=Q(...))`.
- **Contexto en `_ctx_productos`**: `faltantes` por producto, `n_incompletos` por categoría,
  `todas`, `n_duplicados` y `aviso` (leído de `?msg=&n=&cat=`). Los avisos viajan por querystring
  porque el panel no usa el framework de mensajes.
- **Acciones masivas con el atributo `form` de HTML5**: un `<form id="acciones-masivas">` antes de la
  lista y checkboxes `form="acciones-masivas"`; así la lista puede contener el form `#precios` sin anidar forms.
- **Edición inline server-side** (form `#precios` + botón "Guardar precios"): accesible y testeable, sin JS.
- **Borrado destructivo**: `eliminar` masivo con `confirm()`; `producto_eliminar` con página de confirmación.
- **Modal de alta rápida extraído** a `panel/_alta_rapida.html` (ahora tiene 2 consumidores: el formulario
  de producto y el bloque de acciones masivas para crear la categoría destino).

## Task List

### Phase 1: Foundation
- [ ] Task E1: `catalog/calidad.py` — `faltantes_producto`, `clave_nombre`, `q_sin_fotos/caracteristicas/precio`, `contar_grupos_duplicados`. Unit tests en `catalog/tests.py`.
- [ ] Task E2: `_ctx_productos` enriquecido + `productos.html` (badges por fila, `⚠ N` por pill, checkbox `todas=1`, banner de aviso). Tests en `panel/tests.py`.

### Checkpoint: Fase 1
- [ ] `manage.py test panel catalog` en verde. Manual: ver badges y buscar en todas las categorías.

### Phase 2: Core Features
- [ ] Task E3: `productos_acciones` (activar/desactivar/mover/eliminar) + URL + form de acciones + `+ Nueva` categoría reusando `_alta_rapida.html`. Tests: 4 acciones, sin selección, permiso.
- [ ] Task E4: `productos_precios` (precio/stock inline) + URL + form `#precios`. Tests: ok, datos inválidos, permiso.
- [ ] Task E5: `productos_duplicados` + URL + template `productos_duplicados.html` + enlace con conteo en la lista. Tests: agrupación por (categoría, nombre normalizado).
- [ ] Task E6: `producto_eliminar` + URL + template `producto_eliminar.html` + enlace desde duplicados. Tests: borra (GET confirma / POST borra) y permiso.

### Checkpoint: Fase 2
- [ ] Flujo end-to-end: seleccionar, mover, desactivar, eliminar; editar precios; limpiar un duplicado.

### Phase 3: Verification
- [ ] Task E7: Verificación integral (`manage.py check`, `test panel catalog`) + repaso manual en navegador (login → badges → global → masivas → precios → duplicados → borrado).

### Checkpoint: Complete
- [ ] `manage.py check` limpio y `test panel catalog` en verde (el fallo de `calculator` es preexistente).
- [ ] Repaso manual end-to-end documentado.
- [ ] Review humano del diff.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| `Count(filter=Q(...))` con `imagen__isnull` no cuenta igual que la regla Python | Med | Test que compara los conteos anotados con `faltantes_producto` sobre los mismos datos |
| Forms anidados al mezclar acciones masivas y edición de precios | Med | Asociación con el atributo `form` de HTML5; se verifica en el HTML con test |
| Redirect perdiendo el contexto (categoría/q/todas) | Med | `_url_productos_desde_post` reconstruye la URL y todos los forms llevan los hidden |
| Borrado masivo accidental | Alta | `confirm()` en el cliente + POST-only + conteo en el aviso final |
| Escaneo completo para el conteo de duplicados en cada carga | Baja | Un solo `values_list`; escala de la tienda es pequeña (< 1k productos) |

## Open Questions
- (resueltas) Búsqueda global con checkbox `todas=1`; edición inline con form + botón; duplicados por
  (categoría + nombre normalizado); "mover a categoría" permite crear categoría con el modal de alta rápida.

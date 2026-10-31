# Todo: Django + HTMX Webapp

## Task 1: Scaffold proyecto Django + base HTMX/Tailwind
**Description:** Crear proyecto `megra_prime/`, settings dev/prod, apps `core catalog cart calculator accounts`, HTMX CDN + middleware, Tailwind local, WhiteNoise, Dockerfile existente.
**Acceptance criteria:**
- [ ] `python manage.py runserver` levanta y `/` responde 200
- [ ] `GET /` incluye `hx-get/hx-post` funcionales y CSRF ok
**Verification:** `python manage.py check` + `python manage.py test` en verde; manual: inspeccionar header HTMX.
**Dependencies:** None. **Files:** `megra_prime/settings/*`, `requirements.txt`, `templates/base.html`. **Scope:** M

## Task 2: Login usuario/contraseña (accounts)
**Description:** Login/logout con `User` built-in, grupos `gestor_catalogo/vendedor`, `Profile` opcional, plantillas login, protección CRUD.
**Acceptance criteria:**
- [ ] Login válido redirige a `next` o `/gestion/`; inválido muestra error sin 500
- [ ] Rutas gestión exigen login; anónimo → 302 a login
**Verification:** tests `accounts/tests.py` (login ok/ko, guard). Manual: login/logout en navegador.
**Dependencies:** Task 1. **Files:** `accounts/{views,urls,templates,tests}.py`. **Scope:** S

## Task 3: base.html + home estática (8 secciones code.html)
**Description:** Partir `code.html` en `base.html` + 8 includes; sin dinámica aún, paridad visual.
**Acceptance criteria:**
- [ ] `/` renderiza las 8 secciones con estilos/fuentes/iconos iguales
- [ ] Sin errores consola por assets externos
**Verification:** comparativa visual vs `code.html`; `manage.py check`. **Dependencies:** Task 1. **Files:** `templates/base.html`, `core/templates/core/*`. **Scope:** M

## Task 4: Modelos catalog + admin (Category/Product/ProductImage)
**Description:** Modelos con SKU único, precios, stock, ficha JSON, imágenes; admin con filtros; fixtures iniciales.
**Acceptance criteria:**
- [ ] Migraciones aplican limpio; admin crea/edita con imagen
- [ ] `Product.activo=False` oculta de tienda
**Verification:** `migrate` + tests modelo (sku único, precio>0). Manual: CRUD en `/admin/`.
**Dependencies:** Tasks 1-3. **Files:** `catalog/{models,admin,migrations,fixtures}.py`. **Scope:** M

## Task 5: Grid catálogo HTMX (Sección 3 dinámica)
**Description:** `hx-get` filtro categoría/búsqueda/stock + paginación, `hx-trigger` debounce, parcial `_grid.html`.
**Acceptance criteria:**
- [ ] Filtrar no recarga página; URL no se ensucia (`hx-push-url=false`)
- [ ] Cambio de stock en DB se refleja al re-filtrar sin deploy
**Verification:** tests vista (200 parcial vs completa). Manual: escribir en buscador, cambiar categoría.
**Dependencies:** Task 4. **Files:** `catalog/{views,urls,templates/catalog/partials/*}`. **Scope:** M

## Task 6: CRUD gestión productos (staff, HTMX)
**Description:** Crear/editar/desactivar producto desde `/gestion/` solo staff, parciales con errores inline.
**Acceptance criteria:**
- [ ] No-staff recibe 403; validación precio/stock muestra error inline
- [ ] Editar precio actualiza grid público al refrescar fragmento
**Verification:** tests permisos + form inválido. Manual: editar y ver cambio en home.
**Dependencies:** Tasks 2,5. **Files:** `catalog/views_manage.py`, `templates/gestion/*`. **Scope:** M

## Task 7: Carrito sesión+DB con HTMX
**Description:** `Cart/CartItem` (user o session_key), add/remove/qty, drawer + badge con `hx-swap-oob`, snapshot precio.
**Acceptance criteria:**
- [ ] Anónimo agrega sin login; badge se actualiza sin reload
- [ ] Cantidad 0 elimina item; total cuadra con snapshots
**Verification:** tests carrito anónimo/autenticado + merge al login. Manual: agregar/quitar.
**Dependencies:** Task 4. **Files:** `cart/{models,views,services,templates/cart/partials/*}`. **Scope:** M

## Task 8: Checkout WhatsApp (sin pago)
**Description:** Form datos cliente → `Order` PENDING + `build_wa_link()` con resumen urlencode → botón wa.me + confirmación; vacía carrito.
**Acceptance criteria:**
- [ ] Orden persiste con items snapshot aunque producto cambie luego
- [ ] Link wa.me abre con mensaje legible (<2000 chars, truncado seguro)
**Verification:** test `build_wa_link` + test checkout crea orden y limpia carrito. Manual: click → WhatsApp real.
**Dependencies:** Task 7. **Files:** `cart/{models Order, views_checkout, urls}`. **Scope:** M

## Task 9: Calculadora impuestos EC (HSCode/TaxRule/estimate)
**Description:** `services.estimate()` pura (CIF=FOB+flete+seguro; ad-valorem sobre CIF; fodinfa 0.5% sobre CIF; IVA sobre CIF+aranceles; total), widget HTMX Sección 5, `QuoteLog`.
**Acceptance criteria:**
- [ ] `estimate()` coincide con ejemplo manual (tolerancia 0.01)
- [ ] `hx-post` devuelve desglose sin reload; cambia TaxRule y resultado cambia
**Verification:** tests unitarios `estimate` (3 casos) + vista. Manual: cotizar y verificar números.
**Dependencies:** Task 3. **Files:** `calculator/{models,services,views,templates/*}`. **Scope:** M

## Task 10: Calculadora → carrito/WhatsApp
**Description:** Botón "Enviar cotización por WhatsApp" prellena checkout o mensaje directo con desglose.
**Acceptance criteria:**
- [ ] Desglose viaja intacto al mensaje WA
- [ ] QuoteLog guarda cada cálculo con sesión/usuario
**Verification:** test integración calculadora→wa link. Manual: flujo completo.
**Dependencies:** Tasks 8,9. **Files:** `calculator/views.py`, `cart/services.py`. **Scope:** S

## Task 11: Polish prod (media, SEO, Docker Coolify)
**Description:** Pillow thumbnails, `media/` local, meta/OG, sitemap, rate-limit, `collectstatic`, build Docker verde.
**Acceptance criteria:**
- [ ] `docker build` + `collectstatic` ok; imágenes sirven vía WhiteNoise/Nginx
- [ ] Sin Tailwind CDN en prod
**Verification:** `docker compose up --build`, Lighthouse básico. **Dependencies:** Tasks 1-10. **Files:** `Dockerfile`, `nginx.conf`, `static/css/*`. **Scope:** M

---

# Feature: Catálogo por categoría + alta rápida de categoría/tipo en modales

## Task A1: Filtro por categoría en la lista de productos
**Description:** `panel:productos` acepta `?categoria=<slug>` combinable con `?q=`; arma contexto de categorías (con conteo de productos), categoría activa y lista filtrada. `productos.html` muestra una banda de categorías (pills/sidebar) con estado activo, "Todas" y la búsqueda existentes.
**Acceptance criteria:**
- [x] `?categoria=<slug>` lista sólo los productos de esa categoría y respeta `?q=`
- [x] `Todas` (sin `categoria`) lista todo; la categoría activa se marca visualmente
**Verification:** tests `panel/tests.py` (filtro por categoría y combinado con búsqueda). Manual: click en cada categoría.
**Dependencies:** None. **Files:** `panel/views.py`, `panel/templates/panel/productos.html`. **Scope:** M

## Task A2: Alta de producto dentro de la categoría activa
**Description:** El botón de la lista pasa a "+ Nuevo en {Categoría}" y apunta a `/webadmin/productos/nuevo/?categoria=<slug>`. `producto_editar` preselecciona esa categoría (`initial`) y, al guardar, redirige a `/webadmin/productos/?categoria=<slug>`; "Cancelar" vuelve al mismo filtro.
**Acceptance criteria:**
- [x] El select `categoría` llega preseleccionado según el querystring
- [x] Al guardar se vuelve a la lista filtrada y el producto aparece ahí
**Verification:** tests (POST con producto Nuevo ya preseleccionado + redirect a `?categoria=`). Manual: alta en contexto.
**Dependencies:** A1. **Files:** `panel/views.py`, `panel/urls.py`, `panel/templates/panel/producto_form.html`. **Scope:** S

## Task B1: Endpoints JSON de alta rápida (categoría / tipo)
**Description:** `categoria_crear_rapida` y `tipo_crear_rapido` (POST, `@staff_only`) reutilizan `CategoryForm`/`TipoForm`. Responden 200 `{ok, id, nombre, slug}` o 400 `{ok:false, errors}`. URL: `/webadmin/categorias/rapida/` y `/webadmin/tipos/rapido/`.
**Acceptance criteria:**
- [x] POST válido crea el registro y responde 200 JSON con `id/nombre/slug`
- [x] POST inválido responde 400 JSON con `errors`; no-staff no crea (302/403)
**Verification:** tests de endpoint válido, inválido y permiso. Manual: `curl`/fetch.
**Dependencies:** None. **Files:** `panel/views.py`, `panel/urls.py`, `panel/tests.py`. **Scope:** S

## Task B2: Modales de alta rápida en el formulario de producto
**Description:** Botones `+ Nuevo` junto a `categoría` y `tipo` que abren un `<dialog>` con los campos del form (nombre, slug auto, descripción, orden). Submit por `fetch` con `X-CSRFToken`; al éxito agrega la `<option>` al select y la selecciona; errores inline sin cerrar el modal; cierra con Escape/Cancelar.
**Acceptance criteria:**
- [x] Crear categoría desde el modal la deja seleccionada sin recargar
- [x] Error (duplicado/faltante) se muestra en el modal y conserva lo escrito
**Verification:** tests que verifican el markup del modal + endpoint; manual en navegador (crear, error, cancelar).
**Dependencies:** B1. **Files:** `panel/templates/panel/producto_form.html`, `panel/templates/panel/_form_sections.html`. **Scope:** M
**Nota:** el `<dialog>` + JS viven inline en `producto_form.html`; no se creó `_modal_rapido.html` (un solo consumidor). El alta rápida sólo pide nombre y descripción: el slug se deriva y `orden` cae a 0. Mensaje de duplicado suavizado a "Ya existe un registro con ese nombre."

## Task C1: Verificación integral
**Description:** Tests de todo el flujo A/B y `python manage.py check`; repaso manual end-to-end.
**Acceptance criteria:**
- [x] `python manage.py test` en verde
- [x] Flujo manual completo: categoría → alta → guardar → ver producto; crear categoría y tipo desde modales
**Verification:** `python manage.py test panel` + `python manage.py check`. **Dependencies:** A1, A2, B1, B2. **Files:** `panel/tests.py`. **Scope:** S

## Task D1: Lectura/escritura de plantilla Excel de productos
**Description:** `catalog/excel_productos.py` con `build_productos_xlsx()` (plantilla con encabezados estilo calculadora) y `read_productos_xlsx(upload)` que devuelve filas normalizadas. Columnas: SKU, nombre, categoría, tipo, precio_mayor, unidad, stock_cantidad, badge, origen, imagen_url, descripcion. Valida encabezados, números, categoría/tipo existentes y SKU duplicados.
**Acceptance criteria:**
- [x] Plantilla generada abre en Excel y sus encabezados coinciden con el lector
- [x] Fila inválida (sin SKU/nombre, precio no numérico, categoría inexistente) produce error legible
**Verification:** tests unitarios `catalog/tests.py` (idempotencia encabezados + casos de error). **Dependencies:** None. **Files:** `catalog/excel_productos.py`, `catalog/tests.py`. **Scope:** M
**Nota:** `Categoría` vacía es válida en el lector (`categoria=None`); el importador aplica la categoría activa como valor por defecto.

## Task D2: Importación masiva por Excel (staff)
**Description:** Vista `productos_importar` (POST staff) + URL `productos/importar/`; botones "Importar Excel" y "Descargar plantilla" en la lista, usando la categoría activa como valor por defecto. Resumen "X creados / Y actualizados" y errores por fila.
**Acceptance criteria:**
- [x] Subir plantilla válida crea/actualiza productos y muestra el resumen
- [x] Archivo inválido o >5 MB responde con error legible; no-staff no importa
**Verification:** tests (import ok, archivo inválido, permiso). Manual: descargar plantilla → llenar → importar. **Dependencies:** A1, D1. **Files:** `panel/views.py`, `panel/urls.py`, `panel/templates/panel/productos.html`, `panel/tests.py`. **Scope:** M
**Nota:** el resumen y los errores se renderizan en la misma lista (sin framework de mensajes). SLA: 5 MB y 1000 filas.

---

# Feature v2: Calidad de fichas, búsqueda global, acciones masivas, duplicados y edición inline

Spec: `tasks/spec-productos-v2.md` · Plan: `tasks/plan.md` (sección v2).

## Task E1: Reglas de calidad y normalización (`catalog/calidad.py`)
**Description:** Módulo con `faltantes_producto(prod)` (`sin fotos`, `sin características`, `sin precio`), `clave_nombre(nombre)` (sin tildes/mayúsculas/espacios), los `Q` reutilizables `q_sin_fotos/q_sin_caracteristicas/q_sin_precio` y `contar_grupos_duplicados()`.
**Acceptance criteria:**
- [x] Un producto sin imagen ni `imagen_url`, sin características y con precio 0 devuelve los 3 faltantes; uno completo devuelve `[]`
- [x] `clave_nombre` iguala "Teja  Roma" y "teja roma" (y "Grifería"/"griferia")
- [x] Los `Q` reproducen exactamente la regla de `faltantes_producto` sobre los mismos datos
**Verification:** `& ".venv\Scripts\python.exe" manage.py test catalog`. **Dependencies:** None. **Files:** `catalog/calidad.py`, `catalog/tests.py`. **Scope:** S

## Task E2: Badges de faltantes + búsqueda global en la lista
**Description:** `_ctx_productos` agrega `faltantes` por producto, `n_incompletos` por categoría, `todas`, `n_duplicados` y `aviso`. `productos.html`: badges por fila, `⚠ N` en el pill, checkbox "Buscar en todas las categorías" (`todas=1`) y banner de aviso verde/rojo.
**Acceptance criteria:**
- [x] La fila muestra "sin fotos", "sin características" y/o "sin precio" según corresponda
- [x] `?q=...&todas=1` encuentra productos de otra categoría; sin `todas`, el filtro por categoría se respeta
- [x] El pill de una categoría con incompletos muestra `⚠ N`
**Verification:** `manage.py test panel`. Manual: ver badges y buscar en todas. **Dependencies:** E1. **Files:** `panel/views.py`, `panel/templates/panel/productos.html`, `panel/tests.py`. **Scope:** M

## Task E3: Acciones masivas (activar/desactivar/mover/eliminar)
**Description:** Vista `productos_acciones` (POST staff) + URL `productos/acciones/`; form `#acciones-masivas` con checkboxes asociados por el atributo `form`, select de acción, select de categoría destino con `+ Nueva` (reusa `_alta_rapida.html`, extraído del formulario de producto).
**Acceptance criteria:**
- [x] `activar`/`desactivar` cambian `activo` sólo en los ids seleccionados y redirigen con aviso
- [x] `mover` cambia la categoría; sin destino responde aviso de error sin cambios
- [x] `eliminar` borra los seleccionados; sin selección o acción inválida no cambia nada; no-staff no cambia nada
**Verification:** `manage.py test panel`. Manual: seleccionar → aplicar cada acción. **Dependencies:** E2. **Files:** `panel/views.py`, `panel/urls.py`, `panel/templates/panel/productos.html`, `panel/templates/panel/_alta_rapida.html`, `panel/templates/panel/producto_form.html`, `panel/tests.py`. **Scope:** M

## Task E4: Edición inline de precio y stock
**Description:** Vista `productos_precios` (POST staff) + URL `productos/precios/`; form `#precios` con inputs `precio_<pk>`/`stock_<pk>` (con `ids_precio`) y botón "Guardar precios". Valida números ≥ 0 y cuantiza a 2 decimales; si algo es inválido no guarda nada.
**Acceptance criteria:**
- [x] POST válido actualiza `precio_mayor` y `stock_cantidad` de cada fila y redirige con aviso
- [x] Valor no numérico o negativo → aviso de error y BD intacta
- [x] no-staff no cambia nada
**Verification:** `manage.py test panel`. Manual: cambiar un precio y guardar. **Dependencies:** E2. **Files:** `panel/views.py`, `panel/urls.py`, `panel/templates/panel/productos.html`, `panel/tests.py`. **Scope:** S

## Task E5: Detector de duplicados
**Description:** Vista `productos_duplicados` + URL `productos/duplicados/` + template con grupos (≥2 productos del mismo nombre normalizado dentro de la misma categoría), enlaces a Editar/Eliminar, y enlace con conteo en el encabezado de la lista (`🔍 Duplicados (N)`).
**Acceptance criteria:**
- [x] Dos productos con el mismo nombre normalizado en la misma categoría aparecen agrupados
- [x] El mismo nombre en categorías distintas NO se agrupa
- [x] Cada grupo muestra el conteo y los enlaces a editar/eliminar de cada producto
**Verification:** `manage.py test panel`. Manual: crear dos parecidos y verlos agrupados. **Dependencies:** E1, E2. **Files:** `panel/views.py`, `panel/urls.py`, `panel/templates/panel/productos_duplicados.html`, `panel/templates/panel/productos.html`, `panel/tests.py`. **Scope:** M

## Task E6: Borrado de un producto con confirmación
**Description:** Vista `producto_eliminar` + URL `productos/<pk>/eliminar/` + template de confirmación (GET confirma, POST borra); enlace desde la página de duplicados.
**Acceptance criteria:**
- [x] GET muestra la confirmación con el SKU y no borra
- [x] POST borra y redirige a la lista con aviso (preservando la categoría si venía)
- [x] no-staff no borra
**Verification:** `manage.py test panel`. Manual: borrar un duplicado desde la página de duplicados. **Dependencies:** E3. **Files:** `panel/views.py`, `panel/urls.py`, `panel/templates/panel/producto_eliminar.html`, `panel/templates/panel/productos_duplicados.html`, `panel/tests.py`. **Scope:** S

## Task E7: Verificación integral
**Description:** `manage.py check`, `test panel catalog`, y repaso manual end-to-end en navegador (login → badges → búsqueda global → acciones masivas → precios inline → duplicados → borrado).
**Acceptance criteria:**
- [x] `manage.py check` sin issues y `test panel catalog` en verde
- [x] Flujo manual completo verificado con capturas/observaciones
- [x] BD de desarrollo sin residuos de las pruebas manuales
**Hallazgos del repaso manual (corregidos):** (1) `@staff_only` estaba en el helper `_ctx_productos` en vez de en la vista `productos`: anónimo/no-staff recibía 500 en lugar de redirigir a login — sin cobertura de test, se agregó `test_lista_productos_requiere_staff`; (2) con `LANGUAGE_CODE='es-ec'` los Decimal se renderizaban localizados (`68,50`) dentro de `<input type="number">`, y el navegador los vaciaba: guardar precios habría borrado los valores — se corrigió con `|unlocalize` + `{% load l10n %}` y se agregó `test_precios_y_stock_sin_localizar_en_inputs_number`; (3) el aviso de éxito y el de importación no se anunciaban a lectores de pantalla (`role="status"`); (4) el estado vacío decía "Sin productos en <categoría>" aunque hubiera una búsqueda activa. Verificado en navegador: badges, pills `⚠ N`, búsqueda global con `todas=1` y sin ella, acciones masivas (activar/desactivar/mover/eliminar + alta rápida de categoría destino), precios inline, página de duplicados y borrado con confirmación. **Verification:** comandos + navegador. **Dependencies:** E1–E6. **Files:** (ninguno). **Scope:** S

---

# Feature v4: Experiencia Interactiva 3D (Three.js) + GSAP ScrollTrigger + Didáctica Ecuador

Spec: `tasks/spec-experiencia-3d-gsap.md` · Plan: `tasks/plan.md` (sección v4).

## Task G1: Optimizar `base_landing.html` y utilidades CSS GPU
**Description:** Eliminar carga duplicada de Google Fonts Material Symbols, añadir barra de progreso de lectura/scroll, clases utilitarias aceleradas por GPU (`will-change`, línea láser, perspectiva 3D, soporte `prefers-reduced-motion`) y scripts `defer` para GSAP, ScrollTrigger, Three.js y `mpi-experience.js`.
**Acceptance criteria:**
- [x] `Material+Symbols+Outlined` se carga una sola vez en `<head>`
- [x] Scripts `gsap.min.js`, `ScrollTrigger.min.js`, `three.min.js` y `mpi-experience.js` cargan con `defer`
**Verification:** `manage.py test core`. **Dependencies:** None. **Files:** `templates/base_landing.html`. **Scope:** S

## Task G2: Motor `static/js/mpi-experience.js` (Three.js + GSAP + Didáctica + HTMX)
**Description:** Implementar escena 3D interactiva del Hero en Three.js (perfiles/cubiertas/paneles con iluminación dorada, pausa con `IntersectionObserver` fuera del viewport, DPR máx 1.0 en mobile / 1.5 en desktop), animaciones GSAP ScrollTrigger bidireccionales (bajada y subida), revelar de títulos con línea láser, contadores animados, explorador interactivo de capas de materiales y re-animación tras `htmx:afterSwap`.
**Acceptance criteria:**
- [x] Pausado automático del loop WebGL cuando el Hero sale del viewport
- [x] Separación mobile/desktop mediante `gsap.matchMedia()` y respeto a `prefers-reduced-motion`
**Verification:** inspección y tests de integración en `core/tests.py`. **Dependencies:** G1. **Files:** `static/js/mpi-experience.js`. **Scope:** M

## Task G3: Hero 3D y Header inteligente (`_hero.html`, `_header.html`)
**Description:** Integrar `<canvas id="mpi-hero-3d">` en `_hero.html`, añadir capas `data-parallax` bidireccionales, animaciones de título y subtítulo, selectores interactivos en el showcase del hero (preservando la rotación automática y los selectores de test) y estado compacto en `_header.html` al hacer scroll.
**Acceptance criteria:**
- [x] El Hero incluye el canvas 3D, capas parallax y mantiene intactos todos los tests de `HeroRotationTest` y `HeroMediaTest`
**Verification:** `manage.py test core`. **Dependencies:** G1, G2. **Files:** `core/templates/core/partials/_hero.html`, `core/templates/core/partials/_header.html`. **Scope:** M

## Task G4: Pilares Mayoristas + Explorador Didáctico de Materiales (`_pillars.html`)
**Description:** Actualizar `_pillars.html` reflejando las líneas reales que importan en Ecuador (Tejas PVC Roma/Española/Trapezoidal, Wall Panel WPC / Cielo Razo / Policarbonato, Pisos SPC / Porcelanato y Herramientas) e incorporar el laboratorio interactivo **"Anatomía Técnica del Material"** donde el cliente explora capa por capa por qué cada material rinde mejor en el clima de Costa, Sierra y Oriente del Ecuador.
**Acceptance criteria:**
- [x] Selector interactivo de materiales (`data-didactic-tab`) con visualización multicapa animada y beneficios técnicos reales
- [x] Enlaces directos al catálogo filtrado por categoría real (`/catalogo/?categoria=...`)
**Verification:** `manage.py test core`. **Dependencies:** G2. **Files:** `core/templates/core/partials/_pillars.html`. **Scope:** M

## Task G5: Ruta Logística Ecuador, Calculadora Real y Secciones de Confianza (`_advantages.html`, `_calculator.html`, `_certs.html`, `_testimonials.html`, `_mission_vision.html`, `_cta.html`)
**Description:** Incorporar la línea de tiempo interactiva de importación directa (Fábrica → Puerto Guayaquil/Posorja → Bodega Matriz Ambato → Despacho Nacional 24-48h) en `_advantages.html`, actualizar `_calculator.html` con cálculo técnico real por línea (Tejas PVC, Wall Panel WPC, Pisos SPC/Porcelanato, Cielo Razo, Policarbonato), contextualizar `_testimonials.html` a constructoras y proyectos en Ecuador, y añadir parallax bidireccional y revelación de títulos en todas las secciones.
**Acceptance criteria:**
- [x] Todas las secciones tienen `data-animate="title"` y `data-parallax` o `data-stagger-group`
- [x] La calculadora calcula unidades/planchas/cajas reales según la línea elegida y anima el resultado
**Verification:** `manage.py test core`. **Dependencies:** G2. **Files:** `core/templates/core/partials/_advantages.html`, `_calculator.html`, `_certs.html`, `_testimonials.html`, `_mission_vision.html`, `_cta.html`, `_footer.html`. **Scope:** M

## Task G6: Animaciones en Catálogo, Tarjetas y Ficha de Producto (`catalogo.html`, `_card.html`, `detalle.html`)
**Description:** Añadir animaciones de entrada y micro-interacción en `_card.html`, cabecera animada y transición suave con HTMX en `catalogo.html`, y animación de entrada + cambio fluido de imagen/color en `detalle.html` sin alterar las aserciones de `catalog/tests.py`.
**Acceptance criteria:**
- [x] `manage.py test catalog` pasa al 100% (incluyendo conteo exacto de clases en `_card.html` y respuesta parcial HTMX)
**Verification:** `manage.py test catalog`. **Dependencies:** G2. **Files:** `catalog/templates/catalog/catalogo.html`, `catalog/templates/catalog/_card.html`, `catalog/templates/catalog/detalle.html`. **Scope:** M

## Task G7: Suite de Tests y Verificación Integral
**Description:** Escribir tests automatizados en `core/tests.py` para verificar la presencia del motor 3D/GSAP, el explorador didáctico, la ausencia de fuentes duplicadas y correr toda la suite de tests.
**Acceptance criteria:**
- [x] `manage.py check` sin errores
- [x] `manage.py test core catalog` 100% en verde
**Verification:** `& ".venv\Scripts\python.exe" manage.py test core catalog`. **Dependencies:** G1–G6. **Files:** `core/tests.py`. **Scope:** S

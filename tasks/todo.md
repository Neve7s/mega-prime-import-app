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

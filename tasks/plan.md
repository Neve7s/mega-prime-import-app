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

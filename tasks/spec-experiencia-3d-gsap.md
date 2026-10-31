# Spec: Experiencia Interactiva 3D (Three.js) + Animaciones GSAP / ScrollTrigger + Didáctica B2B Ecuador

## Objective
Dar vida a la web pública de **MEGA PRIME IMPORT LGM (Ecuador)** (`index` / `home`, `catalogo` y `detalle`) con una experiencia visual e interactiva de alto nivel usando **GSAP + ScrollTrigger** y **Three.js**, diseñada para:
1. Mostrar de forma **didáctica** las ventajas constructivas de las líneas que realmente importan y distribuyen en Ecuador: **Tejas y Cubiertas PVC (Roma, Española, Trapezoidal), Cielorrasos y Policarbonato Alveolar, Pisos SPC y Porcelanato, Revestimientos Wall Panel WPC, Accesorios y Herramientas**.
2. Implementar **efectos Parallax bidireccionales** (al bajar y subir el scroll) y **animaciones cinemáticas en títulos** con estética arquitectónica e industrial.
3. Garantizar **rendimiento óptimo (60 FPS, cero lag)** tanto en **mobile** como en **desktop**, pausando WebGL fuera del viewport, usando `gsap.matchMedia()`, respetando `prefers-reduced-motion`, y limpiando cargas duplicadas en `<head>`.

## Tech Stack
- **Backend / Templates:** Django 5.x + Django Templates + HTMX 1.9
- **Animación 2D / Scroll:** GSAP 3.12.5 + ScrollTrigger 3.12.5 (CDN oficial `cdnjs`, carga con `defer`)
- **Gráficos 3D:** Three.js r128 (CDN oficial `cdnjs`, carga con `defer` e inicialización perezosa en `<canvas id="mpi-hero-3d">`)
- **Script propio:** `static/js/mpi-experience.js` (modular, sin dependencias de build, compatible con WhiteNoise y HTMX)

## Commands
- **Check:** `& ".venv\Scripts\python.exe" manage.py check`
- **Tests:** `& ".venv\Scripts\python.exe" manage.py test core catalog`
- **Full Suite:** `& ".venv\Scripts\python.exe" manage.py test`

## Project Structure
```
templates/base_landing.html                  → Head optimizado, CSS de animaciones GPU, scripts GSAP/Three/mpi-experience.js
static/js/mpi-experience.js                  → Motor Three.js (Hero 3D) + GSAP ScrollTrigger + Parallax + Didáctica + HTMX hooks
core/templates/core/partials/_hero.html      → Hero con Canvas 3D, parallax multicapa, switcher didáctico y showcase
core/templates/core/partials/_pillars.html   → Pilares + explorador didáctico interactivo de materiales reales en Ecuador
core/templates/core/partials/_advantages.html→ Ruta de importación directa a Ecuador (Puerto → Ambato → Obra Nacional)
core/templates/core/partials/_calculator.html→ Calculadora interactiva adaptada a líneas reales (Tejas, WPC, SPC, Cielo Razo)
core/templates/core/partials/_certs.html     → Sellos técnicos con revelación escalonada
core/templates/core/partials/_testimonials.html → Testimonios reales contextualizados en Ecuador (Quito, Guayaquil, Ambato, Cuenca)
core/templates/core/partials/_cta.html       → CTA final con parallax y micro-interacciones
catalog/templates/catalog/catalogo.html      → Títulos animados y re-animación suave tras filtrado HTMX
catalog/templates/catalog/_card.html         → Tarjetas con micro-interacción 3D sutil y revelación por scroll
catalog/templates/catalog/detalle.html       → Transiciones suaves en galería, colores y pestañas
```

## Code Style
- **HTML Data Attributes para Hooks GSAP:**
  - `data-animate="title"` para títulos con revelación arquitectónica y línea láser dorada (`data-laser-line`).
  - `data-parallax="<velocidad>"` para capas con parallax bidireccional (`scrub: 0.6`).
  - `data-stagger-group` y `data-stagger-item` para grillas y tarjetas que entran/salen suavemente.
  - `data-didactic-tab` y `data-didactic-layer` para el explorador interactivo de capas de materiales.
- **Regla de Oro de Rendimiento:**
  - Solo animar `transform` (`translate3d`, `scale`, `rotate`) y `opacity`.
  - Pausar el loop de Three.js (`requestAnimationFrame`) automáticamente con `IntersectionObserver` y `document.visibilitychange`.
  - Limitar `renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1 : 1.5))`.

## Testing Strategy
- Tests de integración en `core/tests.py` y `catalog/tests.py` verificando:
  - Carga del motor `mpi-experience.js` y librerías con `defer`, sin duplicación de fuentes en `base_landing.html`.
  - Presencia del `<canvas id="mpi-hero-3d">`, atributos `data-animate`, `data-parallax` y sección didáctica de materiales ecuatorianos.
  - Preservación de toda la funcionalidad existente (SEO, JSON-LD, rotación del hero, filtros HTMX, carrito y calculadora).

## Boundaries
- **Always:** Mantener todos los tests existentes en verde, respetar variables dinámicas de `site_settings`, usar `defer` en scripts externos.
- **Ask first:** Cambiar modelos de base de datos o agregar paquetes Python.
- **Never:** Bloquear el renderizado inicial si el CDN falla (el contenido debe ser 100% legible sin JS) o animar propiedades que causen reflow (`top`, `left`, `width`, `height`).

## Success Criteria
1. `base_landing.html` elimina la carga duplicada de Google Fonts Material Symbols y carga GSAP + ScrollTrigger + Three.js + `mpi-experience.js` con `defer`.
2. El Hero presenta una escena 3D Three.js fluida (ensamble arquitectónico de perfiles/cubiertas/paneles con iluminación dorada) que responde al cursor/scroll y se pausa fuera del viewport.
3. Todos los títulos principales (`h1`, `h2`) tienen animación de revelación y todas las secciones del `home` tienen parallax bidireccional (bajada y subida).
4. La web explica didácticamente las líneas reales de importación en Ecuador (Tejas PVC, Wall Panel WPC, Pisos SPC/Porcelanato, Cielo Razo, Policarbonato, Accesorios y Herramientas) con un módulo interactivo de capas ("Anatomía del Material") y ruta logística Ecuador.
5. `python manage.py check` y `python manage.py test` pasan sin errores.

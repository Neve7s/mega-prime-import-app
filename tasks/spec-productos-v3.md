# Spec v3 — Rediseño de la lista de Productos

## Objetivo
Que `/webadmin/productos/` se vea como software serio y no como una página de
pruebas: una tabla legible, acciones claras, iconos vectoriales y edición en
modal. Sin dependencias nuevas (Tailwind CDN + JS nativo del navegador).

## Decisiones (aprobadas por el cliente)
| Tema | Decisión |
|------|----------|
| Acción masiva | Se elimina por completo (vista, URL, formulario y tests). |
| Edición | Modal `<dialog>` que carga el formulario por `fetch`; la URL `/productos/<pk>/` sigue funcionando como respaldo. |
| Iconos | SVG en línea (estilo Lucide) con color por acción. Se retiran los emoji de la interfaz. |
| Excel | Botón «Importar Excel» en la cabecera que abre un panel (`<dialog>`). |

## Alcance
1. **Tabla** con columnas: Producto (miniatura, nombre, SKU, tipo, badges de
   ficha incompleta), Categoría, Estado, Precio USD, Stock y Acciones.
   Precio y stock siguen siendo editables en línea mediante un único formulario
   `#precios` (los inputs se asocian con `form="precios"`, porque un `<form>` no
   puede envolver filas de una tabla).
2. **Cabecera**: título con contador, botones secundarios (Categorías, Tipos,
   Duplicados, Importar Excel) y primario «Nuevo producto».
3. **Filtros**: píldoras por categoría con contador y aviso `⚠ N`, más barra de
   búsqueda con la casilla «todas las categorías».
4. **Modal de edición**: `data-editar-producto` + `fetch(?modal=1)`, reinyecta
   los `<script>` del fragmento (colores/características e imagen) y cae a la
   página completa si el `fetch` falla.
5. **Iconos**: `{% icon "nombre" %}` desde `panel/templatetags/panel_ui.py`.
6. **Shell**: navegación con iconos SVG, estado activo y botones unificados.

## Fuera de alcance
- Cambiar el modelo de datos, permisos o el flujo de importación.
- Rehacer las páginas de categorías y tipos (solo se enlazan).

## Criterios de aceptación
- [ ] La lista no contiene ninguna referencia a `acciones-masivas`.
- [ ] La tabla renderiza una fila por producto con acciones Editar/Eliminar.
- [ ] Editar abre el modal con el formulario completo y guarda correctamente.
- [ ] `/productos/<pk>/` sin `modal=1` sigue mostrando la página completa.
- [ ] El panel de Excel solo aparece al pulsarlo y la importación funciona.
- [ ] Precio y stock se guardan juntos y sin localizar (`1234.50`).
- [ ] No quedan emoji en las pantallas tocadas; los iconos son SVG con color.
- [ ] `manage.py check` limpio y `panel catalog` en verde.

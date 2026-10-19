# Spec: Colaboradores con acceso por sección

## Objective
Que el **dueño** del panel (`is_staff` / `is_superuser`) cree **colaboradores** (empleados) y
decida exactamente qué secciones del panel ve cada uno. Un empleado es un usuario normal
(`is_staff=False`, sin acceso a `/admin`) que solo puede entrar a las secciones asignadas,
tanto en el nav como por URL directa.

Decisiones aprobadas con el cliente:
- **Productos** = módulo completo (productos, categorías, tipos, precios, alta rápida, Excel).
- **Ajustes del sitio** y **Colaboradores** = solo el dueño.
- Empleados **sin** acceso a `/admin` (nunca `is_staff=True`).

## Modelo
`panel.models.AccesoPanel` (OneToOne con `AUTH_USER_MODEL`, `related_name="acceso_panel"`):

| campo | tipo | nota |
|---|---|---|
| `usuario` | OneToOne | CASCADE |
| `calculadora` | bool | sección Calculadora |
| `pedidos` | bool | Punto de venta + detalle de pedido |
| `codigos` | bool | Códigos WhatsApp |
| `productos` | bool | Productos + Categorías + Tipos |
| `activo` | bool | si es False no puede entrar al panel |
| `creado` / `actualizado` | datetime | auto |

`AJUSTES` y `COLABORADORES` no son campos: son exclusivos del dueño.

## Reglas de acceso (`panel/accesos.py`)
```
SECCIONES = (("calculadora",…), ("pedidos",…), ("codigos",…), ("productos",…))
es_dueno(user)      -> user.is_superuser or user.is_staff
acceso(user)        -> AccesoPanel activo del usuario, o None
puede(user, clave)  -> True si es dueño; si no, perfil activo con ese flag
tiene_panel(user)   -> es_dueno o acceso(user) != None
primera_seccion(user)-> primera sección marcada (para el landing)
```

Decoradores:
- `@seccion_requerida("productos")` → sin sesión: redirect a login; sin perfil: redirect a login;
  sin permiso: `panel/sin_acceso.html` con **HTTP 403**.
- `@staff_only` se conserva y significa **solo dueño** (Ajustes, Colaboradores).

## Mapa vista → sección
| sección | vistas |
|---|---|
| (landing) | `dashboard` (dueño ve tablero; empleado redirige a su primera sección) |
| productos | `productos`, `productos_precios`, `productos_duplicados`, `producto_eliminar`, `productos_importar`, `productos_plantilla`, `producto_editar`, `categorias`, `categoria_editar`, `categoria_eliminar`, `categoria_crear_rapida`, `tipos`, `tipo_editar`, `tipo_eliminar`, `tipo_crear_rapido` |
| pedidos | `pedidos`, `pedido_detalle` |
| codigos | `codigos`, `codigo_crear`, `codigo_detalle` |
| calculadora | `calculadora`, `calculadora_guardar`, `calculadora_plantilla`, `calculadora_importar`, `calculadora_reporte` |
| solo dueño | `ajustes`, `colaboradores*` |

## Login
`PanelLoginView` acepta a quien `tiene_panel(user)`; si no, error
"Esta cuenta no tiene acceso al panel." (igual que hoy).

## Nav
Template tags en `panel_ui`: `{% puede_seccion request.user "productos" as ver_productos %}` y
`{% es_dueno request.user as dueno %}`. El nav:
- "Tablero" solo dueño.
- Tienda: Punto de venta / Códigos / Productos / Calculadora según permiso.
- Sistema: Ajustes y Colaboradores solo dueño.
- La barra de búsqueda del header solo aparece si el usuario puede Productos.
- Empleado: nav con solo sus secciones; nunca ve "Sistema".

## Página Colaboradores
Rutas:
- `colaboradores/` → lista (usuario, nombre, secciones, activo, último acceso) + botón Nuevo.
- `colaboradores/nuevo/` y `colaboradores/<pk>/` → formulario alta/edición.
- `colaboradores/<pk>/estado/` → POST activar/desactivar.
- `colaboradores/<pk>/eliminar/` → POST con página de confirmación (borra User).

Formulario: `username`, `first_name` (opcional), `password` (obligatoria al crear; vacía al
editar = no cambiar), checkboxes de las 4 secciones, `activo`. Validaciones:
- username único (case-insensitive) excluyendo la instancia.
- ≥ 1 sección marcada.
- contraseña con `validate_password`; en edición solo si viene.
- Nunca se crea/edita un `is_staff` desde aquí (el queryset es `AccesoPanel`).

## UI
Mismo lenguaje visual que Productos v3: `panel-dialog` no aplica (páginas), `.btn`,
`.icon-btn`, tarjetas, iconos SVG con `{% icon %}`. Añadir el icono `colaboradores`
(personas) a `panel_ui`.

## Success criteria
1. Superuser/staff ve las 5 secciones + Ajustes + Colaboradores.
2. Empleado con solo Calculadora: login OK, `/webadmin/` redirige a `/webadmin/calculadora/`,
   nav solo muestra Calculadora, `/webadmin/productos/` y `/webadmin/pedidos/` → 403.
3. Empleado con Productos: nav muestra Productos, puede listar/editar/crear; Calculadora → 403.
4. Empleado desactivado o sin perfil: no puede iniciar sesión en el panel (el login de la web
   pública no se ve afectado).
5. Dueño crea colaborador desde el panel, define secciones y contraseña; el colaborador entra
   con ellas.
6. Un colaborador nunca obtiene `is_staff` ni entra a `/admin` (403/redirect).
7. `manage.py check` limpio, `panel catalog` en verde, y tests nuevos cubren 1–6.
8. Nada de la web pública cambia (login/registro de clientes intactos).

## Boundaries
- Always: migración nueva, tests por cada regla, 403 (no 404) cuando falta permiso.
- Ask first: cambiar el modelo de usuario, añadir dependencias, tocar `accounts`.
- Never: marcar empleados como `is_staff`, dar Ajustes/Colaboradores a un empleado,
  romper los tests existentes de Productos.

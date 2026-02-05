# Módulo de Producción Textil - PRD

## Problema Original
Crear un módulo de producción textil con las siguientes tablas y relaciones:
- **Marca, Tipo, Entalle, Tela, Hilo**: Tablas maestras simples
- **Tallas (catálogo)**: Tabla maestra de tallas con orden
- **Colores (catálogo)**: Tabla maestra de colores con código hex
- **Modelo**: Con relaciones muchos-a-uno con Marca, Tipo, Entalle, Tela, Hilo
- **Registro**: Con N Corte, Fecha Creación, relación con Modelo, Curva (texto), Estado, Urgente

## Flujo de Tallas y Colores
1. **Paso 1 - En Corte**: Al crear registro, seleccionar tallas del catálogo con cantidades
2. **Paso 2 - En Lavandería**: Distribuir cantidades por colores usando botón de paleta
   - Validación: suma de colores no puede exceder cantidad total de la talla

## Preferencias del Usuario
- Diseño corporativo minimalista claro con dark mode
- Todo en español
- Estados: Para Corte, Corte, Para Costura, Costura, Para Atraque, Atraque, Para Lavandería, Muestra Lavanderia, Lavandería, Para Acabado, Acabado, Almacén PT, Tienda
- Inputs numéricos sin flechitas (spinners)
- Eliminación directa sin confirmación

## Arquitectura

### Backend (FastAPI + MongoDB)
- `/api/marcas`, `/api/tipos`, `/api/entalles`, `/api/telas`, `/api/hilos` - CRUDs básicos
- `/api/tallas-catalogo` - CRUD tallas maestras
- `/api/colores-catalogo` - CRUD colores maestros con hex
- `/api/modelos` - CRUD modelos con relaciones
- `/api/registros` - CRUD registros con tallas y distribución colores
- `/api/estados` - Lista de estados
- `/api/stats` - Estadísticas dashboard
- `/api/inventario` - CRUD items de inventario
- `/api/inventario-ingresos` - Entradas de inventario
- `/api/inventario-salidas` - Salidas de inventario con método FIFO
- `/api/inventario-ajustes` - Ajustes de inventario
- **NUEVO** `/api/servicios-produccion` - CRUD servicios de producción (nombre, secuencia)
- **NUEVO** `/api/personas-produccion` - CRUD personas de producción (nombre, servicios[], teléfono, activo)
- **NUEVO** `/api/movimientos-produccion` - CRUD movimientos de producción (vinculados a registros)

### Frontend (React + Shadcn/UI)
- Dashboard con contadores
- CRUDs para todas las entidades
- Registros con flujo de 2 pasos
- Dark/Light mode toggle
- Módulo de Inventario FIFO con navegación separada
- **NUEVO** Sección "Maestros" con Servicios y Personas
- **NUEVO** Movimientos de Producción integrados en formulario de Registro

## Implementado

### Enero 2025 - MVP
- ✅ Backend completo con todos los endpoints
- ✅ Frontend con todas las páginas y CRUDs
- ✅ Catálogo de Tallas y Colores
- ✅ Flujo de 2 pasos para tallas/colores
- ✅ Validación de cantidades en distribución
- ✅ Dark mode toggle
- ✅ Inputs sin spinners
- ✅ Eliminación directa
- ✅ Accesibilidad mejorada en Dialogs (DialogDescription)

### Enero 2025 - Módulo Inventario FIFO
- ✅ CRUD de Items de Inventario (código, nombre, descripción, unidad_medida, stock_minimo)
- ✅ **Campo Categoría** en items (Telas, Avios, Otros) con badges de colores
- ✅ **Control por Rollos** para telas:
  - Checkbox "Control por Rollos" al crear/editar items de categoría Telas
  - Ingreso con múltiples rollos: cada rollo tiene N° Rollo, Metraje, Ancho, Tono
  - Página dedicada `/inventario/rollos` para ver todos los rollos con filtros y resumen
  - Stock se calcula automáticamente sumando metrajes de todos los rollos
- ✅ **Salidas por Rollo**: Al crear salida de item con rollos, se debe seleccionar el rollo específico
  - Selector de rollo muestra: N° Rollo, Tono, Metraje disponible
  - Trazabilidad completa: saber qué tono/rollo se usó en cada producción
  - El metraje disponible del rollo se descuenta automáticamente
- ✅ Ingresos de inventario (entradas con costo unitario, proveedor, documento)
- ✅ Salidas de inventario con método FIFO (calcula costo automáticamente)
- ✅ Vinculación de salidas con registros de producción
- ✅ Tabla de salidas integrada en formulario de registro (con selector de rollo)
- ✅ Ajustes de inventario (entrada/salida con motivo)
- ✅ Control de stock mínimo con alertas visuales
- ✅ **Reporte de Movimientos** - Vista general con filtros
- ✅ **Kardex de Inventario** - Historial detallado por item con saldos
- ✅ Navegación sidebar con sección "Inventario FIFO" completa

### Enero 2025 - Módulo de Movimientos de Producción
- ✅ **Servicios de Producción**: CRUD completo en `/maestros/servicios`
  - Campos: nombre, secuencia (para ordenar manualmente)
  - Ordenamiento drag & drop con @dnd-kit
  - **Sin campo tarifa** (tarifas se configuran en Personas)
- ✅ **Personas de Producción**: CRUD completo en `/maestros/personas`
  - Campos: nombre, teléfono, activo, orden
  - **Tarifas por servicio**: Cada persona tiene tarifa específica por cada servicio que realiza
  - Estructura: servicios: [{servicio_id, tarifa}]
  - Toggle para activar/desactivar personas
  - Badges mostrando servicios con tarifas (Ej: "Corte (S/ 0.75)")
- ✅ **Movimientos de Producción** integrados en RegistroForm y página dedicada:
  - Tabla de movimientos vinculados al registro
  - Campos: servicio, persona, fecha inicio, fecha fin, cantidad, tarifa_aplicada
  - **Filtro dinámico**: al seleccionar servicio, personas se filtran
  - **Pre-llenado de tarifa**: al seleccionar persona, tarifa se pre-llena desde configuración persona-servicio
  - **Tarifa editable**: usuario puede ajustar tarifa en cada movimiento
  - Costo calculado automáticamente (cantidad × tarifa_aplicada)
  - Vista general en `/maestros/movimientos` con filtros avanzados
- ✅ **Reporte de Productividad** en `/maestros/productividad`
  - Resumen de prendas y costos por persona y servicio
  - Filtros por fecha
- ✅ Nueva sección "Maestros" en el menú lateral

### Enero 2025 - Rutas de Producción y BOM
- ✅ **Rutas de Producción**: CRUD completo en `/maestros/rutas`
  - Define secuencias de etapas (servicios) para modelos
  - Drag & drop para reordenar etapas
  - Validación: no se puede eliminar ruta si hay modelos usándola
- ✅ **Modelos con BOM y Ruta**:
  - Formulario con 3 pestañas: General, Materiales, Producción
  - **Lista de Materiales (BOM)**: Items de inventario con cantidades estimadas
  - **Servicios Requeridos**: Checkboxes para seleccionar servicios del modelo
  - **Ruta de Producción**: Selector para asignar ruta al modelo
  - Columnas nuevas en tabla: Ruta, Materiales, Servicios
- ✅ **Estados Dinámicos en Registros**:
  - Si el modelo tiene ruta, los estados del registro vienen de las etapas de la ruta
  - El registro solo puede avanzar al siguiente estado de la ruta
  - Validación: requiere movimiento con fechas antes de cambiar estado
  - Endpoint: `GET /api/registros/{id}/estados-disponibles`

### Enero 2025 - Migración a PostgreSQL
- ✅ **Migración completa de MongoDB a PostgreSQL**
  - Todas las tablas ahora con prefijo `prod_`
  - Backend refactorizado usando `asyncpg` y `databases`
  - Esquema SQL creado para todas las entidades
  - Datos migrados exitosamente

### Enero 2025 - Colores Generales y Mejoras
- ✅ **Refactorización de Colores Generales**:
  - Nueva tabla `prod_colores_generales` para categorías de colores
  - CRUD completo en `/colores-generales` con validación de duplicados
  - Validación: no se puede eliminar si hay colores usando el color general
  - `prod_colores_catalogo` ahora tiene `color_general_id` (FK)
  - Formulario de colores usa **Select** en lugar de Input de texto
  - API retorna `color_general_nombre` en listado
- ✅ **Edición en módulo Inventario**:
  - Editar Ingresos (proveedor, documento, observaciones, costo unitario)
  - Editar Salidas (registro vinculado, observaciones)
  - Editar Ajustes (motivo, observaciones)
- ✅ **Hilos Específicos por Registro**:
  - Nueva tabla `prod_registro_hilos`
  - Página `/registros/:id/hilos` para gestionar hilos por registro
  - Botón "Hilos" en tabla de registros
- ✅ **Diálogo de Salida de Múltiples Rollos** (`SalidaRollosDialog.jsx`):
  - Selector de tela (items con control_por_rollos)
  - Filtros por ancho y tono
  - Selección múltiple con checkboxes
  - Opción de uso parcial por rollo
  - Procesamiento batch de salidas

### Enero 2025 - Ordenamiento Manual y Hilos Específicos
- ✅ **Ordenamiento Manual (Drag & Drop)** en tablas de catálogo:
  - Componente reutilizable `SortableTable.jsx` usando `@dnd-kit`
  - Tablas habilitadas: Marcas, Tipos, Entalles, Telas, Hilos, Tallas, Colores, Colores Generales, Hilos Específicos
  - Campo `orden` en todas las tablas
  - Endpoint genérico `PUT /api/reorder/{tabla}` para guardar orden
  - Persistencia automática al soltar
- ✅ **Nueva tabla "Hilos Específicos"**:
  - Catálogo independiente de hilos especiales para registros
  - Campos: nombre, código, color, descripción
  - CRUD completo en `/hilos-especificos`
  - Enlace en menú lateral con icono Sparkles

### Enero 2025 - Sistema de Autenticación y Permisos
- ✅ **Autenticación JWT Completa**:
  - Login con usuario/contraseña (sin OAuth/Google)
  - Token JWT con expiración de 24 horas (algoritmo HS256)
  - Hash de contraseñas con bcrypt (passlib)
  - Endpoints: `POST /api/auth/login`, `GET /api/auth/me`, `PUT /api/auth/change-password`
- ✅ **Sistema de Roles**:
  - **Admin**: Acceso total, puede gestionar usuarios
  - **Usuario**: Permisos personalizables por tabla (CRUD)
  - **Lectura**: Solo puede ver datos
- ✅ **Gestión de Usuarios** (solo admin):
  - CRUD completo en `/usuarios`
  - Crear, editar, eliminar usuarios
  - Activar/desactivar usuarios
  - Resetear contraseña (nueva = username + "123")
  - Endpoint estructura de permisos: `GET /api/permisos/estructura`
- ✅ **Permisos Granulares por Tabla**:
  - Cada usuario tipo "usuario" puede tener permisos específicos
  - Permisos CRUD (ver, crear, editar, eliminar) por cada tabla
  - Estructura de permisos organizada por categorías
  - Dialog de configuración de permisos con checkboxes
- ✅ **Frontend Protegido**:
  - `AuthProvider` context para estado de autenticación
  - `ProtectedRoute` redirige a `/login` si no autenticado
  - `PublicRoute` redirige a `/` si ya autenticado
  - Menú de usuario en header con dropdown (logout, gestión usuarios)
  - Persistencia de token en localStorage
- ✅ **Usuario Administrador**: eduard / eduard123

### Enero 2025 - Historial de Actividad y UI
- ✅ **Historial de Actividad Completo**:
  - Nueva tabla `prod_actividad_historial`
  - Registro automático de: login, crear, editar, eliminar, cambio de contraseña
  - Almacena datos anteriores y nuevos para cada acción
  - Página `/historial-actividad` con diseño tipo timeline
  - Agrupación por fecha (Sábado 24 de Enero, etc.)
  - Filtros por usuario, tipo de acción, fechas
  - Click en registro navega al módulo correspondiente
  - Badges con datos relevantes
- ✅ **Cambio de Contraseña por Usuario**:
  - Admin puede establecer contraseña específica para cualquier usuario
  - Cada usuario puede cambiar su propia contraseña desde el menú
- ✅ **Sidebar Colapsable**:
  - Botón para colapsar/expandir menú lateral
  - Modo colapsado muestra solo iconos
  - Persistencia de preferencia en localStorage
  - Tooltips en modo colapsado

### Enero 2025 - Optimización para Producción
- ✅ **Limpieza de Código**:
  - Eliminada tabla `prod_registro_hilos` (obsoleta)
  - Eliminados endpoints de registro-hilos
  - Eliminada página RegistroHilos.jsx
  - Eliminada ruta /registros/:id/hilos
  - Limpieza de caché Python
  - Corrección de errores de linting

### Febrero 2025 - Módulo BOM Avanzado
- ✅ **Drag-and-Drop en BOM**:
  - Reordenamiento de líneas de BOM mediante arrastrar y soltar
  - Componente `SortableTable.jsx` actualizado para soportar items con `__tempId` (drafts)
  - Ícono de arrastre (GripVertical) en cada fila
  - Endpoint `PUT /api/modelos/{modeloId}/bom/reorder` funcionando
  - Guardado automático del nuevo orden
- ✅ **Correcciones de bugs**:
  - Botón "Agregar línea" con `type="button"` para evitar submit del formulario
  - Endpoint de reorder movido antes de rutas con `{linea_id}` para evitar conflicto de rutas

### Febrero 2025 - FASE 2B: Frontend UI para Reservas + Requerimiento
- ✅ **Nuevo componente `RegistroDetalleFase2.jsx`** con 4 sub-pestañas:
  - **Tallas (Corte)**: Grid de inputs por talla con autosave (debounce), muestra total de prendas
  - **Requerimiento**: Cards resumen + tabla detallada, botón "Regenerar desde BOM"
  - **Reservas**: Lista items pendientes, input cantidad a reservar, historial de reservas
  - **Salidas**: Panel dual (items pendientes + formulario nueva salida), selector de rollo para TELA, historial de salidas
- ✅ **Integración en `Registros.jsx`**: Dialog de detalle ahora tiene tabs "Información General" y "Materia Prima"
- ✅ **Badges de estado**: PENDIENTE, PARCIAL, COMPLETO con colores distintivos
- ✅ **Indicador TELA**: Badge "TELA" en items con `control_por_rollos=true`

### Febrero 2025 - FASE 2A: Reservas + Requerimiento MP (Backend)
- ✅ **Nuevas tablas creadas** en schema `produccion`:
  - `prod_registro_tallas` - Cantidades reales por talla (corte)
  - `prod_registro_requerimiento_mp` - Resultado de explosión BOM
  - `prod_inventario_reservas` - Cabecera de reservas
  - `prod_inventario_reservas_linea` - Líneas de reservas
  - Columna `talla_id` agregada a `prod_inventario_salidas`

- ✅ **Endpoints implementados**:
  - `GET/POST/PUT /api/registros/{id}/tallas` - CRUD tallas reales (autosave)
  - `POST /api/registros/{id}/generar-requerimiento` - Explosión BOM
  - `GET /api/registros/{id}/requerimiento` - Ver requerimiento MP
  - `POST /api/registros/{id}/reservas` - Crear reserva
  - `GET /api/registros/{id}/reservas` - Listar reservas
  - `POST /api/registros/{id}/liberar-reservas` - Liberar reservas
  - `GET /api/inventario/{id}/disponibilidad` - Stock disponible real

- ✅ **Endpoint de salidas modificado** (`POST /inventario-salidas`):
  - Valida reserva pendiente antes de permitir salida
  - Para TELA: rollo_id obligatorio, valida pertenencia y metraje
  - Para NO tela: rollo_id debe ser NULL
  - Actualiza `cantidad_consumida` en requerimiento tras salida
  - FIFO intacto

### Febrero 2025 - UI Stock Disponible y Detalle de Reservas
- ✅ **Tabla de Inventario mejorada**:
  - Nueva columna "Reservado": muestra cantidad total reservada por órdenes de producción (en naranja)
  - Nueva columna "Disponible": muestra stock real disponible = stock_actual - total_reservado (en verde/rojo según nivel)
  - Botón desplegable (chevron) en filas con reservas activas
  - Fila expandible con detalle de reservas: N° Corte, Modelo, Estado Registro, Cantidad Reservada
  - Resumen en pie del detalle: Total reservado, Stock actual, Disponible
- ✅ **Endpoint GET /api/inventario mejorado**:
  - Ahora devuelve `total_reservado` y `stock_disponible` para cada item
- ✅ **Endpoint GET /api/inventario/{item_id}/reservas-detalle**:
  - Devuelve detalle de reservas activas agrupadas por registro (orden de producción)

## Backlog

### P1 - Importante
- [x] ~~Aplicar permisos granulares en frontend (ocultar botones según rol)~~ ✅ Implementado
- [x] ~~Proteger endpoints de backend según permisos de usuario~~ ✅ Parcialmente (función verificar_permiso creada)
- [ ] Filtros y búsqueda en tablas de producción
- [x] ~~Exportar registros a Excel~~ ✅ Implementado (registros, inventario, productividad, personas, modelos)
- [x] ~~Copias de seguridad~~ ✅ Implementado (crear, descargar, restaurar)
- [ ] Clarificar lógica de "borrado inteligente" del BOM (vinculación con salida de materia prima)

### P2 - Mejoras
- [ ] Dashboard de Producción con gráficos
- [ ] Reportes de producción con costos de materiales
- [ ] Gráficos de estados
- [ ] Historial de cambios de estado
- [ ] Exportar Kardex y Reportes a PDF
- [ ] Dropdowns en cascada para creación de Modelos
- [ ] Reportes de Merma por período o persona
- [ ] Vista de detalle (drill-down) en "Reporte Item-Estados"
- [ ] Filtros y ordenamiento avanzados en "Reporte Item-Estados"
- [ ] "Explosión del BOM" para calcular requerimientos de materiales
- [ ] Finalizar exportación Excel/PDF en página de Kardex

### P3 - Futuro
- [ ] Reporte de "Productividad por persona/servicio"
- [ ] Pre-llenado de tarifa en formulario de registro
- [ ] Aplicar permisos granulares con hook `usePermissions` en toda la UI
- [ ] Auditar accesibilidad en componentes `Dialog` (DialogTitle, DialogDescription)


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
  - Ordenamiento por secuencia
- ✅ **Personas de Producción**: CRUD completo en `/maestros/personas`
  - Campos: nombre, servicios (múltiples), teléfono, activo
  - Filtros por estado activo/inactivo
  - Toggle para activar/desactivar personas
  - Badges mostrando los servicios asignados
- ✅ **Movimientos de Producción** integrados en RegistroForm:
  - Tabla de movimientos vinculados al registro
  - Campos: servicio, persona, fecha inicio, fecha fin, cantidad de prendas
  - Filtro dinámico: al seleccionar servicio, las personas se filtran
  - Validación: persona debe tener el servicio asignado
  - Total de prendas entregadas calculado
- ✅ Nueva sección "Maestros" en el menú lateral

## Backlog

### P0 - En Progreso
- [ ] Completar diálogo de salida masiva de rollos (`SalidaRollosDialog.jsx`)
  - Filtrar rollos por ancho y tono
  - Selección múltiple con checkboxes
  - Uso parcial o total por rollo
  - Endpoint batch: `/api/inventario/salidas/batch-rollos`

### P1 - Importante
- [ ] Autenticación de usuarios
- [ ] Filtros y búsqueda en tablas de producción
- [ ] Exportar registros a Excel

### P2 - Mejoras
- [ ] Reportes de producción con costos de materiales
- [ ] Gráficos de estados
- [ ] Historial de cambios de estado
- [ ] Exportar Kardex y Reportes a PDF/Excel
- [ ] Dropdowns en cascada para creación de Modelos

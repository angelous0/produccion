# PRD - Sistema de Produccion Textil

## Problema Original
Sistema ERP de produccion textil con gestion de inventario FIFO, BOM (Bill of Materials), ordenes de produccion, reportes y mas.

## Arquitectura
- **Backend**: FastAPI + AsyncPG + PostgreSQL
- **Frontend**: React + Shadcn UI + Axios
- **DB**: PostgreSQL (schema `produccion`)

## Modelo de Datos - Relaciones Clave

### Materiales = Items (prod_inventario)
- Categorias: Telas, Avios, Otros
- NO se usa para servicios productivos (deprecated)

### Servicios = Servicios de Produccion (prod_servicios_produccion)
- Catalogo maestro: Corte, Costura, Lavanderia, Bordado, Acabado
- Se usa en: BOM (lineas SERVICIO), Ruta de Produccion, movimientos de produccion

### Ruta de Produccion (prod_rutas_produccion)
- Vinculada al Modelo via `ruta_produccion_id`
- Etapas (JSONB): cada etapa tiene `nombre` (estado) + `servicio_id` (opcional)
- Las etapas definen los estados validos del registro
- Unica fuente de verdad para el flujo del registro

### BOM (prod_modelo_bom_linea)
- Lineas de materiales: usan `inventario_id`
- Lineas de servicios: usan `servicio_produccion_id` (NO inventario_id)
- `costo_manual` editable por linea SERVICIO

### Modelo (prod_modelos)
- `ruta_produccion_id` -> ruta de produccion
- `pt_item_id` -> item PT vinculado (Producto Terminado)
- `servicios_ids` (JSONB) -> legacy, mantener por compatibilidad
- Al crear/editar: puede vincular PT existente o crear automaticamente con nombre del modelo
- Endpoint: `POST /api/modelos/{id}/crear-pt` (auto-genera PT-XXX con nombre del modelo)
- Endpoint: `GET /api/items-pt` (solo items tipo PT para selectores)

### Registro (prod_registros)
- `modelo_id` -> modelo
- `pt_item_id` -> se auto-completa desde el modelo al crear/editar
- `estado` -> viene de las etapas de la ruta del modelo
- Estados disponibles = etapas de la ruta, en orden

## API Endpoints Clave

### BOM
- `GET/POST /api/bom` - Cabeceras BOM
- `GET/PUT/DELETE /api/bom/{bom_id}` - Detalle BOM (lineas incluyen servicio_nombre/servicio_tarifa para SERVICIO)
- `POST /api/bom/{bom_id}/lineas` - Agregar linea (servicio_produccion_id para SERVICIO)
- `PUT /api/bom/{bom_id}/lineas/{linea_id}` - Actualizar linea
- `GET /api/bom/{bom_id}/costo-estandar` - Calculo costo (usa costo_manual > servicio_tarifa para SERVICIO)
- `POST /api/bom/{bom_id}/duplicar` - Duplicar BOM (copia servicio_produccion_id)
- `POST /api/bom/explosion/{orden_id}` - Explosion BOM

### Cierre de Produccion (WIP -> PT)
- `GET /api/registros/{id}/preview-cierre` - Preview de costos antes de cerrar
- `POST /api/registros/{id}/cierre-produccion` - Ejecutar cierre (crea ingreso PT, actualiza stock, marca CERRADA)
- `GET /api/registros/{id}/cierre-produccion` - Obtener datos del cierre existente
- Costos MP: desde `prod_inventario_salidas` (FIFO)
- Costos Servicios: desde `prod_movimientos_produccion` (fuente unica, consistente con WIP)
- Otros Costos: desde `prod_registro_costos_servicio` (costos adicionales manuales)
- Al cerrar: estado_op='CERRADA', libera reservas, crea ingreso en prod_inventario_ingresos

### Registros
- `GET /api/registros/{id}/estados-disponibles` - Estados de la ruta del modelo (usa_ruta=true)

### Rutas
- `GET/POST /api/rutas-produccion` - CRUD rutas
- Etapas: [{nombre, servicio_id (opc), orden}]

## Funcionalidades Implementadas

### Core
- Autenticacion JWT
- Dashboard, Modelos, Inventario FIFO, Ingresos/Salidas con rollos
- Registros/Ordenes de produccion
- Rutas de produccion con etapas nombradas

### BOM
- CRUD lineas (TELA, AVIO, SERVICIO, EMPAQUE, OTRO)
- Materiales -> selector de items de inventario
- Servicios -> selector de servicios de produccion (NO items)
- Costo manual editable por linea SERVICIO
- Costo estandar referencial, reordenamiento, duplicar, explosion

### UX/UI
- NumericInput, ScrollToTop, formulario simplificado para servicios
- Columna Valorizado en inventario
- Vista agrupada de salidas en registro (expandible)
- Buscador de items en salidas (excluye servicios)
- Pestana "Materia Prima" renombrada a "Gestion OP" en Registros.jsx
- Pestana "Costos" renombrada a "Otros Costos" en RegistroDetalleFase2.jsx
- Preview de cierre muestra detalle de movimientos de produccion (servicios) y 5 columnas de resumen

### Validacion
- Constraint UNIQUE en codigo de item
- Sanitizacion de FKs opcionales (empty string -> null)

## Backlog Priorizado

### P2
- Limpiar lineas BOM huerfanas del schema antiguo

### P3
- Conectar modulo Produccion con Finanzas
- Reporte de productividad por persona/servicio
- Reordenar tallas con drag-and-drop
- Permisos granulares con usePermissions
- Exportacion Excel/PDF en varias pantallas
- Accesibilidad en Dialogs (DialogTitle/DialogDescription)

## Credenciales de Prueba
- Usuario: `eduard` / Contrasena: `eduard123`

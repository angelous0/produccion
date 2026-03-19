# PRD - Produccion Textil

## Original Problem Statement
Sistema de gestion de produccion textil con flujo de trabajo completo: desde corte hasta almacen PT. Incluye gestion de inventario FIFO, BOM, movimientos de produccion, cierre de produccion, integracion con modulo de Finanzas, y control operativo por movimiento.

## What's Been Implemented
- Flujo de produccion completo con linea de tiempo de estado
- Panel de cierre integrado en RegistroForm
- Automatizacion Modelo -> PT (autocompletado)
- Selector de proveedores desde finanzas2.cont_tercero en Ingresos
- Badge de estado de facturacion en lista de Ingresos
- Proteccion anti doble-click con hook useSaving() en 21+ paginas
- Fix tarifa_aplicada persistencia en movimientos
- Sidebar fijo al navegar
- **Control Operativo Completo:**
  - fecha_entrega_final en cabecera del registro
  - fecha_esperada_movimiento + responsable_movimiento por cada movimiento
  - Alertas visuales por movimiento (normal/por vencer/vencido)
  - Estado operativo automatico (NORMAL/EN_RIESGO/PARALIZADA)
  - Incidencias con vinculacion opcional a movimiento
  - Paralizaciones con vinculacion opcional a movimiento

## DB Schema
- prod_registros: +fecha_entrega_final, +estado_operativo, +responsable_actual
- prod_movimientos_produccion: +tarifa_aplicada, +fecha_esperada_movimiento, +responsable_movimiento
- prod_incidencia: id, registro_id, movimiento_id(nullable), tipo, comentario, estado, usuario, fecha_hora
- prod_paralizacion: id, registro_id, movimiento_id(nullable), motivo, comentario, activa, fecha_inicio, fecha_fin

## Key API Endpoints
- PUT /api/registros/{id}/control - Fecha entrega final
- GET/POST /api/incidencias/{registro_id} - CRUD incidencias
- GET/POST /api/paralizaciones/{registro_id} - CRUD paralizaciones  
- PUT /api/paralizaciones/{id}/levantar - Levantar paralizacion
- POST/PUT /api/movimientos-produccion - Con fecha_esperada y responsable

## Prioritized Backlog
### P1
- [ ] Logica en modulo Finanzas para vincular ingresos MP a facturas
### P2
- [ ] Limpiar lineas BOM huerfanas
### P3
- [ ] Reporte productividad por persona/servicio
- [ ] Drag-and-drop reordenar tallas
- [ ] Permisos granulares con usePermissions
- [ ] Exportacion Excel/PDF (Kardex, etc.)
- [ ] Refactorizar RegistroForm.jsx (1800+ lineas)

## Key Credentials
- Usuario: eduard / eduard123

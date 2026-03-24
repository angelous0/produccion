# PRD - Produccion Textil

## Original Problem Statement
Sistema de gestion de produccion textil con flujo de trabajo completo: desde corte hasta almacen PT. Incluye gestion de inventario FIFO, BOM, movimientos de produccion, cierre de produccion, integracion con modulo de Finanzas, control operativo por movimiento, division de lotes, y reportes de produccion P0.

## What's Been Implemented
- Flujo de produccion completo con linea de tiempo de estado
- Panel de cierre integrado en RegistroForm
- Proteccion anti doble-click con hook useSaving() en 21+ paginas
- Sidebar fijo al navegar
- **Control Operativo**: fecha_esperada por movimiento, alertas, incidencias, paralizaciones
- **Personal Interno/Externo**: tipo_persona y unidad_interna en personas y movimientos
- **Vinculacion Bidireccional Estado-Movimientos**:
  - Etapas con obligatorio/aparece_en_estado (toggles editables en Rutas)
  - Endpoint analisis-estado y validar-cambio-estado
  - Sugerencias movimiento->estado y estado->movimiento
  - Banner inconsistencias, bloqueos para saltar etapas obligatorias
  - Auto-guardado de estado (sin boton Actualizar)
  - Sugerencias solo hacia adelante (no retroceder)
  - Fecha inicio auto-sugerida basada en etapa anterior de la ruta
  - Validacion min en fechas (fin >= inicio, esperada >= inicio)
- **Division de Lote (Split)**:
  - POST /api/registros/{id}/dividir: crea registro hijo con tallas seleccionadas
  - POST /api/registros/{id}/reunificar: merge hijo al padre (si no tiene movimientos/salidas)
  - GET /api/registros/{id}/divisiones: info de padre, hijos, hermanos
  - Nomenclatura automatica: 15-1, 15-2, 15-3...
  - Divisiones multiples soportadas
  - Sincronizacion JSONB + prod_registro_tallas
  - Frontend: boton Dividir Lote, dialogo selector tallas, banner de divisiones, links navegables, boton Reunificar
  - Badges en lista de registros para lotes divididos
- **Performance**: GET registros 5.8s->0.5s, GET modelos 3.3s->0.5s (JOINs)
- **Rutas editables**: nombre, servicio, obligatorio, aparece_en_estado inline
- **Modulo Reportes P0** (2026-03-24):
  - Dashboard KPIs: lotes en proceso, prendas, atrasados, movimientos abiertos, fraccionados
  - Produccion en Proceso: tabla con filtros (estado, modelo), dias en proceso, movimientos
  - WIP por Etapa: grafico de barras + tabla con distribucion por estado actual
  - Lotes Atrasados: tabla con motivo (entrega vencida, movimientos vencidos)
  - Trazabilidad: timeline cronologico de movimientos por registro, tallas, ruta esperada
  - Cumplimiento de Ruta: barra de progreso por registro, detalle etapas completadas/pendientes
  - Balance por Terceros: tabla y grafico por servicio/persona, prendas en poder
  - Lotes Fraccionados: cards de familias padre/hijo con cantidades
  - Filtros globales: servicio, ruta, modelo, estado
  - Navegacion desde sidebar y desde cualquier reporte al detalle

## DB Schema Changes
- prod_registros: +dividido_desde_registro_id (VARCHAR NULL), +division_numero (INT DEFAULT 0)

## Key API Endpoints
- POST /api/registros/{id}/dividir - Division de lote
- POST /api/registros/{id}/reunificar - Reunificacion de lote hijo
- GET /api/registros/{id}/divisiones - Info de divisiones
- GET /api/registros/{id}/analisis-estado - Analisis coherencia
- POST /api/registros/{id}/validar-cambio-estado - Validacion con bloqueos
- GET /api/reportes-produccion/dashboard - KPIs dashboard
- GET /api/reportes-produccion/en-proceso - Produccion en proceso con filtros
- GET /api/reportes-produccion/wip-etapa - WIP agrupado por etapa
- GET /api/reportes-produccion/atrasados - Lotes atrasados
- GET /api/reportes-produccion/trazabilidad/{id} - Timeline de movimientos
- GET /api/reportes-produccion/cumplimiento-ruta - Cumplimiento ruta con filtros
- GET /api/reportes-produccion/balance-terceros - Balance por servicio/persona
- GET /api/reportes-produccion/lotes-fraccionados - Familias de lotes
- GET /api/reportes-produccion/filtros - Opciones de filtro

## Prioritized Backlog
### P0 (COMPLETADO)
- [x] Modulo Reportes P0 (8 reportes + filtros)

### P1
- [ ] Logica en modulo Finanzas para cargos internos
- [ ] Reportes P1: Productividad persona/servicio, Incidencias/Glosas, PT generado, Antiguedad, Mermas

### P2
- [ ] Reportes P2: Reprocesos, Eficiencia vs Estandar, Cumplimiento por modelo, Carga futura, Consistencia
- [ ] Limpiar lineas BOM huerfanas

### P3
- [ ] Drag-and-drop reordenar tallas
- [ ] Permisos granulares con usePermissions
- [ ] Exportacion Excel/PDF
- [ ] Refactorizar RegistroForm.jsx (~2700 lineas)
- [ ] Migrar server.py a routers modulares

## Key Credentials
- Usuario: eduard / eduard123

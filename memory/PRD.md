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
  - POST /api/registros/{id}/reunificar: merge hijo al padre
  - Nomenclatura automatica: 15-1, 15-2, 15-3...
  - Sincronizacion JSONB + prod_registro_tallas
  - Frontend: boton Dividir Lote, dialogo selector tallas, banner de divisiones, links navegables
- **Performance**: GET registros 5.8s->0.5s, GET modelos 3.3s->0.5s (JOINs)
- **Rutas editables**: nombre, servicio, obligatorio, aparece_en_estado inline
- **Modulo Reportes P0** (2026-03-24):
  - Dashboard KPIs, En Proceso, WIP por Etapa, Atrasados, Trazabilidad, Cumplimiento Ruta, Balance Terceros, Lotes Fraccionados
  - 9 endpoints optimizados, filtros globales, navegacion entre reportes
- **Matriz Dinamica de Produccion** (2026-03-24):
  - Reporte tipo Power BI: Filas = Item (Marca-Tipo-Entalle-Tela) + Hilo
  - Columnas = Estados dinamicos (se adaptan segun ruta seleccionada)
  - Toggle Registros/Prendas para cambiar metrica en toda la tabla
  - 7 filtros (Ruta, Marca, Tipo, Entalle, Tela, Hilo, Modelo) + 3 toggles (activos, atrasados, fraccionados)
  - Columnas visibles configurables con show/hide
  - Reordenamiento de columnas con botones izq/der
  - Filas expandibles con detalle (Corte, Estado, Prendas, Modelo, Ruta, Entrega, acciones)
  - Totales por fila, columna y total general
  - Columnas sticky (Item + Hilo)
  - Preferencias guardadas en localStorage
  - Prendas: usa prod_registro_tallas con fallback a JSONB tallas
  - Fraccionados: incluye padres e hijos (prendas correctamente distribuidas)
  - Sin ruta: columnas derivadas de todas las rutas activas (aparece_en_estado)
  - Con ruta: columnas respetan orden de la ruta seleccionada

## Key API Endpoints
- POST /api/registros/{id}/dividir
- POST /api/registros/{id}/reunificar
- GET /api/registros/{id}/analisis-estado
- POST /api/registros/{id}/validar-cambio-estado
- GET /api/reportes-produccion/dashboard
- GET /api/reportes-produccion/en-proceso
- GET /api/reportes-produccion/wip-etapa
- GET /api/reportes-produccion/atrasados
- GET /api/reportes-produccion/trazabilidad/{id}
- GET /api/reportes-produccion/cumplimiento-ruta
- GET /api/reportes-produccion/balance-terceros
- GET /api/reportes-produccion/lotes-fraccionados
- GET /api/reportes-produccion/filtros
- GET /api/reportes-produccion/matriz

## Prioritized Backlog
### P0 (COMPLETADO)
- [x] Modulo Reportes P0 (8 reportes + filtros)
- [x] Matriz Dinamica de Produccion

### P1
- [ ] Logica en modulo Finanzas para cargos internos
- [ ] Reportes P1: Productividad persona/servicio, Incidencias/Glosas, PT generado, Antiguedad, Mermas

### P2
- [ ] Reportes P2: Reprocesos, Eficiencia vs Estandar, Cumplimiento por modelo, Carga futura, Consistencia
- [ ] Limpiar lineas BOM huerfanas

### P3
- [ ] Permisos granulares con usePermissions
- [ ] Exportacion Excel/PDF
- [ ] Refactorizar RegistroForm.jsx (~2700 lineas)
- [ ] Migrar server.py a routers modulares

## Key Credentials
- Usuario: eduard / eduard123

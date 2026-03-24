# PRD - Produccion Textil

## Original Problem Statement
Sistema de gestion de produccion textil con flujo de trabajo completo: desde corte hasta almacen PT. Incluye gestion de inventario FIFO, BOM, movimientos de produccion, cierre de produccion, integracion con modulo de Finanzas, control operativo por movimiento, division de lotes, y reportes de produccion P0.

## What's Been Implemented
- Flujo de produccion completo con linea de tiempo de estado
- Panel de cierre integrado en RegistroForm
- Proteccion anti doble-click con hook useSaving() en 21+ paginas
- Sidebar fijo al navegar
- Control Operativo: fecha_esperada por movimiento, alertas, incidencias, paralizaciones
- Personal Interno/Externo: tipo_persona y unidad_interna en personas y movimientos
- Vinculacion Bidireccional Estado-Movimientos (sugerencias, bloqueos, auto-guardado)
- Division de Lote (Split): dividir, reunificar, nomenclatura automatica
- Performance: GET registros 5.8s->0.5s, GET modelos 3.3s->0.5s
- Rutas editables inline
- **Modulo Reportes P0** (2026-03-24):
  - Dashboard KPIs, En Proceso, WIP por Etapa, Atrasados, Trazabilidad, Cumplimiento Ruta, Balance Terceros, Lotes Fraccionados
  - 9 endpoints optimizados, filtros globales, navegacion entre reportes
- **Matriz Dinamica de Produccion** (2026-03-24):
  - Reporte tipo Power BI: Filas = Item (Marca-Tipo-Entalle-Tela) + Hilo
  - Columnas = Estados dinamicos (adaptan segun ruta seleccionada)
  - Toggle Registros/Prendas, 7 filtros + 3 toggles
  - Columnas visibles/reordenables, preferencias en localStorage
  - **Fusion de columnas**: Acabado absorbe Limpieza, valores se suman, persistente
  - **Pop-up modal detallado**: click en celda/fila/total abre dialogo con
    n_corte, modelo, curva, curva_detalle (tallas), hilo_especifico, estado,
    prendas, ruta, fecha_entrega, dias_proceso, ultimo_movimiento, diferencia,
    total_movimientos, badges urgente/fraccionado, botones Trazabilidad y Abrir

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
- [x] Fusion de columnas en Matriz
- [x] Pop-up modal detallado en Matriz

### P1
- [ ] Logica en modulo Finanzas para cargos internos
- [ ] Reportes P1: Productividad persona/servicio, Incidencias/Glosas, PT generado, Antiguedad, Mermas

### P2
- [ ] Reportes P2: Reprocesos, Eficiencia vs Estandar, Cumplimiento por modelo, Carga futura
- [ ] Limpiar lineas BOM huerfanas

### P3
- [ ] Permisos granulares con usePermissions
- [ ] Exportacion Excel/PDF
- [ ] Refactorizar RegistroForm.jsx (~2700 lineas)
- [ ] Migrar server.py a routers modulares

## Key Credentials
- Usuario: eduard / eduard123

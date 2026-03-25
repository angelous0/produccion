# PRD - Produccion Textil

## Original Problem Statement
Sistema de gestion de produccion textil con flujo de trabajo completo: desde corte hasta almacen PT. Incluye gestion de inventario FIFO, BOM, movimientos de produccion, cierre de produccion, control operativo por movimiento, division de lotes, reportes de produccion P0, y trazabilidad unificada de cantidades.

## What's Been Implemented
- Flujo de produccion completo con linea de tiempo de estado
- Panel de cierre integrado en RegistroForm
- Proteccion anti doble-click con hook useSaving() en 21+ paginas
- Control Operativo: fecha_esperada por movimiento, alertas, incidencias, paralizaciones
- Personal Interno/Externo: tipo_persona y unidad_interna
- Vinculacion Bidireccional Estado-Movimientos (sugerencias, bloqueos, auto-guardado)
- Division de Lote (Split): dividir, reunificar, nomenclatura automatica
- Performance: GET registros 5.8s->0.5s, GET modelos 3.3s->0.5s
- Rutas editables inline
- **Modulo Reportes P0** (2026-03-24):
  - Dashboard KPIs, En Proceso, WIP por Etapa, Atrasados, Trazabilidad, Cumplimiento Ruta, Balance Terceros, Lotes Fraccionados
- **Matriz Dinamica de Produccion** (2026-03-24):
  - Filas = Item (Marca-Tipo-Entalle-Tela) + Hilo
  - Columnas = Estados dinamicos (adaptan segun ruta seleccionada)
  - Toggle Registros/Prendas, 7 filtros + 3 toggles
  - Columnas visibles/reordenables, preferencias en localStorage
  - Fusion de columnas (absorber columnas, valores sumados, persistente)
  - **Pop-up modal tipo tabla Excel** con: Corte, Estado, Modelo, Prendas, Curva, Hilo Esp., Ruta, Entrega, Inicio Prod., Dias, Ult. Mov, Dif., Info, Accion
  - Click en celda filtra por estado; click en item/total muestra todos
  - **Dias = desde fecha_inicio del primer movimiento** (no creacion)
  - **Todas las fechas en formato dd-mm-yy** en todo el modulo de reportes
- **Trazabilidad Unificada** (2026-03-24):
  - Backend: Tablas prod_fallados y prod_arreglos con init en startup
  - CRUD completo: Fallados (crear, editar, eliminar) y Arreglos (crear, cerrar, eliminar)
  - Validaciones: cantidades reparable+no_reparable <= detectada, arreglos <= reparables, cierre <= enviada
  - Resumen de cantidades calculado en tiempo real (GET /api/registros/{id}/resumen-cantidades)
  - Timeline unificado cronologico: movimientos + mermas + fallados + arreglos + divisiones
  - Integracion automatica de mermas cuando hay diferencia en movimientos
  - Frontend: TrazabilidadPanel.jsx con Balance del Lote, Tabs (Timeline, Fallados, Arreglos, Diferencias, Divisiones)
  - Dialogs para registrar fallados, crear arreglos y cerrar arreglos
  - Alertas visuales para vencidos, mermas y pendientes
  - Relacion padre-hijo visible en el balance

## Key API Endpoints
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
- GET /api/fallados
- POST /api/fallados
- PUT /api/fallados/{id}
- DELETE /api/fallados/{id}
- GET /api/arreglos
- POST /api/arreglos
- PUT /api/arreglos/{id}/cerrar
- DELETE /api/arreglos/{id}
- GET /api/registros/{id}/resumen-cantidades
- GET /api/registros/{id}/trazabilidad-completa
- GET /api/guias-remision (listado con filtros)
- GET /api/guias-remision/{id} (detalle enriquecido)
- POST /api/guias-remision/from-movimiento/{id} (crear/actualizar desde movimiento)
- DELETE /api/guias-remision/{id}

## Prioritized Backlog
### P0 (COMPLETADO)
- [x] Modulo Reportes P0 (8 reportes + filtros)
- [x] Matriz Dinamica de Produccion (fusion, modal Excel, dias desde primer mov, dd-mm-yy)
- [x] Trazabilidad Unificada Backend (tablas, CRUD fallados/arreglos, resumen, timeline)
- [x] Trazabilidad Unificada Frontend (Balance del Lote, Tabs, Dialogs, Alertas)
- [x] Bug Fix: Guias de Remision - URL mismatch, response parsing, campos incorrectos, filtros de fecha (2026-03-25)
- [x] Mejora Matriz: Colores como popup en modal en vez de columna. Tabla agrupada por Color General con subtotales (2026-03-25)
- [x] Migración MariaDB → PostgreSQL: 8 marcas, 25 tipos, 26 entalles, 28 telas, 1160 modelos, 1150 registros, 3418 movimientos, 79 personas, 17 servicios, 165 colores, 13 tallas, 613 historial (2026-03-25)
- [x] Migración Inventario: 390 items, 505 ingresos, 272 salidas. Ajuste empresa_id=8 global (2026-03-25)
- [x] Optimización N+1 queries: inventario, ingresos y salidas refactorizados a JOINs (2026-03-25)

### P1
- [ ] Logica en modulo Finanzas para cargos internos
- [ ] Reportes P1: Productividad persona/servicio, Incidencias/Glosas, PT generado, Antiguedad, Mermas
- [ ] Reportes y KPIs de Trazabilidad: perdidas por servicio, fallados por responsable, arreglos vencidos

### P2
- [ ] Reportes P2: Reprocesos, Eficiencia vs Estandar, Cumplimiento por modelo, Carga futura
- [ ] Limpiar lineas BOM huerfanas

### P3
- [ ] Permisos granulares con usePermissions
- [ ] Exportacion Excel/PDF
- [ ] Refactorizar RegistroForm.jsx (~2800 lineas)
- [ ] Migrar server.py a routers modulares

## Key Credentials
- Usuario: eduard / eduard123

## Code Architecture
```
/app
├── backend/
│   ├── routes/
│   │   ├── reportes_produccion.py
│   │   ├── trazabilidad.py (Fallados, Arreglos, Resumen, Timeline)
│   │   └── ... (otros routers)
│   ├── tests/
│   │   ├── test_trazabilidad.py (22 tests)
│   │   └── test_guias_remision.py (11 tests)
│   └── server.py
└── frontend/
    └── src/
        ├── components/
        │   └── TrazabilidadPanel.jsx (Balance, Tabs, Dialogs)
        └── pages/
            ├── MatrizProduccion.jsx
            └── RegistroForm.jsx (integra TrazabilidadPanel)
```

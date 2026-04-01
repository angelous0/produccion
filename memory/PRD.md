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
  - **Pop-up modal tipo tabla Excel** con detalle completo
  - **Dias = desde fecha_inicio del primer movimiento**
  - **Todas las fechas en formato dd-mm-yy**
- **Trazabilidad Unificada** (2026-03-24):
  - Backend: Tablas prod_fallados y prod_arreglos con init en startup
  - CRUD completo: Fallados y Arreglos con validaciones
  - Resumen de cantidades calculado en tiempo real
  - Timeline unificado cronologico
  - Frontend: TrazabilidadPanel.jsx con Balance del Lote y Tabs
- **Migracion MariaDB -> PostgreSQL** (2026-03-25)
- **Optimizacion Performance** (2026-03-25):
  - Paginacion server-side en Registros, Modelos, Movimientos, Inventario
  - Eliminacion de N+1 queries
- **Forzar Cambio de Estado** (2026-03-25)
- **Incidencias Unificadas con Paralizaciones** (2026-03-26)
- **Skip Validacion por Registro** (2026-03-25)
- **Tabla Registros Estilo Excel** (2026-03-26)
- **QA General y Correcciones** (2026-03-26)
- **Vista Unificada Materiales** (2026-03-26)
- **Selector de BOM en Materiales** (2026-03-27)
- **Bugfix Dar Salida desde Materiales** (2026-03-27)
- **Feature Consumir Reservado** (2026-03-27)
- **Selector de Rollos en Materiales** (2026-03-27)
- **Anular Salidas** (2026-03-27)
- **Linea de Negocio en Produccion/Inventario** (2026-03-27)
- **Hilo de Conversacion por Registro** (2026-03-27)
- **Avance Porcentaje en Servicios y Movimientos** (2026-03-27)
- **Bloqueo por Paralizacion** (2026-03-28)
- **Auto-post Incidencias a Conversacion + Timezone Lima** (2026-03-28)
- **UI/UX Mejoras** (2026-03-28):
  - Multi-select visual (Grid checkboxes) para Tallas
  - Reubicacion "Articulo PT" a Modelos
  - Simplificacion BOM
  - Modal Avanzado Inventario
  - Hilo Especifico en Registros y Exportacion
  - Correccion impresion Guias de Remision
- **Refactorizacion Backend** (2026-03-28):
  - server.py reducido de 7805 a ~1088 lineas
  - Routers modulares: auth, catalogos, inventario_main, modelos, registros_main, movimientos, stats_reportes
  - Archivos centrales: models.py, helpers.py, auth_utils.py
- **Fix SyntaxError post-refactorizacion** (2026-03-28):
  - Corregido truncamiento en registros_main.py (reunion de lotes)
  - Verificados todos los routers: auth, registros, modelos, inventario, movimientos, stats, catalogos

## Code Architecture
```
/app
├── backend/
│   ├── auth_utils.py (Utilidades de autenticacion)
│   ├── helpers.py (Funciones compartidas)
│   ├── models.py (Esquemas Pydantic)
│   ├── server.py (~1088 lineas, entrypoint + websockets + BD)
│   └── routes/
│       ├── auth.py
│       ├── catalogos.py
│       ├── inventario_main.py
│       ├── modelos.py
│       ├── registros_main.py (~1990 lineas)
│       ├── movimientos.py
│       ├── stats_reportes.py
│       ├── trazabilidad.py
│       └── ... (costos, cierre, bom, control_produccion, etc.)
└── frontend/
    └── src/
        ├── pages/
        │   ├── RegistroForm.jsx (~3353 lineas - PENDIENTE refactorizar)
        │   └── ...
```

## Key API Endpoints
- GET /api/registros (paginado: limit, offset, search, estados)
- GET /api/modelos (paginado: limit, offset, search, marca, tipo, entalle, tela)
- GET /api/inventario (paginado: limit, offset, search, categoria, stock_status)
- GET /api/movimientos-produccion (paginado)
- GET /api/registros/{id}/trazabilidad-completa
- GET /api/registros/{id}/resumen-cantidades
- POST /api/auth/login
- GET /api/stats/charts

## Prioritized Backlog
### P0
- [ ] Refactorizacion Frontend: Desglosar RegistroForm.jsx (~3353 lineas) en subcomponentes
- [ ] Trazabilidad Unificada - Frontend (UI de timeline y balance en detalle registro)

### P1
- [ ] Reportes y KPIs de Trazabilidad (perdidas por servicio, fallados por responsable)

### P2
- [ ] Filtrar alertas por usuario/servicio
- [ ] Exportacion a Excel/PDF

### P3
- [ ] Permisos granulares con usePermissions

## Credentials
- Login: eduard / eduard123

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
- **Modulo Reportes P0**: Dashboard KPIs, En Proceso, WIP por Etapa, Atrasados, Trazabilidad, Cumplimiento Ruta, Balance Terceros, Lotes Fraccionados
- **Matriz Dinamica de Produccion**: Filas=Item, Columnas=Estados, Toggle Registros/Prendas, Fusion columnas, Pop-up modal
- **Trazabilidad Unificada**: Backend completo con Fallados, Arreglos, Timeline, Balance
- **Migracion MariaDB -> PostgreSQL**
- **Optimizacion Performance**: Paginacion server-side, Eliminacion N+1 queries
- **UI/UX Mejoras**: Multi-select tallas, BOM simplificado, Modal inventario, Hilo Especifico, Guias impresion
- **Refactorizacion Backend** (2026-03-28): server.py de 7805 a ~1088 lineas, routers modulares
- **Refactorizacion Frontend** (2026-04-01): RegistroForm.jsx de 3354 a 789 lineas, 7 subcomponentes extraidos

## Code Architecture
```
/app
├── backend/
│   ├── auth_utils.py
│   ├── helpers.py
│   ├── models.py (Pydantic + constants like ESTADOS_PRODUCCION)
│   ├── server.py (~1088 lines, entrypoint)
│   └── routes/
│       ├── auth.py
│       ├── catalogos.py
│       ├── inventario_main.py
│       ├── modelos.py
│       ├── registros_main.py (~1990 lines)
│       ├── movimientos.py
│       ├── stats_reportes.py
│       ├── trazabilidad.py
│       └── ...
└── frontend/
    └── src/
        ├── components/
        │   └── registro/    <-- NEW modular subcomponents
        │       ├── index.js
        │       ├── RegistroHeader.jsx (151 lines)
        │       ├── RegistroDatosCard.jsx (251 lines)
        │       ├── RegistroTallasCard.jsx (118 lines)
        │       ├── RegistroMovimientosCard.jsx (179 lines)
        │       ├── RegistroIncidenciasCard.jsx (116 lines)
        │       ├── RegistroPanelLateral.jsx (144 lines)
        │       └── RegistroDialogs.jsx (728 lines)
        └── pages/
            └── RegistroForm.jsx (789 lines - orchestrator only)
```

## Prioritized Backlog
### P0
- [x] Refactorizacion Backend: server.py modularizado (DONE)
- [x] Refactorizacion Frontend: RegistroForm.jsx modularizado (DONE 2026-04-01)
- [x] Reporte Paralizados: KPIs + tabla + historial + filtro solo activas (DONE 2026-04-01)
- [x] Mejora Layout Registro: Sistema de 3 pestanas (General/Produccion/Control) (DONE 2026-04-01)
- [ ] Restaurar graficos Recharts en Dashboard principal
- [ ] Verificar paginas de Reportes Consolidados
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

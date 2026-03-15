# Producción Textil - PRD

## Problema Original
Refactorización arquitectónica masiva del módulo de Producción Textil: separar dominios, normalizar tablas, tipificación fuerte de ítems, lógica de costos y flujo de producción.

## Stack Técnico
- **Backend**: FastAPI, AsyncPG, PostgreSQL (puerto 9090, schema `produccion`)
- **Frontend**: React, axios, Shadcn/UI, Recharts
- **Auth**: JWT (passlib + python-jose)
- **DB**: PostgreSQL con search_path=produccion,public

## Empresa de prueba
- empresa_id = 7
- Usuario: eduard / eduard123

## Arquitectura de Routers (Backend)
```
/app/backend/routes/
├── inventario.py    # CRUD inventario con tipo_item (MP, AVIO, SERVICIO, PT)
├── rollos.py        # CRUD rollos de tela, disponibles/{item_id}
├── ordenes.py       # CRUD ordenes de producción
├── consumo.py       # Consumo MP simple y multi-rollo + WIP
├── servicios.py     # Servicios externos por orden + WIP
├── cierre_v2.py     # Preview y ejecución cierre OP → Ingreso PT
├── reportes.py      # MP/WIP/PT valorizado, Kardex, Ordenes, Resumen
├── costos.py        # Legacy costos
└── cierre.py        # Legacy cierre
```

## Tablas Principales (schema: produccion)
- `prod_registros` (ordenes de producción) → estado_op: ABIERTA, EN_PROCESO, CERRADA, ANULADA
- `prod_inventario` → tipo_item: MP, AVIO, SERVICIO, PT; control_por_rollos
- `prod_inventario_rollos` → metros_iniciales, metros_saldo, costo_unitario_metro
- `prod_consumo_mp` → consumo por orden con rollo_id, costo FIFO
- `prod_servicio_orden` → servicios externos sin inventario, con WIP
- `prod_wip_movimiento` → movimientos WIP por orden (CONSUMO_MP, SERVICIO, AJUSTE)
- `v_wip_resumen` → vista que acumula WIP por orden
- `prod_registro_cierre` → cierre de OP con costos finales
- `prod_ingreso_pt` → ingreso de PT al inventario post-cierre

## Endpoints Principales
- `GET /api/reportes/wip?empresa_id=7` → ordenes en proceso con costos
- `GET /api/reportes/mp-valorizado?empresa_id=7` → MP con FIFO
- `GET /api/reportes/pt-valorizado?empresa_id=7` → PT con cierres
- `GET /api/reportes/resumen-general?empresa_id=7` → MP+WIP+PT total
- `GET /api/rollos/disponibles/{item_id}` → rollos activos
- `POST /api/consumos` → consumo simple
- `POST /api/consumos/multi-rollo` → consumo múltiples rollos
- `POST /api/servicios-orden` → registrar servicio
- `GET /api/ordenes/{id}/cierre/preview` → preview cierre
- `POST /api/ordenes/{id}/cierre` → ejecutar cierre

## Estado Actual (Dic 2025)

### Completado
- [x] Refactorización arquitectónica DB (schema produccion, tablas normalizadas)
- [x] Modularización backend (routers por dominio)
- [x] Resolución conflicto rutas /api/reportes/wip (legacy removido)
- [x] Frontend actualizado para nuevos campos API
- [x] Validación multi-rollo (consumo, saldos, costos por rollo)
- [x] Flujo E2E: Ingreso MP → Consumo → Servicio → WIP → Cierre → Ingreso PT
- [x] Reportes MP/WIP/PT/Resumen funcionando con empresa_id=7
- [x] Testing completo: 20/20 tests backend + frontend OK

### Backlog P2
- [ ] Implementar vista drill-down en Reporte Item-Estados
- [ ] Filtros avanzados en tabla Reporte Item-Estados
- [ ] Ajustes frontend adicionales para empresa_id=7

### Backlog P3
- [ ] Continuar refactorización server.py (mover lógica legacy a routers)
- [ ] Reporte productividad por persona/servicio
- [ ] Drag-and-drop tallas
- [ ] Exportación Excel/PDF Kardex
- [ ] Permisos granulares usePermissions
- [ ] Accesibilidad Dialog (DialogTitle/DialogDescription)

### Backlog P4
- [ ] Puente Producción ↔ Finanzas
- [ ] Lógica borrado inteligente BOM

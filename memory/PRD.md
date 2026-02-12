# Módulo de Producción Textil - PRD

## Problema Original
Sistema de gestión de producción textil con inventario FIFO, MRP, reservas y valorización.

## Arquitectura
- **Backend**: FastAPI + asyncpg + PostgreSQL
- **Frontend**: React + Shadcn/UI
- **DB**: PostgreSQL con schemas `produccion` y `finanzas2` (misma DB)
- **Empresa activa**: id=6 (Ambission Industries SAC)

### Estructura de Routers
```
/app/backend/
├── server.py                    # App principal + legacy routes (5700+ líneas)
├── db.py                        # Pool asyncpg compartido
├── auth.py                      # Auth dependencies
├── helpers.py                   # Funciones helper
├── routes/
│   ├── costos.py                # CRUD costos servicio por registro
│   ├── cierre.py                # Preview/ejecutar cierre + asignar PT
│   └── reportes_valorizacion.py # Reportes MP/WIP/PT + ingresos from-finanzas + empresas
└── migrations/
    └── 001_multiempresa_valorizacion.py
```

## Implementado

### Enero 2025 - MVP + Fase 1 (Inventario FIFO)
- CRUDs para marcas, tipos, entalles, telas, hilos, modelos, registros
- Inventario FIFO con ingresos/salidas/rollos/ajustes/kardex
- Dark mode, tallas catálogo, colores catálogo

### Enero 2025 - Fase 2 (MRP y Reservas)
- Requerimiento de MP desde BOM, reservas ATP, salidas con validación

### Febrero 2025 - Fase 2C + UX
- Cerrar/Anular OP, liberación automática de reservas
- Salidas en lote, selección múltiple de rollos con checkboxes
- Búsqueda de ítems en ajustes

### Febrero 7, 2025 - Selección Múltiple de Rollos (P0)
- Modal multi-select con checkboxes y distribución inteligente

### Febrero 12, 2025 - Valorización MP + WIP + Cierre PT
- **A) Multiempresa**: empresa_id en todas las tablas de producción, FK a finanzas2.cont_empresa, backfill a id=6
- **B) PT por registro**: pt_item_id en prod_registros, selector en formulario de edición
- **C) Trazabilidad financiera**: fin_origen_tipo, fin_origen_id, fin_numero_doc en ingresos
- **D) Ingresos from-finanzas**: POST /api/inventario/ingresos/from-finanzas con idempotencia
- **E) Costos servicio**: CRUD completo + tabla prod_registro_costos_servicio + UI pestaña Costos
- **F) Cierre producción**: Preview + ejecución de cierre, cálculo FIFO, ingreso PT automático, tabla prod_registro_cierre
- **G) Reportes valorización**: MP Valorizado, WIP, PT Valorizado con UI completa
- **Router split**: Nuevos endpoints en routes/costos.py, routes/cierre.py, routes/reportes_valorizacion.py
- **Navegación**: Sección "Valorización" en sidebar con 3 reportes
- **6 pestañas en detalle registro**: Tallas, Requerimiento, Reservas, Salidas, Costos, Cierre

## DB Schema Producción
### Tablas nuevas
- `prod_registro_costos_servicio` (id, empresa_id, registro_id, fecha, descripcion, proveedor_texto, monto, fin_origen_tipo, fin_origen_id)
- `prod_registro_cierre` (id, empresa_id, registro_id, fecha, qty_terminada, costo_mp, costo_servicios, costo_total, costo_unit_pt, pt_ingreso_id)

### Columnas nuevas
- `prod_registros.pt_item_id` (FK a prod_inventario)
- `prod_registros.empresa_id` (FK a finanzas2.cont_empresa)
- `prod_inventario_ingresos.fin_origen_tipo`, `.fin_origen_id`, `.fin_numero_doc`
- `empresa_id` en: prod_registro_tallas, prod_registro_requerimiento_mp, prod_inventario_ingresos, prod_inventario_salidas, prod_inventario_rollos, prod_inventario_reservas, prod_inventario_reservas_linea

## Key API Endpoints
### Nuevos
- `GET/POST /api/registros/{id}/costos-servicio` - CRUD costos
- `PUT/DELETE /api/registros/{id}/costos-servicio/{costo_id}`
- `GET /api/registros/{id}/preview-cierre` - Preview costos
- `POST /api/registros/{id}/cierre-produccion` - Ejecutar cierre
- `GET /api/registros/{id}/cierre-produccion` - Consultar cierre
- `PUT /api/registros/{id}/pt-item` - Asignar artículo PT
- `GET /api/reportes/inventario-mp-valorizado?empresa_id=X`
- `GET /api/reportes/wip?empresa_id=X`
- `GET /api/reportes/inventario-pt-valorizado?empresa_id=X`
- `POST /api/inventario/ingresos/from-finanzas` - Ingresos desde finanzas
- `GET /api/empresas` - Lista empresas

## Backlog

### P1 - Importante
- [ ] Completar split de server.py en routers (mover legacy routes)
- [ ] Clarificar lógica de "borrado inteligente" del BOM
- [ ] Vista drill-down en "Reporte Item-Estados"
- [ ] Filtros y ordenamiento avanzados en "Reporte Item-Estados"

### P2 - Mejoras
- [ ] Exportación Excel/PDF en Kardex
- [ ] Dashboard de Producción con gráficos
- [ ] Filtro de fecha/período en reportes de valorización
- [ ] Reportes de Merma por período

### P3 - Futuro
- [ ] Reporte productividad por persona/servicio
- [ ] Drag-and-drop para reordenar tallas
- [ ] Permisos granulares con usePermissions
- [ ] Auditoría accesibilidad Dialog (issue recurrente x6)

## Credenciales de Prueba
- **Usuario**: `eduard`
- **Contraseña**: `eduard123`
- **Empresa**: id=6 (Ambission Industries SAC)

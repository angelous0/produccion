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
├── ordenes.py       # CRUD ordenes de producción + etapas
├── consumo.py       # Consumo MP simple y multi-rollo + WIP
├── servicios.py     # Servicios externos por orden + WIP
├── cierre_v2.py     # Preview y ejecución cierre OP → Ingreso PT
├── reportes.py      # MP/WIP/PT valorizado, Kardex, Ordenes, Resumen
├── bom.py           # BOM cabecera + líneas + costo estándar + duplicar
├── costos.py        # Legacy costos
└── cierre.py        # Legacy cierre
```

## Tablas Principales (schema: produccion)
- `prod_registros` → ordenes de producción
- `prod_inventario` → tipo_item: MP, AVIO, SERVICIO, PT
- `prod_inventario_rollos` → metros_iniciales, metros_saldo, costo_unitario_metro
- `prod_consumo_mp` → consumo por orden con rollo_id, costo FIFO
- `prod_servicio_orden` → servicios externos sin inventario, con WIP
- `prod_wip_movimiento` → movimientos WIP por orden
- `v_wip_resumen` → vista WIP acumulado
- `prod_registro_cierre` → cierre de OP con costos finales
- `prod_ingreso_pt` → ingreso PT post-cierre
- **`prod_bom_cabecera`** → BOM con version, estado, vigencia
- **`prod_modelo_bom_linea`** → líneas BOM con tipo_componente, merma, cantidad_total, etapa, es_opcional

## BOM - Rol y Estructura
El BOM sirve para planeación y estándar:
- Definir materiales estándar por modelo
- Estimar consumo aproximado con merma
- Costo estándar referencial (NO reemplaza costo real)
- Preparado para: requerimiento MP, reservas

**Cabecera**: id, modelo_id, codigo, version, estado (BORRADOR/APROBADO/INACTIVO), vigente_desde/hasta
**Detalle**: bom_id, inventario_id, tipo_componente (TELA/AVIO/SERVICIO/EMPAQUE/OTRO), talla_id, etapa_id, cantidad_base, merma_pct, cantidad_total, es_opcional

## Endpoints BOM
- `GET /api/bom?modelo_id=X` → listar cabeceras
- `POST /api/bom` → crear cabecera (auto-versión)
- `GET /api/bom/{id}` → detalle con líneas
- `PUT /api/bom/{id}` → cambiar estado
- `POST /api/bom/{id}/lineas` → agregar línea
- `PUT /api/bom/{id}/lineas/{lid}` → actualizar línea
- `DELETE /api/bom/{id}/lineas/{lid}` → eliminar línea
- `GET /api/bom/{id}/costo-estandar?cantidad_prendas=N` → costo referencial
- `POST /api/bom/{id}/duplicar` → nueva versión con copia

## Estado Actual (Dic 2025)

### Completado
- [x] Refactorización arquitectónica DB + backend modular
- [x] Resolución conflicto rutas /api/reportes/wip
- [x] Frontend alineado con nuevos campos API
- [x] Validación multi-rollo (consumo, saldos, costos)
- [x] Flujo E2E: Ingreso MP → Consumo → Servicio → WIP → Cierre → Ingreso PT
- [x] Reportes MP/WIP/PT/Resumen con empresa_id=7
- [x] **BOM refinado**: cabecera+detalle, tipo_componente, merma, costo estándar, versiones
- [x] Testing: 48+ tests (20 Producción + 28 BOM) + frontend verificado

### Backlog P2
- [ ] Vista drill-down en Reporte Item-Estados
- [ ] Filtros avanzados en reportes
- [ ] Limpiar líneas BOM huérfanas (ítems que no existen en produccion schema)

### Backlog P3
- [ ] Refactorizar server.py legacy → routers modulares
- [ ] Reporte productividad por persona/servicio
- [ ] Drag-and-drop tallas
- [ ] Exportación Excel/PDF Kardex
- [ ] Permisos granulares usePermissions
- [ ] Accesibilidad Dialog

### Backlog P4
- [ ] Puente Producción ↔ Finanzas
- [ ] Lógica borrado inteligente BOM
- [ ] BOM: explosión automática → requerimiento MP
- [ ] BOM: comparación estándar vs real

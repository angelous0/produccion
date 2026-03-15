# Producción Textil - PRD

## Problema Original
Refactorización arquitectónica del módulo de Producción Textil. Separar dominios, normalizar tablas, tipificación fuerte de ítems, lógica de costos y flujo de producción.

## Stack Técnico
- **Backend**: FastAPI, AsyncPG, PostgreSQL (puerto 9090, schema `produccion`)
- **Frontend**: React, axios, Shadcn/UI, Recharts
- **Auth**: JWT (passlib + python-jose)
- **DB**: PostgreSQL con search_path=produccion,public

## Empresa de prueba
- empresa_id = 7, Usuario: eduard / eduard123

## Arquitectura de Routers (Backend)
```
/app/backend/routes/
├── inventario.py    # CRUD inventario (MP, AVIO, SERVICIO, PT)
├── rollos.py        # CRUD rollos de tela
├── ordenes.py       # CRUD ordenes + etapas
├── consumo.py       # Consumo MP simple y multi-rollo + WIP
├── servicios.py     # Servicios externos + WIP
├── cierre_v2.py     # Preview y cierre OP → Ingreso PT
├── reportes.py      # MP/WIP/PT valorizado, Kardex, Ordenes, Resumen
├── bom.py           # BOM cabecera+líneas + costo estándar + explosión → req MP
├── costos.py        # Legacy
└── cierre.py        # Legacy
```

## Flujo E2E Validado
```
Ingreso MP → Consumo MP (FIFO/multi-rollo) → Servicio → WIP → Preview Cierre → Cierre → Ingreso PT
                                                                    ↑
BOM → Explosión → Requerimiento MP (planificación, merma, déficit, costo estimado)
```

## BOM - Estructura y Rol
**Rol**: Planificación y estándar (NO reemplaza consumo/costo real)
- Definir materiales estándar por modelo
- Estimar consumo con merma
- Generar requerimiento MP
- Costo estándar referencial
- Base para comparar vs consumo real

**Cabecera** (`prod_bom_cabecera`): id, modelo_id, codigo, version, estado (BORRADOR/APROBADO/INACTIVO), vigente_desde/hasta
**Detalle** (`prod_modelo_bom_linea`): bom_id, inventario_id, tipo_componente (TELA/AVIO/SERVICIO/EMPAQUE/OTRO), talla_id, etapa_id, cantidad_base, merma_pct, cantidad_total, es_opcional

## Explosión BOM → Requerimiento MP
**Tabla**: `prod_registro_requerimiento_mp` (reutilizada + columnas: bom_id, tipo_componente, merma_pct, unidad_medida, inventario_nombre)
**Lógica**:
- Solo genera para TELA, AVIO, EMPAQUE (NO SERVICIO)
- talla_id=null → aplica a TODAS las tallas → cant_total_bom × total_prendas
- talla_id específica → aplica solo a esa talla
- Calcula déficit: max(0, requerido - stock_actual)
- Costo estimado: requerido × costo_promedio
- SERVICIO retornado como referencial sin generar requerimiento

## Endpoints BOM
- `GET/POST /api/bom` → listar/crear cabecera
- `GET/PUT /api/bom/{id}` → detalle/estado
- `POST/PUT/DELETE /api/bom/{id}/lineas/{lid}` → CRUD líneas
- `GET /api/bom/{id}/costo-estandar` → costo referencial
- `POST /api/bom/{id}/duplicar` → nueva versión
- `POST /api/bom/explosion/{orden_id}` → generar requerimiento MP
- `GET /api/bom/requerimiento/{orden_id}` → ver requerimiento

## Estado (Dic 2025)

### Completado
- [x] Refactorización arquitectónica DB + backend modular
- [x] Resolución conflicto rutas /api/reportes/wip
- [x] Validación multi-rollo + flujo E2E
- [x] Reportes MP/WIP/PT/Resumen
- [x] BOM cabecera+detalle con versiones y estados
- [x] Tipos componente, merma, costo estándar
- [x] **Explosión BOM → Requerimiento MP** con merma, déficit, costo estimado
- [x] Frontend requerimiento: cards resumen + tabla + déficit en rojo
- [x] Testing: 66+ tests (20 Producción + 28 BOM + 18 Explosión) + frontend

### Backlog P2
- [ ] Vista drill-down Reporte Item-Estados
- [ ] Filtros avanzados en reportes
- [ ] Limpiar líneas BOM huérfanas
- [ ] Comparación costo estándar BOM vs costo real cierre

### Backlog P3
- [ ] Refactorizar server.py legacy → routers
- [ ] Reporte productividad por persona/servicio
- [ ] Drag-and-drop tallas
- [ ] Excel/PDF Kardex
- [ ] Permisos granulares usePermissions
- [ ] Accesibilidad Dialog

### Backlog P4
- [ ] Puente Producción ↔ Finanzas
- [ ] Lógica borrado inteligente BOM

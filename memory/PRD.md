# Sistema de Produccion Textil - PRD

## Problema Original
Sistema de gestion de produccion textil full-stack con trazabilidad unificada, permisos granulares, reportes operativos, cierre de costos auditables, distribucion PT con conciliacion Odoo, y Kardex de Producto Terminado.

## Stack
- Backend: FastAPI + asyncpg + PostgreSQL
- Frontend: React + Tailwind + Shadcn/UI
- BD: PostgreSQL (schema `produccion`, ODS en schema `odoo`)

## Credenciales
- Admin: `eduard` / `eduard123`
- empresa_id: **7**

## Funcionalidades Implementadas

### Core
- Gestion de registros de produccion (CRUD completo)
- Modelos, marcas, tipos, entalles, telas, hilos, tallas, colores
- Rutas de produccion con etapas
- Movimientos entre servicios/personas
- Incidencias con paralizacion

### Cierre de Produccion
- Fuentes de costo: costo_mp (FIFO), costo_servicios, otros_costos
- Congelamiento: snapshot_json al cerrar
- Reapertura controlada con trazabilidad

### Trazabilidad Unificada
- CRUD fallados, arreglos, liquidacion directa
- Timeline unificado, resumen de cantidades, mermas automaticas
- TrazabilidadPanel en pestana Control

### Distribucion PT y Conciliacion Odoo (07-Abr-2026)
- Tabla prod_registro_pt_relacion: distribucion por tipo_salida + product_template_id_odoo
- Tabla prod_registro_pt_odoo_vinculo: vinculacion 1:1 ajustes Odoo a registros
- Validacion suma = total producido
- Conciliacion: esperado vs ingresado, estados SIN_DISTRIBUCION/PENDIENTE/PARCIAL/COMPLETO
- Bloque Trazabilidad del Lote como card separado arriba de distribucion
- UI: Pestana "PT Odoo" con 4 bloques (trazabilidad, distribucion, vinculos, conciliacion)

### Kardex de Producto Terminado (08-Abr-2026)
- Endpoint GET /api/kardex-pt con clasificacion de movimientos:
  - INGRESO_PRODUCCION (via vinculos con prod_registro_pt_odoo_vinculo)
  - SALIDA_VENTA (internal -> customer)
  - AJUSTE_POSITIVO/NEGATIVO (inventory_id sin vinculo)
  - TRANSFERENCIA (internal -> internal, excluida del saldo global)
- Saldo acumulado via window function SUM() OVER(PARTITION BY product_tmpl_id)
- Filtros: producto, tipo_movimiento, company_key, location_id, fecha_desde, fecha_hasta
- Endpoint GET /api/kardex-pt/resumen: totales y desglose por producto
- Endpoint GET /api/kardex-pt/filtros: opciones de filtro disponibles
- UI: Pantalla completa con cards resumen, filtros, tabla movimientos, resumen por producto
- Datos reales: 2151 movimientos, 226 productos, saldo global 1173
- Testing: 100% pass rate iteration_48 (17/17 backend, frontend 100%)

### Transferencias Internas entre Lineas de Negocio
- Flujo completo: Borrador -> Confirmado / Cancelado
- Logica FIFO preservada
- Transaccion atomica con FOR UPDATE

### Optimizacion de Performance
- Backend: JOINs en vez de N+1 queries (3.3x mas rapido)
- BD: 15+ indices
- Frontend: Code splitting con React.lazy, lazy loading de tabs

### Modulo de Auditoria
- Tabla centralizada audit_log con JSONB
- 11 endpoints instrumentados
- UI admin con filtros y detalle expandible

### Inventario FIFO
- Items, ingresos, salidas, kardex, BOM, reservas, consumo

## Campos Eliminados (08-Abr-2026)
- `id_odoo` y `lq_odoo_id` eliminados de prod_registros (BD + backend + frontend)
- Reemplazados por el modulo formal de distribucion PT y vinculos Odoo

## Backlog Priorizado

### P1 - Linea de Negocio
- Filtro linea_negocio_id en Reportes (Dashboard, Matriz) - pendiente
- Validacion de inventario/materiales por linea

### P2
- Refactorizar registros_main.py y server.py (modularizar)
- Logging estructurado en backend

### P3
- Exportacion PDF de reportes
- Rate limiting API

## Arquitectura
```
backend/routes/
  kardex_pt.py            - Kardex PT (clasificacion, saldo, filtros)
  distribucion_pt.py      - Distribucion PT, vinculos Odoo, conciliacion
  trazabilidad.py         - Fallados, arreglos, balance, KPIs
  auditoria.py            - Auditoria
  registros_main.py       - CRUD registros
  reportes_produccion.py  - Dashboard, matriz, alertas
  inventario_main.py      - FIFO
  movimientos.py          - Movimientos produccion
  cierre.py               - Cierre produccion

frontend/src/pages/
  KardexPT.jsx            - Pantalla Kardex PT
  RegistroForm.jsx        - Detalle registro (tabs: General, Produccion, Control, PT Odoo)
```

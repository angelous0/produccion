# Sistema de Produccion Textil - PRD

## Problema Original
Sistema de gestion de produccion textil full-stack con trazabilidad unificada, permisos granulares, reportes operativos y cierre de costos auditables.

## Stack
- Backend: FastAPI + asyncpg + PostgreSQL
- Frontend: React + Tailwind + Shadcn/UI
- BD: PostgreSQL (schema `produccion`, ODS en schema `odoo`)

## Credenciales
- Admin: `eduard` / `eduard123`
- empresa_id estandarizado: **7**

## Funcionalidades Implementadas

### Core
- Gestion de registros de produccion (CRUD completo)
- Modelos, marcas, tipos, entalles, telas, hilos, tallas, colores
- Rutas de produccion con etapas
- Movimientos entre servicios/personas
- Incidencias con paralizacion

### Cierre de Produccion (Consolidado)
- Archivo unico oficial: `routes/cierre.py`
- Fuentes de costo: costo_mp (FIFO), costo_servicios, otros_costos
- Congelamiento: snapshot_json al cerrar
- Reapertura controlada con trazabilidad

### Trazabilidad Unificada
- Backend: CRUD fallados, arreglos, liquidacion directa
- Timeline unificado, resumen de cantidades, mermas automaticas
- Frontend: TrazabilidadPanel en pestana Control

### Distribucion PT y Conciliacion Odoo (07-Abr-2026)
- Tabla `prod_registro_pt_relacion`: distribucion de producto terminado por tipo_salida (normal, arreglo, liquidacion_leve, liquidacion_grave) y product_template_id_odoo
- Tabla `prod_registro_pt_odoo_vinculo`: vinculacion 1:1 de ajustes de inventario Odoo a registros (UNIQUE stock_inventory_odoo_id)
- Validacion estricta: suma de lineas de distribucion = total producido del registro
- Conciliacion: esperado (distribucion) vs ingresado (stock_move de ajustes vinculados), agrupado por product_tmpl_id
- Estados de conciliacion: SIN_DISTRIBUCION, PENDIENTE, PARCIAL, COMPLETO
- Buscador de productos Odoo (product_template) con nombre/ID
- Buscador de ajustes de inventario filtrado por x_es_ingreso_produccion=true, con indicador de disponibilidad
- UI: Pestana "PT Odoo" en detalle de registro con 3 bloques (distribucion, vinculos, conciliacion)
- Testing: 100% pass rate iteration_47 (21/21 backend, frontend 100%)

### Transferencias Internas entre Lineas de Negocio (06-Abr-2026)
- Flujo completo: Borrador -> Confirmado / Cancelado
- Tablas: prod_transferencias_linea, prod_transferencias_linea_detalle
- Logica FIFO preservada: N ingresos destino con costo individual exacto
- Salida tipo TRANSFERENCIA en prod_inventario_salidas
- Transaccion atomica con FOR UPDATE
- Frontend: Pagina completa con listado, crear, detalle, confirmar/cancelar
- Testing: 100% pass rate iteration_44

### Optimizacion de Performance - Registros (06-Abr-2026)
- Backend: Detalle registro de 2.63s a 0.79s (3.3x mas rapido) - JOINs en vez de N+1 queries
- Backend: Listado de 0.97s a 0.75s - COUNT(*) OVER() window function elimina 1 round-trip
- BD: 15 indices creados
- Frontend: Code splitting con React.lazy - 50+ paginas lazy loaded
- Frontend: Lazy loading de tabs en RegistroForm
- Testing: 100% pass rate iteration_46

### Responsive Mobile Completo (07-Abr-2026)
- Registros, Movimientos, Inventario, Auditoria: Cards en mobile
- 0 overflow horizontal verificado programaticamente

### Modulo de Auditoria (06-Abr-2026)
- Tabla centralizada audit_log con JSONB
- 11 endpoints criticos instrumentados
- UI exclusiva admin con filtros y detalle expandible

### Permisos Granulares
- servicios, acciones, estados por usuario
- Sidebar y alertas filtrados por permisos

### Reportes
- Dashboard con KPIs reactivos
- Matriz de produccion, Seguimiento (5 tabs)
- KPIs de Calidad

### Inventario FIFO
- Items, ingresos, salidas, kardex, BOM, reservas, consumo

## Backlog Priorizado

### P1 - Linea de Negocio (En progreso parcial)
- Filtro linea_negocio_id en Reportes (Dashboard, Matriz) - pendiente
- Validacion de inventario/materiales por linea

### P2
- Refactorizar registros_main.py y server.py (modularizar)
- Logging estructurado en backend

### P3
- Exportacion PDF de reportes
- Rate limiting API

## Arquitectura Clave
```
backend/routes/
  distribucion_pt.py    - Distribucion PT, vinculos Odoo, conciliacion
  auditoria.py          - Auditoria: helper + endpoints GET
  transferencias_linea.py - Transferencias internas entre lineas
  cierre.py             - Cierre de produccion (consolidado)
  trazabilidad.py       - Fallados, arreglos, balance, KPIs
  registros_main.py     - CRUD registros
  reportes_produccion.py - Dashboard, matriz, alertas
  inventario_main.py    - FIFO, ingresos, salidas, ajustes
  movimientos.py        - Movimientos de produccion

frontend/src/
  pages/
    RegistroForm.jsx         - Formulario principal (tabs: General, Produccion, Control, PT Odoo)
  components/registro/
    DistribucionPTPanel.jsx  - Panel PT Odoo (distribucion + vinculos + conciliacion)
    RegistroPanelLateral.jsx - Panel derecho
    RegistroMovimientosCard.jsx - Movimientos con menu "..."
```

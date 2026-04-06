# Sistema de Produccion Textil - PRD

## Problema Original
Sistema de gestion de produccion textil full-stack con trazabilidad unificada, permisos granulares, reportes operativos y cierre de costos auditables.

## Stack
- Backend: FastAPI + asyncpg + PostgreSQL
- Frontend: React + Tailwind + Shadcn/UI
- BD: PostgreSQL (schema `produccion`)

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

### Cierre de Produccion (Consolidado - 06-Abr-2026)
- **Archivo unico oficial**: `routes/cierre.py` (unificado desde cierre.py + cierre_v2.py)
- Fuentes de costo oficiales:
  - `costo_mp` = prod_inventario_salidas (FIFO real)
  - `costo_servicios` = prod_movimientos_produccion.costo_calculado
  - `otros_costos` = prod_registro_costos_servicio
  - `costo_total_final` = costo_mp + costo_servicios + otros_costos
  - `costo_unitario_final` = costo_total_final / qty_terminada_real
- **Congelamiento**: snapshot_json guarda desglose completo al cerrar (no se recalcula)
- **Reapertura controlada**: requiere motivo (5+ chars), revierte stock PT, guarda trazabilidad
- **Frontend**: Preview desglose -> Confirmar -> Badge CERRADO -> Historial reapertura

### Trazabilidad Unificada
- Backend: CRUD fallados, arreglos, liquidacion directa
- Timeline unificado, resumen de cantidades, mermas automaticas
- Frontend: TrazabilidadPanel en pestana Control

### Transferencias Internas entre Lineas de Negocio (06-Abr-2026)
- **Flujo completo**: Borrador -> Confirmado / Cancelado
- **Tablas nuevas**:
  - `prod_transferencias_linea` (maestra: codigo, item, linea_origen, linea_destino, cantidad, estado, costo, trazabilidad de usuarios)
  - `prod_transferencias_linea_detalle` (1:1 por capa FIFO: ingreso_origen_id, ingreso_destino_id, cantidad, costo_unitario)
- **Logica FIFO preservada**: Opcion (b) - N ingresos destino, uno por capa consumida, con costo individual exacto
- **Salida tipo TRANSFERENCIA**: Registra en `prod_inventario_salidas` con tipo='TRANSFERENCIA' y transferencia_id
- **Validaciones**:
  - Stock por linea desde capas FIFO reales (`prod_inventario_ingresos.cantidad_disponible`)
  - Descuenta reservas activas filtradas por linea del registro (OP)
  - No usa stock_actual global para validar disponibilidad
  - linea_origen != linea_destino, item existe, lineas existen, cantidad > 0
- **Transaccion atomica**: Todo dentro de `conn.transaction()` con `FOR UPDATE` para evitar race conditions
- **stock_actual**: Neto 0 (sale e ingresa la misma cantidad)
- **Frontend**: Pagina completa con listado, filtros, modal crear con stock por linea y estimacion FIFO, modal detalle con trazabilidad, confirmar/cancelar
- **Endpoints**:
  - `GET /api/transferencias-linea` (listar con filtros)
  - `POST /api/transferencias-linea` (crear borrador)
  - `GET /api/transferencias-linea/{id}` (detalle con capas FIFO)
  - `POST /api/transferencias-linea/{id}/confirmar` (ejecutar FIFO atomico)
  - `POST /api/transferencias-linea/{id}/cancelar` (cancelar borrador)
  - `GET /api/transferencias-linea/estimar-costo` (preview FIFO)
  - `GET /api/transferencias-linea/stock-por-linea/{item_id}` (stock desglosado)
- **Preparado para Finanzas**: campo `referencia_externa` y columnas `fin_origen_tipo/fin_origen_id` en ingresos destino

### Permisos Granulares
- servicios, acciones, estados permitidos por usuario
- Sidebar y alertas filtrados por permisos

### Reportes
- Dashboard con KPIs reactivos
- Matriz de produccion, Seguimiento (5 tabs incluyendo Paralizados)
- KPIs de Calidad (mermas/fallados/arreglos por servicio)
- Semaforo de Salud del Lote en listado

### Inventario FIFO
- Items, ingresos, salidas, kardex, BOM, reservas, consumo

### Exportacion CSV
- Registros, inventario, movimientos, mermas, fallados, arreglos

## Backlog Priorizado

### P2
- Lazy loading en frontend
- Logging estructurado en backend
- Refactorizar registros_main.py (1991 lineas)

### P3
- Exportacion PDF ademas de CSV
- Rate limiting en API

## Arquitectura Clave
```
backend/routes/
  transferencias_linea.py - Transferencias internas entre lineas (NUEVO)
  cierre.py           - UNICO archivo de cierre (consolidado)
  trazabilidad.py     - Fallados, arreglos, balance, KPIs
  registros_main.py   - CRUD registros (con salud del lote)
  reportes_produccion.py - Dashboard, matriz, alertas
  inventario_main.py  - FIFO, ingresos, salidas, ajustes
  auth.py             - Login, usuarios, permisos

frontend/src/
  pages/
    TransferenciasLinea.jsx - Listado, crear, detalle, confirmar/cancelar
    RegistroForm.jsx   - Orchestrador con handleReabrirCierre
  components/
    Layout.jsx         - Sidebar con entrada Transferencias
```

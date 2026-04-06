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
- **cierre_v2.py deprecado** (desmontado del server, queda como referencia)
- Fuentes de costo oficiales:
  - `costo_mp` = prod_inventario_salidas (FIFO real)
  - `costo_servicios` = prod_movimientos_produccion.costo_calculado
  - `otros_costos` = prod_registro_costos_servicio
  - `costo_total_final` = costo_mp + costo_servicios + otros_costos
  - `costo_unitario_final` = costo_total_final / qty_terminada_real
- **Congelamiento**: snapshot_json guarda desglose completo al cerrar (no se recalcula)
- **Reapertura controlada**: requiere motivo (5+ chars), revierte stock PT, guarda trazabilidad
- **Validaciones pre-cierre**: registro existe, no cerrado, qty>0, PT asignado, estado compatible
- **Ingreso PT automatico**: genera ingreso FIFO con costo unitario calculado
- **Frontend**: Preview desglose → Confirmar → Badge CERRADO → Historial reapertura
- **PDF Balance**: genera PDF detallado con costos congelados

### Tabla prod_registro_cierre (migrada)
Columnas nuevas agregadas: merma_qty, otros_costos, costo_unitario_final, cerrado_por, observacion_cierre, estado_cierre, snapshot_json, reabierto_por, reabierto_at, motivo_reapertura

### Endpoints oficiales de cierre
- `GET /api/registros/{id}/preview-cierre` - Preview con validaciones
- `POST /api/registros/{id}/cierre-produccion` - Ejecutar cierre
- `GET /api/registros/{id}/cierre-produccion` - Leer cierre congelado
- `POST /api/registros/{id}/reabrir-cierre` - Reapertura controlada
- `GET /api/registros/{id}/balance-pdf` - PDF balance
- `PUT /api/registros/{id}/pt-item` - Asignar PT

### Trazabilidad Unificada
- Backend: CRUD fallados, arreglos, liquidacion directa
- Timeline unificado, resumen de cantidades, mermas automaticas
- Frontend: TrazabilidadPanel en pestana Control

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
  cierre.py           - UNICO archivo de cierre (consolidado)
  cierre_v2.py        - DEPRECADO (desmontado, referencia)
  trazabilidad.py     - Fallados, arreglos, balance, KPIs
  registros_main.py   - CRUD registros (con salud del lote)
  reportes_produccion.py - Dashboard, matriz, alertas
  auth.py             - Login, usuarios, permisos

frontend/src/
  components/registro/
    RegistroDatosCard.jsx - Panel de cierre con badge/reapertura/snapshot
  pages/
    RegistroForm.jsx   - Orchestrador con handleReabrirCierre
```

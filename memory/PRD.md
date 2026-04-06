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

### Cierre de Produccion (Consolidado)
- Archivo unico oficial: `routes/cierre.py`
- Fuentes de costo: costo_mp (FIFO), costo_servicios, otros_costos
- Congelamiento: snapshot_json al cerrar
- Reapertura controlada con trazabilidad

### Trazabilidad Unificada
- Backend: CRUD fallados, arreglos, liquidacion directa
- Timeline unificado, resumen de cantidades, mermas automaticas
- Frontend: TrazabilidadPanel en pestana Control

### Transferencias Internas entre Lineas de Negocio (06-Abr-2026)
- Flujo completo: Borrador -> Confirmado / Cancelado
- Tablas: prod_transferencias_linea, prod_transferencias_linea_detalle
- Logica FIFO preservada: N ingresos destino con costo individual exacto
- Salida tipo TRANSFERENCIA en prod_inventario_salidas
- Transaccion atomica con FOR UPDATE
- Frontend: Pagina completa con listado, crear, detalle, confirmar/cancelar
- Testing: 100% pass rate iteration_44

### Bug Fix: Balance de Lote (06-Abr-2026)
- Problema: cantidad_no_resuelta de arreglos con resultado_final='BUENO' no se contabilizaba
- Fix: Toda cantidad_no_resuelta de arreglos RESUELTOS va a liquidacion por defecto

### Mejoras UX Layout Registro (06-Abr-2026)
- "Total Recibidas" reemplazado por "Cantidad efectiva (ultima recibida)" - muestra 232 en vez de 1192
- Panel lateral: Prendas muestra original tachado + efectiva en ambar (240 -> 232)
- Acciones de fila en menu "..." en vez de 3 iconos sueltos
- "Dividir Lote" movido a menu secundario (...)
- Datos del modelo se mantienen visibles por peticion del usuario
- Cantidad sugerida en nuevos movimientos usa ultima cantidad_recibida, no cantidad original

### Modulo de Auditoria - Fase 1 (06-Abr-2026)
- Tabla centralizada `produccion.audit_log` con JSONB (datos_antes, datos_despues)
- Helper `audit_log()` atomico dentro de transacciones PostgreSQL
- Helper `audit_log_safe()` best-effort para operaciones no criticas
- 11 endpoints criticos instrumentados:
  - registros_main.py: CREATE, UPDATE
  - movimientos.py: CREATE, DELETE
  - cierre.py: CONFIRM (atomico), REOPEN (atomico)
  - inventario_main.py: CREATE ingreso, CREATE salida, UPDATE ajuste
  - transferencias_linea.py: CONFIRM (atomico), CANCEL
- UI exclusiva admin: tabla, filtros (usuario/modulo/accion/fecha), paginacion, detalle expandible antes/despues
- Testing: 100% pass rate iteration_45 (17/17 backend, frontend 100%)

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

### P1 - UX/Simplificacion Avanzada (Pendiente)
- Separar modo tecnico vs operativo (operario vs admin)
- Ocultar BOM en operacion diaria
- Simplificar pantallas por etapa (Corte, Costura, Lavanderia, Acabado)
- Auto-llenado desde BOM

### P2
- Refactorizar registros_main.py y server.py (modularizar)
- Lazy loading en frontend
- Logging estructurado en backend

### P3
- Exportacion PDF
- Rate limiting API

## Arquitectura Clave
```
backend/routes/
  auditoria.py         - Auditoria: helper + endpoints GET
  transferencias_linea.py - Transferencias internas entre lineas
  cierre.py            - Cierre de produccion (consolidado)
  trazabilidad.py      - Fallados, arreglos, balance, KPIs
  registros_main.py    - CRUD registros
  reportes_produccion.py - Dashboard, matriz, alertas
  inventario_main.py   - FIFO, ingresos, salidas, ajustes
  movimientos.py       - Movimientos de produccion

frontend/src/
  pages/
    AuditoriaLogs.jsx       - UI de auditoria (admin)
    TransferenciasLinea.jsx  - Transferencias entre lineas
    RegistroForm.jsx         - Formulario principal
  components/registro/
    RegistroPanelLateral.jsx - Panel derecho
    RegistroMovimientosCard.jsx - Movimientos con menu "..."
```

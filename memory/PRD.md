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

### Bug Fix: Balance de Lote no cuadraba (06-Abr-2026)
- **Problema**: Las prendas `cantidad_no_resuelta` de arreglos con `resultado_final='BUENO'` no se contabilizaban en ninguna categoria del balance. Ejemplo: Corte 007 tenia 240 iniciales pero la suma daba 239.
- **Causa raiz**: El calculo en `trazabilidad.py` solo sumaba `cantidad_no_resuelta` cuando `resultado_final` era LIQUIDACION/SEGUNDA/DESCARTE, ignorando los casos BUENO/NULL.
- **Solucion**: TODA `cantidad_no_resuelta` de arreglos RESUELTOS va a liquidacion por defecto, excepto las marcadas explicitamente como SEGUNDA o DESCARTE.
- **Resultado**: Balance del Corte 007 ahora cuadra: 231 + 8 + 1 = 240

### Permisos Granulares
- servicios, acciones, estados por usuario
- Sidebar y alertas filtrados por permisos

### Reportes
- Dashboard con KPIs reactivos
- Matriz de produccion, Seguimiento (5 tabs incluyendo Paralizados)
- KPIs de Calidad (mermas/fallados/arreglos por servicio)
- Semaforo de Salud del Lote

### Inventario FIFO
- Items, ingresos, salidas, kardex, BOM, reservas, consumo

## Backlog Priorizado

### P1 - UX/Simplificacion (Pendiente - aplazado por usuario)
- Separar modo tecnico vs operativo
- Ocultar BOM en operacion diaria
- Simplificar pantallas por etapa (Corte, Costura, Lavanderia, Acabado)
- Auto-llenado desde BOM
- Reducir campos visibles
- Separacion por roles (operario vs admin)

### P2
- Lazy loading en frontend
- Logging estructurado en backend
- Refactorizar registros_main.py

### P3
- Exportacion PDF
- Rate limiting API

## Arquitectura Clave
```
backend/routes/
  transferencias_linea.py - Transferencias internas entre lineas
  cierre.py           - Cierre de produccion (consolidado)
  trazabilidad.py     - Fallados, arreglos, balance, KPIs
  registros_main.py   - CRUD registros
  reportes_produccion.py - Dashboard, matriz, alertas
  inventario_main.py  - FIFO, ingresos, salidas, ajustes

frontend/src/
  pages/
    TransferenciasLinea.jsx - Transferencias entre lineas
    RegistroForm.jsx   - Formulario principal de registro
  components/
    TrazabilidadPanel.jsx - Balance, timeline, fallados, arreglos
    Layout.jsx         - Sidebar con menus
```

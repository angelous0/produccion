# PRD - Produccion Textil

## Original Problem Statement
Sistema de gestion de produccion textil con flujo de trabajo completo: desde corte hasta almacen PT. Incluye gestion de inventario FIFO, BOM, movimientos de produccion, cierre de produccion, integracion con modulo de Finanzas.

## Core Requirements
1. Flujo de produccion completo con estados (Para Corte -> Almacen PT)
2. Gestion de inventario FIFO con ingresos, salidas, ajustes y rollos
3. BOM (Bill of Materials) por modelo con tallas
4. Cierre de produccion consistente con WIP
5. Integracion con modulo de Finanzas (proveedores, facturacion)
6. Automatizacion Modelo -> PT
7. Sistema de usuarios con permisos granulares
8. Control de produccion: atrasos, incidencias, paralizaciones

## What's Been Implemented
- Flujo de produccion completo con linea de tiempo de estado
- Panel de cierre integrado en RegistroForm
- Automatizacion Modelo -> PT (autocompletado)
- Selector de proveedores desde finanzas2.cont_tercero en Ingresos
- Badge de estado de facturacion en lista de Ingresos
- Endpoint GET /api/ingresos-mp/para-finanzas
- Endpoint GET /api/proveedores
- Correccion de bugs: empresa_id, ordenamiento servicios, decimales, fechas
- Boton prorratear cantidades por color
- Filtros por categoria en Inventario
- **2026-03-18**: Filtrado de items PT en selectores de Ingresos y Salidas
- **2026-03-18**: Proteccion anti doble-click con hook `useSaving()` en 21 paginas
- **2026-03-18**: Fix tarifa_aplicada: nueva columna en BD
- **2026-03-18**: Fix WIP vacio (empresa_id=7 → 6)
- **2026-03-18**: Sidebar fijo al navegar
- **2026-03-19**: Control de Produccion completo:
  - Fecha entrega esperada con alertas visuales
  - Estado operativo automatico (NORMAL/EN_RIESGO/PARALIZADA)
  - Responsable actual
  - Sistema de incidencias (CRUD + historial)
  - Sistema de paralizaciones (crear/levantar + validacion 1 activa)

## DB Changes
- `prod_movimientos_produccion`: columna `tarifa_aplicada NUMERIC(14,4)`
- `prod_registros`: columnas `fecha_entrega_esperada DATE`, `estado_operativo VARCHAR(20)`, `responsable_actual VARCHAR(100)`
- `prod_incidencia`: tabla nueva (id, empresa_id, registro_id, fecha_hora, usuario, tipo, comentario, estado)
- `prod_paralizacion`: tabla nueva (id, empresa_id, registro_id, fecha_inicio, fecha_fin, motivo, comentario, activa)

## Prioritized Backlog

### P0 - Completado
- [x] Selector proveedores Finanzas en Ingresos
- [x] Filtrar PT de selectores Ingresos/Salidas
- [x] Proteccion anti doble-click global
- [x] Fix tarifa_aplicada persistencia
- [x] Fix WIP vacio
- [x] Sidebar fijo
- [x] Control de produccion (fecha entrega, estado operativo, incidencias, paralizaciones, responsable)

### P1
- [ ] Logica en modulo Finanzas para vincular ingresos MP a facturas

### P2
- [ ] Limpiar lineas BOM huerfanas

### P3
- [ ] Reporte productividad por persona/servicio
- [ ] Drag-and-drop reordenar tallas
- [ ] Permisos granulares con usePermissions
- [ ] Exportacion Excel/PDF (Kardex, etc.)
- [ ] Refactorizar RegistroForm.jsx (1600+ lineas)
- [ ] Accesibilidad en componentes Dialog

## Architecture
- Backend: FastAPI + PostgreSQL (asyncpg)
- Frontend: React + Shadcn/UI + Tailwind
- DB Schemas: produccion (principal), finanzas2 (proveedores, facturas)
- Auth: JWT con bcrypt

## Key Files
- /app/frontend/src/hooks/useSaving.js - Hook anti doble-click
- /app/frontend/src/pages/Registros.jsx - Tabla registros con control produccion
- /app/frontend/src/pages/RegistroForm.jsx - Formulario registro produccion
- /app/backend/routes/control_produccion.py - Endpoints incidencias/paralizaciones
- /app/backend/routes/integracion_finanzas.py - Endpoints integracion Finanzas
- /app/backend/server.py - Backend principal

## Key API Endpoints
- PUT /api/registros/{id}/control - Actualizar fecha entrega y responsable
- GET/POST /api/incidencias/{registro_id} - Listar/crear incidencias
- PUT /api/incidencias/{id} - Resolver incidencia
- GET /api/paralizaciones/{registro_id} - Listar paralizaciones
- POST /api/paralizaciones - Crear paralizacion
- PUT /api/paralizaciones/{id}/levantar - Levantar paralizacion

## Key Credentials
- Usuario: eduard / eduard123

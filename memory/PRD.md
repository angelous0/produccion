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
- **2026-03-18**: Fix tarifa_aplicada: nueva columna en BD, backend guarda/devuelve la tarifa del movimiento

## DB Changes
- `prod_movimientos_produccion`: Agregada columna `tarifa_aplicada NUMERIC(14,4)`

## Prioritized Backlog

### P0 - Completado
- [x] Selector proveedores Finanzas en Ingresos
- [x] Filtrar PT de selectores Ingresos/Salidas
- [x] Proteccion anti doble-click global (useSaving hook)
- [x] Fix tarifa_aplicada persistencia en movimientos

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
- [ ] Accesibilidad en componentes Dialog (DialogTitle/Description)

## Architecture
- Backend: FastAPI + PostgreSQL (asyncpg)
- Frontend: React + Shadcn/UI + Tailwind
- DB Schemas: produccion (principal), finanzas2 (proveedores, facturas)
- Auth: JWT con bcrypt
- Hook reutilizable: useSaving() para proteccion anti doble-click

## Key Credentials
- Usuario: eduard / eduard123

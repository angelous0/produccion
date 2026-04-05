# Sistema de Produccion Textil - PRD

## Problema Original
Sistema de gestion de produccion textil full-stack con trazabilidad unificada de lotes, permisos granulares y reportes operativos.

## Stack
- Backend: FastAPI + asyncpg + PostgreSQL
- Frontend: React + Tailwind + Shadcn/UI
- BD: PostgreSQL (schema `produccion`)

## Credenciales
- Admin: `eduard` / `eduard123`
- empresa_id estandarizado: **7** (en todo el sistema)

## Funcionalidades Implementadas

### Core
- Gestion de registros de produccion (CRUD completo)
- Modelos, marcas, tipos, entalles, telas, hilos, tallas, colores
- Rutas de produccion con etapas
- Movimientos entre servicios/personas
- Incidencias con paralizacion

### Trazabilidad Unificada (Completa)
- Backend: CRUD fallados, arreglos, liquidacion directa
- Resumen de cantidades (balance del lote)
- Timeline unificado (movimientos + mermas + fallados + arreglos + divisiones)
- Reporte general de trazabilidad
- Mermas automaticas cuando cantidad_enviada != cantidad_recibida
- Frontend: TrazabilidadPanel integrado en pestana "Control"

### Permisos Granulares
- servicios_permitidos, acciones_produccion, acciones_inventario, estados_permitidos
- Hook usePermissions para frontend
- Restriccion visual en timeline y dropdown de estados

### Reportes
- Dashboard con KPIs reactivos
- Matriz de produccion (fusión columnas, modal enriquecido, colores)
- Seguimiento: En Proceso, WIP Etapa, Atrasados, Cumplimiento Ruta, Paralizados
- Operativo: Balance Terceros, Costura, Tiempos Muertos
- Lotes: Trazabilidad, Fraccionados
- Calidad: Mermas, Estados Item
- Valorizacion: MP, WIP, PT

### Inventario FIFO
- Items, ingresos, salidas, ajustes, rollos, kardex
- BOM (Bill of Materials) con explosion
- Reservas y consumo de materia prima

### UI/UX
- RegistroForm con pestanas (General, Produccion, Control)
- Panel lateral contextual
- Tema oscuro/claro

## Limpieza realizada (05-Abr-2026)
- Estandarizado empresa_id = 7 en 10 archivos y 5 tablas BD
- Eliminados 8 archivos muertos (2723 lineas): scripts de migracion, tests sueltos
- Corregidos todos los bare except: a except especificos
- Conectado ReporteParalizados al menu de Seguimiento
- Fix bug: variable cantidad_inicial usada antes de definirse en trazabilidad.py
- Migracion automatica en startup para normalizar empresa_id

## Backlog Priorizado

### P1
- Reportes/KPIs de Trazabilidad (perdidas por servicio, fallados por responsable, arreglos vencidos)

### P2
- Filtrar alertas (campana) por servicios del usuario
- Filtrar Sidebar por permisos con usePermissions

### P3
- Exportacion a Excel/PDF
- Lazy loading en frontend

## Arquitectura de Archivos Clave
```
backend/
  server.py          - Startup, DDL, middleware (1089 lineas)
  auth.py            - Utilidades JWT, get_current_user
  auth_utils.py      - Helpers de auth
  db.py              - Pool PostgreSQL
  helpers.py         - row_to_dict, utilidades
  routes/
    auth.py          - Login, usuarios, permisos
    registros_main.py - CRUD registros (1991 lineas)
    trazabilidad.py  - Fallados, arreglos, balance, timeline
    movimientos.py   - Movimientos produccion, mermas auto
    reportes_produccion.py - Dashboard, matriz, KPIs
    + 15 routers mas

frontend/src/
  pages/
    RegistroForm.jsx - Detalle registro (3 pestanas)
    Registros.jsx    - Listado con RegistroDetalleFase2
    Dashboard.jsx    - KPIs principales
  components/
    TrazabilidadPanel.jsx - Balance + timeline + CRUD fallados/arreglos
    registro/        - Subcomponentes modulares
  hooks/
    usePermissions.js - Permisos granulares
```

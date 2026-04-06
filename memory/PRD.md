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
- Sidebar filtrado por permisos del usuario
- Alertas (campana) filtradas por servicios permitidos

### Reportes
- Dashboard con KPIs reactivos
- Matriz de produccion (fusion columnas, modal enriquecido, colores)
- Seguimiento: En Proceso, WIP Etapa, Atrasados, Cumplimiento Ruta, Paralizados
- Operativo: Balance Terceros, Costura, Tiempos Muertos
- Lotes: Trazabilidad, Fraccionados, KPIs Calidad (mermas/fallados/arreglos por servicio/responsable)
- Calidad: Mermas, Estados Item
- Valorizacion: MP, WIP, PT

### Semaforo de Salud del Lote
- Columna "Salud" en listado de registros
- Indicadores visuales: mermas (ambar), fallados (rojo), arreglos vencidos (rosa)
- "OK" verde cuando no hay novedades

### Exportacion CSV
- Registros, inventario, movimientos, productividad, personas, modelos
- Mermas, fallados, arreglos (nuevo)
- Compatible con Excel (BOM UTF-8)

### Inventario FIFO
- Items, ingresos, salidas, ajustes, rollos, kardex
- BOM (Bill of Materials) con explosion
- Reservas y consumo de materia prima

### UI/UX
- RegistroForm con pestanas (General, Produccion, Control)
- Panel lateral contextual
- Tema oscuro/claro

## Limpieza realizada
- Estandarizado empresa_id = 7 en 10 archivos y 5 tablas BD
- Eliminados 8 archivos muertos (2723 lineas)
- Corregidos todos los bare except a excepciones especificas
- Migracion automatica en startup para normalizar empresa_id

## Backlog Priorizado

### P1
- (Nada pendiente critico)

### P2
- Lazy loading en frontend (todas las paginas cargan de golpe)
- Logging estructurado en backend

### P3
- Exportacion PDF ademas de CSV
- Rate limiting en API
- Refactorizar registros_main.py (1991 lineas)

## Arquitectura de Archivos Clave
```
backend/
  server.py          - Startup, DDL, middleware
  auth.py            - Utilidades JWT, get_current_user
  routes/
    auth.py          - Login, usuarios, permisos
    registros_main.py - CRUD registros (con salud del lote)
    trazabilidad.py  - Fallados, arreglos, balance, timeline, KPIs
    movimientos.py   - Movimientos produccion, mermas auto
    reportes_produccion.py - Dashboard, matriz, alertas (con servicio_id)
    stats_reportes.py - Export CSV (mermas, fallados, arreglos)
    + 15 routers mas

frontend/src/
  pages/
    RegistroForm.jsx       - Detalle registro (3 pestanas)
    Registros.jsx          - Listado con columna Salud
    ReporteTrazabilidadKPIs.jsx - KPIs calidad (mermas/fallados/arreglos)
    LotesTrazabilidad.jsx  - Hub con 3 pestanas
    SeguimientoProduccion.jsx - 5 pestanas incluyendo Paralizados
  components/
    TrazabilidadPanel.jsx  - Balance + timeline + CRUD
    NotificacionesBell.jsx - Alertas filtradas por permisos
    Layout.jsx             - Sidebar filtrado por permisos
    ExportButton.jsx       - Boton reutilizable de exportacion
  hooks/
    usePermissions.js      - Permisos granulares con RUTA_A_TABLA
```

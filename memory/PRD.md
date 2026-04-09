# Sistema de Produccion Textil - PRD

## Descripcion General
ERP full-stack para gestion de produccion textil. Backend FastAPI + Frontend React + PostgreSQL.

## Modulos Implementados

### 1. Produccion Core
- Registros de produccion (OP), modelos, rutas, tallas, colores
- Movimientos de produccion (envio/recepcion entre servicios)
- Incidencias y paralizaciones

### 2. Inventario FIFO
- Items de inventario con control de stock
- Ingresos, salidas, ajustes con costeo FIFO
- Rollos de tela con trazabilidad
- Alertas de stock minimo

### 3. Trazabilidad Simplificada (V2)
- prod_fallados simplificada: fuente oficial de total_fallados
- prod_registro_arreglos: envios a arreglo con resolucion (recuperado/liquidacion/merma)
- Estados automaticos: EN_ARREGLO, PARCIAL, COMPLETADO, VENCIDO (3 dias limite)
- Ecuacion de validacion en tiempo real

### 4. Control de Fallados
- Integrado como tab "Fallados y Arreglos" dentro de Calidad
- KPIs: Total Fallados, Pendientes, Vencidos, Recuperado, Liquidacion, Merma
- Filtros y tabla consolidada por registro
- Endpoint: GET /api/fallados-control

### 5. Distribucion PT y Conciliacion Odoo
- Tab PT Odoo en detalle de registro

### 6. Kardex PT
- Lectura del schema Odoo (stock_move, stock_location)

### 7. Cierre de Produccion
- Preview con costos + resultado_final de arreglos V2

### 8. Reportes - Reestructurado 2026-04-09
Dashboard unico con KPIs, alertas, WIP por etapa, carga por servicio y accesos rapidos.
Pantallas consolidadas con Tabs:
- **Seguimiento**: En Proceso, WIP por Etapa, Atrasados, Cumplimiento Ruta, Paralizados
- **Operativo y Terceros**: Rep. Operativo, Tiempos Muertos, Paralizados, Balance Terceros
- **Lotes y Trazabilidad**: Fraccionados, Trazabilidad General, KPIs Calidad
- **Valorizacion**: MP Valorizado, WIP, PT Valorizado
- **Calidad**: Resumen Calidad, Mermas, Estados del Item, Fallados y Arreglos
- **Matriz Dinamica**: pantalla independiente

### 9. Sidebar y Dashboard Rediseñados - 2026-04-09
**Sidebar** reorganizado en 6 grupos jerárquicos:
- OPERACIONES (sin titulo): Dashboard, Registros, Seguimiento
- INVENTARIO (titulo visible, siempre expandido): 10 items
- REPORTES (titulo visible, siempre expandido): 5 items
- CATÁLOGOS (colapsable, cerrado por defecto): 11 items
- MAESTROS (colapsable, cerrado por defecto): 6 items
- CONFIGURACIÓN (colapsable, cerrado, solo admin): 4 items
Chevrons que rotan, estado en localStorage.

**Dashboard** rediseñado:
- Saludo dinámico según hora + fecha
- 4 KPIs con colores semáforo (azul, verde, rojo, ámbar)
- 3 Acciones Rápidas (Nuevo Registro, Ver Seguimiento, Ingresar Stock)
- Lotes Activos con pills filtro (Todos/Corte/Costura/Acabado/Atrasados)
- Alertas inline max 3
- WIP por Etapa + Carga por Servicio

## Arquitectura
```
/app/backend/routes/
  trazabilidad.py, cierre.py, registros_main.py
  distribucion_pt.py, kardex_pt.py
  reportes_produccion.py, stats_reportes.py

/app/frontend/src/
  components/Layout.jsx         - Sidebar con 6 grupos jerárquicos
  components/ArreglosPanel.jsx  - Panel arreglos en tab Control
  pages/Dashboard.jsx           - Dashboard rediseñado
  pages/CalidadConsolidado.jsx  - 4 tabs con useSearchParams
  pages/OperativoTerceros.jsx   - 4 tabs reordenados
  pages/SeguimientoProduccion.jsx - 5 tabs
  pages/LotesTrazabilidad.jsx  - 3 tabs
  pages/ValorizacionConsolidado.jsx - 3 tabs
  pages/ControlFallados.jsx     - Integrado como tab en Calidad
  pages/RegistroForm.jsx        - Formulario registro
```

## Tareas Pendientes
- P1: Integrar filtro linea_negocio_id en Reportes e Inventario
- P2: Fase 2 de Reportes (indicadores por servicio, ranking, tiempos promedio)
- P2: Refactorizar registros_main.py y server.py (modularizacion)
- P2: Logging estructurado backend
- P3: Exportacion PDF de reportes
- P3: Rate limiting API

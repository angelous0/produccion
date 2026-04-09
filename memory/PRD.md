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

### 3. Trazabilidad Simplificada (V2) - NUEVO 2026-04-09
- **prod_fallados simplificada**: fuente oficial de total_fallados (id, registro_id, cantidad_detectada, fecha_deteccion, observacion, created_by)
- **prod_registro_arreglos**: envios a arreglo con resolucion (recuperado/liquidacion/merma)
- Estados automaticos: EN_ARREGLO, PARCIAL, COMPLETADO, VENCIDO (3 dias limite)
- Resumen de cantidades: total_producido = normal + recuperado + liquidacion + merma + fallado_pendiente
- Ecuacion de validacion en tiempo real
- Alertas por arreglos vencidos y fallados pendientes

### 4. Distribucion PT y Conciliacion Odoo
- Tabla prod_registro_pt_relacion (distribucion planificada)
- Tabla prod_registro_pt_odoo_vinculo (vinculo con ajustes Odoo)
- Tab PT Odoo en detalle de registro

### 5. Kardex PT
- Lectura del schema Odoo (stock_move, stock_location)
- Saldo historico acumulado con Window Functions
- Filtros por fecha, producto, tipo de movimiento

### 6. Cierre de Produccion
- Preview con costos (MP, servicios, otros)
- Ingreso automatico a inventario PT
- Snapshot de auditoria congelado
- Integrado con resultado_final de arreglos V2

### 7. Reportes
- Dashboard con KPIs
- Reporte de trazabilidad general
- KPIs de trazabilidad (mermas, fallados, arreglos)
- Reporte de costura, atrasados, balance terceros

## Arquitectura

```
/app
├── backend/
│   ├── routes/
│   │   ├── trazabilidad.py (REESCRITO V2: fallados simplificados + arreglos V2)
│   │   ├── distribucion_pt.py
│   │   ├── kardex_pt.py
│   │   ├── cierre.py (actualizado con resultado_final arreglos)
│   │   ├── registros_main.py
│   │   ├── inventario_main.py
│   │   ├── reportes_produccion.py
│   │   └── stats_reportes.py (actualizado query arreglos)
│   ├── tests/
│   │   └── test_fallados_arreglos_v2.py (25 tests, 100% passed)
│   ├── models.py
│   └── server.py
└── frontend/
    └── src/
        ├── components/
        │   ├── ArreglosPanel.jsx (NUEVO: panel simplificado 3 bloques)
        │   ├── TrazabilidadPanel.jsx (legacy, reemplazado por ArreglosPanel)
        │   └── registro/
        │       └── DistribucionPTPanel.jsx
        ├── pages/
        │   ├── RegistroForm.jsx (usa ArreglosPanel en tab Control)
        │   ├── TrazabilidadReporte.jsx (actualizado campos V2)
        │   ├── ReporteTrazabilidadKPIs.jsx (actualizado campos V2)
        │   └── KardexPT.jsx
```

## Tablas Clave (Schema produccion)
- prod_registros: registros de produccion
- prod_fallados: deteccion de fallados (simplificada)
- prod_registro_arreglos: envios a arreglo V2 (nueva)
- prod_arreglos: tabla legacy (mantenida para datos historicos)
- prod_mermas: mermas/faltantes
- prod_registro_cierre: cierres de produccion
- prod_registro_pt_relacion: distribucion PT
- prod_registro_pt_odoo_vinculo: vinculos con Odoo

## Endpoints Clave
- CRUD Fallados: GET/POST /api/fallados, PUT/DELETE /api/fallados/{id}
- CRUD Arreglos V2: GET/POST /api/registros/{id}/arreglos, PUT/DELETE /api/arreglos/{id}
- Resumen: GET /api/registros/{id}/resumen-cantidades
- Timeline: GET /api/registros/{id}/trazabilidad-completa
- KPIs: GET /api/reportes/trazabilidad-kpis
- Reporte: GET /api/reporte-trazabilidad
- Preview cierre: GET /api/registros/{id}/preview-cierre

## Tareas Pendientes
- P1: Integrar filtro linea_negocio_id en Reportes (Dashboard, KPIs, Matriz)
- P2: Refactorizar registros_main.py y server.py (modularizacion)
- P2: Logging estructurado backend
- P3: Exportacion PDF de reportes
- P3: Rate limiting API

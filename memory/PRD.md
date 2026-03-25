# PRD - Produccion Textil

## Original Problem Statement
Sistema de gestion de produccion textil con flujo de trabajo completo: desde corte hasta almacen PT. Incluye gestion de inventario FIFO, BOM, movimientos de produccion, cierre de produccion, control operativo por movimiento, division de lotes, reportes de produccion P0, y trazabilidad unificada de cantidades.

## What's Been Implemented
- Flujo de produccion completo con linea de tiempo de estado
- Panel de cierre integrado en RegistroForm
- Proteccion anti doble-click con hook useSaving() en 21+ paginas
- Control Operativo: fecha_esperada por movimiento, alertas, incidencias, paralizaciones
- Personal Interno/Externo: tipo_persona y unidad_interna
- Vinculacion Bidireccional Estado-Movimientos (sugerencias, bloqueos, auto-guardado)
- Division de Lote (Split): dividir, reunificar, nomenclatura automatica
- Performance: GET registros 5.8s->0.5s, GET modelos 3.3s->0.5s
- Rutas editables inline
- **Modulo Reportes P0** (2026-03-24):
  - Dashboard KPIs, En Proceso, WIP por Etapa, Atrasados, Trazabilidad, Cumplimiento Ruta, Balance Terceros, Lotes Fraccionados
- **Matriz Dinamica de Produccion** (2026-03-24):
  - Filas = Item (Marca-Tipo-Entalle-Tela) + Hilo
  - Columnas = Estados dinamicos (adaptan segun ruta seleccionada)
  - Toggle Registros/Prendas, 7 filtros + 3 toggles
  - Columnas visibles/reordenables, preferencias en localStorage
  - Fusion de columnas (absorber columnas, valores sumados, persistente)
  - **Pop-up modal tipo tabla Excel** con: Corte, Estado, Modelo, Prendas, Curva, Hilo Esp., Ruta, Entrega, Inicio Prod., Dias, Ult. Mov, Dif., Info, Accion
  - Click en celda filtra por estado; click en item/total muestra todos
  - **Dias = desde fecha_inicio del primer movimiento** (no creacion)
  - **Todas las fechas en formato dd-mm-yy** en todo el modulo de reportes
- **Trazabilidad Unificada** (2026-03-24):
  - Backend: Tablas prod_fallados y prod_arreglos con init en startup
  - CRUD completo: Fallados (crear, editar, eliminar) y Arreglos (crear, cerrar, eliminar)
  - Validaciones: cantidades reparable+no_reparable <= detectada, arreglos <= reparables, cierre <= enviada
  - Resumen de cantidades calculado en tiempo real (GET /api/registros/{id}/resumen-cantidades)
  - Timeline unificado cronologico: movimientos + mermas + fallados + arreglos + divisiones
  - Integracion automatica de mermas cuando hay diferencia en movimientos
  - Frontend: TrazabilidadPanel.jsx con Balance del Lote, Tabs (Timeline, Fallados, Arreglos, Diferencias, Divisiones)
  - Dialogs para registrar fallados, crear arreglos y cerrar arreglos
  - Alertas visuales para vencidos, mermas y pendientes
  - Relacion padre-hijo visible en el balance
- **Migracion MariaDB -> PostgreSQL** (2026-03-25):
  - 8 marcas, 25 tipos, 26 entalles, 28 telas, 1160 modelos, 1150 registros, 3418 movimientos, 79 personas, 17 servicios, 165 colores, 13 tallas, 613 historial
  - Inventario: 390 items, 505 ingresos, 272 salidas
- **Optimizacion Performance** (2026-03-25):
  - Paginacion server-side en Registros (174 items, limit/offset/search/estados)
  - Paginacion server-side en Modelos (1161 items, limit/offset/search/marca/tipo/entalle/tela)
  - Paginacion server-side en Movimientos de Produccion (3422 items, limit/offset/search/servicio/persona/fecha)
  - Eliminacion de N+1 queries en movimientos (3-4 queries por item -> JOINs)
  - Endpoint GET /api/modelos-filtros para opciones de filtro
  - Endpoint GET /api/registros-estados para estados unicos
  - Carga independiente de catalogos (Promise.allSettled) para resiliencia contra BD lenta
  - Combobox buscable para Modelo en RegistroForm
  - Vista tipo Excel para Modelos con buscadores, metricas de registros y navegacion cruzada
- **Forzar Cambio de Estado** (2026-03-25):
- **Skip Validacion por Registro** (2026-03-25):
  - POST /api/registros/{id}/validar-cambio-estado acepta {forzar: true} para saltar validaciones
  - Dialog en frontend "Cambio de Estado Bloqueado" con boton "Forzar Cambio" (destructive)
  - Util para registros migrados que ya tienen todos sus movimientos
- **Paginación Server-Side en Inventario** (2026-03-25):
  - GET /api/inventario paginado (limit/offset/search/categoria/stock_status; o all=true)
  - GET /api/inventario-filtros para categorias desde la BD
  - Buscador por nombre y codigo
  - Filtros por categoria (9 categorias reales) y estado de stock (OK, Stock bajo, Sin stock)
  - 392 items → carga 50/pagina instantaneamente
  - Campo persistente `skip_validacion_estado` en prod_registros (boolean)
  - PUT /api/registros/{id}/skip-validacion para activar/desactivar
  - Checkbox "Sin restricciones" visible junto al selector de estado en RegistroForm
  - Cuando esta activo, el registro puede cambiar de estado libremente sin validar movimientos
  - Ideal para registros migrados antiguos (ej: 228-2025) que no tienen movimientos en el sistema nuevo

## Key API Endpoints
- GET /api/registros (paginado: limit, offset, search, estados, excluir_estados, modelo_id)
- GET /api/registros-estados
- GET /api/registros/{id}
- POST /api/registros/{id}/validar-cambio-estado (con opcion forzar: true)
- GET /api/modelos (paginado: limit, offset, search, marca, tipo, entalle, tela; o all=true)
- GET /api/modelos-filtros
- GET /api/movimientos-produccion (paginado: limit, offset, search, servicio_id, persona_id, fecha_desde, fecha_hasta; o all=true)
- GET /api/reportes-produccion/dashboard
- GET /api/reportes-produccion/matriz
- GET /api/fallados / POST / PUT / DELETE
- GET /api/arreglos / POST / PUT / DELETE
- GET /api/registros/{id}/resumen-cantidades
- GET /api/registros/{id}/trazabilidad-completa
- GET /api/guias-remision (listado con filtros)

## Prioritized Backlog
### P0 (COMPLETADO)
- [x] Modulo Reportes P0 (8 reportes + filtros)
- [x] Matriz Dinamica de Produccion (fusion, modal Excel, dias desde primer mov, dd-mm-yy)
- [x] Trazabilidad Unificada Backend + Frontend
- [x] Migracion MariaDB -> PostgreSQL completa
- [x] Optimizacion N+1 queries
- [x] Paginacion server-side: Registros, Modelos, Movimientos
- [x] Forzar cambio de estado para registros migrados
- [x] Combobox buscable + Carga resiliente de catalogos
- [x] Vista tipo Excel para Modelos

### P1
- [ ] Logica en modulo Finanzas para cargos internos
- [ ] Reportes P1: Productividad persona/servicio, Incidencias/Glosas, PT generado, Antiguedad, Mermas
- [ ] Reportes y KPIs de Trazabilidad: perdidas por servicio, fallados por responsable, arreglos vencidos

### P2
- [ ] Reportes P2: Reprocesos, Eficiencia vs Estandar, Cumplimiento por modelo, Carga futura
- [ ] Limpiar lineas BOM huerfanas

### P3
- [ ] Permisos granulares con usePermissions
- [ ] Exportacion Excel/PDF
- [ ] Refactorizar RegistroForm.jsx (~2900 lineas)
- [ ] Migrar server.py a routers modulares (~6800 lineas)

## Key Credentials
- Usuario: eduard / eduard123

## Code Architecture
```
/app
├── backend/
│   ├── routes/
│   │   ├── reportes_produccion.py
│   │   ├── trazabilidad.py (Fallados, Arreglos, Resumen, Timeline)
│   │   └── inventario.py
│   ├── tests/
│   │   ├── test_trazabilidad.py
│   │   ├── test_guias_remision.py
│   │   ├── test_matriz_colores.py
│   │   ├── test_pagination_force_state.py
│   │   └── test_movimientos_produccion.py
│   └── server.py (~6800 lines - needs modularization)
└── frontend/
    └── src/
        ├── components/
        │   └── TrazabilidadPanel.jsx
        └── pages/
            ├── MatrizProduccion.jsx
            ├── Modelos.jsx (paginacion server-side)
            ├── Registros.jsx (paginacion server-side)
            ├── MovimientosProduccion.jsx (paginacion server-side)
            └── RegistroForm.jsx (~2900 lines - needs refactoring)
```

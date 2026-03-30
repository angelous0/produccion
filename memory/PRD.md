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
- **Incidencias Unificadas con Paralizaciones** (2026-03-26):
  - Unificado: una incidencia puede opcionalmente paralizar la produccion (check "Paraliza produccion")
  - Al resolver incidencia con paralizacion, se levanta automaticamente
  - Catalogo administrable de motivos: tabla prod_motivos_incidencia con CRUD
  - Creacion inline de motivos desde el dialog de incidencia
  - Seccion de Incidencias movida dentro del formulario RegistroForm
  - Lista de Registros simplificada: de 7 a 4 botones (Ver, Colores, Editar, Eliminar)
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
- **Incidencias Unificadas con Paralizaciones** (2026-03-26):
  - Incidencias y Paralizaciones fusionadas en una sola entidad con check "Paraliza produccion"
  - Catalogo administrable de motivos (prod_motivos_incidencia) con CRUD inline
  - Seccion de Incidencias reubicada dentro de RegistroForm
  - Lista de Registros simplificada: de 7 a 4 botones de acción
- **Tabla Registros Estilo Excel** (2026-03-26):
  - 15 columnas configuradas (N Corte, Fecha, Modelo, Marca, Tipo, Entalle, Tela, Color, Talla, Cantidad, Estado, etc.)
  - Filtro y resaltado visual de filas Urgentes
  - Combobox buscable para Servicio y Persona en modal de movimientos
- **QA General y Correcciones** (2026-03-26):
  - Corregidos crasheos en InventarioSalidas, GuiasRemision, CalidadMerma por cambio a paginacion
  - 14/14 paginas principales verificadas y funcionando
  - Backend 96% tests pasados (26/27)
- **Vista Unificada Materiales** (2026-03-26):
  - Pestaña "Materiales" reemplaza Requerimiento + Reservas + Salidas en Gestion OP
  - Endpoint consolidado GET /api/registros/{id}/materiales
  - KPIs: Requerido, Reservado, Consumido, Pendiente
  - Toggle Dar Salida / Reservar en misma vista
  - Boton "Llenar pendientes" auto-completa cantidades
  - Salida extra para items fuera del BOM
  - Historial colapsable de reservas y salidas
  - Componente reutilizable MaterialesTab.jsx y SearchableSelect.jsx
  - Endpoint GET /api/inventario/alertas-stock con modo fisico/disponible
  - Endpoint PUT /api/inventario/{id}/ignorar-alerta para archivar items
  - Campo ignorar_alerta_stock en prod_inventario
  - Stats del dashboard incluyen conteos de alertas de stock
  - Pagina ReporteStockBajo.jsx con KPIs, toggle modo, toggle ignorados, tabla con boton ignorar
  - Banner de alerta clickeable en Dashboard y en pagina de Inventario
  - Link "Alertas Stock" en sidebar bajo Inventario FIFO
  - Solo items con stock_minimo > 0 configurado son evaluados

- **Selector de BOM en Materiales** (2026-03-27):
  - Al generar requerimiento, el sistema ahora selecciona el BOM específico (no mezcla líneas de múltiples BOMs)
  - Si hay 1 solo BOM: muestra etiqueta informativa (codigo, versión, estado)
  - Si hay múltiples BOMs: muestra dropdown selector, auto-selecciona el APROBADO
  - Backend: endpoint generar-requerimiento acepta ?bom_id= opcional; auto-selecciona APROBADO > BORRADOR si no se especifica
  - Toast de éxito incluye nombre del BOM usado
- **Bugfix Dar Salida desde Materiales** (2026-03-27):
  - Corregido empresa_id inválido (items con empresa_id=1 que no existía en cont_empresa)
  - empresa_id ahora se toma del registro, no del item
  - Items con control_por_rollos ahora auto-seleccionan rollo FIFO si no se especifica rollo_id
  - Manejo de errores parciales: si una línea falla, las demás se procesan y se reporta el resultado
- **Feature Consumir Reservado** (2026-03-27):
  - Nuevo botón "Consumir reservado" en MaterialesTab que llena automáticamente las cantidades con lo reservado menos lo ya consumido
  - Solo aparece cuando hay material reservado pendiente de consumir
  - Cambia automáticamente al modo "Dar Salida"
- **Selector de Rollos en Materiales** (2026-03-27):
  - Items con control_por_rollos muestran botón "Seleccionar rollos" que abre modal pop-up
  - Modal con buscador, filtros por ancho y tono, tabla de rollos con cantidad individual
  - Botón "Todo" por rollo para tomar metraje completo, "Quitar" para limpiar
  - "Llenar pendiente FIFO" auto-distribuye cantidad entre rollos (más antiguos primero)
  - Muestra total seleccionado vs pendiente. Botón padre muestra resumen (ej: "310.0 (4 rollos)")
  - Salidas se crean una por rollo con rollo_id específico
- **Anular Salidas** (2026-03-27):
  - Botón "Anular" en historial de salidas, restaura stock y metraje de rollos

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
- GET /api/registros/{id}/conversacion (mensajes del hilo)
- POST /api/registros/{id}/conversacion (crear mensaje o respuesta)
- DELETE /api/conversacion/{id} (eliminar mensaje y sus respuestas)
- GET /api/fallados / POST / PUT / DELETE
- GET /api/arreglos / POST / PUT / DELETE
- GET /api/registros/{id}/resumen-cantidades
- GET /api/registros/{id}/trazabilidad-completa
- GET /api/guias-remision (listado con filtros)
- GET /api/inventario/alertas-stock (modo=fisico|disponible, incluir_ignorados=true|false)
- PUT /api/inventario/{id}/ignorar-alerta (toggle)
- GET /api/lineas-negocio (lineas activas de finanzas2)
- GET /api/inventario/stock-por-linea (stock agrupado por item y linea)

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
- [x] **Linea de Negocio en Produccion/Inventario** (2026-03-27):
  - Endpoint GET /api/lineas-negocio (lee de finanzas2.cont_linea_negocio)
  - Endpoint GET /api/inventario/stock-por-linea (stock agrupado por item + linea)
  - linea_negocio_id en: prod_modelos, prod_registros, prod_inventario_ingresos, prod_inventario_salidas
  - Modelos: selector de linea en form, columna en tabla
  - Registros: herencia automatica del modelo, no editable si tiene consumos/movimientos
  - Inventario: linea_negocio_id nullable (null=GLOBAL), filtro por linea, selector en form
  - Ingresos: auto-herencia de linea desde item exclusivo
  - Salidas: herencia de linea desde registro
  - MaterialesTab: filtro automatico MP por linea del registro (misma linea + global)
  - Propiedad es_cierre en etapas de ruta de produccion
- **Bugfix Overflow CSS en RegistroForm** (2026-03-27):
  - Corregido desbordamiento de pantalla al hacer scroll en RegistroForm
  - Fixes: min-h-0/min-w-0 en Layout flex containers, overflow-x-hidden en main, overflow:hidden en body/html/#root
  - pb-8 en wrapper del formulario para padding inferior adecuado
- **Bugfix Error Crear Incidencia + CRUD Motivos** (2026-03-27):
  - Corregido varchar(30) en columna tipo de prod_incidencia que impedía guardar UUIDs (36 chars)
  - Nuevo endpoint PUT /api/motivos-incidencia/{id} para editar nombre de motivos
  - UI: enlace "Gestionar motivos" despliega lista con edicion inline y eliminacion por motivo
- **Hilo de Conversacion por Registro** (2026-03-27):
  - Nueva tabla prod_conversacion (id, registro_id, mensaje_padre_id, autor, mensaje, estado, fijado, created_at)
  - Endpoints: GET/POST /api/registros/{id}/conversacion, PATCH/DELETE /api/conversacion/{id}
  - Estados visuales: normal, importante (rojo), pendiente (amarillo), resuelto (verde)
  - Mensajes fijados aparecen arriba con icono de pin
  - Menu de acciones: responder, cambiar estado, fijar/desfijar, eliminar
  - UI: Boton flotante fijo arriba-derecha con contadores (total, importantes, pendientes, fijados). Panel lateral derecho slide-in con boton X para cerrar. Overlay en movil.
- **Avance Porcentaje en Servicios y Movimientos** (2026-03-27):
  - Nueva columna `usa_avance_porcentaje` en prod_servicios_produccion (configurable por servicio)
  - Nueva columna `avance_porcentaje` en prod_movimientos_produccion
  - UI: Checkbox en catalogo de servicios, campo condicional en dialog de movimiento, barra visual en tabla de movimientos
- **Bloqueo por Paralizacion** (2026-03-28):
  - Backend: validar-cambio-estado, crear y editar movimiento verifican si hay paralizacion activa y rechazan con error claro
  - Frontend: Banner rojo "Registro PARALIZADO" arriba del form, botones de movimiento y select de estado deshabilitados
  - Auto-desbloqueo: al resolver la incidencia paralizante, la paralizacion se levanta y el registro vuelve a su estado normal
- **Auto-post Incidencias a Conversacion + Timezone Lima** (2026-03-28):
  - Al crear incidencia: auto-publica mensaje en conversacion (pendiente si normal, importante+fijado si paraliza)
  - Al resolver incidencia: auto-publica mensaje "INCIDENCIA RESUELTA" con estado resuelto
  - Corregido timezone de UTC a America/Lima (UTC-5) en incidencias y conversacion
- **Feedback Visual Incidencias Resueltas** (2026-03-28):
  - Badge "RESUELTA" + fecha de resolucion con icono verde en la seccion de incidencias
  - Incidencias con paralizacion muestran badge "Reanudada" cuando fueron resueltas
- **Reorganizacion REAL Layout RegistroForm** (2026-03-29):
  - Header operativo: Estado/Ruta extraidos del formulario a barra superior dominante con select, ruta visual con pills, badge PARALIZADO y boton Guardar
  - Layout 2 columnas [1fr_320px]: izquierda (bloques: Datos, Tallas, Materiales, Movimientos, Incidencias, Trazabilidad) + derecha sticky
  - Panel derecho enriquecido: contadores movimientos/incidencias, modelo compacto, conversacion integrada con stats
  - Conversacion: boton flotante eliminado en desktop, integrado en panel derecho; drawer se mantiene
  - ConversacionStats: mini-componente con resumen del hilo
  - Banners (paralizado, inconsistencias) integrados en header operativo
- **Ajustes finales Layout RegistroForm** (2026-03-29):
  - Balance del Lote movido arriba de Incidencias (prioridad operativa)
  - Incidencias: solo abiertas visibles; resueltas colapsadas en "Historial resueltas (N)" con toggle expandible
  - Modelo en panel derecho ultra-compacto: nombre + atributos en una sola linea separados por punto medio
  - Orden final de bloques: Datos → Tallas → Materiales → Movimientos → Balance/Trazabilidad → Incidencias
- **Reporte Operativo de Costura** (2026-03-29):
  - Nuevo endpoint GET /api/reportes-produccion/costura con query SQL completa (JOINs a registros, modelos, personas, servicios, incidencias)
  - Endpoint PUT /api/reportes-produccion/costura/avance/{movimiento_id} para actualizar avance inline
  - Nueva columna avance_updated_at en prod_movimientos_produccion (se auto-actualiza al cambiar avance)
  - Logica de riesgo automatica: Normal/Atencion/Critico/Vencido basada en fechas, avance, dias sin actualizar, incidencias
  - Frontend: ReporteCostura.jsx con KPIs (7 tarjetas), filtros (6 campos), tabla agrupada por persona expandible (16 columnas)
  - Acciones rapidas inline: editar avance %, crear incidencia rapida (dialog), abrir registro
  - Ruta: /reportes/costura, sidebar: Op. Costura
  - Testing: 100% backend (15/15) y 100% frontend
- **Incidencias Expandibles en Reporte Costura** (2026-03-29):
  - Sub-fila expandible debajo de cada registro mostrando incidencias abiertas
  - Boton Resolver abre dialog con detalle y textarea obligatorio (asterisco rojo)
  - Comentario de resolucion se guarda via PUT /api/incidencias/{id}
  - Tras resolver se refresca lista de incidencias y KPIs del reporte
- **Ajustes Reporte Costura** (2026-03-29):
  - Eliminada columna "Pend." (pendiente estimado) — no existe en DB, solo se calculaba
  - Nueva tabla prod_avance_historial (movimiento_id, avance_porcentaje, usuario, created_at) para tracking de cambios
  - Nuevo endpoint GET /api/reportes-produccion/costura/avance-historial/{movimiento_id}
  - Endpoint PUT avance ahora registra automaticamente en historial con usuario
  - UI: Dialog modal "Historial de Avance" accesible desde icono reloj en columna Avance, muestra cronologia con diferencias (+N%) y usuario/fecha
- **Mejoras Reporte Costura** (2026-03-30):
  - Exportar CSV: boton descarga archivo con 16 columnas, formato UTF-8 con BOM para Excel
  - Incidencia con Paraliza: checkbox en dialog, advertencia roja, boton rojo "Crear y Paralizar"
  - Usuario registrador: al crear incidencia se guarda el usuario actual, se muestra en sub-fila expandida
  - Simulacion datos: 6 personas, 7 modelos, 17 registros, 13 incidencias, 3 paralizaciones
  - Testing: 100% backend (7/7) y 100% frontend
- [ ] Logica en modulo Finanzas para cargos internos
- [ ] Reportes P1: Productividad persona/servicio, Incidencias/Glosas, PT generado, Antiguedad, Mermas
- [ ] Reportes y KPIs de Trazabilidad: perdidas por servicio, fallados por responsable, arreglos vencidos

### P2
- [ ] Reportes P2: Reprocesos, Eficiencia vs Estandar, Cumplimiento por modelo, Carga futura
- [ ] Limpiar lineas BOM huerfanas

### P3
- [ ] Permisos granulares con usePermissions
- [ ] Exportacion Excel/PDF
- [ ] Refactorizar RegistroForm.jsx (~3370 lineas)
- [ ] Migrar server.py a routers modulares (~7400 lineas)

## Key Credentials
- Usuario: eduard / eduard123

## Code Architecture
```
/app
├── backend/
│   ├── db.py (Pool de conexiones con reintentos automáticos)
│   ├── routes/
│   │   ├── control_produccion.py (CRUD incidencias y motivos)
│   │   ├── reportes_produccion.py
│   │   ├── trazabilidad.py (Fallados, Arreglos, Resumen, Timeline)
│   │   └── inventario.py
│   ├── tests/
│   │   ├── test_trazabilidad.py
│   │   ├── test_guias_remision.py
│   │   ├── test_matriz_colores.py
│   │   ├── test_pagination_force_state.py
│   │   ├── test_movimientos_produccion.py
│   │   └── test_comprehensive_general.py
│   └── server.py (~7400 lines - needs modularization)
└── frontend/
    └── src/
        ├── components/
        │   ├── TrazabilidadPanel.jsx
        │   └── MaterialesTab.jsx (filtro por linea de negocio)
        └── pages/
            ├── MatrizProduccion.jsx
            ├── Modelos.jsx (paginacion server-side, columna linea)
            ├── Registros.jsx (paginacion server-side, 15 columnas)
            ├── MovimientosProduccion.jsx (paginacion server-side)
            ├── Inventario.jsx (filtro por linea de negocio)
            ├── InventarioIngresos.jsx (selector linea de negocio)
            ├── InventarioSalidas.jsx (corregido paginacion)
            ├── GuiasRemision.jsx (corregido paginacion)
            ├── CalidadMerma.jsx (corregido paginacion)
            └── RegistroForm.jsx (~3100 lines - needs refactoring)
```

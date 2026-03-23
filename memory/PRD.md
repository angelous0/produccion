# PRD - Produccion Textil

## Original Problem Statement
Sistema de gestion de produccion textil con flujo de trabajo completo: desde corte hasta almacen PT. Incluye gestion de inventario FIFO, BOM, movimientos de produccion, cierre de produccion, integracion con modulo de Finanzas, y control operativo por movimiento.

## What's Been Implemented
- Flujo de produccion completo con linea de tiempo de estado
- Panel de cierre integrado en RegistroForm
- Automatizacion Modelo -> PT (autocompletado)
- Selector de proveedores desde finanzas2.cont_tercero en Ingresos
- Badge de estado de facturacion en lista de Ingresos
- Proteccion anti doble-click con hook useSaving() en 21+ paginas
- Fix tarifa_aplicada persistencia en movimientos
- Sidebar fijo al navegar
- **Control Operativo Completo:**
  - fecha_entrega_final en cabecera del registro
  - fecha_esperada_movimiento por cada movimiento
  - Alertas visuales por movimiento (normal/por vencer/vencido)
  - Estado operativo automatico (NORMAL/EN_RIESGO/PARALIZADA)
  - Incidencias y paralizaciones vinculadas a registros o movimientos
- **Personal Interno/Externo (COMPLETADO 2026-03-20):**
  - Backend y Frontend: tipo_persona (INTERNO/EXTERNO) y unidad_interna en personas y movimientos
  - Badges visuales en tabla de movimientos y dropdown de personas en RegistroForm
- **Vinculacion Bidireccional Estado-Movimientos (COMPLETADO 2026-03-23):**
  - EtapaRuta: campos `obligatorio` y `aparece_en_estado` (toggles en UI de Rutas)
  - Endpoint `GET /api/registros/{id}/analisis-estado`: estado_sugerido, inconsistencias, bloqueos
  - Endpoint `POST /api/registros/{id}/validar-cambio-estado`: valida cambios, bloquea estado fuera de ruta, sugiere crear movimiento
  - `GET /api/registros/{id}/estados-disponibles`: filtra por aparece_en_estado, retorna etapas_completas
  - Frontend RutasProduccion: toggles Oblig/Opc y Estado/Solo mov por etapa
  - Frontend RegistroForm: banner de inconsistencias amarillo con detalles y boton "Aplicar estado sugerido"
  - Frontend RegistroForm: al guardar movimiento, sugiere cambiar estado (dialogo)
  - Frontend RegistroForm: al cambiar estado, si falta movimiento, sugiere crearlo (dialogo con formulario pre-llenado)
  - Frontend RegistroForm: bloqueo de estado fuera de ruta y salto de etapa obligatoria

## DB Schema
- prod_registros: +fecha_entrega_final, +estado_operativo
- prod_movimientos_produccion: +tarifa_aplicada, +fecha_esperada_movimiento
- prod_incidencia: id, registro_id, movimiento_id(nullable), tipo, comentario, estado, usuario, fecha_hora
- prod_paralizacion: id, registro_id, movimiento_id(nullable), motivo, comentario, activa, fecha_inicio, fecha_fin
- prod_personas_produccion: tipo_persona (INTERNO/EXTERNO), unidad_interna_id (FK a finanzas2.fin_unidad_interna)
- prod_rutas_produccion.etapas (JSONB): cada etapa tiene nombre, servicio_id, orden, obligatorio, aparece_en_estado

## Key API Endpoints
- `GET /api/registros/{id}/analisis-estado` - Analisis coherencia estado vs movimientos
- `POST /api/registros/{id}/validar-cambio-estado` - Validacion con bloqueos y sugerencias
- `GET /api/registros/{id}/estados-disponibles` - Estados filtrados por ruta + etapas_completas
- `PUT /api/registros/{id}/control` - Fecha entrega final
- `GET/POST /api/incidencias/{registro_id}` - CRUD incidencias
- `GET/POST /api/paralizaciones/{registro_id}` - CRUD paralizaciones
- `PUT /api/paralizaciones/{id}/levantar` - Levantar paralizacion
- `POST/PUT /api/movimientos-produccion` - Con fecha_esperada
- `GET /api/unidades-internas` - Lista unidades internas de finanzas
- `GET /api/personas-produccion` - tipo_persona y unidad_interna_nombre
- `GET /api/movimientos-produccion` - persona_tipo y unidad_interna_nombre

## Prioritized Backlog
### P1
- [ ] Logica en modulo Finanzas para consumir GET /api/ingresos-mp/para-finanzas y generar cargos internos
### P2
- [ ] Limpiar lineas BOM huerfanas
### P3
- [ ] Reporte productividad por persona/servicio
- [ ] Drag-and-drop reordenar tallas
- [ ] Permisos granulares con usePermissions
- [ ] Exportacion Excel/PDF (Kardex, etc.)
- [ ] Refactorizar RegistroForm.jsx (2500+ lineas) en sub-componentes

## Key Credentials
- Usuario: eduard / eduard123

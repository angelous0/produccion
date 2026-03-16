# PRD - Sistema de Produccion Textil

## Problema Original
Sistema ERP de produccion textil con gestion de inventario FIFO, BOM (Bill of Materials), ordenes de produccion, reportes y mas.

## Arquitectura
- **Backend**: FastAPI + AsyncPG + PostgreSQL
- **Frontend**: React + Shadcn UI + Axios
- **DB**: PostgreSQL (schema `produccion`)

## Funcionalidades Implementadas

### Core
- Autenticacion JWT (login/logout)
- Dashboard principal
- Gestion de modelos, marcas, tipos, entalles, tallas, colores
- Inventario FIFO con categorias (Telas, Avios, Servicios)
- Ingresos y salidas de inventario con rollos
- Registros / Ordenes de produccion
- Rutas de produccion con etapas

### BOM (Bill of Materials)
- CRUD cabecera BOM (crear, editar, eliminar, duplicar)
- CRUD lineas BOM (TELA, AVIO, SERVICIO, EMPAQUE, OTRO)
- Selector de items filtrado por tipo de componente
- Selector de etapas desde ruta de produccion vinculada
- Reordenamiento manual de lineas
- Calculo de costo estandar referencial
- **Costo manual editable para lineas SERVICIO** (Feb 2026)
- Explosion BOM para generar requerimiento de MP
- Duplicar BOM a nueva version

### UX/UI
- Componente NumericInput reutilizable (limpia 0 al hacer click)
- ScrollToTop automatico al navegar
- Formulario simplificado para items de tipo Servicio
- Columna "Valorizado" en inventario

### Validacion de Datos
- Constraint UNIQUE en codigo de item (prod_inventario.codigo)

## Schema DB Relevante

### prod_modelo_bom_linea
- id, modelo_id, bom_id, inventario_id (nullable)
- tipo_componente (TELA, AVIO, SERVICIO, EMPAQUE, OTRO)
- talla_id, etapa_id (nullable)
- cantidad_base, merma_pct, cantidad_total
- costo_manual (NUMERIC, nullable) - costo manual para SERVICIO
- es_opcional, activo, orden, observaciones

## API Endpoints Clave
- `GET/POST /api/bom` - Cabeceras BOM
- `GET/PUT/DELETE /api/bom/{bom_id}` - Detalle BOM
- `POST /api/bom/{bom_id}/lineas` - Agregar linea
- `PUT /api/bom/{bom_id}/lineas/{linea_id}` - Actualizar linea (incluye costo_manual)
- `DELETE /api/bom/{bom_id}/lineas/{linea_id}` - Eliminar linea
- `GET /api/bom/{bom_id}/costo-estandar` - Calculo costo (usa costo_manual para SERVICIO)
- `POST /api/bom/{bom_id}/duplicar` - Duplicar BOM (copia costo_manual)
- `POST /api/bom/explosion/{orden_id}` - Explosion BOM

## Backlog Priorizado

### P2
- Limpiar lineas BOM huerfanas del schema antiguo

### P3
- Conectar modulo Produccion con Finanzas
- Reporte de productividad por persona/servicio
- Reordenar tallas con drag-and-drop
- Permisos granulares con usePermissions
- Exportacion Excel/PDF en varias pantallas
- Accesibilidad en Dialogs (DialogTitle/DialogDescription)
- Logica de "borrado inteligente" del BOM (requiere input del usuario)

## Credenciales de Prueba
- Usuario: `eduard` / Contrasena: `eduard123`

## Archivos Clave
- `/app/backend/routes/bom.py`
- `/app/frontend/src/pages/ModelosBOM.jsx`
- `/app/frontend/src/components/ui/numeric-input.jsx`
- `/app/backend/server.py`
- `/app/backend/db.py`

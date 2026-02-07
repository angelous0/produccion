# Módulo de Producción Textil - PRD

## Problema Original
Crear un módulo de producción textil con las siguientes tablas y relaciones:
- **Marca, Tipo, Entalle, Tela, Hilo**: Tablas maestras simples
- **Tallas (catálogo)**: Tabla maestra de tallas con orden
- **Colores (catálogo)**: Tabla maestra de colores con código hex
- **Modelo**: Con relaciones muchos-a-uno con Marca, Tipo, Entalle, Tela, Hilo
- **Registro**: Con N Corte, Fecha Creación, relación con Modelo, Curva (texto), Estado, Urgente

## Flujo de Tallas y Colores
1. **Paso 1 - En Corte**: Al crear registro, seleccionar tallas del catálogo con cantidades
2. **Paso 2 - En Lavandería**: Distribuir cantidades por colores usando botón de paleta
   - Validación: suma de colores no puede exceder cantidad total de la talla

## Preferencias del Usuario
- Diseño corporativo minimalista claro con dark mode
- Todo en español
- Estados: Para Corte, Corte, Para Costura, Costura, Para Atraque, Atraque, Para Lavandería, Muestra Lavanderia, Lavandería, Para Acabado, Acabado, Almacén PT, Tienda
- Inputs numéricos sin flechitas (spinners)
- Eliminación directa sin confirmación

## Arquitectura

### Backend (FastAPI + PostgreSQL)
- `/api/marcas`, `/api/tipos`, `/api/entalles`, `/api/telas`, `/api/hilos` - CRUDs básicos
- `/api/tallas-catalogo` - CRUD tallas maestras
- `/api/colores-catalogo` - CRUD colores maestros con hex
- `/api/modelos` - CRUD modelos con relaciones
- `/api/registros` - CRUD registros con tallas y distribución colores
- `/api/estados` - Lista de estados
- `/api/stats` - Estadísticas dashboard
- `/api/inventario` - CRUD items de inventario
- `/api/inventario-ingresos` - Entradas de inventario
- `/api/inventario-salidas` - Salidas de inventario con método FIFO
- `/api/inventario-ajustes` - Ajustes de inventario
- `/api/servicios-produccion` - CRUD servicios de producción
- `/api/personas-produccion` - CRUD personas de producción
- `/api/movimientos-produccion` - CRUD movimientos de producción
- `/api/registros/{id}/generar-requerimiento` - Genera requerimiento de MP
- `/api/registros/{id}/requerimiento` - Obtiene requerimiento
- `/api/registros/{id}/reservas` - Gestión de reservas
- `/api/registros/{id}/cerrar` - Cerrar OP
- `/api/registros/{id}/anular` - Anular OP
- `/api/registros/{id}/resumen` - Resumen completo de OP

### Frontend (React + Shadcn/UI)
- Dashboard con contadores
- CRUDs para todas las entidades
- Registros con flujo de 2 pasos
- Dark/Light mode toggle
- Módulo de Inventario FIFO con navegación separada
- Sección "Maestros" con Servicios y Personas
- Movimientos de Producción integrados en formulario de Registro

## Implementado

### Enero 2025 - MVP
- Backend completo con todos los endpoints
- Frontend con todas las páginas y CRUDs
- Catálogo de Tallas y Colores
- Flujo de 2 pasos para tallas/colores
- Validación de cantidades en distribución
- Dark mode toggle
- Inputs sin spinners
- Eliminación directa

### Enero 2025 - Fase 1 (Inventario FIFO)
- Módulo completo de inventario con control FIFO
- Ingresos y salidas con trazabilidad
- Kardex por item
- Ajustes de inventario
- Items con control por rollos (telas)
- Gestión de rollos (metraje, tono, activo)

### Enero 2025 - Fase 2 (MRP y Reservas)
- Generación de requerimiento de MP desde BOM del modelo
- Sistema de reservas de inventario (ATP)
- Salidas de MP con validación contra reservas
- Visualización de stock disponible vs reservado
- Detalle de reservas por item

### Febrero 2025 - Fase 2C (Cierre/Anulación de OP)
- Endpoints cerrar/anular OP con liberación automática de reservas
- Bloqueos automáticos en OP cerrada/anulada
- UI con botones Cerrar/Anular OP en detalle de registro
- Modal de confirmación con resumen
- Resumen endpoint GET /api/registros/{id}/resumen

### Febrero 2025 - UX Mejoras
- Buscador de ítems en ajustes de inventario
- Lógica condicional de rollos (opcional para entradas, obligatorio para salidas)
- Salidas de material en lote (tabla editable)
- Modal de selección de rollo para ítems con control_por_rollos

### Febrero 7, 2025 - Selección Múltiple de Rollos (P0 COMPLETADO)
- Modal de selección múltiple de rollos con checkboxes
- Botón "Sel. Todos" con distribución inteligente del metraje pendiente
- Cantidades editables por rollo individual
- Buscador por número de rollo o tono
- Resumen de selección (rollos seleccionados, total metraje)
- Confirmación actualiza la tabla principal con conteo de rollos y total
- Registro en lote: una salida por cada rollo seleccionado

## Backlog

### P1 - Importante
- [ ] Clarificar lógica de "borrado inteligente" del BOM (vinculación con producción)
- [ ] Vista de detalle (drill-down) en "Reporte Item-Estados"
- [ ] Filtros y ordenamiento avanzados en "Reporte Item-Estados"

### P2 - Mejoras
- [ ] Finalizar exportación Excel/PDF en página de Kardex
- [ ] Dashboard de Producción con gráficos
- [ ] Reportes de producción con costos de materiales
- [ ] Reportes de Merma por período o persona

### P3 - Futuro
- [ ] Reporte de "Productividad por persona/servicio"
- [ ] Drag-and-drop para reordenar tallas en formularios
- [ ] Aplicar permisos granulares con hook `usePermissions` en toda la UI
- [ ] Auditar accesibilidad en componentes `Dialog` (DialogTitle, DialogDescription) - Issue recurrente x6

### Refactoring Necesario
- [ ] Dividir `server.py` (5700+ líneas) en módulos/routers por funcionalidad
- [ ] Componentizar `RegistroDetalleFase2.jsx` (extraer lógica de pestañas y modales)

## Credenciales de Prueba
- **Usuario**: `eduard`
- **Contraseña**: `eduard123`

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

### Backend (FastAPI + MongoDB)
- `/api/marcas`, `/api/tipos`, `/api/entalles`, `/api/telas`, `/api/hilos` - CRUDs básicos
- `/api/tallas-catalogo` - CRUD tallas maestras
- `/api/colores-catalogo` - CRUD colores maestros con hex
- `/api/modelos` - CRUD modelos con relaciones
- `/api/registros` - CRUD registros con tallas y distribución colores
- `/api/estados` - Lista de estados
- `/api/stats` - Estadísticas dashboard
- **NUEVO** `/api/inventario` - CRUD items de inventario
- **NUEVO** `/api/inventario-ingresos` - Entradas de inventario
- **NUEVO** `/api/inventario-salidas` - Salidas de inventario con método FIFO
- **NUEVO** `/api/inventario-ajustes` - Ajustes de inventario

### Frontend (React + Shadcn/UI)
- Dashboard con contadores
- CRUDs para todas las entidades
- Registros con flujo de 2 pasos
- Dark/Light mode toggle
- **NUEVO** Módulo de Inventario FIFO con navegación separada

## Implementado

### Enero 2025 - MVP
- ✅ Backend completo con todos los endpoints
- ✅ Frontend con todas las páginas y CRUDs
- ✅ Catálogo de Tallas y Colores
- ✅ Flujo de 2 pasos para tallas/colores
- ✅ Validación de cantidades en distribución
- ✅ Dark mode toggle
- ✅ Inputs sin spinners
- ✅ Eliminación directa
- ✅ Accesibilidad mejorada en Dialogs (DialogDescription)

### Enero 2025 - Módulo Inventario FIFO
- ✅ CRUD de Items de Inventario (código, nombre, descripción, unidad_medida, stock_minimo)
- ✅ Ingresos de inventario (entradas con costo unitario, proveedor, documento)
- ✅ Salidas de inventario con método FIFO (calcula costo automáticamente de lotes más antiguos)
- ✅ Vinculación de salidas con registros de producción (un registro puede tener muchas salidas)
- ✅ Ajustes de inventario (entrada/salida con motivo)
- ✅ Control de stock mínimo con alertas visuales
- ✅ Estadísticas de inventario en API /stats
- ✅ Navegación sidebar separada para módulo "Inventario FIFO"
- ✅ Testing completo (22/22 tests pasados)

## Backlog

### P0 - En Progreso
- [ ] Implementar dropdowns en cascada para creación de Modelos (seleccionar Marca → filtra Tipos → filtra Entalles, etc.)
  - Backend ya tiene relaciones many-to-many (marca_ids, tipo_ids, etc.)
  - Falta: actualizar frontend de Telas.jsx, Hilos.jsx con multi-selects
  - Falta: implementar lógica de filtrado en Modelos.jsx

### P1 - Importante
- [ ] Autenticación de usuarios
- [ ] Filtros y búsqueda en tablas
- [ ] Exportar registros a Excel
- [ ] Reporte de movimientos de inventario

### P2 - Mejoras
- [ ] Reportes de producción
- [ ] Gráficos de estados
- [ ] Historial de cambios de estado
- [ ] Kardex de inventario (reporte detallado FIFO)

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

### Frontend (React + Shadcn/UI)
- Dashboard con contadores
- CRUDs para todas las entidades
- Registros con flujo de 2 pasos
- Dark/Light mode toggle

## Implementado (Enero 2025)
- ✅ Backend completo con todos los endpoints
- ✅ Frontend con todas las páginas y CRUDs
- ✅ Catálogo de Tallas y Colores
- ✅ Flujo de 2 pasos para tallas/colores
- ✅ Validación de cantidades en distribución
- ✅ Dark mode toggle
- ✅ Inputs sin spinners
- ✅ Eliminación directa

## Backlog

### P1 - Importante
- Autenticación de usuarios
- Filtros y búsqueda en tablas
- Exportar registros a Excel

### P2 - Mejoras
- Reportes de producción
- Gráficos de estados
- Historial de cambios de estado

# Módulo de Producción Textil - PRD

## Problema Original
Crear un módulo de producción textil con las siguientes tablas y relaciones:
- **Marca, Tipo, Entalle, Tela, Hilo**: Tablas maestras simples
- **Modelo**: Con relaciones muchos-a-uno con todas las tablas anteriores
- **Registro**: Con N Corte, Fecha Creación, relación con Modelo, Curva, Estado, Urgente
- **Tallas/Colores**: Matriz estilo Excel donde tallas son columnas y colores filas

## Preferencias del Usuario
- Diseño corporativo minimalista claro con dark mode
- Todo en español
- Estados: Para Corte, Corte, Para Costura, Costura, Para Atraque, Atraque, Para Lavandería, Muestra Lavanderia, Lavandería, Para Acabado, Acabado, Almacén PT, Tienda
- Curva como texto
- Sin autenticación por ahora

## Arquitectura

### Backend (FastAPI + MongoDB)
- `/api/marcas` - CRUD marcas
- `/api/tipos` - CRUD tipos
- `/api/entalles` - CRUD entalles
- `/api/telas` - CRUD telas
- `/api/hilos` - CRUD hilos
- `/api/modelos` - CRUD modelos con relaciones
- `/api/registros` - CRUD registros con matriz tallas/colores
- `/api/estados` - Lista de estados de producción
- `/api/stats` - Estadísticas del dashboard

### Frontend (React + Shadcn/UI)
- Dashboard con contadores y estados
- CRUDs para todas las entidades
- Matriz de producción estilo Excel
- Dark/Light mode toggle

## Implementado (Diciembre 2025)
- ✅ Backend completo con todos los endpoints
- ✅ Frontend con todas las páginas y CRUDs
- ✅ Matriz de tallas/colores con totales
- ✅ Dark mode toggle
- ✅ Navegación lateral
- ✅ Todo en español

## Backlog (P0/P1/P2)

### P0 - Crítico
- (Completado)

### P1 - Importante
- Autenticación de usuarios
- Filtros y búsqueda en tablas
- Exportar registros a Excel

### P2 - Mejoras
- Reportes de producción
- Gráficos de estados
- Historial de cambios de estado
- Notificaciones de urgentes

## Próximos Pasos
1. Agregar autenticación de usuarios
2. Implementar filtros en las tablas
3. Exportación a Excel

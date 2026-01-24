import { useAuth } from '../context/AuthContext';

/**
 * Hook para verificar permisos del usuario actual
 * 
 * Uso:
 * const { canView, canCreate, canEdit, canDelete, isReadOnly } = usePermissions('registros');
 */
export const usePermissions = (tabla) => {
  const { user, isAdmin } = useAuth();

  // Admin tiene todos los permisos
  if (isAdmin()) {
    return {
      canView: true,
      canCreate: true,
      canEdit: true,
      canDelete: true,
      isReadOnly: false,
      isAdmin: true,
    };
  }

  // Usuario de solo lectura
  if (user?.rol === 'lectura') {
    return {
      canView: true,
      canCreate: false,
      canEdit: false,
      canDelete: false,
      isReadOnly: true,
      isAdmin: false,
    };
  }

  // Usuario normal - verificar permisos específicos
  const permisos = user?.permisos || {};
  const permisosTabla = permisos[tabla] || {};

  return {
    canView: permisosTabla.ver !== false, // Por defecto puede ver
    canCreate: permisosTabla.crear === true,
    canEdit: permisosTabla.editar === true,
    canDelete: permisosTabla.eliminar === true,
    isReadOnly: !permisosTabla.crear && !permisosTabla.editar && !permisosTabla.eliminar,
    isAdmin: false,
  };
};

/**
 * Mapeo de rutas a tablas de permisos
 */
export const RUTA_A_TABLA = {
  '/': 'dashboard',
  '/marcas': 'marcas',
  '/tipos': 'tipos',
  '/entalles': 'entalles',
  '/telas': 'telas',
  '/hilos': 'hilos',
  '/hilos-especificos': 'hilos_especificos',
  '/tallas-catalogo': 'tallas',
  '/colores-catalogo': 'colores',
  '/colores-generales': 'colores_generales',
  '/modelos': 'modelos',
  '/registros': 'registros',
  '/inventario': 'inventario',
  '/inventario/ingresos': 'inventario',
  '/inventario/salidas': 'inventario',
  '/inventario/ajustes': 'inventario',
  '/inventario/rollos': 'inventario',
  '/inventario/movimientos': 'reporte_movimientos',
  '/inventario/kardex': 'kardex',
  '/maestros/servicios': 'servicios',
  '/maestros/personas': 'personas',
  '/maestros/rutas': 'rutas',
  '/maestros/movimientos': 'movimientos_produccion',
  '/maestros/productividad': 'reporte_productividad',
  '/calidad/merma': 'mermas',
  '/guias': 'guias',
};

export default usePermissions;

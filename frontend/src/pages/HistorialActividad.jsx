import { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Label } from '../components/ui/label';
import { 
  History, 
  LogIn, 
  Plus, 
  Pencil, 
  Trash2, 
  Key, 
  Shield, 
  Search,
  Eye,
  ChevronLeft,
  ChevronRight,
  Filter,
  X,
  Calendar
} from 'lucide-react';
import { toast } from 'sonner';
import { formatDate } from '../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TIPO_ACCION_CONFIG = {
  login: { label: 'Inicio de Sesión', icon: LogIn, color: 'bg-green-500' },
  crear: { label: 'Crear', icon: Plus, color: 'bg-blue-500' },
  editar: { label: 'Editar', icon: Pencil, color: 'bg-yellow-500' },
  eliminar: { label: 'Eliminar', icon: Trash2, color: 'bg-red-500' },
  cambio_password: { label: 'Cambio Contraseña', icon: Key, color: 'bg-purple-500' },
  cambio_password_admin: { label: 'Cambio Contraseña (Admin)', icon: Shield, color: 'bg-orange-500' },
};

const TABLA_LABELS = {
  usuarios: 'Usuarios',
  registros: 'Registros',
  marcas: 'Marcas',
  tipos: 'Tipos',
  entalles: 'Entalles',
  telas: 'Telas',
  hilos: 'Hilos',
  modelos: 'Modelos',
  inventario: 'Inventario',
};

export const HistorialActividad = () => {
  const { isAdmin } = useAuth();
  const [actividades, setActividades] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [tablasDisponibles, setTablasDisponibles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(20);
  const [detailDialog, setDetailDialog] = useState({ open: false, actividad: null });
  
  // Filtros
  const [filtros, setFiltros] = useState({
    usuario_id: '',
    tipo_accion: '',
    tabla_afectada: '',
    fecha_desde: '',
    fecha_hasta: '',
  });
  const [filtrosAplicados, setFiltrosAplicados] = useState({});

  const fetchActividades = async (currentFiltros = filtrosAplicados, currentPage = page) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (currentFiltros.usuario_id) params.append('usuario_id', currentFiltros.usuario_id);
      if (currentFiltros.tipo_accion) params.append('tipo_accion', currentFiltros.tipo_accion);
      if (currentFiltros.tabla_afectada) params.append('tabla_afectada', currentFiltros.tabla_afectada);
      if (currentFiltros.fecha_desde) params.append('fecha_desde', currentFiltros.fecha_desde);
      if (currentFiltros.fecha_hasta) params.append('fecha_hasta', currentFiltros.fecha_hasta);
      params.append('limit', limit);
      params.append('offset', currentPage * limit);
      
      const response = await axios.get(`${API}/actividad?${params.toString()}`);
      setActividades(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      toast.error('Error al cargar historial');
    } finally {
      setLoading(false);
    }
  };

  const fetchUsuarios = async () => {
    try {
      const response = await axios.get(`${API}/usuarios`);
      setUsuarios(response.data);
    } catch (error) {
      console.error('Error fetching usuarios:', error);
    }
  };

  const fetchTablas = async () => {
    try {
      const response = await axios.get(`${API}/actividad/tablas`);
      setTablasDisponibles(response.data);
    } catch (error) {
      console.error('Error fetching tablas:', error);
    }
  };

  useEffect(() => {
    fetchActividades();
    fetchUsuarios();
    fetchTablas();
  }, []);

  const handleAplicarFiltros = () => {
    setPage(0);
    setFiltrosAplicados(filtros);
    fetchActividades(filtros, 0);
  };

  const handleLimpiarFiltros = () => {
    const filtrosVacios = {
      usuario_id: '',
      tipo_accion: '',
      tabla_afectada: '',
      fecha_desde: '',
      fecha_hasta: '',
    };
    setFiltros(filtrosVacios);
    setFiltrosAplicados(filtrosVacios);
    setPage(0);
    fetchActividades(filtrosVacios, 0);
  };

  const handlePageChange = (newPage) => {
    setPage(newPage);
    fetchActividades(filtrosAplicados, newPage);
  };

  const getTipoAccionBadge = (tipo) => {
    const config = TIPO_ACCION_CONFIG[tipo] || { label: tipo, color: 'bg-gray-500' };
    const Icon = config.icon || History;
    return (
      <Badge className={`${config.color} text-white flex items-center gap-1`}>
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const formatValue = (value) => {
    if (value === null || value === undefined || value === '') return <span className="text-muted-foreground italic">vacío</span>;
    if (typeof value === 'boolean') return value ? 'Sí' : 'No';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  const CAMPO_LABELS = {
    username: 'Usuario',
    email: 'Correo',
    nombre_completo: 'Nombre Completo',
    rol: 'Rol',
    activo: 'Activo',
    permisos: 'Permisos',
    nombre: 'Nombre',
    descripcion: 'Descripción',
    codigo: 'Código',
    color: 'Color',
    precio: 'Precio',
    cantidad: 'Cantidad',
  };

  const renderCambiosCrear = (datosNuevos) => {
    if (!datosNuevos || Object.keys(datosNuevos).length === 0) {
      return <p className="text-muted-foreground text-center py-4">Sin datos registrados</p>;
    }
    
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-green-600 font-medium">
          <Plus className="h-5 w-5" />
          <span>Datos creados:</span>
        </div>
        <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-4 space-y-2">
          {Object.entries(datosNuevos).map(([campo, valor]) => (
            <div key={campo} className="flex items-start gap-2">
              <span className="text-green-600 mt-1">•</span>
              <div>
                <span className="font-medium text-foreground">{CAMPO_LABELS[campo] || campo.replace(/_/g, ' ')}:</span>
                <span className="ml-2 text-green-700 dark:text-green-400">{formatValue(valor)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderCambiosEditar = (datosAnteriores, datosNuevos) => {
    if (!datosAnteriores && !datosNuevos) {
      return <p className="text-muted-foreground text-center py-4">Sin cambios registrados</p>;
    }
    
    const campos = new Set([
      ...Object.keys(datosAnteriores || {}),
      ...Object.keys(datosNuevos || {})
    ]);
    
    const cambiosReales = Array.from(campos).filter(campo => {
      const anterior = datosAnteriores?.[campo];
      const nuevo = datosNuevos?.[campo];
      return JSON.stringify(anterior) !== JSON.stringify(nuevo);
    });

    if (cambiosReales.length === 0) {
      return <p className="text-muted-foreground text-center py-4">Sin cambios detectados</p>;
    }
    
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-yellow-600 font-medium">
          <Pencil className="h-5 w-5" />
          <span>Cambios realizados:</span>
        </div>
        <div className="space-y-3">
          {cambiosReales.map((campo) => {
            const valorAnterior = datosAnteriores?.[campo];
            const valorNuevo = datosNuevos?.[campo];
            
            return (
              <div key={campo} className="bg-muted/50 rounded-lg p-3">
                <div className="font-medium text-sm text-muted-foreground mb-2">
                  {CAMPO_LABELS[campo] || campo.replace(/_/g, ' ')}
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-red-50 dark:bg-red-950/30 rounded p-2 text-center">
                    <div className="text-xs text-red-600 mb-1">Antes</div>
                    <div className="text-red-700 dark:text-red-400 line-through">
                      {formatValue(valorAnterior)}
                    </div>
                  </div>
                  <div className="text-muted-foreground">→</div>
                  <div className="flex-1 bg-green-50 dark:bg-green-950/30 rounded p-2 text-center">
                    <div className="text-xs text-green-600 mb-1">Después</div>
                    <div className="text-green-700 dark:text-green-400 font-medium">
                      {formatValue(valorNuevo)}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderCambiosEliminar = (datosAnteriores) => {
    if (!datosAnteriores || Object.keys(datosAnteriores).length === 0) {
      return <p className="text-muted-foreground text-center py-4">Sin datos registrados</p>;
    }
    
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-red-600 font-medium">
          <Trash2 className="h-5 w-5" />
          <span>Datos eliminados:</span>
        </div>
        <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-4 space-y-2">
          {Object.entries(datosAnteriores).map(([campo, valor]) => (
            <div key={campo} className="flex items-start gap-2">
              <span className="text-red-600 mt-1">✕</span>
              <div>
                <span className="font-medium text-foreground">{CAMPO_LABELS[campo] || campo.replace(/_/g, ' ')}:</span>
                <span className="ml-2 text-red-700 dark:text-red-400 line-through">{formatValue(valor)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderCambios = (tipoAccion, datosAnteriores, datosNuevos) => {
    switch (tipoAccion) {
      case 'crear':
        return renderCambiosCrear(datosNuevos);
      case 'editar':
        return renderCambiosEditar(datosAnteriores, datosNuevos);
      case 'eliminar':
        return renderCambiosEliminar(datosAnteriores);
      case 'cambio_password':
      case 'cambio_password_admin':
        return (
          <div className="flex items-center gap-2 text-purple-600 bg-purple-50 dark:bg-purple-950/30 rounded-lg p-4">
            <Key className="h-5 w-5" />
            <span>La contraseña fue modificada</span>
          </div>
        );
      case 'login':
        return (
          <div className="flex items-center gap-2 text-green-600 bg-green-50 dark:bg-green-950/30 rounded-lg p-4">
            <LogIn className="h-5 w-5" />
            <span>Inicio de sesión exitoso</span>
          </div>
        );
      default:
        if (!datosAnteriores && !datosNuevos) {
          return <p className="text-muted-foreground text-center py-4">Sin detalles adicionales</p>;
        }
        return renderCambiosEditar(datosAnteriores, datosNuevos);
    }
  };

  const totalPages = Math.ceil(total / limit);

  if (!isAdmin()) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-muted-foreground">No tienes permisos para ver esta página</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="historial-actividad-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <History className="h-6 w-6" />
            Historial de Actividad
          </h2>
          <p className="text-muted-foreground">
            Registro de todas las acciones realizadas en el sistema
          </p>
        </div>
      </div>

      {/* Filtros */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="space-y-2">
              <Label>Usuario</Label>
              <Select 
                value={filtros.usuario_id || "all"} 
                onValueChange={(value) => setFiltros({ ...filtros, usuario_id: value === "all" ? "" : value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {usuarios.map((u) => (
                    <SelectItem key={u.id} value={u.id}>{u.username}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Tipo de Acción</Label>
              <Select 
                value={filtros.tipo_accion || "all"} 
                onValueChange={(value) => setFiltros({ ...filtros, tipo_accion: value === "all" ? "" : value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {Object.entries(TIPO_ACCION_CONFIG).map(([key, config]) => (
                    <SelectItem key={key} value={key}>{config.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Tabla</Label>
              <Select 
                value={filtros.tabla_afectada || "all"} 
                onValueChange={(value) => setFiltros({ ...filtros, tabla_afectada: value === "all" ? "" : value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  {tablasDisponibles.map((t) => (
                    <SelectItem key={t} value={t}>{TABLA_LABELS[t] || t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Desde</Label>
              <Input
                type="date"
                value={filtros.fecha_desde}
                onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Hasta</Label>
              <Input
                type="date"
                value={filtros.fecha_hasta}
                onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })}
              />
            </div>
            
            <div className="space-y-2 flex items-end gap-2">
              <Button onClick={handleAplicarFiltros} className="flex-1">
                <Search className="h-4 w-4 mr-2" />
                Buscar
              </Button>
              <Button variant="outline" onClick={handleLimpiarFiltros}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabla de actividades */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[180px]">Fecha</TableHead>
                <TableHead>Usuario</TableHead>
                <TableHead>Acción</TableHead>
                <TableHead>Tabla</TableHead>
                <TableHead>Registro</TableHead>
                <TableHead>Descripción</TableHead>
                <TableHead className="w-[80px]">Detalle</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">Cargando...</TableCell>
                </TableRow>
              ) : actividades.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No hay actividades registradas
                  </TableCell>
                </TableRow>
              ) : (
                actividades.map((act) => (
                  <TableRow key={act.id}>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(act.created_at, true)}
                    </TableCell>
                    <TableCell className="font-medium">{act.usuario_nombre}</TableCell>
                    <TableCell>{getTipoAccionBadge(act.tipo_accion)}</TableCell>
                    <TableCell>
                      {act.tabla_afectada ? (
                        <Badge variant="outline">
                          {TABLA_LABELS[act.tabla_afectada] || act.tabla_afectada}
                        </Badge>
                      ) : '-'}
                    </TableCell>
                    <TableCell className="text-sm">{act.registro_nombre || '-'}</TableCell>
                    <TableCell className="text-sm max-w-[300px] truncate" title={act.descripcion}>
                      {act.descripcion}
                    </TableCell>
                    <TableCell>
                      {(act.datos_anteriores || act.datos_nuevos) && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDetailDialog({ open: true, actividad: act })}
                          title="Ver detalles"
                        >
                          <Eye className="h-4 w-4 text-blue-500" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
        
        {/* Paginación */}
        {total > limit && (
          <div className="flex items-center justify-between px-4 py-3 border-t">
            <span className="text-sm text-muted-foreground">
              Mostrando {page * limit + 1} - {Math.min((page + 1) * limit, total)} de {total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 0}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="flex items-center px-3 text-sm">
                Página {page + 1} de {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages - 1}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Dialog de detalle */}
      <Dialog open={detailDialog.open} onOpenChange={(open) => setDetailDialog({ open, actividad: null })}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5 text-blue-500" />
              Detalle de Cambios
            </DialogTitle>
            <DialogDescription>
              {detailDialog.actividad?.descripcion}
            </DialogDescription>
          </DialogHeader>
          
          {detailDialog.actividad && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Usuario:</span>
                  <span className="ml-2 font-medium">{detailDialog.actividad.usuario_nombre}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Fecha:</span>
                  <span className="ml-2">{formatDate(detailDialog.actividad.created_at, true)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Acción:</span>
                  <span className="ml-2">{getTipoAccionBadge(detailDialog.actividad.tipo_accion)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Tabla:</span>
                  <span className="ml-2">{TABLA_LABELS[detailDialog.actividad.tabla_afectada] || detailDialog.actividad.tabla_afectada || '-'}</span>
                </div>
              </div>
              
              <div className="border-t pt-4">
                <h4 className="font-medium mb-2">Cambios realizados:</h4>
                {renderCambios(
                  detailDialog.actividad.datos_anteriores,
                  detailDialog.actividad.datos_nuevos
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

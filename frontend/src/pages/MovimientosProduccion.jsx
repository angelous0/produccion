import { useEffect, useState } from 'react';
import axios from 'axios';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Play, Pencil, Trash2, Calendar, Users, Cog, Filter, X, Plus, DollarSign } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const MovimientosProduccion = () => {
  const [movimientos, setMovimientos] = useState([]);
  const [servicios, setServicios] = useState([]);
  const [personas, setPersonas] = useState([]);
  const [registros, setRegistros] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filtros
  const [filtroServicio, setFiltroServicio] = useState('');
  const [filtroPersona, setFiltroPersona] = useState('');
  const [filtroRegistro, setFiltroRegistro] = useState('');
  const [filtroFechaDesde, setFiltroFechaDesde] = useState('');
  const [filtroFechaHasta, setFiltroFechaHasta] = useState('');

  // Dialog para crear nuevo
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [personasFiltradasCreate, setPersonasFiltradasCreate] = useState([]);
  const [createFormData, setCreateFormData] = useState({
    registro_id: '',
    servicio_id: '',
    persona_id: '',
    fecha_inicio: '',
    fecha_fin: '',
    cantidad: 0,
    tarifa_aplicada: 0,
    observaciones: '',
  });

  // Dialog de edición
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingMovimiento, setEditingMovimiento] = useState(null);
  const [personasFiltradas, setPersonasFiltradas] = useState([]);
  const [formData, setFormData] = useState({
    registro_id: '',
    servicio_id: '',
    persona_id: '',
    fecha_inicio: '',
    fecha_fin: '',
    cantidad: 0,
    tarifa_aplicada: 0,
    observaciones: '',
  });

  const fetchData = async () => {
    try {
      const [movRes, servRes, persRes, regRes] = await Promise.all([
        axios.get(`${API}/movimientos-produccion`),
        axios.get(`${API}/servicios-produccion`),
        axios.get(`${API}/personas-produccion`),
        axios.get(`${API}/registros`),
      ]);
      setMovimientos(movRes.data);
      setServicios(servRes.data);
      setPersonas(persRes.data);
      setRegistros(regRes.data);
    } catch (error) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const getRegistroLabel = (registroId) => {
    const registro = registros.find(r => r.id === registroId);
    if (!registro) return '-';
    const modelo = registro.modelo_nombre || 'Sin modelo';
    return `${modelo} - ${registro.n_corte}`;
  };

  const handleOpenEdit = (movimiento) => {
    setEditingMovimiento(movimiento);
    setFormData({
      registro_id: movimiento.registro_id,
      servicio_id: movimiento.servicio_id,
      persona_id: movimiento.persona_id,
      fecha_inicio: movimiento.fecha_inicio || '',
      fecha_fin: movimiento.fecha_fin || '',
      cantidad: movimiento.cantidad || 0,
      tarifa_aplicada: movimiento.tarifa_aplicada || 0,
      observaciones: movimiento.observaciones || '',
    });
    // Filtrar personas por el servicio del movimiento
    const filtradas = personas.filter(p => 
      p.servicio_ids && p.servicio_ids.includes(movimiento.servicio_id)
    );
    setPersonasFiltradas(filtradas);
    setDialogOpen(true);
  };

  const handleServicioChange = (servicioId) => {
    const tarifaServicio = getServicioTarifa(servicioId);
    setFormData({ 
      ...formData, 
      servicio_id: servicioId,
      persona_id: '',
      tarifa_aplicada: tarifaServicio
    });
    const filtradas = personas.filter(p => 
      p.servicio_ids && p.servicio_ids.includes(servicioId)
    );
    setPersonasFiltradas(filtradas);
  };

  const handleSubmit = async () => {
    if (!formData.servicio_id || !formData.persona_id) {
      toast.error('Selecciona servicio y persona');
      return;
    }

    try {
      await axios.put(`${API}/movimientos-produccion/${editingMovimiento.id}`, formData);
      toast.success('Movimiento actualizado');
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al actualizar');
    }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/movimientos-produccion/${id}`);
      toast.success('Movimiento eliminado');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  // ===== Funciones para Crear Nuevo =====
  const handleOpenCreateDialog = () => {
    setCreateFormData({
      registro_id: '',
      servicio_id: '',
      persona_id: '',
      fecha_inicio: new Date().toISOString().split('T')[0],
      fecha_fin: '',
      cantidad: 0,
      tarifa_aplicada: 0,
      observaciones: '',
    });
    setPersonasFiltradasCreate([]);
    setCreateDialogOpen(true);
  };

  const handleCreateServicioChange = (servicioId) => {
    const tarifaServicio = getServicioTarifa(servicioId);
    setCreateFormData({ 
      ...createFormData, 
      servicio_id: servicioId,
      persona_id: '',
      tarifa_aplicada: tarifaServicio
    });
    const filtradas = personas.filter(p => 
      p.servicio_ids && p.servicio_ids.includes(servicioId)
    );
    setPersonasFiltradasCreate(filtradas);
  };

  // Helper para obtener tarifa del servicio
  const getServicioTarifa = (servicioId) => {
    const servicio = servicios.find(s => s.id === servicioId);
    return servicio?.tarifa || 0;
  };

  // Helper para calcular costo del formulario de crear (usa tarifa_aplicada)
  const calcularCostoCreate = () => {
    return (createFormData.tarifa_aplicada || 0) * (createFormData.cantidad || 0);
  };

  // Helper para calcular costo del formulario de editar (usa tarifa_aplicada)
  const calcularCostoEdit = () => {
    return (formData.tarifa_aplicada || 0) * (formData.cantidad || 0);
  };

  const handleCreateSubmit = async () => {
    if (!createFormData.registro_id || !createFormData.servicio_id || !createFormData.persona_id) {
      toast.error('Selecciona registro, servicio y persona');
      return;
    }

    try {
      await axios.post(`${API}/movimientos-produccion`, createFormData);
      toast.success('Movimiento creado');
      setCreateDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear');
    }
  };

  const limpiarFiltros = () => {
    setFiltroServicio('');
    setFiltroPersona('');
    setFiltroRegistro('');
    setFiltroFechaDesde('');
    setFiltroFechaHasta('');
  };

  // Aplicar filtros
  const movimientosFiltrados = movimientos.filter(m => {
    if (filtroServicio && m.servicio_id !== filtroServicio) return false;
    if (filtroPersona && m.persona_id !== filtroPersona) return false;
    if (filtroRegistro && m.registro_id !== filtroRegistro) return false;
    if (filtroFechaDesde && m.fecha_inicio && m.fecha_inicio < filtroFechaDesde) return false;
    if (filtroFechaHasta && m.fecha_inicio && m.fecha_inicio > filtroFechaHasta) return false;
    return true;
  });

  const getTotalCantidad = () => {
    return movimientosFiltrados.reduce((sum, m) => sum + (m.cantidad || 0), 0);
  };

  const getTotalCosto = () => {
    return movimientosFiltrados.reduce((sum, m) => sum + (m.costo || 0), 0);
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN',
    }).format(value || 0);
  };

  const hayFiltrosActivos = filtroServicio || filtroPersona || filtroRegistro || filtroFechaDesde || filtroFechaHasta;

  return (
    <div className="space-y-6" data-testid="movimientos-produccion-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Play className="h-6 w-6" />
            Movimientos de Producción
          </h2>
          <p className="text-muted-foreground">
            Historial completo de movimientos de producción
          </p>
        </div>
        <Button onClick={handleOpenCreateDialog} data-testid="btn-nuevo-movimiento-page">
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Movimiento
        </Button>
      </div>

      {/* Filtros */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filtros
            {hayFiltrosActivos && (
              <Button variant="ghost" size="sm" onClick={limpiarFiltros} className="ml-2">
                <X className="h-4 w-4 mr-1" />
                Limpiar
              </Button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="space-y-1">
              <Label className="text-xs">Registro</Label>
              <Select value={filtroRegistro} onValueChange={(val) => setFiltroRegistro(val === 'all' ? '' : val)}>
                <SelectTrigger data-testid="filtro-registro">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {registros.map((r) => (
                    <SelectItem key={r.id} value={r.id}>
                      {r.modelo_nombre || 'Sin modelo'} - {r.n_corte}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Servicio</Label>
              <Select value={filtroServicio} onValueChange={(val) => setFiltroServicio(val === 'all' ? '' : val)}>
                <SelectTrigger data-testid="filtro-servicio">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {servicios.map((s) => (
                    <SelectItem key={s.id} value={s.id}>{s.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Persona</Label>
              <Select value={filtroPersona} onValueChange={(val) => setFiltroPersona(val === 'all' ? '' : val)}>
                <SelectTrigger data-testid="filtro-persona">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {personas.map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Fecha Desde</Label>
              <Input
                type="date"
                value={filtroFechaDesde}
                onChange={(e) => setFiltroFechaDesde(e.target.value)}
                data-testid="filtro-fecha-desde"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Fecha Hasta</Label>
              <Input
                type="date"
                value={filtroFechaHasta}
                onChange={(e) => setFiltroFechaHasta(e.target.value)}
                data-testid="filtro-fecha-hasta"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabla */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="text-lg">
            {movimientosFiltrados.length} movimientos
            {hayFiltrosActivos && ` (filtrados de ${movimientos.length})`}
          </CardTitle>
          <div className="flex gap-3">
            <Badge variant="secondary" className="text-base px-3 py-1">
              {getTotalCantidad().toLocaleString()} prendas
            </Badge>
            <Badge variant="default" className="text-base px-3 py-1">
              <DollarSign className="h-4 w-4 mr-1" />
              {formatCurrency(getTotalCosto())}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Cargando...</div>
          ) : movimientosFiltrados.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No hay movimientos registrados
            </div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead>Registro (Modelo - N° Corte)</TableHead>
                    <TableHead>Servicio</TableHead>
                    <TableHead>Persona</TableHead>
                    <TableHead className="text-center">Fecha Inicio</TableHead>
                    <TableHead className="text-center">Fecha Fin</TableHead>
                    <TableHead className="text-right">Cantidad</TableHead>
                    <TableHead className="text-right">Costo</TableHead>
                    <TableHead className="w-[100px] text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {movimientosFiltrados.map((mov) => (
                    <TableRow key={mov.id} data-testid={`movimiento-row-${mov.id}`}>
                      <TableCell>
                        <span className="font-medium">{getRegistroLabel(mov.registro_id)}</span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Cog className="h-4 w-4 text-blue-500" />
                          <div>
                            <span>{mov.servicio_nombre}</span>
                            {mov.tarifa > 0 && (
                              <div className="text-xs text-muted-foreground">
                                {formatCurrency(mov.tarifa)}/prenda
                              </div>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Users className="h-4 w-4 text-muted-foreground" />
                          <span>{mov.persona_nombre}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        {mov.fecha_inicio ? (
                          <div className="flex items-center justify-center gap-1 text-sm">
                            <Calendar className="h-3 w-3" />
                            {mov.fecha_inicio}
                          </div>
                        ) : '-'}
                      </TableCell>
                      <TableCell className="text-center text-sm">
                        {mov.fecha_fin || '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono font-semibold">
                        {mov.cantidad.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right font-mono text-green-600">
                        {mov.costo > 0 ? formatCurrency(mov.costo) : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleOpenEdit(mov)}
                            data-testid={`edit-movimiento-${mov.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(mov.id)}
                            data-testid={`delete-movimiento-${mov.id}`}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog de Edición */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Editar Movimiento</DialogTitle>
            <DialogDescription>
              Modifica los datos del movimiento de producción
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Servicio *</Label>
              <Select
                value={formData.servicio_id}
                onValueChange={handleServicioChange}
              >
                <SelectTrigger data-testid="edit-select-servicio">
                  <SelectValue placeholder="Seleccionar servicio..." />
                </SelectTrigger>
                <SelectContent>
                  {servicios.map((servicio) => (
                    <SelectItem key={servicio.id} value={servicio.id}>
                      {servicio.nombre}
                      {servicio.tarifa > 0 && ` (${formatCurrency(servicio.tarifa)}/prenda)`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {formData.servicio_id && getServicioTarifa(formData.servicio_id) > 0 && (
                <p className="text-xs text-green-600 font-medium">
                  Tarifa: {formatCurrency(getServicioTarifa(formData.servicio_id))} por prenda
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Persona *</Label>
              <Select
                value={formData.persona_id}
                onValueChange={(value) => setFormData({ ...formData, persona_id: value })}
                disabled={!formData.servicio_id}
              >
                <SelectTrigger data-testid="edit-select-persona">
                  <SelectValue placeholder={formData.servicio_id ? "Seleccionar persona..." : "Selecciona servicio primero"} />
                </SelectTrigger>
                <SelectContent>
                  {personasFiltradas.length === 0 ? (
                    <SelectItem value="none" disabled>
                      No hay personas asignadas a este servicio
                    </SelectItem>
                  ) : (
                    personasFiltradas.map((persona) => (
                      <SelectItem key={persona.id} value={persona.id}>
                        {persona.nombre}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-fecha-inicio">Fecha Inicio</Label>
                <Input
                  id="edit-fecha-inicio"
                  type="date"
                  value={formData.fecha_inicio}
                  onChange={(e) => setFormData({ ...formData, fecha_inicio: e.target.value })}
                  data-testid="edit-input-fecha-inicio"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-fecha-fin">Fecha Fin</Label>
                <Input
                  id="edit-fecha-fin"
                  type="date"
                  value={formData.fecha_fin}
                  onChange={(e) => setFormData({ ...formData, fecha_fin: e.target.value })}
                  data-testid="edit-input-fecha-fin"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-cantidad">Cantidad de Prendas</Label>
              <Input
                id="edit-cantidad"
                type="number"
                min="0"
                value={formData.cantidad}
                onChange={(e) => setFormData({ ...formData, cantidad: parseInt(e.target.value) || 0 })}
                className="font-mono"
                data-testid="edit-input-cantidad"
              />
            </div>

            {/* Tarifa editable */}
            <div className="space-y-2">
              <Label htmlFor="edit-tarifa">Tarifa por Prenda (S/)</Label>
              <Input
                id="edit-tarifa"
                type="number"
                min="0"
                step="0.01"
                value={formData.tarifa_aplicada}
                onChange={(e) => setFormData({ ...formData, tarifa_aplicada: parseFloat(e.target.value) || 0 })}
                className="font-mono"
                placeholder="0.00"
                data-testid="edit-input-tarifa"
              />
              {formData.servicio_id && getServicioTarifa(formData.servicio_id) > 0 && (
                <p className="text-xs text-muted-foreground">
                  Tarifa referencial del servicio: {formatCurrency(getServicioTarifa(formData.servicio_id))}
                </p>
              )}
            </div>

            {/* Mostrar costo calculado en edición */}
            {formData.cantidad > 0 && formData.tarifa_aplicada > 0 && (
              <div className="p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-green-700 dark:text-green-300">Costo calculado:</span>
                  <span className="text-lg font-bold text-green-700 dark:text-green-300">
                    {formatCurrency(calcularCostoEdit())}
                  </span>
                </div>
                <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                  {formData.cantidad} prendas × {formatCurrency(formData.tarifa_aplicada)}
                </p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="edit-observaciones">Observaciones</Label>
              <Textarea
                id="edit-observaciones"
                value={formData.observaciones}
                onChange={(e) => setFormData({ ...formData, observaciones: e.target.value })}
                placeholder="Notas adicionales..."
                rows={2}
                data-testid="edit-input-observaciones"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSubmit}
              disabled={!formData.servicio_id || !formData.persona_id}
              data-testid="btn-actualizar-movimiento"
            >
              Actualizar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog para Crear Nuevo Movimiento */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Nuevo Movimiento de Producción</DialogTitle>
            <DialogDescription>
              Registra un nuevo movimiento de producción
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Registro *</Label>
              <Select
                value={createFormData.registro_id}
                onValueChange={(value) => setCreateFormData({ ...createFormData, registro_id: value })}
              >
                <SelectTrigger data-testid="create-select-registro">
                  <SelectValue placeholder="Seleccionar registro..." />
                </SelectTrigger>
                <SelectContent>
                  {registros.map((r) => (
                    <SelectItem key={r.id} value={r.id}>
                      {r.modelo_nombre || 'Sin modelo'} - {r.n_corte}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Servicio *</Label>
              <Select
                value={createFormData.servicio_id}
                onValueChange={handleCreateServicioChange}
              >
                <SelectTrigger data-testid="create-select-servicio">
                  <SelectValue placeholder="Seleccionar servicio..." />
                </SelectTrigger>
                <SelectContent>
                  {servicios.map((servicio) => (
                    <SelectItem key={servicio.id} value={servicio.id}>
                      {servicio.nombre}
                      {servicio.tarifa > 0 && ` (${formatCurrency(servicio.tarifa)}/prenda)`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Persona *</Label>
              <Select
                value={createFormData.persona_id}
                onValueChange={(value) => setCreateFormData({ ...createFormData, persona_id: value })}
                disabled={!createFormData.servicio_id}
              >
                <SelectTrigger data-testid="create-select-persona">
                  <SelectValue placeholder={createFormData.servicio_id ? "Seleccionar persona..." : "Selecciona servicio primero"} />
                </SelectTrigger>
                <SelectContent>
                  {personasFiltradasCreate.length === 0 ? (
                    <SelectItem value="none" disabled>
                      No hay personas asignadas a este servicio
                    </SelectItem>
                  ) : (
                    personasFiltradasCreate.map((persona) => (
                      <SelectItem key={persona.id} value={persona.id}>
                        {persona.nombre}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="create-fecha-inicio">Fecha Inicio</Label>
                <Input
                  id="create-fecha-inicio"
                  type="date"
                  value={createFormData.fecha_inicio}
                  onChange={(e) => setCreateFormData({ ...createFormData, fecha_inicio: e.target.value })}
                  data-testid="create-input-fecha-inicio"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="create-fecha-fin">Fecha Fin</Label>
                <Input
                  id="create-fecha-fin"
                  type="date"
                  value={createFormData.fecha_fin}
                  onChange={(e) => setCreateFormData({ ...createFormData, fecha_fin: e.target.value })}
                  data-testid="create-input-fecha-fin"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-cantidad">Cantidad de Prendas</Label>
              <Input
                id="create-cantidad"
                type="number"
                min="0"
                value={createFormData.cantidad}
                onChange={(e) => setCreateFormData({ ...createFormData, cantidad: parseInt(e.target.value) || 0 })}
                className="font-mono"
                data-testid="create-input-cantidad"
              />
            </div>

            {/* Tarifa editable */}
            <div className="space-y-2">
              <Label htmlFor="create-tarifa">Tarifa por Prenda (S/)</Label>
              <Input
                id="create-tarifa"
                type="number"
                min="0"
                step="0.01"
                value={createFormData.tarifa_aplicada}
                onChange={(e) => setCreateFormData({ ...createFormData, tarifa_aplicada: parseFloat(e.target.value) || 0 })}
                className="font-mono"
                placeholder="0.00"
                data-testid="create-input-tarifa"
              />
              {createFormData.servicio_id && getServicioTarifa(createFormData.servicio_id) > 0 && (
                <p className="text-xs text-muted-foreground">
                  Tarifa referencial del servicio: {formatCurrency(getServicioTarifa(createFormData.servicio_id))}
                </p>
              )}
            </div>

            {/* Mostrar costo calculado */}
            {createFormData.cantidad > 0 && createFormData.tarifa_aplicada > 0 && (
              <div className="p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-green-700 dark:text-green-300">Costo calculado:</span>
                  <span className="text-lg font-bold text-green-700 dark:text-green-300">
                    {formatCurrency(calcularCostoCreate())}
                  </span>
                </div>
                <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                  {createFormData.cantidad} prendas × {formatCurrency(createFormData.tarifa_aplicada)}
                </p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="create-observaciones">Observaciones</Label>
              <Textarea
                id="create-observaciones"
                value={createFormData.observaciones}
                onChange={(e) => setCreateFormData({ ...createFormData, observaciones: e.target.value })}
                placeholder="Notas adicionales..."
                rows={2}
                data-testid="create-input-observaciones"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleCreateSubmit}
              disabled={!createFormData.registro_id || !createFormData.servicio_id || !createFormData.persona_id}
              data-testid="btn-crear-movimiento"
            >
              Crear Movimiento
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
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
  DialogFooter,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Plus, Pencil, Trash2, Route, ArrowRight, GripVertical, X } from 'lucide-react';
import { toast } from 'sonner';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Componente sorteable para etapas
const SortableEtapa = ({ etapa, index, servicios, onRemove }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: etapa.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const servicio = servicios.find(s => s.id === etapa.servicio_id);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-2 p-2 bg-muted/50 rounded-md border ${isDragging ? 'border-primary' : ''}`}
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing p-1 hover:bg-muted rounded"
        data-testid={`drag-etapa-${index}`}
      >
        <GripVertical className="h-4 w-4 text-muted-foreground" />
      </button>
      <Badge variant="outline" className="font-mono">{index + 1}</Badge>
      <span className="flex-1 font-medium">{servicio?.nombre || 'Desconocido'}</span>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6"
        onClick={() => onRemove(etapa.id)}
        data-testid={`remove-etapa-${index}`}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  );
};

export const RutasProduccion = () => {
  const [rutas, setRutas] = useState([]);
  const [servicios, setServicios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRuta, setEditingRuta] = useState(null);
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    etapas: [],
  });
  const [servicioToAdd, setServicioToAdd] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const fetchData = async () => {
    try {
      const [rutasRes, serviciosRes] = await Promise.all([
        axios.get(`${API}/rutas-produccion`),
        axios.get(`${API}/servicios-produccion`),
      ]);
      setRutas(rutasRes.data);
      setServicios(serviciosRes.data.sort((a, b) => (a.secuencia || 0) - (b.secuencia || 0)));
    } catch (error) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleOpenDialog = (ruta = null) => {
    if (ruta) {
      setEditingRuta(ruta);
      // Agregar IDs únicos a las etapas para drag & drop
      const etapasConId = (ruta.etapas || []).map((e, i) => ({
        ...e,
        id: `etapa-${i}-${Date.now()}`,
      }));
      setFormData({
        nombre: ruta.nombre,
        descripcion: ruta.descripcion || '',
        etapas: etapasConId,
      });
    } else {
      setEditingRuta(null);
      setFormData({ nombre: '', descripcion: '', etapas: [] });
    }
    setServicioToAdd('');
    setDialogOpen(true);
  };

  const handleAddEtapa = () => {
    if (!servicioToAdd) return;
    
    const newEtapa = {
      id: `etapa-${Date.now()}`,
      servicio_id: servicioToAdd,
      orden: formData.etapas.length,
    };
    setFormData({
      ...formData,
      etapas: [...formData.etapas, newEtapa],
    });
    setServicioToAdd('');
  };

  const handleRemoveEtapa = (etapaId) => {
    setFormData({
      ...formData,
      etapas: formData.etapas.filter(e => e.id !== etapaId),
    });
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = formData.etapas.findIndex(e => e.id === active.id);
    const newIndex = formData.etapas.findIndex(e => e.id === over.id);
    
    const newEtapas = arrayMove(formData.etapas, oldIndex, newIndex).map((e, i) => ({
      ...e,
      orden: i,
    }));
    
    setFormData({ ...formData, etapas: newEtapas });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.nombre.trim()) {
      toast.error('El nombre es requerido');
      return;
    }
    if (formData.etapas.length === 0) {
      toast.error('Debe agregar al menos una etapa');
      return;
    }

    try {
      // Preparar etapas sin el id temporal
      const etapasLimpias = formData.etapas.map((e, i) => ({
        servicio_id: e.servicio_id,
        orden: i,
      }));

      const payload = {
        nombre: formData.nombre,
        descripcion: formData.descripcion,
        etapas: etapasLimpias,
      };

      if (editingRuta) {
        await axios.put(`${API}/rutas-produccion/${editingRuta.id}`, payload);
        toast.success('Ruta actualizada');
      } else {
        await axios.post(`${API}/rutas-produccion`, payload);
        toast.success('Ruta creada');
      }
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/rutas-produccion/${id}`);
      toast.success('Ruta eliminada');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  // Servicios disponibles para agregar (no repetidos)
  const serviciosDisponibles = servicios.filter(
    s => !formData.etapas.some(e => e.servicio_id === s.id)
  );

  if (loading) {
    return <div className="flex justify-center p-8">Cargando...</div>;
  }

  return (
    <div className="space-y-6" data-testid="rutas-produccion-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Route className="h-6 w-6" />
            Rutas de Producción
          </h1>
          <p className="text-muted-foreground">
            Define las secuencias de etapas para los modelos
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()} data-testid="btn-nueva-ruta">
          <Plus className="h-4 w-4 mr-2" />
          Nueva Ruta
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead>Descripción</TableHead>
                <TableHead>Etapas</TableHead>
                <TableHead className="text-right w-[100px]">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rutas.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                    No hay rutas creadas. Crea una para empezar.
                  </TableCell>
                </TableRow>
              ) : (
                rutas.map((ruta) => (
                  <TableRow key={ruta.id} data-testid={`ruta-row-${ruta.id}`}>
                    <TableCell className="font-medium">{ruta.nombre}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {ruta.descripcion || '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap items-center gap-1">
                        {(ruta.etapas || [])
                          .sort((a, b) => a.orden - b.orden)
                          .map((etapa, i) => (
                            <span key={i} className="flex items-center">
                              <Badge variant="secondary" className="text-xs">
                                {etapa.servicio_nombre || 'N/A'}
                              </Badge>
                              {i < ruta.etapas.length - 1 && (
                                <ArrowRight className="h-3 w-3 mx-1 text-muted-foreground" />
                              )}
                            </span>
                          ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleOpenDialog(ruta)}
                          data-testid={`edit-ruta-${ruta.id}`}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(ruta.id)}
                          data-testid={`delete-ruta-${ruta.id}`}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingRuta ? 'Editar Ruta' : 'Nueva Ruta de Producción'}
            </DialogTitle>
            <DialogDescription>
              Define la secuencia de etapas que seguirán los registros
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre *</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ej: Ruta Estándar, Ruta Premium..."
                  data-testid="input-nombre-ruta"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="descripcion">Descripción</Label>
                <Input
                  id="descripcion"
                  value={formData.descripcion}
                  onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                  placeholder="Descripción opcional..."
                  data-testid="input-descripcion-ruta"
                />
              </div>

              <div className="space-y-2">
                <Label>Etapas de Producción *</Label>
                <div className="flex gap-2">
                  <Select value={servicioToAdd} onValueChange={setServicioToAdd}>
                    <SelectTrigger className="flex-1" data-testid="select-servicio-etapa">
                      <SelectValue placeholder="Seleccionar servicio..." />
                    </SelectTrigger>
                    <SelectContent>
                      {serviciosDisponibles.length === 0 ? (
                        <SelectItem value="none" disabled>
                          Todos los servicios ya están agregados
                        </SelectItem>
                      ) : (
                        serviciosDisponibles.map((s) => (
                          <SelectItem key={s.id} value={s.id}>
                            {s.nombre}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={handleAddEtapa}
                    disabled={!servicioToAdd}
                    data-testid="btn-agregar-etapa"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {formData.etapas.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">
                    Arrastra para reordenar ({formData.etapas.length} etapas)
                  </Label>
                  <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                  >
                    <SortableContext
                      items={formData.etapas.map(e => e.id)}
                      strategy={verticalListSortingStrategy}
                    >
                      <div className="space-y-2">
                        {formData.etapas.map((etapa, i) => (
                          <SortableEtapa
                            key={etapa.id}
                            etapa={etapa}
                            index={i}
                            servicios={servicios}
                            onRemove={handleRemoveEtapa}
                          />
                        ))}
                      </div>
                    </SortableContext>
                  </DndContext>
                </div>
              )}

              {formData.etapas.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4 border-2 border-dashed rounded-md">
                  Agrega servicios para definir las etapas
                </p>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" data-testid="btn-guardar-ruta">
                {editingRuta ? 'Guardar Cambios' : 'Crear Ruta'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

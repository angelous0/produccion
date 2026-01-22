import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import { Plus, Pencil, Trash2, Users, Phone, CheckCircle, XCircle, GripVertical } from 'lucide-react';
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

// Componente de fila sorteable
const SortableRow = ({ persona, onEdit, onDelete, onToggleActivo }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: persona.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <tr
      ref={setNodeRef}
      style={style}
      className={`border-b ${isDragging ? 'bg-muted' : ''}`}
      data-testid={`persona-row-${persona.id}`}
    >
      <td className="p-3">
        <div className="flex items-center gap-2">
          <button
            {...attributes}
            {...listeners}
            className="cursor-grab active:cursor-grabbing p-1 hover:bg-muted rounded"
            data-testid={`drag-handle-${persona.id}`}
          >
            <GripVertical className="h-4 w-4 text-muted-foreground" />
          </button>
          <span className="font-medium">{persona.nombre}</span>
        </div>
      </td>
      <td className="p-3">
        <div className="flex flex-wrap gap-1">
          {(persona.servicios_nombres || []).map((nombre, idx) => (
            <Badge key={idx} variant="secondary" className="text-xs">
              {nombre}
            </Badge>
          ))}
        </div>
      </td>
      <td className="p-3">
        {persona.telefono ? (
          <div className="flex items-center gap-1 text-muted-foreground">
            <Phone className="h-3 w-3" />
            {persona.telefono}
          </div>
        ) : (
          <span className="text-muted-foreground">-</span>
        )}
      </td>
      <td className="p-3 text-center">
        <Switch
          checked={persona.activo !== false}
          onCheckedChange={() => onToggleActivo(persona)}
          data-testid={`toggle-activo-${persona.id}`}
        />
      </td>
      <td className="p-3 text-right">
        <div className="flex justify-end gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onEdit(persona)}
            data-testid={`edit-persona-${persona.id}`}
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onDelete(persona.id)}
            data-testid={`delete-persona-${persona.id}`}
          >
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      </td>
    </tr>
  );
};

export const PersonasProduccion = () => {
  const [personas, setPersonas] = useState([]);
  const [servicios, setServicios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPersona, setEditingPersona] = useState(null);
  const [formData, setFormData] = useState({
    nombre: '',
    servicio_ids: [],
    telefono: '',
    activo: true,
    orden: 0,
  });
  const [filtroActivo, setFiltroActivo] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const fetchData = async () => {
    try {
      const [personasRes, serviciosRes] = await Promise.all([
        axios.get(`${API}/personas-produccion`),
        axios.get(`${API}/servicios-produccion`),
      ]);
      setPersonas(personasRes.data);
      setServicios(serviciosRes.data);
    } catch (error) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleOpenDialog = (persona = null) => {
    if (persona) {
      setEditingPersona(persona);
      setFormData({
        nombre: persona.nombre,
        servicio_ids: persona.servicio_ids || [],
        telefono: persona.telefono || '',
        activo: persona.activo !== false,
        orden: persona.orden || 0,
      });
    } else {
      setEditingPersona(null);
      const maxOrden = personas.reduce((max, p) => Math.max(max, p.orden || 0), 0);
      setFormData({
        nombre: '',
        servicio_ids: [],
        telefono: '',
        activo: true,
        orden: maxOrden + 1,
      });
    }
    setDialogOpen(true);
  };

  const handleServicioToggle = (servicioId) => {
    const current = formData.servicio_ids;
    if (current.includes(servicioId)) {
      setFormData({
        ...formData,
        servicio_ids: current.filter(id => id !== servicioId),
      });
    } else {
      setFormData({
        ...formData,
        servicio_ids: [...current, servicioId],
      });
    }
  };

  const handleSubmit = async () => {
    if (!formData.nombre.trim()) {
      toast.error('El nombre es requerido');
      return;
    }
    if (formData.servicio_ids.length === 0) {
      toast.error('Selecciona al menos un servicio');
      return;
    }

    try {
      if (editingPersona) {
        await axios.put(`${API}/personas-produccion/${editingPersona.id}`, formData);
        toast.success('Persona actualizada');
      } else {
        await axios.post(`${API}/personas-produccion`, formData);
        toast.success('Persona creada');
      }
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/personas-produccion/${id}`);
      toast.success('Persona eliminada');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const handleToggleActivo = async (persona) => {
    try {
      await axios.put(`${API}/personas-produccion/${persona.id}`, {
        nombre: persona.nombre,
        servicio_ids: persona.servicio_ids || [],
        telefono: persona.telefono || '',
        activo: !persona.activo,
        orden: persona.orden || 0,
      });
      toast.success(persona.activo ? 'Persona desactivada' : 'Persona activada');
      fetchData();
    } catch (error) {
      toast.error('Error al actualizar estado');
    }
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      const oldIndex = personasFiltradas.findIndex((p) => p.id === active.id);
      const newIndex = personasFiltradas.findIndex((p) => p.id === over.id);

      const newPersonas = arrayMove(personasFiltradas, oldIndex, newIndex);
      
      // Actualizar orden localmente primero para UI responsiva
      const updatedPersonas = newPersonas.map((p, index) => ({
        ...p,
        orden: index + 1,
      }));
      
      // Actualizar el estado local
      setPersonas(prev => {
        const otrasPersonas = prev.filter(p => !updatedPersonas.find(up => up.id === p.id));
        return [...updatedPersonas, ...otrasPersonas].sort((a, b) => (a.orden || 0) - (b.orden || 0));
      });

      // Actualizar en el backend
      try {
        await Promise.all(
          updatedPersonas.map((p) =>
            axios.put(`${API}/personas-produccion/${p.id}`, {
              nombre: p.nombre,
              servicio_ids: p.servicio_ids || [],
              telefono: p.telefono || '',
              activo: p.activo !== false,
              orden: p.orden,
            })
          )
        );
        toast.success('Orden actualizado');
      } catch (error) {
        toast.error('Error al actualizar orden');
        fetchData(); // Revertir en caso de error
      }
    }
  };

  const personasFiltradas = filtroActivo === null 
    ? personas 
    : personas.filter(p => p.activo === filtroActivo);

  return (
    <div className="space-y-6" data-testid="personas-produccion-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Users className="h-6 w-6" />
            Personas de Producción
          </h2>
          <p className="text-muted-foreground">
            Gestiona el personal asignado a los servicios. Arrastra para reordenar.
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()} data-testid="btn-nueva-persona">
          <Plus className="h-4 w-4 mr-2" />
          Nueva Persona
        </Button>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="text-lg">{personasFiltradas.length} personas</CardTitle>
          <div className="flex gap-2">
            <Button 
              variant={filtroActivo === null ? "default" : "outline"} 
              size="sm"
              onClick={() => setFiltroActivo(null)}
            >
              Todos
            </Button>
            <Button 
              variant={filtroActivo === true ? "default" : "outline"} 
              size="sm"
              onClick={() => setFiltroActivo(true)}
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Activos
            </Button>
            <Button 
              variant={filtroActivo === false ? "default" : "outline"} 
              size="sm"
              onClick={() => setFiltroActivo(false)}
            >
              <XCircle className="h-4 w-4 mr-1" />
              Inactivos
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Cargando...</div>
          ) : personasFiltradas.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No hay personas registradas
            </div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="bg-muted/50 border-b">
                    <th className="p-3 text-left text-sm font-semibold">Nombre</th>
                    <th className="p-3 text-left text-sm font-semibold">Servicios</th>
                    <th className="p-3 text-left text-sm font-semibold">Teléfono</th>
                    <th className="p-3 text-center text-sm font-semibold">Estado</th>
                    <th className="p-3 text-right text-sm font-semibold w-[120px]">Acciones</th>
                  </tr>
                </thead>
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={personasFiltradas.map((p) => p.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    <tbody>
                      {personasFiltradas.map((persona) => (
                        <SortableRow
                          key={persona.id}
                          persona={persona}
                          onEdit={handleOpenDialog}
                          onDelete={handleDelete}
                          onToggleActivo={handleToggleActivo}
                        />
                      ))}
                    </tbody>
                  </SortableContext>
                </DndContext>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingPersona ? 'Editar Persona' : 'Nueva Persona'}
            </DialogTitle>
            <DialogDescription>
              {editingPersona 
                ? 'Modifica los datos de la persona'
                : 'Registra una nueva persona de producción'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="nombre">Nombre *</Label>
              <Input
                id="nombre"
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                placeholder="Nombre completo"
                data-testid="input-nombre-persona"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="telefono">Teléfono</Label>
              <Input
                id="telefono"
                value={formData.telefono}
                onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                placeholder="Número de teléfono"
                data-testid="input-telefono-persona"
              />
            </div>

            <div className="space-y-2">
              <Label>Servicios Asignados *</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Selecciona los servicios que puede realizar esta persona
              </p>
              <div className="border rounded-lg p-3 space-y-2 max-h-[200px] overflow-y-auto">
                {servicios.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-2">
                    No hay servicios registrados
                  </p>
                ) : (
                  servicios.map((servicio) => (
                    <div key={servicio.id} className="flex items-center gap-2">
                      <Checkbox
                        id={`servicio-${servicio.id}`}
                        checked={formData.servicio_ids.includes(servicio.id)}
                        onCheckedChange={() => handleServicioToggle(servicio.id)}
                        data-testid={`checkbox-servicio-${servicio.id}`}
                      />
                      <Label 
                        htmlFor={`servicio-${servicio.id}`}
                        className="cursor-pointer flex-1"
                      >
                        {servicio.nombre}
                      </Label>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch
                id="activo"
                checked={formData.activo}
                onCheckedChange={(checked) => setFormData({ ...formData, activo: checked })}
                data-testid="switch-activo-persona"
              />
              <Label htmlFor="activo">Persona activa</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSubmit} data-testid="btn-guardar-persona">
              {editingPersona ? 'Actualizar' : 'Crear'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
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
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import { Plus, Pencil, Trash2, Users, Phone, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
  });
  const [filtroActivo, setFiltroActivo] = useState(null);

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
      });
    } else {
      setEditingPersona(null);
      setFormData({
        nombre: '',
        servicio_ids: [],
        telefono: '',
        activo: true,
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
        ...persona,
        activo: !persona.activo,
      });
      toast.success(persona.activo ? 'Persona desactivada' : 'Persona activada');
      fetchData();
    } catch (error) {
      toast.error('Error al actualizar estado');
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
            Gestiona el personal asignado a los servicios de producción
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
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead>Nombre</TableHead>
                    <TableHead>Servicios</TableHead>
                    <TableHead>Teléfono</TableHead>
                    <TableHead className="text-center">Estado</TableHead>
                    <TableHead className="w-[120px] text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {personasFiltradas.map((persona) => (
                    <TableRow key={persona.id} data-testid={`persona-row-${persona.id}`}>
                      <TableCell className="font-medium">{persona.nombre}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {(persona.servicios_nombres || []).map((nombre, idx) => (
                            <Badge key={idx} variant="secondary" className="text-xs">
                              {nombre}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        {persona.telefono ? (
                          <div className="flex items-center gap-1 text-muted-foreground">
                            <Phone className="h-3 w-3" />
                            {persona.telefono}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch
                          checked={persona.activo !== false}
                          onCheckedChange={() => handleToggleActivo(persona)}
                          data-testid={`toggle-activo-${persona.id}`}
                        />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleOpenDialog(persona)}
                            data-testid={`edit-persona-${persona.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(persona.id)}
                            data-testid={`delete-persona-${persona.id}`}
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

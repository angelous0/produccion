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
import { Label } from '../components/ui/label';
import { Plus, Pencil, Trash2, Cog, GripVertical } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ServiciosProduccion = () => {
  const [servicios, setServicios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingServicio, setEditingServicio] = useState(null);
  const [formData, setFormData] = useState({ nombre: '', secuencia: 0 });

  const fetchServicios = async () => {
    try {
      const response = await axios.get(`${API}/servicios-produccion`);
      setServicios(response.data);
    } catch (error) {
      toast.error('Error al cargar servicios');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServicios();
  }, []);

  const handleOpenDialog = (servicio = null) => {
    if (servicio) {
      setEditingServicio(servicio);
      setFormData({ nombre: servicio.nombre, secuencia: servicio.secuencia || 0 });
    } else {
      setEditingServicio(null);
      // Calcular la siguiente secuencia
      const maxSecuencia = servicios.reduce((max, s) => Math.max(max, s.secuencia || 0), 0);
      setFormData({ nombre: '', secuencia: maxSecuencia + 1 });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.nombre.trim()) {
      toast.error('El nombre es requerido');
      return;
    }

    try {
      if (editingServicio) {
        await axios.put(`${API}/servicios-produccion/${editingServicio.id}`, formData);
        toast.success('Servicio actualizado');
      } else {
        await axios.post(`${API}/servicios-produccion`, formData);
        toast.success('Servicio creado');
      }
      setDialogOpen(false);
      fetchServicios();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar este servicio?')) return;
    
    try {
      await axios.delete(`${API}/servicios-produccion/${id}`);
      toast.success('Servicio eliminado');
      fetchServicios();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  return (
    <div className="space-y-6" data-testid="servicios-produccion-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Cog className="h-6 w-6" />
            Servicios de Producción
          </h2>
          <p className="text-muted-foreground">
            Gestiona los servicios del proceso productivo
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()} data-testid="btn-nuevo-servicio">
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Servicio
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{servicios.length} servicios registrados</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Cargando...</div>
          ) : servicios.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No hay servicios registrados
            </div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead className="w-[80px]">Orden</TableHead>
                    <TableHead>Nombre</TableHead>
                    <TableHead className="w-[120px] text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {servicios.map((servicio) => (
                    <TableRow key={servicio.id} data-testid={`servicio-row-${servicio.id}`}>
                      <TableCell className="font-mono text-center">
                        <div className="flex items-center gap-2">
                          <GripVertical className="h-4 w-4 text-muted-foreground" />
                          {servicio.secuencia}
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">{servicio.nombre}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleOpenDialog(servicio)}
                            data-testid={`edit-servicio-${servicio.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(servicio.id)}
                            data-testid={`delete-servicio-${servicio.id}`}
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
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingServicio ? 'Editar Servicio' : 'Nuevo Servicio'}
            </DialogTitle>
            <DialogDescription>
              {editingServicio 
                ? 'Modifica los datos del servicio de producción'
                : 'Crea un nuevo servicio de producción'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="nombre">Nombre *</Label>
              <Input
                id="nombre"
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                placeholder="Ej: Corte, Costura, Bordado..."
                data-testid="input-nombre-servicio"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="secuencia">Orden de Secuencia</Label>
              <Input
                id="secuencia"
                type="number"
                min="0"
                value={formData.secuencia}
                onChange={(e) => setFormData({ ...formData, secuencia: parseInt(e.target.value) || 0 })}
                placeholder="0"
                className="font-mono"
                data-testid="input-secuencia-servicio"
              />
              <p className="text-xs text-muted-foreground">
                Define el orden en que aparecen los servicios
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSubmit} data-testid="btn-guardar-servicio">
              {editingServicio ? 'Actualizar' : 'Crear'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

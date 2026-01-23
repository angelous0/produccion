import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  DialogFooter,
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
import { Textarea } from '../components/ui/textarea';
import { Plus, Pencil, Trash2, ArrowLeft, Scissors } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const RegistroHilos = () => {
  const { registroId } = useParams();
  const navigate = useNavigate();
  
  const [registro, setRegistro] = useState(null);
  const [hilosRegistro, setHilosRegistro] = useState([]);
  const [hilos, setHilos] = useState([]);
  const [colores, setColores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({
    registro_id: registroId,
    hilo_id: '',
    color_id: '',
    cantidad: 0,
    observaciones: '',
  });

  const fetchData = async () => {
    try {
      const [regRes, hilosRegRes, hilosRes, coloresRes] = await Promise.all([
        axios.get(`${API}/registros/${registroId}`),
        axios.get(`${API}/registro-hilos?registro_id=${registroId}`),
        axios.get(`${API}/hilos`),
        axios.get(`${API}/colores-catalogo`),
      ]);
      setRegistro(regRes.data);
      setHilosRegistro(hilosRegRes.data);
      setHilos(hilosRes.data);
      setColores(coloresRes.data);
    } catch (error) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (registroId) {
      fetchData();
    }
  }, [registroId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingItem) {
        await axios.put(`${API}/registro-hilos/${editingItem.id}`, formData);
        toast.success('Hilo actualizado');
      } else {
        await axios.post(`${API}/registro-hilos`, formData);
        toast.success('Hilo agregado');
      }
      setDialogOpen(false);
      setEditingItem(null);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const resetForm = () => {
    setFormData({
      registro_id: registroId,
      hilo_id: '',
      color_id: '',
      cantidad: 0,
      observaciones: '',
    });
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({
      registro_id: registroId,
      hilo_id: item.hilo_id,
      color_id: item.color_id || '',
      cantidad: item.cantidad || 0,
      observaciones: item.observaciones || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar este hilo del registro?')) return;
    try {
      await axios.delete(`${API}/registro-hilos/${id}`);
      toast.success('Hilo eliminado');
      fetchData();
    } catch (error) {
      toast.error('Error al eliminar');
    }
  };

  const handleNew = () => {
    setEditingItem(null);
    resetForm();
    setDialogOpen(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Cargando...</p>
      </div>
    );
  }

  if (!registro) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Registro no encontrado</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="registro-hilos-page">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h2 className="text-2xl font-bold tracking-tight">Hilos Específicos</h2>
          <p className="text-muted-foreground">
            Registro: <span className="font-semibold text-foreground">{registro.n_corte}</span>
            {registro.modelo_nombre && ` - ${registro.modelo_nombre}`}
          </p>
        </div>
        <Button onClick={handleNew} data-testid="btn-agregar-hilo">
          <Plus className="h-4 w-4 mr-2" />
          Agregar Hilo
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Scissors className="h-5 w-5" />
            Hilos Asignados ({hilosRegistro.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="data-table-header">
                <TableHead>Hilo</TableHead>
                <TableHead>Color Asignado</TableHead>
                <TableHead className="text-right">Cantidad</TableHead>
                <TableHead>Observaciones</TableHead>
                <TableHead className="w-[100px]">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {hilosRegistro.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                    No hay hilos específicos asignados a este registro
                  </TableCell>
                </TableRow>
              ) : (
                hilosRegistro.map((item) => (
                  <TableRow key={item.id} data-testid={`hilo-registro-row-${item.id}`}>
                    <TableCell className="font-medium">{item.hilo_nombre || '-'}</TableCell>
                    <TableCell>{item.color_nombre || '-'}</TableCell>
                    <TableCell className="text-right font-mono">{item.cantidad || '-'}</TableCell>
                    <TableCell className="text-muted-foreground text-sm max-w-[200px] truncate">
                      {item.observaciones || '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(item)}
                          data-testid={`edit-hilo-${item.id}`}
                        >
                          <Pencil className="h-4 w-4 text-blue-500" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(item.id)}
                          data-testid={`delete-hilo-${item.id}`}
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
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingItem ? 'Editar Hilo' : 'Agregar Hilo'}</DialogTitle>
            <DialogDescription>
              Asignar un hilo específico al registro {registro.n_corte}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Hilo *</Label>
                <Select
                  value={formData.hilo_id}
                  onValueChange={(v) => setFormData({ ...formData, hilo_id: v })}
                >
                  <SelectTrigger data-testid="select-hilo">
                    <SelectValue placeholder="Seleccionar hilo..." />
                  </SelectTrigger>
                  <SelectContent>
                    {hilos.map((h) => (
                      <SelectItem key={h.id} value={h.id}>
                        {h.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Color Asignado (opcional)</Label>
                <Select
                  value={formData.color_id}
                  onValueChange={(v) => setFormData({ ...formData, color_id: v === 'none' ? '' : v })}
                >
                  <SelectTrigger data-testid="select-color">
                    <SelectValue placeholder="Sin color específico" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sin color específico</SelectItem>
                    {colores.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.nombre} {c.color_general && `(${c.color_general})`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="cantidad">Cantidad</Label>
                <Input
                  id="cantidad"
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.cantidad}
                  onChange={(e) => setFormData({ ...formData, cantidad: parseFloat(e.target.value) || 0 })}
                  placeholder="0"
                  data-testid="input-cantidad"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="observaciones">Observaciones</Label>
                <Textarea
                  id="observaciones"
                  value={formData.observaciones}
                  onChange={(e) => setFormData({ ...formData, observaciones: e.target.value })}
                  placeholder="Notas adicionales..."
                  rows={2}
                  data-testid="input-observaciones"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={!formData.hilo_id} data-testid="btn-guardar">
                {editingItem ? 'Actualizar' : 'Agregar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

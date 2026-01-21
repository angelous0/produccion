import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
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
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Label } from '../components/ui/label';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const Modelos = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({
    nombre: '',
    marca_id: '',
    tipo_id: '',
    entalle_id: '',
    tela_id: '',
    hilo_id: '',
  });

  // Datos para los selects
  const [marcas, setMarcas] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [entalles, setEntalles] = useState([]);
  const [telas, setTelas] = useState([]);
  const [hilos, setHilos] = useState([]);

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API}/modelos`);
      setItems(response.data);
    } catch (error) {
      toast.error('Error al cargar modelos');
    } finally {
      setLoading(false);
    }
  };

  const fetchRelatedData = async () => {
    try {
      const [marcasRes, tiposRes, entallesRes, telasRes, hilosRes] = await Promise.all([
        axios.get(`${API}/marcas`),
        axios.get(`${API}/tipos`),
        axios.get(`${API}/entalles`),
        axios.get(`${API}/telas`),
        axios.get(`${API}/hilos`),
      ]);
      setMarcas(marcasRes.data);
      setTipos(tiposRes.data);
      setEntalles(entallesRes.data);
      setTelas(telasRes.data);
      setHilos(hilosRes.data);
    } catch (error) {
      toast.error('Error al cargar datos relacionados');
    }
  };

  useEffect(() => {
    fetchItems();
    fetchRelatedData();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingItem) {
        await axios.put(`${API}/modelos/${editingItem.id}`, formData);
        toast.success('Modelo actualizado');
      } else {
        await axios.post(`${API}/modelos`, formData);
        toast.success('Modelo creado');
      }
      setDialogOpen(false);
      setEditingItem(null);
      setFormData({
        nombre: '',
        marca_id: '',
        tipo_id: '',
        entalle_id: '',
        tela_id: '',
        hilo_id: '',
      });
      fetchItems();
    } catch (error) {
      toast.error('Error al guardar modelo');
    }
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({
      nombre: item.nombre,
      marca_id: item.marca_id,
      tipo_id: item.tipo_id,
      entalle_id: item.entalle_id,
      tela_id: item.tela_id,
      hilo_id: item.hilo_id,
    });
    setDialogOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/modelos/${id}`);
      toast.success('Modelo eliminado');
      fetchItems();
    } catch (error) {
      toast.error('Error al eliminar modelo');
    }
  };

  const handleNew = () => {
    setEditingItem(null);
    setFormData({
      nombre: '',
      marca_id: '',
      tipo_id: '',
      entalle_id: '',
      tela_id: '',
      hilo_id: '',
    });
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6" data-testid="modelos-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Modelos</h2>
          <p className="text-muted-foreground">Gestión de modelos de productos</p>
        </div>
        <Button onClick={handleNew} data-testid="btn-nuevo-modelo">
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Modelo
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="data-table-header">
                  <TableHead>Nombre</TableHead>
                  <TableHead>Marca</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Entalle</TableHead>
                  <TableHead>Tela</TableHead>
                  <TableHead>Hilo</TableHead>
                  <TableHead className="w-[100px]">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      Cargando...
                    </TableCell>
                  </TableRow>
                ) : items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      No hay modelos registrados
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((item) => (
                    <TableRow key={item.id} className="data-table-row" data-testid={`modelo-row-${item.id}`}>
                      <TableCell className="font-medium">{item.nombre}</TableCell>
                      <TableCell>{item.marca_nombre || '-'}</TableCell>
                      <TableCell>{item.tipo_nombre || '-'}</TableCell>
                      <TableCell>{item.entalle_nombre || '-'}</TableCell>
                      <TableCell>{item.tela_nombre || '-'}</TableCell>
                      <TableCell>{item.hilo_nombre || '-'}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(item)}
                            data-testid={`edit-modelo-${item.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(item.id)}
                            data-testid={`delete-modelo-${item.id}`}
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
          </div>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingItem ? 'Editar Modelo' : 'Nuevo Modelo'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Nombre del modelo"
                  required
                  data-testid="input-nombre-modelo"
                />
              </div>

              <div className="space-y-2">
                <Label>Marca</Label>
                <Select
                  value={formData.marca_id}
                  onValueChange={(value) => setFormData({ ...formData, marca_id: value })}
                >
                  <SelectTrigger data-testid="select-marca">
                    <SelectValue placeholder="Seleccionar marca" />
                  </SelectTrigger>
                  <SelectContent>
                    {marcas.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Tipo</Label>
                <Select
                  value={formData.tipo_id}
                  onValueChange={(value) => setFormData({ ...formData, tipo_id: value })}
                >
                  <SelectTrigger data-testid="select-tipo">
                    <SelectValue placeholder="Seleccionar tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    {tipos.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Entalle</Label>
                <Select
                  value={formData.entalle_id}
                  onValueChange={(value) => setFormData({ ...formData, entalle_id: value })}
                >
                  <SelectTrigger data-testid="select-entalle">
                    <SelectValue placeholder="Seleccionar entalle" />
                  </SelectTrigger>
                  <SelectContent>
                    {entalles.map((e) => (
                      <SelectItem key={e.id} value={e.id}>
                        {e.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Tela</Label>
                <Select
                  value={formData.tela_id}
                  onValueChange={(value) => setFormData({ ...formData, tela_id: value })}
                >
                  <SelectTrigger data-testid="select-tela">
                    <SelectValue placeholder="Seleccionar tela" />
                  </SelectTrigger>
                  <SelectContent>
                    {telas.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Hilo</Label>
                <Select
                  value={formData.hilo_id}
                  onValueChange={(value) => setFormData({ ...formData, hilo_id: value })}
                >
                  <SelectTrigger data-testid="select-hilo">
                    <SelectValue placeholder="Seleccionar hilo" />
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
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" data-testid="btn-guardar-modelo">
                {editingItem ? 'Actualizar' : 'Crear'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

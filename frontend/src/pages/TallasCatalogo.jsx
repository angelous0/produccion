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
import { Label } from '../components/ui/label';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const TallasCatalogo = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({ nombre: '', orden: 0 });

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API}/tallas-catalogo`);
      setItems(response.data);
    } catch (error) {
      toast.error('Error al cargar tallas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingItem) {
        await axios.put(`${API}/tallas-catalogo/${editingItem.id}`, formData);
        toast.success('Talla actualizada');
      } else {
        await axios.post(`${API}/tallas-catalogo`, formData);
        toast.success('Talla creada');
      }
      setDialogOpen(false);
      setEditingItem(null);
      setFormData({ nombre: '', orden: 0 });
      fetchItems();
    } catch (error) {
      toast.error('Error al guardar talla');
    }
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({ nombre: item.nombre, orden: item.orden || 0 });
    setDialogOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/tallas-catalogo/${id}`);
      toast.success('Talla eliminada');
      fetchItems();
    } catch (error) {
      toast.error('Error al eliminar talla');
    }
  };

  const handleNew = () => {
    setEditingItem(null);
    setFormData({ nombre: '', orden: items.length });
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6" data-testid="tallas-catalogo-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Catálogo de Tallas</h2>
          <p className="text-muted-foreground">Gestión de tallas disponibles</p>
        </div>
        <Button onClick={handleNew} data-testid="btn-nueva-talla">
          <Plus className="h-4 w-4 mr-2" />
          Nueva Talla
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="data-table-header">
                <TableHead className="w-[80px]">Orden</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead className="w-[100px]">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={3} className="text-center py-8">
                    Cargando...
                  </TableCell>
                </TableRow>
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={3} className="text-center py-8 text-muted-foreground">
                    No hay tallas registradas
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow key={item.id} className="data-table-row" data-testid={`talla-row-${item.id}`}>
                    <TableCell className="font-mono text-muted-foreground">{item.orden}</TableCell>
                    <TableCell className="font-medium">{item.nombre}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(item)}
                          data-testid={`edit-talla-${item.id}`}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(item.id)}
                          data-testid={`delete-talla-${item.id}`}
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
            <DialogTitle>{editingItem ? 'Editar Talla' : 'Nueva Talla'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ej: 28, 30, S, M, L"
                  required
                  data-testid="input-nombre-talla"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="orden">Orden</Label>
                <Input
                  id="orden"
                  type="number"
                  value={formData.orden}
                  onChange={(e) => setFormData({ ...formData, orden: parseInt(e.target.value) || 0 })}
                  placeholder="0"
                  data-testid="input-orden-talla"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" data-testid="btn-guardar-talla">
                {editingItem ? 'Actualizar' : 'Crear'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

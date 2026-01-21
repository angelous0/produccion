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

export const Telas = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({ nombre: '' });

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API}/telas`);
      setItems(response.data);
    } catch (error) {
      toast.error('Error al cargar telas');
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
        await axios.put(`${API}/telas/${editingItem.id}`, formData);
        toast.success('Tela actualizada');
      } else {
        await axios.post(`${API}/telas`, formData);
        toast.success('Tela creada');
      }
      setDialogOpen(false);
      setEditingItem(null);
      setFormData({ nombre: '' });
      fetchItems();
    } catch (error) {
      toast.error('Error al guardar tela');
    }
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({ nombre: item.nombre });
    setDialogOpen(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar esta tela?')) return;
    try {
      await axios.delete(`${API}/telas/${id}`);
      toast.success('Tela eliminada');
      fetchItems();
    } catch (error) {
      toast.error('Error al eliminar tela');
    }
  };

  const handleNew = () => {
    setEditingItem(null);
    setFormData({ nombre: '' });
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6" data-testid="telas-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Telas</h2>
          <p className="text-muted-foreground">Gestión de telas de productos</p>
        </div>
        <Button onClick={handleNew} data-testid="btn-nueva-tela">
          <Plus className="h-4 w-4 mr-2" />
          Nueva Tela
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="data-table-header">
                <TableHead>Nombre</TableHead>
                <TableHead className="w-[100px]">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={2} className="text-center py-8">
                    Cargando...
                  </TableCell>
                </TableRow>
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={2} className="text-center py-8 text-muted-foreground">
                    No hay telas registradas
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow key={item.id} className="data-table-row" data-testid={`tela-row-${item.id}`}>
                    <TableCell className="font-medium">{item.nombre}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(item)}
                          data-testid={`edit-tela-${item.id}`}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(item.id)}
                          data-testid={`delete-tela-${item.id}`}
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
            <DialogTitle>{editingItem ? 'Editar Tela' : 'Nueva Tela'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ nombre: e.target.value })}
                  placeholder="Nombre de la tela"
                  required
                  data-testid="input-nombre-tela"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" data-testid="btn-guardar-tela">
                {editingItem ? 'Actualizar' : 'Crear'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

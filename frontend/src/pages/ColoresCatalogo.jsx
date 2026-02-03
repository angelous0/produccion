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
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { SortableRow, useSortableTable, SortableTableWrapper } from '../components/SortableTable';
import { ColorGeneralCombobox } from '../components/ColorGeneralCombobox';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ColoresCatalogo = () => {
  const [items, setItems] = useState([]);
  const [coloresGenerales, setColoresGenerales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({ nombre: '', color_general_id: '', orden: 0 });

  const { sensors, handleDragEnd, isSaving, modifiers } = useSortableTable(items, setItems, 'colores-catalogo');

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API}/colores-catalogo`);
      setItems(response.data);
    } catch (error) {
      toast.error('Error al cargar colores');
    } finally {
      setLoading(false);
    }
  };

  const fetchColoresGenerales = async () => {
    try {
      const response = await axios.get(`${API}/colores-generales`);
      setColoresGenerales(response.data);
    } catch (error) {
      console.error('Error al cargar colores generales');
    }
  };

  useEffect(() => {
    fetchItems();
    fetchColoresGenerales();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        nombre: formData.nombre,
        // codigo_hex se mantiene en DB pero no se usa desde UI
        codigo_hex: '',
        color_general_id: formData.color_general_id || null,
        orden: formData.orden,
      };
      if (editingItem) {
        await axios.put(`${API}/colores-catalogo/${editingItem.id}`, payload);
        toast.success('Color actualizado');
      } else {
        await axios.post(`${API}/colores-catalogo`, payload);
        toast.success('Color creado');
      }
      setDialogOpen(false);
      setEditingItem(null);
      setFormData({ nombre: '', codigo_hex: '', color_general_id: '', orden: 0 });
      fetchItems();
    } catch (error) {
      toast.error('Error al guardar color');
    }
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({ 
      nombre: item.nombre, 
      color_general_id: item.color_general_id || '',
      orden: item.orden || 0
    });
    setDialogOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/colores-catalogo/${id}`);
      toast.success('Color eliminado');
      fetchItems();
    } catch (error) {
      toast.error('Error al eliminar color');
    }
  };

  const handleNew = () => {
    setEditingItem(null);
    setFormData({ nombre: '', codigo_hex: '', color_general_id: '', orden: 0 });
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6" data-testid="colores-catalogo-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Catálogo de Colores</h2>
          <p className="text-muted-foreground">
            Gestión de colores disponibles
            {isSaving && <span className="ml-2 text-xs">(Guardando...)</span>}
          </p>
        </div>
        <Button onClick={handleNew} data-testid="btn-nuevo-color">
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Color
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="data-table-header">
                <TableHead className="w-[40px]"></TableHead>
                <TableHead className="w-[60px]">Vista</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Color General</TableHead>
                <TableHead>Código Hex</TableHead>
                <TableHead className="w-[100px]">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    Cargando...
                  </TableCell>
                </TableRow>
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No hay colores registrados
                  </TableCell>
                </TableRow>
              ) : (
                <SortableTableWrapper
                  items={items}
                  sensors={sensors}
                  handleDragEnd={handleDragEnd}
                  modifiers={modifiers}
                >
                  {items.map((item) => (
                    <SortableRow key={item.id} id={item.id}>
                      <TableCell>
                        <div 
                          className="w-8 h-8 rounded border"
                          style={{ backgroundColor: item.codigo_hex || '#ccc' }}
                        />
                      </TableCell>
                      <TableCell className="font-medium">{item.nombre}</TableCell>
                      <TableCell className="text-muted-foreground">{item.color_general_nombre || '-'}</TableCell>
                      <TableCell className="font-mono text-sm">{item.codigo_hex || '-'}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(item)}
                            data-testid={`edit-color-${item.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(item.id)}
                            data-testid={`delete-color-${item.id}`}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </SortableRow>
                  ))}
                </SortableTableWrapper>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingItem ? 'Editar Color' : 'Nuevo Color'}</DialogTitle>
            <DialogDescription>
              {editingItem ? 'Modifica los datos del color específico' : 'Agrega un nuevo color al catálogo'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre Específico</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ej: Celeste Claro, Celeste Oscuro"
                  required
                  data-testid="input-nombre-color"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="color_general_id">Color General</Label>
                <Select
                  value={formData.color_general_id}
                  onValueChange={(value) => setFormData({ ...formData, color_general_id: value })}
                >
                  <SelectTrigger data-testid="select-color-general">
                    <SelectValue placeholder="Seleccionar color general" />
                  </SelectTrigger>
                  <SelectContent>
                    {coloresGenerales.map((cg) => (
                      <SelectItem key={cg.id} value={cg.id}>
                        {cg.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Agrupa colores similares (Celeste Claro, Celeste Oscuro → "Celeste")
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="codigo_hex">Código Hex (opcional)</Label>
                <div className="flex gap-2">
                  <Input
                    id="codigo_hex"
                    value={formData.codigo_hex}
                    onChange={(e) => setFormData({ ...formData, codigo_hex: e.target.value })}
                    placeholder="#000000"
                    data-testid="input-hex-color"
                  />
                  <input
                    type="color"
                    value={formData.codigo_hex || '#000000'}
                    onChange={(e) => setFormData({ ...formData, codigo_hex: e.target.value })}
                    className="w-12 h-10 rounded border cursor-pointer"
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" data-testid="btn-guardar-color">
                {editingItem ? 'Actualizar' : 'Crear'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

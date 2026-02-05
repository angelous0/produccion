import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
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
import { Textarea } from '../components/ui/textarea';
import { Plus, Pencil, Trash2, Package, AlertTriangle, Layers, Eye, BookmarkCheck } from 'lucide-react';
import { toast } from 'sonner';
import { ExportButton } from '../components/ExportButton';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const UNIDADES = ['unidad', 'metro', 'kg', 'litro', 'rollo', 'caja', 'par'];
const CATEGORIAS = ['Telas', 'Avios', 'Otros'];

export const Inventario = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [reservasDialogOpen, setReservasDialogOpen] = useState(false);
  const [reservasDetalle, setReservasDetalle] = useState(null);
  const [loadingReservas, setLoadingReservas] = useState(false);
  const [formData, setFormData] = useState({
    codigo: '',
    nombre: '',
    descripcion: '',
    categoria: 'Otros',
    unidad_medida: 'unidad',
    stock_minimo: 0,
    control_por_rollos: false,
  });

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API}/inventario`);
      setItems(response.data);
    } catch (error) {
      toast.error('Error al cargar inventario');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const resetForm = () => {
    setFormData({
      codigo: '',
      nombre: '',
      descripcion: '',
      categoria: 'Otros',
      unidad_medida: 'unidad',
      stock_minimo: 0,
      control_por_rollos: false,
    });
    setEditingItem(null);
  };

  const handleOpenDialog = (item = null) => {
    if (item) {
      setEditingItem(item);
      setFormData({
        codigo: item.codigo,
        nombre: item.nombre,
        descripcion: item.descripcion || '',
        categoria: item.categoria || 'Otros',
        unidad_medida: item.unidad_medida || 'unidad',
        stock_minimo: item.stock_minimo || 0,
        control_por_rollos: item.control_por_rollos || false,
      });
    } else {
      resetForm();
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingItem) {
        await axios.put(`${API}/inventario/${editingItem.id}`, formData);
        toast.success('Item actualizado');
      } else {
        await axios.post(`${API}/inventario`, formData);
        toast.success('Item creado');
      }
      setDialogOpen(false);
      resetForm();
      fetchItems();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const getCategoriaColor = (categoria) => {
    switch (categoria) {
      case 'Telas': return 'bg-blue-500';
      case 'Avios': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar este item? También se eliminarán sus movimientos.')) return;
    try {
      await axios.delete(`${API}/inventario/${id}`);
      toast.success('Item eliminado');
      fetchItems();
    } catch (error) {
      toast.error('Error al eliminar');
    }
  };

  const getStockStatus = (item) => {
    if (item.stock_actual <= 0) return 'destructive';
    if (item.stock_actual <= item.stock_minimo) return 'warning';
    return 'success';
  };

  const getStockLabel = (item) => {
    if (item.stock_actual <= 0) return 'Sin stock';
    if (item.stock_actual <= item.stock_minimo) return 'Stock bajo';
    return 'OK';
  };

  return (
    <div className="space-y-6" data-testid="inventario-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Inventario</h2>
          <p className="text-muted-foreground">Gestión de items de inventario (FIFO)</p>
        </div>
        <div className="flex gap-2">
          <ExportButton tabla="inventario" />
          <Button onClick={() => handleOpenDialog()} data-testid="btn-nuevo-item">
            <Plus className="h-4 w-4 mr-2" />
            Nuevo Item
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="data-table-header">
                  <TableHead>Código</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Categoría</TableHead>
                  <TableHead>Unidad</TableHead>
                  <TableHead className="text-right">Stock Actual</TableHead>
                  <TableHead className="text-right">Stock Mínimo</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="w-[100px]">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8">
                      Cargando...
                    </TableCell>
                  </TableRow>
                ) : items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      No hay items en el inventario
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((item) => (
                    <TableRow key={item.id} className="data-table-row" data-testid={`item-row-${item.id}`}>
                      <TableCell className="font-mono font-medium">{item.codigo}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Package className="h-4 w-4 text-muted-foreground" />
                          <div>
                            {item.nombre}
                            {item.control_por_rollos && (
                              <Badge variant="outline" className="ml-2 text-xs">
                                <Layers className="h-3 w-3 mr-1" />
                                Rollos
                              </Badge>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={getCategoriaColor(item.categoria)}>
                          {item.categoria || 'Otros'}
                        </Badge>
                      </TableCell>
                      <TableCell className="capitalize">{item.unidad_medida}</TableCell>
                      <TableCell className="text-right font-mono font-semibold">
                        {item.stock_actual}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {item.stock_minimo}
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant={getStockStatus(item) === 'success' ? 'default' : getStockStatus(item)}
                          className={getStockStatus(item) === 'success' ? 'bg-green-600' : getStockStatus(item) === 'warning' ? 'bg-yellow-500' : ''}
                        >
                          {item.stock_actual <= item.stock_minimo && item.stock_actual > 0 && (
                            <AlertTriangle className="h-3 w-3 mr-1" />
                          )}
                          {getStockLabel(item)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleOpenDialog(item)}
                            title="Editar"
                            data-testid={`edit-item-${item.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(item.id)}
                            title="Eliminar"
                            data-testid={`delete-item-${item.id}`}
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
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingItem ? 'Editar Item' : 'Nuevo Item'}</DialogTitle>
            <DialogDescription>
              {editingItem ? 'Modifica los datos del item' : 'Agrega un nuevo item al inventario'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="codigo">Código *</Label>
                  <Input
                    id="codigo"
                    value={formData.codigo}
                    onChange={(e) => setFormData({ ...formData, codigo: e.target.value })}
                    placeholder="COD-001"
                    required
                    className="font-mono"
                    data-testid="input-codigo"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Categoría</Label>
                  <Select
                    value={formData.categoria}
                    onValueChange={(value) => setFormData({ 
                      ...formData, 
                      categoria: value,
                      control_por_rollos: value !== 'Telas' ? false : formData.control_por_rollos
                    })}
                  >
                    <SelectTrigger data-testid="select-categoria">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIAS.map((c) => (
                        <SelectItem key={c} value={c}>
                          {c}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre *</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Nombre del item"
                  required
                  data-testid="input-nombre"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="unidad_medida">Unidad de Medida</Label>
                  <Select
                    value={formData.unidad_medida}
                    onValueChange={(value) => setFormData({ ...formData, unidad_medida: value })}
                  >
                    <SelectTrigger data-testid="select-unidad">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {UNIDADES.map((u) => (
                        <SelectItem key={u} value={u} className="capitalize">
                          {u}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="stock_minimo">Stock Mínimo</Label>
                  <Input
                    id="stock_minimo"
                    type="number"
                    min="0"
                    value={formData.stock_minimo}
                    onChange={(e) => setFormData({ ...formData, stock_minimo: parseFloat(e.target.value) || 0 })}
                    placeholder="0"
                    className="font-mono"
                    data-testid="input-stock-minimo"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="descripcion">Descripción</Label>
                <Textarea
                  id="descripcion"
                  value={formData.descripcion}
                  onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                  placeholder="Descripción del item..."
                  rows={2}
                  data-testid="input-descripcion"
                />
              </div>
              
              {formData.categoria === 'Telas' && (
                <div className="flex items-center space-x-2 p-3 border rounded-lg bg-muted/30">
                  <Checkbox
                    id="control_por_rollos"
                    checked={formData.control_por_rollos}
                    onCheckedChange={(checked) => setFormData({ ...formData, control_por_rollos: checked })}
                    data-testid="checkbox-rollos"
                  />
                  <div>
                    <Label htmlFor="control_por_rollos" className="cursor-pointer">
                      Control por Rollos
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      Permite registrar cada rollo con su metraje, ancho y tono individual
                    </p>
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" data-testid="btn-guardar-item">
                {editingItem ? 'Actualizar' : 'Crear'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

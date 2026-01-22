import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
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
import { Plus, Trash2, ArrowUpCircle, Link2, Layers } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const InventarioSalidas = () => {
  const [salidas, setSalidas] = useState([]);
  const [items, setItems] = useState([]);
  const [registros, setRegistros] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [rollosDisponibles, setRollosDisponibles] = useState([]);
  const [selectedRollo, setSelectedRollo] = useState(null);
  const [formData, setFormData] = useState({
    item_id: '',
    cantidad: 1,
    registro_id: '',
    rollo_id: '',
    observaciones: '',
  });

  const fetchData = async () => {
    try {
      const [salidasRes, itemsRes, registrosRes] = await Promise.all([
        axios.get(`${API}/inventario-salidas`),
        axios.get(`${API}/inventario`),
        axios.get(`${API}/registros`),
      ]);
      setSalidas(salidasRes.data);
      setItems(itemsRes.data);
      setRegistros(registrosRes.data);
    } catch (error) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const resetForm = () => {
    setFormData({
      item_id: '',
      cantidad: 1,
      registro_id: '',
      rollo_id: '',
      observaciones: '',
    });
    setSelectedItem(null);
    setRollosDisponibles([]);
    setSelectedRollo(null);
  };

  const handleOpenDialog = () => {
    resetForm();
    setDialogOpen(true);
  };

  const handleItemChange = async (itemId) => {
    const item = items.find(i => i.id === itemId);
    setSelectedItem(item);
    setSelectedRollo(null);
    setFormData({ ...formData, item_id: itemId, rollo_id: '', cantidad: 1 });
    
    // Si tiene control por rollos, cargar rollos disponibles
    if (item?.control_por_rollos) {
      try {
        const response = await axios.get(`${API}/inventario-rollos?item_id=${itemId}&activo=true`);
        setRollosDisponibles(response.data.filter(r => r.metraje_disponible > 0));
      } catch (error) {
        console.error('Error loading rollos:', error);
        setRollosDisponibles([]);
      }
    } else {
      setRollosDisponibles([]);
    }
  };

  const handleRolloChange = (rolloId) => {
    const rollo = rollosDisponibles.find(r => r.id === rolloId);
    setSelectedRollo(rollo);
    setFormData({ ...formData, rollo_id: rolloId, cantidad: 1 });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...formData };
      if (!payload.registro_id) {
        delete payload.registro_id;
      }
      if (!payload.rollo_id) {
        delete payload.rollo_id;
      }
      await axios.post(`${API}/inventario-salidas`, payload);
      toast.success('Salida registrada');
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar esta salida? Se restaurará el stock.')) return;
    try {
      await axios.delete(`${API}/inventario-salidas/${id}`);
      toast.success('Salida eliminada');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN',
    }).format(value);
  };

  return (
    <div className="space-y-6" data-testid="salidas-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Salidas de Inventario</h2>
          <p className="text-muted-foreground">Registro de salidas con método FIFO</p>
        </div>
        <Button onClick={handleOpenDialog} data-testid="btn-nueva-salida">
          <Plus className="h-4 w-4 mr-2" />
          Nueva Salida
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="data-table-header">
                  <TableHead>Fecha</TableHead>
                  <TableHead>Código</TableHead>
                  <TableHead>Item</TableHead>
                  <TableHead>Rollo</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead className="text-right">Costo FIFO</TableHead>
                  <TableHead>Registro Vinculado</TableHead>
                  <TableHead className="w-[80px]">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8">
                      Cargando...
                    </TableCell>
                  </TableRow>
                ) : salidas.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      No hay salidas registradas
                    </TableCell>
                  </TableRow>
                ) : (
                  salidas.map((salida) => (
                    <TableRow key={salida.id} className="data-table-row" data-testid={`salida-row-${salida.id}`}>
                      <TableCell className="font-mono text-sm">
                        {formatDate(salida.fecha)}
                      </TableCell>
                      <TableCell className="font-mono">{salida.item_codigo}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <ArrowUpCircle className="h-4 w-4 text-red-500" />
                          {salida.item_nombre}
                        </div>
                      </TableCell>
                      <TableCell>
                        {salida.rollo_numero ? (
                          <Badge variant="outline" className="gap-1">
                            <Layers className="h-3 w-3" />
                            {salida.rollo_numero}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono font-semibold">
                        {salida.cantidad}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(salida.costo_total)}
                      </TableCell>
                      <TableCell>
                        {salida.registro_n_corte ? (
                          <Badge variant="outline" className="gap-1">
                            <Link2 className="h-3 w-3" />
                            Corte #{salida.registro_n_corte}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(salida.id)}
                          title="Eliminar"
                          data-testid={`delete-salida-${salida.id}`}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
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
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Nueva Salida</DialogTitle>
            <DialogDescription>
              Registrar una salida de inventario (FIFO)
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Item *</Label>
                <Select
                  value={formData.item_id}
                  onValueChange={handleItemChange}
                  required
                >
                  <SelectTrigger data-testid="select-item">
                    <SelectValue placeholder="Seleccionar item..." />
                  </SelectTrigger>
                  <SelectContent>
                    {items.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        <span className="font-mono mr-2">{item.codigo}</span>
                        {item.nombre}
                        <span className="ml-2 text-muted-foreground">(Stock: {item.stock_actual})</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedItem && (
                  <p className="text-sm text-muted-foreground">
                    Stock disponible: <span className="font-mono font-semibold">{selectedItem.stock_actual}</span> {selectedItem.unidad_medida}
                  </p>
                )}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="cantidad">Cantidad *</Label>
                <Input
                  id="cantidad"
                  type="number"
                  min="1"
                  max={selectedItem?.stock_actual || 999999}
                  value={formData.cantidad}
                  onChange={(e) => setFormData({ ...formData, cantidad: parseInt(e.target.value) || 1 })}
                  required
                  className="font-mono"
                  data-testid="input-cantidad"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Vincular a Registro (opcional)</Label>
                <Select
                  value={formData.registro_id || "none"}
                  onValueChange={(value) => setFormData({ ...formData, registro_id: value === "none" ? "" : value })}
                >
                  <SelectTrigger data-testid="select-registro">
                    <SelectValue placeholder="Sin vincular" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sin vincular</SelectItem>
                    {registros.map((reg) => (
                      <SelectItem key={reg.id} value={reg.id}>
                        <span className="font-mono mr-2">#{reg.n_corte}</span>
                        {reg.modelo_nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Vincula esta salida a un registro de producción
                </p>
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
              <Button type="submit" data-testid="btn-guardar-salida">
                Registrar Salida
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

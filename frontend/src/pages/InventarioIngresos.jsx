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
import { Plus, Trash2, ArrowDownCircle, Layers, Pencil } from 'lucide-react';
import { toast } from 'sonner';
import { formatDate } from '../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const InventarioIngresos = () => {
  const [ingresos, setIngresos] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingIngreso, setEditingIngreso] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [formData, setFormData] = useState({
    item_id: '',
    cantidad: 0,
    costo_unitario: 0,
    proveedor: '',
    numero_documento: '',
    observaciones: '',
  });
  // Rollos para items con control_por_rollos
  const [rollos, setRollos] = useState([]);

  const fetchData = async () => {
    try {
      const [ingresosRes, itemsRes] = await Promise.all([
        axios.get(`${API}/inventario-ingresos`),
        axios.get(`${API}/inventario`),
      ]);
      setIngresos(ingresosRes.data);
      setItems(itemsRes.data);
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
      cantidad: 0,
      costo_unitario: 0,
      proveedor: '',
      numero_documento: '',
      observaciones: '',
    });
    setSelectedItem(null);
    setRollos([]);
  };

  const handleItemChange = (itemId) => {
    const item = items.find(i => i.id === itemId);
    setSelectedItem(item);
    setFormData({ ...formData, item_id: itemId, cantidad: 0 });
    setRollos([]);
  };

  const addRollo = () => {
    setRollos([...rollos, {
      numero_rollo: '',
      metraje: 0,
      ancho: 0,
      tono: '',
    }]);
  };

  const updateRollo = (index, field, value) => {
    const newRollos = [...rollos];
    newRollos[index][field] = value;
    setRollos(newRollos);
    
    // Actualizar cantidad total
    if (field === 'metraje') {
      const totalMetraje = newRollos.reduce((sum, r) => sum + (parseFloat(r.metraje) || 0), 0);
      setFormData({ ...formData, cantidad: totalMetraje });
    }
  };

  const removeRollo = (index) => {
    const newRollos = rollos.filter((_, i) => i !== index);
    setRollos(newRollos);
    const totalMetraje = newRollos.reduce((sum, r) => sum + (parseFloat(r.metraje) || 0), 0);
    setFormData({ ...formData, cantidad: totalMetraje });
  };

  const handleOpenDialog = () => {
    setEditingIngreso(null);
    resetForm();
    setDialogOpen(true);
  };

  const handleOpenEdit = (ingreso) => {
    setEditingIngreso(ingreso);
    const item = items.find(i => i.id === ingreso.item_id);
    setSelectedItem(item);
    setFormData({
      item_id: ingreso.item_id,
      cantidad: ingreso.cantidad,
      costo_unitario: ingreso.costo_unitario,
      proveedor: ingreso.proveedor || '',
      numero_documento: ingreso.numero_documento || '',
      observaciones: ingreso.observaciones || '',
    });
    setRollos([]);
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...formData };
      // Si es item con control por rollos, incluir rollos
      if (selectedItem?.control_por_rollos && rollos.length > 0) {
        payload.rollos = rollos.map(r => ({
          ...r,
          metraje: parseFloat(r.metraje) || 0,
          ancho: parseFloat(r.ancho) || 0,
        }));
      }
      
      if (editingIngreso) {
        // Solo permitir editar campos no relacionados con cantidad
        await axios.put(`${API}/inventario-ingresos/${editingIngreso.id}`, {
          proveedor: formData.proveedor,
          numero_documento: formData.numero_documento,
          observaciones: formData.observaciones,
          costo_unitario: formData.costo_unitario,
        });
        toast.success('Ingreso actualizado');
      } else {
        await axios.post(`${API}/inventario-ingresos`, payload);
        toast.success('Ingreso registrado');
      }
      setDialogOpen(false);
      resetForm();
      setEditingIngreso(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar este ingreso?')) return;
    try {
      await axios.delete(`${API}/inventario-ingresos/${id}`);
      toast.success('Ingreso eliminado');
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
    <div className="space-y-6" data-testid="ingresos-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Ingresos de Inventario</h2>
          <p className="text-muted-foreground">Registro de entradas al inventario</p>
        </div>
        <Button onClick={handleOpenDialog} data-testid="btn-nuevo-ingreso">
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Ingreso
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
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead className="text-right">Disponible</TableHead>
                  <TableHead className="text-right">Costo Unit.</TableHead>
                  <TableHead>Proveedor</TableHead>
                  <TableHead>N° Doc.</TableHead>
                  <TableHead className="w-[80px]">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8">
                      Cargando...
                    </TableCell>
                  </TableRow>
                ) : ingresos.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      No hay ingresos registrados
                    </TableCell>
                  </TableRow>
                ) : (
                  ingresos.map((ingreso) => (
                    <TableRow key={ingreso.id} className="data-table-row" data-testid={`ingreso-row-${ingreso.id}`}>
                      <TableCell className="font-mono text-sm">
                        {formatDate(ingreso.fecha)}
                      </TableCell>
                      <TableCell className="font-mono">{ingreso.item_codigo}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <ArrowDownCircle className="h-4 w-4 text-green-600" />
                          <div>
                            {ingreso.item_nombre}
                            {ingreso.rollos_count > 0 && (
                              <Badge variant="outline" className="ml-2 text-xs">
                                <Layers className="h-3 w-3 mr-1" />
                                {ingreso.rollos_count} rollos
                              </Badge>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono font-semibold">
                        {ingreso.cantidad}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        <span className={ingreso.cantidad_disponible < ingreso.cantidad ? 'text-orange-500' : 'text-green-600'}>
                          {ingreso.cantidad_disponible}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(ingreso.costo_unitario)}
                      </TableCell>
                      <TableCell>{ingreso.proveedor || '-'}</TableCell>
                      <TableCell className="font-mono">{ingreso.numero_documento || '-'}</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleOpenEdit(ingreso)}
                            title="Editar"
                            data-testid={`edit-ingreso-${ingreso.id}`}
                          >
                            <Pencil className="h-4 w-4 text-blue-500" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(ingreso.id)}
                            title={ingreso.cantidad_disponible !== ingreso.cantidad ? "No se puede eliminar: tiene salidas" : "Eliminar"}
                            disabled={ingreso.cantidad_disponible !== ingreso.cantidad}
                            data-testid={`delete-ingreso-${ingreso.id}`}
                          >
                            <Trash2 className={`h-4 w-4 ${ingreso.cantidad_disponible !== ingreso.cantidad ? 'text-gray-300' : 'text-destructive'}`} />
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

      <Dialog open={dialogOpen} onOpenChange={(open) => {
        setDialogOpen(open);
        if (!open) setEditingIngreso(null);
      }}>
        <DialogContent className={selectedItem?.control_por_rollos && !editingIngreso ? "max-w-3xl max-h-[90vh] overflow-y-auto" : "max-w-lg"}>
          <DialogHeader>
            <DialogTitle>{editingIngreso ? 'Editar Ingreso' : 'Nuevo Ingreso'}</DialogTitle>
            <DialogDescription>
              {editingIngreso ? 'Modificar datos del ingreso' : 'Registrar una entrada de inventario'}
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
                        {item.control_por_rollos && (
                          <Badge variant="outline" className="ml-2 text-xs">Rollos</Badge>
                        )}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Si el item tiene control por rollos */}
              {selectedItem?.control_por_rollos ? (
                <>
                  <div className="border rounded-lg p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Layers className="h-5 w-5 text-primary" />
                        <Label className="text-base font-semibold">Rollos</Label>
                      </div>
                      <Button type="button" size="sm" onClick={addRollo} data-testid="btn-agregar-rollo">
                        <Plus className="h-4 w-4 mr-1" />
                        Agregar Rollo
                      </Button>
                    </div>
                    
                    {rollos.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        Agrega rollos para este ingreso
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {rollos.map((rollo, index) => (
                          <div key={index} className="grid grid-cols-12 gap-2 items-end p-3 border rounded-lg bg-muted/30">
                            <div className="col-span-3">
                              <Label className="text-xs">N° Rollo</Label>
                              <Input
                                value={rollo.numero_rollo}
                                onChange={(e) => updateRollo(index, 'numero_rollo', e.target.value)}
                                placeholder="R001"
                                className="font-mono"
                                data-testid={`rollo-${index}-numero`}
                              />
                            </div>
                            <div className="col-span-2">
                              <Label className="text-xs">Metraje (m)</Label>
                              <Input
                                type="number"
                                step="0.01"
                                min="0"
                                value={rollo.metraje}
                                onChange={(e) => updateRollo(index, 'metraje', e.target.value)}
                                className="font-mono"
                                data-testid={`rollo-${index}-metraje`}
                              />
                            </div>
                            <div className="col-span-2">
                              <Label className="text-xs">Ancho (cm)</Label>
                              <Input
                                type="number"
                                step="0.1"
                                min="0"
                                value={rollo.ancho}
                                onChange={(e) => updateRollo(index, 'ancho', e.target.value)}
                                className="font-mono"
                                data-testid={`rollo-${index}-ancho`}
                              />
                            </div>
                            <div className="col-span-4">
                              <Label className="text-xs">Tono</Label>
                              <Input
                                value={rollo.tono}
                                onChange={(e) => updateRollo(index, 'tono', e.target.value)}
                                placeholder="Ej: Claro, Oscuro, Lote A"
                                data-testid={`rollo-${index}-tono`}
                              />
                            </div>
                            <div className="col-span-1">
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                onClick={() => removeRollo(index)}
                                data-testid={`rollo-${index}-eliminar`}
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    <div className="flex justify-between items-center pt-2 border-t">
                      <span className="text-sm text-muted-foreground">Total Metraje:</span>
                      <span className="font-mono font-bold text-lg">{formData.cantidad.toFixed(2)} m</span>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="costo_unitario">Costo por Metro</Label>
                    <Input
                      id="costo_unitario"
                      type="number"
                      min="0"
                      step="0.01"
                      value={formData.costo_unitario}
                      onChange={(e) => setFormData({ ...formData, costo_unitario: parseFloat(e.target.value) || 0 })}
                      className="font-mono"
                      data-testid="input-costo"
                    />
                  </div>
                </>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="cantidad">Cantidad *</Label>
                    <Input
                      id="cantidad"
                      type="number"
                      min="0.01"
                      step="0.01"
                      value={formData.cantidad}
                      onChange={(e) => setFormData({ ...formData, cantidad: parseFloat(e.target.value) || 0 })}
                      required
                      className="font-mono"
                      data-testid="input-cantidad"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="costo_unitario">Costo Unitario</Label>
                    <Input
                      id="costo_unitario"
                      type="number"
                      min="0"
                      step="0.01"
                      value={formData.costo_unitario}
                      onChange={(e) => setFormData({ ...formData, costo_unitario: parseFloat(e.target.value) || 0 })}
                      className="font-mono"
                      data-testid="input-costo"
                    />
                  </div>
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="proveedor">Proveedor</Label>
                  <Input
                    id="proveedor"
                    value={formData.proveedor}
                    onChange={(e) => setFormData({ ...formData, proveedor: e.target.value })}
                    placeholder="Nombre del proveedor"
                    data-testid="input-proveedor"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="numero_documento">N° Documento</Label>
                  <Input
                    id="numero_documento"
                    value={formData.numero_documento}
                    onChange={(e) => setFormData({ ...formData, numero_documento: e.target.value })}
                    placeholder="Factura, guía, etc."
                    className="font-mono"
                    data-testid="input-documento"
                  />
                </div>
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
              <Button type="submit" data-testid="btn-guardar-ingreso">
                Registrar Ingreso
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

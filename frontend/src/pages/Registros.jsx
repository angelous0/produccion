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
import { Separator } from '../components/ui/separator';
import { Plus, Pencil, Trash2, AlertTriangle, Eye } from 'lucide-react';
import { toast } from 'sonner';
import { getStatusClass } from '../lib/utils';
import { ProductionMatrix } from '../components/ProductionMatrix';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const Registros = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [viewingItem, setViewingItem] = useState(null);
  const [formData, setFormData] = useState({
    n_corte: '',
    modelo_id: '',
    curva: '',
    estado: 'Para Corte',
    urgente: false,
  });

  // Datos para la matriz
  const [tallas, setTallas] = useState([]);
  const [colores, setColores] = useState([]);
  const [matriz, setMatriz] = useState([]);

  // Datos relacionados
  const [modelos, setModelos] = useState([]);
  const [estados, setEstados] = useState([]);

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API}/registros`);
      setItems(response.data);
    } catch (error) {
      toast.error('Error al cargar registros');
    } finally {
      setLoading(false);
    }
  };

  const fetchRelatedData = async () => {
    try {
      const [modelosRes, estadosRes] = await Promise.all([
        axios.get(`${API}/modelos`),
        axios.get(`${API}/estados`),
      ]);
      setModelos(modelosRes.data);
      setEstados(estadosRes.data.estados);
    } catch (error) {
      toast.error('Error al cargar datos relacionados');
    }
  };

  useEffect(() => {
    fetchItems();
    fetchRelatedData();
  }, []);

  // Funciones para manejar la matriz
  const handleAddTalla = () => {
    const newTalla = `T${tallas.length + 1}`;
    setTallas([...tallas, newTalla]);
    // Añadir columna vacía a la matriz
    const newMatriz = matriz.length > 0 
      ? [...matriz, { talla: newTalla, colores: colores.map(c => ({ color: c, cantidad: 0 })) }]
      : [{ talla: newTalla, colores: colores.map(c => ({ color: c, cantidad: 0 })) }];
    setMatriz(newMatriz);
  };

  const handleRemoveTalla = (index) => {
    const newTallas = tallas.filter((_, i) => i !== index);
    const newMatriz = matriz.filter((_, i) => i !== index);
    setTallas(newTallas);
    setMatriz(newMatriz);
  };

  const handleAddColor = () => {
    const newColor = `Color ${colores.length + 1}`;
    setColores([...colores, newColor]);
    // Añadir fila a cada columna de la matriz
    const newMatriz = matriz.map((talla, i) => ({
      ...talla,
      colores: [...(talla.colores || []), { color: newColor, cantidad: 0 }]
    }));
    setMatriz(newMatriz);
  };

  const handleRemoveColor = (index) => {
    const newColores = colores.filter((_, i) => i !== index);
    const newMatriz = matriz.map(talla => ({
      ...talla,
      colores: (talla.colores || []).filter((_, i) => i !== index)
    }));
    setColores(newColores);
    setMatriz(newMatriz);
  };

  const handleTallaNameChange = (index, value) => {
    const newTallas = [...tallas];
    newTallas[index] = value;
    setTallas(newTallas);
    
    const newMatriz = [...matriz];
    if (newMatriz[index]) {
      newMatriz[index].talla = value;
    }
    setMatriz(newMatriz);
  };

  const handleColorNameChange = (index, value) => {
    const newColores = [...colores];
    newColores[index] = value;
    setColores(newColores);
    
    const newMatriz = matriz.map(talla => ({
      ...talla,
      colores: (talla.colores || []).map((c, i) => 
        i === index ? { ...c, color: value } : c
      )
    }));
    setMatriz(newMatriz);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        matriz_tallas_colores: matriz,
      };
      
      if (editingItem) {
        await axios.put(`${API}/registros/${editingItem.id}`, payload);
        toast.success('Registro actualizado');
      } else {
        await axios.post(`${API}/registros`, payload);
        toast.success('Registro creado');
      }
      setDialogOpen(false);
      resetForm();
      fetchItems();
    } catch (error) {
      toast.error('Error al guardar registro');
    }
  };

  const resetForm = () => {
    setEditingItem(null);
    setFormData({
      n_corte: '',
      modelo_id: '',
      curva: '',
      estado: 'Para Corte',
      urgente: false,
    });
    setTallas([]);
    setColores([]);
    setMatriz([]);
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({
      n_corte: item.n_corte,
      modelo_id: item.modelo_id,
      curva: item.curva || '',
      estado: item.estado,
      urgente: item.urgente,
    });
    
    // Reconstruir tallas, colores y matriz desde los datos guardados
    const matrizData = item.matriz_tallas_colores || [];
    const tallasData = matrizData.map(t => t.talla);
    const coloresData = matrizData.length > 0 && matrizData[0].colores 
      ? matrizData[0].colores.map(c => c.color)
      : [];
    
    setTallas(tallasData);
    setColores(coloresData);
    setMatriz(matrizData);
    setDialogOpen(true);
  };

  const handleView = (item) => {
    setViewingItem(item);
    setViewDialogOpen(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar este registro?')) return;
    try {
      await axios.delete(`${API}/registros/${id}`);
      toast.success('Registro eliminado');
      fetchItems();
    } catch (error) {
      toast.error('Error al eliminar registro');
    }
  };

  const handleNew = () => {
    resetForm();
    setDialogOpen(true);
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  // Calcular total de piezas de un registro
  const getTotalPiezas = (registro) => {
    if (!registro.matriz_tallas_colores) return 0;
    return registro.matriz_tallas_colores.reduce((sum, talla) => {
      if (!talla.colores) return sum;
      return sum + talla.colores.reduce((s, c) => s + (c.cantidad || 0), 0);
    }, 0);
  };

  return (
    <div className="space-y-6" data-testid="registros-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Registros de Producción</h2>
          <p className="text-muted-foreground">Gestión de registros de corte y producción</p>
        </div>
        <Button onClick={handleNew} data-testid="btn-nuevo-registro">
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Registro
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="data-table-header">
                  <TableHead>N° Corte</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Modelo</TableHead>
                  <TableHead>Marca</TableHead>
                  <TableHead>Curva</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Piezas</TableHead>
                  <TableHead className="w-[120px]">Acciones</TableHead>
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
                      No hay registros
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((item) => (
                    <TableRow key={item.id} className="data-table-row" data-testid={`registro-row-${item.id}`}>
                      <TableCell className="font-mono font-medium">
                        <div className="flex items-center gap-2">
                          {item.urgente && (
                            <AlertTriangle className="h-4 w-4 text-destructive badge-urgent" />
                          )}
                          {item.n_corte}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {formatDate(item.fecha_creacion)}
                      </TableCell>
                      <TableCell>{item.modelo_nombre || '-'}</TableCell>
                      <TableCell>{item.marca_nombre || '-'}</TableCell>
                      <TableCell className="font-mono">{item.curva || '-'}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`${getStatusClass(item.estado)} whitespace-nowrap`}>
                          {item.estado}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono font-semibold">
                        {getTotalPiezas(item)}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleView(item)}
                            data-testid={`view-registro-${item.id}`}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(item)}
                            data-testid={`edit-registro-${item.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(item.id)}
                            data-testid={`delete-registro-${item.id}`}
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

      {/* Dialog para crear/editar */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingItem ? 'Editar Registro' : 'Nuevo Registro'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-6 py-4">
              {/* Información General */}
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">
                  Información General
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="n_corte">N° Corte</Label>
                    <Input
                      id="n_corte"
                      value={formData.n_corte}
                      onChange={(e) => setFormData({ ...formData, n_corte: e.target.value })}
                      placeholder="Número de corte"
                      required
                      className="font-mono"
                      data-testid="input-n-corte"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Modelo</Label>
                    <Select
                      value={formData.modelo_id}
                      onValueChange={(value) => setFormData({ ...formData, modelo_id: value })}
                    >
                      <SelectTrigger data-testid="select-modelo">
                        <SelectValue placeholder="Seleccionar modelo" />
                      </SelectTrigger>
                      <SelectContent>
                        {modelos.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.nombre} - {m.marca_nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="curva">Curva</Label>
                    <Input
                      id="curva"
                      value={formData.curva}
                      onChange={(e) => setFormData({ ...formData, curva: e.target.value })}
                      placeholder="Curva"
                      className="font-mono"
                      data-testid="input-curva"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Estado</Label>
                    <Select
                      value={formData.estado}
                      onValueChange={(value) => setFormData({ ...formData, estado: value })}
                    >
                      <SelectTrigger data-testid="select-estado">
                        <SelectValue placeholder="Seleccionar estado" />
                      </SelectTrigger>
                      <SelectContent>
                        {estados.map((e) => (
                          <SelectItem key={e} value={e}>
                            {e}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex items-center space-x-2 mt-4">
                  <Checkbox
                    id="urgente"
                    checked={formData.urgente}
                    onCheckedChange={(checked) => setFormData({ ...formData, urgente: checked })}
                    data-testid="checkbox-urgente"
                  />
                  <Label htmlFor="urgente" className="flex items-center gap-2 cursor-pointer">
                    <AlertTriangle className="h-4 w-4 text-destructive" />
                    Marcar como Urgente
                  </Label>
                </div>
              </div>

              <Separator />

              {/* Matriz de Tallas y Colores */}
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">
                  Tallas y Colores
                </h3>
                <ProductionMatrix
                  tallas={tallas}
                  colores={colores}
                  matriz={matriz}
                  onMatrizChange={setMatriz}
                  onAddTalla={handleAddTalla}
                  onRemoveTalla={handleRemoveTalla}
                  onAddColor={handleAddColor}
                  onRemoveColor={handleRemoveColor}
                  onTallaNameChange={handleTallaNameChange}
                  onColorNameChange={handleColorNameChange}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" data-testid="btn-guardar-registro">
                {editingItem ? 'Actualizar' : 'Crear'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dialog para ver detalle */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Detalle del Registro</DialogTitle>
          </DialogHeader>
          {viewingItem && (
            <div className="space-y-6 py-4">
              {/* Info del registro */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {viewingItem.urgente && (
                      <AlertTriangle className="h-5 w-5 text-destructive badge-urgent" />
                    )}
                    Corte #{viewingItem.n_corte}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Fecha:</span>
                      <p className="font-mono">{formatDate(viewingItem.fecha_creacion)}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Modelo:</span>
                      <p className="font-medium">{viewingItem.modelo_nombre || '-'}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Marca:</span>
                      <p>{viewingItem.marca_nombre || '-'}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Tipo:</span>
                      <p>{viewingItem.tipo_nombre || '-'}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Entalle:</span>
                      <p>{viewingItem.entalle_nombre || '-'}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Tela:</span>
                      <p>{viewingItem.tela_nombre || '-'}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Hilo:</span>
                      <p>{viewingItem.hilo_nombre || '-'}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Curva:</span>
                      <p className="font-mono">{viewingItem.curva || '-'}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Estado:</span>
                      <p>
                        <Badge variant="outline" className={getStatusClass(viewingItem.estado)}>
                          {viewingItem.estado}
                        </Badge>
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Total Piezas:</span>
                      <p className="font-mono font-bold text-lg">{getTotalPiezas(viewingItem)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Matriz de cantidades (solo lectura) */}
              {viewingItem.matriz_tallas_colores && viewingItem.matriz_tallas_colores.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Distribución por Talla y Color</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse text-sm">
                        <thead>
                          <tr>
                            <th className="bg-muted/50 p-2 border text-left font-semibold">Color</th>
                            {viewingItem.matriz_tallas_colores.map((t, i) => (
                              <th key={i} className="bg-muted/50 p-2 border text-center font-semibold">
                                {t.talla}
                              </th>
                            ))}
                            <th className="bg-muted/70 p-2 border text-center font-semibold">Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {viewingItem.matriz_tallas_colores[0]?.colores?.map((_, colorIndex) => (
                            <tr key={colorIndex}>
                              <td className="bg-muted/30 p-2 border font-medium">
                                {viewingItem.matriz_tallas_colores[0].colores[colorIndex]?.color}
                              </td>
                              {viewingItem.matriz_tallas_colores.map((talla, tallaIndex) => (
                                <td key={tallaIndex} className="p-2 border text-center font-mono">
                                  {talla.colores?.[colorIndex]?.cantidad || 0}
                                </td>
                              ))}
                              <td className="bg-muted/50 p-2 border text-center font-mono font-semibold">
                                {viewingItem.matriz_tallas_colores.reduce((sum, t) => 
                                  sum + (t.colores?.[colorIndex]?.cantidad || 0), 0
                                )}
                              </td>
                            </tr>
                          ))}
                          <tr>
                            <td className="bg-muted/70 p-2 border font-semibold">Total</td>
                            {viewingItem.matriz_tallas_colores.map((talla, i) => (
                              <td key={i} className="bg-muted/50 p-2 border text-center font-mono font-semibold">
                                {talla.colores?.reduce((sum, c) => sum + (c.cantidad || 0), 0) || 0}
                              </td>
                            ))}
                            <td className="bg-primary/10 p-2 border text-center font-mono font-bold text-primary">
                              {getTotalPiezas(viewingItem)}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setViewDialogOpen(false)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

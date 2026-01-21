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
import { Plus, Pencil, Trash2, AlertTriangle, Eye, Palette, X } from 'lucide-react';
import { toast } from 'sonner';
import { getStatusClass } from '../lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const Registros = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [coloresDialogOpen, setColoresDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [viewingItem, setViewingItem] = useState(null);
  const [colorEditItem, setColorEditItem] = useState(null);
  
  const [formData, setFormData] = useState({
    n_corte: '',
    modelo_id: '',
    curva: '',
    estado: 'Para Corte',
    urgente: false,
  });

  // Datos para tallas seleccionadas
  const [tallasSeleccionadas, setTallasSeleccionadas] = useState([]);
  
  // Datos para distribución de colores - matriz [colorIndex][tallaIndex] = cantidad
  const [coloresSeleccionados, setColoresSeleccionados] = useState([]);
  const [matrizCantidades, setMatrizCantidades] = useState({});

  // Datos del catálogo
  const [tallasCatalogo, setTallasCatalogo] = useState([]);
  const [coloresCatalogo, setColoresCatalogo] = useState([]);
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
      const [modelosRes, estadosRes, tallasRes, coloresRes] = await Promise.all([
        axios.get(`${API}/modelos`),
        axios.get(`${API}/estados`),
        axios.get(`${API}/tallas-catalogo`),
        axios.get(`${API}/colores-catalogo`),
      ]);
      setModelos(modelosRes.data);
      setEstados(estadosRes.data.estados);
      setTallasCatalogo(tallasRes.data);
      setColoresCatalogo(coloresRes.data);
    } catch (error) {
      toast.error('Error al cargar datos relacionados');
    }
  };

  useEffect(() => {
    fetchItems();
    fetchRelatedData();
  }, []);

  // Agregar talla al registro
  const handleAddTalla = (tallaId) => {
    const talla = tallasCatalogo.find(t => t.id === tallaId);
    if (!talla || tallasSeleccionadas.find(t => t.talla_id === tallaId)) return;
    
    setTallasSeleccionadas([...tallasSeleccionadas, {
      talla_id: talla.id,
      talla_nombre: talla.nombre,
      cantidad: 0
    }]);
  };

  // Actualizar cantidad de talla
  const handleTallaCantidadChange = (tallaId, cantidad) => {
    setTallasSeleccionadas(tallasSeleccionadas.map(t => 
      t.talla_id === tallaId ? { ...t, cantidad: parseInt(cantidad) || 0 } : t
    ));
  };

  // Remover talla
  const handleRemoveTalla = (tallaId) => {
    setTallasSeleccionadas(tallasSeleccionadas.filter(t => t.talla_id !== tallaId));
  };

  // ========== LÓGICA DE COLORES ==========

  // Abrir dialog de colores para un registro
  const handleOpenColoresDialog = (item) => {
    setColorEditItem(item);
    
    // Reconstruir colores seleccionados y matriz desde datos guardados
    if (item.distribucion_colores && item.distribucion_colores.length > 0) {
      // Extraer colores únicos
      const coloresUnicos = [];
      const matriz = {};
      
      item.distribucion_colores.forEach(talla => {
        (talla.colores || []).forEach(c => {
          if (!coloresUnicos.find(cu => cu.id === c.color_id)) {
            const colorCat = coloresCatalogo.find(cc => cc.id === c.color_id);
            if (colorCat) {
              coloresUnicos.push(colorCat);
            }
          }
          // Guardar en matriz
          const key = `${c.color_id}_${talla.talla_id}`;
          matriz[key] = c.cantidad;
        });
      });
      
      setColoresSeleccionados(coloresUnicos);
      setMatrizCantidades(matriz);
    } else {
      setColoresSeleccionados([]);
      setMatrizCantidades({});
    }
    
    setColoresDialogOpen(true);
  };

  // Toggle selección de color
  const handleToggleColor = (colorId) => {
    const color = coloresCatalogo.find(c => c.id === colorId);
    if (!color) return;
    
    const existe = coloresSeleccionados.find(c => c.id === colorId);
    
    if (existe) {
      // Remover color y limpiar matriz
      setColoresSeleccionados(coloresSeleccionados.filter(c => c.id !== colorId));
      const nuevaMatriz = { ...matrizCantidades };
      Object.keys(nuevaMatriz).forEach(key => {
        if (key.startsWith(`${colorId}_`)) {
          delete nuevaMatriz[key];
        }
      });
      setMatrizCantidades(nuevaMatriz);
    } else {
      // Agregar color
      const esElPrimero = coloresSeleccionados.length === 0;
      setColoresSeleccionados([...coloresSeleccionados, color]);
      
      // Si es el primer color, asignar todo el total a este color
      if (esElPrimero && colorEditItem?.tallas) {
        const nuevaMatriz = { ...matrizCantidades };
        colorEditItem.tallas.forEach(t => {
          nuevaMatriz[`${colorId}_${t.talla_id}`] = t.cantidad;
        });
        setMatrizCantidades(nuevaMatriz);
      }
    }
  };

  // Obtener cantidad de la matriz
  const getCantidadMatriz = (colorId, tallaId) => {
    return matrizCantidades[`${colorId}_${tallaId}`] || 0;
  };

  // Actualizar cantidad en la matriz
  const handleMatrizChange = (colorId, tallaId, valor) => {
    const cantidad = parseInt(valor) || 0;
    const talla = colorEditItem?.tallas?.find(t => t.talla_id === tallaId);
    
    if (!talla) return;
    
    // Calcular suma actual de otros colores para esta talla
    let sumaOtros = 0;
    coloresSeleccionados.forEach(c => {
      if (c.id !== colorId) {
        sumaOtros += getCantidadMatriz(c.id, tallaId);
      }
    });
    
    // Validar que no exceda el total
    if (cantidad + sumaOtros > talla.cantidad) {
      toast.error(`La suma (${cantidad + sumaOtros}) excede el total de la talla ${talla.talla_nombre} (${talla.cantidad})`);
      return;
    }
    
    setMatrizCantidades({
      ...matrizCantidades,
      [`${colorId}_${tallaId}`]: cantidad
    });
  };

  // Calcular total por color (fila)
  const getTotalColor = (colorId) => {
    let total = 0;
    (colorEditItem?.tallas || []).forEach(t => {
      total += getCantidadMatriz(colorId, t.talla_id);
    });
    return total;
  };

  // Calcular total por talla (columna)
  const getTotalTallaAsignado = (tallaId) => {
    let total = 0;
    coloresSeleccionados.forEach(c => {
      total += getCantidadMatriz(c.id, tallaId);
    });
    return total;
  };

  // Calcular total general asignado
  const getTotalGeneralAsignado = () => {
    let total = 0;
    coloresSeleccionados.forEach(c => {
      total += getTotalColor(c.id);
    });
    return total;
  };

  // Guardar distribución de colores
  const handleSaveColores = async () => {
    try {
      // Construir estructura de distribución
      const distribucion = (colorEditItem?.tallas || []).map(t => ({
        talla_id: t.talla_id,
        talla_nombre: t.talla_nombre,
        cantidad_total: t.cantidad,
        colores: coloresSeleccionados.map(c => ({
          color_id: c.id,
          color_nombre: c.nombre,
          cantidad: getCantidadMatriz(c.id, t.talla_id)
        })).filter(c => c.cantidad > 0) // Solo guardar colores con cantidad > 0
      }));
      
      const payload = {
        n_corte: colorEditItem.n_corte,
        modelo_id: colorEditItem.modelo_id,
        curva: colorEditItem.curva,
        estado: colorEditItem.estado,
        urgente: colorEditItem.urgente,
        tallas: colorEditItem.tallas,
        distribucion_colores: distribucion
      };
      
      await axios.put(`${API}/registros/${colorEditItem.id}`, payload);
      toast.success('Distribución de colores guardada');
      setColoresDialogOpen(false);
      setColorEditItem(null);
      setColoresSeleccionados([]);
      setMatrizCantidades({});
      fetchItems();
    } catch (error) {
      toast.error('Error al guardar distribución de colores');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        tallas: tallasSeleccionadas,
        distribucion_colores: [],
      };
      
      if (editingItem) {
        payload.distribucion_colores = editingItem.distribucion_colores || [];
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
    setTallasSeleccionadas([]);
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
    setTallasSeleccionadas(item.tallas || []);
    setDialogOpen(true);
  };

  const handleView = (item) => {
    setViewingItem(item);
    setViewDialogOpen(true);
  };

  const handleDelete = async (id) => {
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

  const getTotalPiezas = (registro) => {
    if (!registro.tallas) return 0;
    return registro.tallas.reduce((sum, t) => sum + (t.cantidad || 0), 0);
  };

  const tieneColores = (registro) => {
    return registro.distribucion_colores && 
           registro.distribucion_colores.some(t => t.colores && t.colores.length > 0);
  };

  const tallasDisponibles = tallasCatalogo.filter(
    t => !tallasSeleccionadas.find(ts => ts.talla_id === t.id)
  );

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
                  <TableHead className="w-[150px]">Acciones</TableHead>
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
                            title="Ver detalle"
                            data-testid={`view-registro-${item.id}`}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleOpenColoresDialog(item)}
                            title="Distribuir colores"
                            data-testid={`colores-registro-${item.id}`}
                          >
                            <Palette className={`h-4 w-4 ${tieneColores(item) ? 'text-primary' : ''}`} />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(item)}
                            title="Editar"
                            data-testid={`edit-registro-${item.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(item.id)}
                            title="Eliminar"
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

      {/* Dialog para crear/editar - PASO 1: Info general y Tallas */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
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

              {/* Tallas */}
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">
                  Tallas y Cantidades
                </h3>
                
                <div className="flex gap-2 mb-4">
                  <Select onValueChange={handleAddTalla}>
                    <SelectTrigger className="w-[200px]" data-testid="select-agregar-talla">
                      <SelectValue placeholder="Agregar talla..." />
                    </SelectTrigger>
                    <SelectContent>
                      {tallasDisponibles.map((t) => (
                        <SelectItem key={t.id} value={t.id}>
                          {t.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {tallasSeleccionadas.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/50">
                          <TableHead className="font-semibold">Talla</TableHead>
                          <TableHead className="font-semibold w-[150px]">Cantidad</TableHead>
                          <TableHead className="w-[60px]"></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {tallasSeleccionadas.map((t) => (
                          <TableRow key={t.talla_id}>
                            <TableCell className="font-medium">{t.talla_nombre}</TableCell>
                            <TableCell>
                              <Input
                                type="number"
                                min="0"
                                value={t.cantidad || ''}
                                onChange={(e) => handleTallaCantidadChange(t.talla_id, e.target.value)}
                                className="w-full font-mono text-center"
                                placeholder="0"
                                data-testid={`input-cantidad-talla-${t.talla_id}`}
                              />
                            </TableCell>
                            <TableCell>
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                onClick={() => handleRemoveTalla(t.talla_id)}
                                data-testid={`remove-talla-${t.talla_id}`}
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                        <TableRow className="bg-muted/30">
                          <TableCell className="font-semibold">Total</TableCell>
                          <TableCell className="font-mono font-bold text-center">
                            {tallasSeleccionadas.reduce((sum, t) => sum + (t.cantidad || 0), 0)}
                          </TableCell>
                          <TableCell></TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground border rounded-lg bg-muted/20">
                    Selecciona tallas del catálogo para agregar cantidades
                  </div>
                )}
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

      {/* Dialog para distribuir colores - MATRIZ */}
      <Dialog open={coloresDialogOpen} onOpenChange={setColoresDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Distribución de Colores - Corte #{colorEditItem?.n_corte}</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            {/* Selector de colores múltiple */}
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Seleccionar Colores
              </h3>
              <div className="flex flex-wrap gap-2">
                {coloresCatalogo.map((color) => {
                  const seleccionado = coloresSeleccionados.find(c => c.id === color.id);
                  return (
                    <button
                      key={color.id}
                      type="button"
                      onClick={() => handleToggleColor(color.id)}
                      className={`
                        flex items-center gap-2 px-3 py-2 rounded-lg border transition-all
                        ${seleccionado 
                          ? 'border-primary bg-primary/10 ring-2 ring-primary' 
                          : 'border-border hover:border-primary/50 hover:bg-muted'
                        }
                      `}
                      data-testid={`toggle-color-${color.id}`}
                    >
                      <div 
                        className="w-5 h-5 rounded border"
                        style={{ backgroundColor: color.codigo_hex || '#ccc' }}
                      />
                      <span className="text-sm font-medium">{color.nombre}</span>
                      {seleccionado && <X className="h-4 w-4 text-muted-foreground" />}
                    </button>
                  );
                })}
              </div>
              {coloresCatalogo.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No hay colores en el catálogo. Agrega colores primero.
                </p>
              )}
            </div>

            <Separator />

            {/* Matriz de cantidades */}
            {colorEditItem?.tallas?.length > 0 && coloresSeleccionados.length > 0 ? (
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                  Distribución por Talla y Color
                </h3>
                <p className="text-xs text-muted-foreground mb-4">
                  El primer color agregado recibe todo el total. Redistribuye según necesites.
                </p>
                
                <div className="border rounded-lg overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr>
                        <th className="bg-muted/50 p-3 text-left text-xs font-semibold uppercase tracking-wider border-b min-w-[120px]">
                          Color
                        </th>
                        {colorEditItem.tallas.map((t) => (
                          <th key={t.talla_id} className="bg-muted/50 p-3 text-center text-xs font-semibold uppercase tracking-wider border-b min-w-[100px]">
                            <div>{t.talla_nombre}</div>
                            <div className="text-muted-foreground font-normal mt-1">
                              Total: {t.cantidad}
                            </div>
                          </th>
                        ))}
                        <th className="bg-muted/70 p-3 text-center text-xs font-semibold uppercase tracking-wider border-b min-w-[80px]">
                          Total
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {coloresSeleccionados.map((color, colorIndex) => (
                        <tr key={color.id} className={colorIndex % 2 === 0 ? 'bg-background' : 'bg-muted/20'}>
                          <td className="p-2 border-b">
                            <div className="flex items-center gap-2">
                              <div 
                                className="w-5 h-5 rounded border shrink-0"
                                style={{ backgroundColor: color.codigo_hex || '#ccc' }}
                              />
                              <span className="font-medium text-sm">{color.nombre}</span>
                            </div>
                          </td>
                          {colorEditItem.tallas.map((t) => {
                            const asignado = getTotalTallaAsignado(t.talla_id);
                            const maximo = t.cantidad - asignado + getCantidadMatriz(color.id, t.talla_id);
                            return (
                              <td key={t.talla_id} className="p-1 border-b">
                                <Input
                                  type="number"
                                  min="0"
                                  max={maximo}
                                  value={getCantidadMatriz(color.id, t.talla_id) || ''}
                                  onChange={(e) => handleMatrizChange(color.id, t.talla_id, e.target.value)}
                                  className="w-full font-mono text-center h-10"
                                  placeholder="0"
                                  data-testid={`matriz-${color.id}-${t.talla_id}`}
                                />
                              </td>
                            );
                          })}
                          <td className="p-2 border-b bg-muted/30 text-center font-mono font-semibold">
                            {getTotalColor(color.id)}
                          </td>
                        </tr>
                      ))}
                      {/* Fila de totales asignados */}
                      <tr className="bg-muted/50">
                        <td className="p-3 font-semibold text-sm">Asignado</td>
                        {colorEditItem.tallas.map((t) => {
                          const asignado = getTotalTallaAsignado(t.talla_id);
                          const completo = asignado === t.cantidad;
                          return (
                            <td key={t.talla_id} className="p-3 text-center font-mono font-semibold">
                              <span className={completo ? 'text-green-600' : 'text-orange-500'}>
                                {asignado}
                              </span>
                              <span className="text-muted-foreground">/{t.cantidad}</span>
                            </td>
                          );
                        })}
                        <td className="p-3 text-center font-mono font-bold bg-primary/10 text-primary">
                          {getTotalGeneralAsignado()}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            ) : colorEditItem?.tallas?.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground border rounded-lg bg-muted/20">
                Este registro no tiene tallas definidas. Edita el registro primero.
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground border rounded-lg bg-muted/20">
                Selecciona al menos un color para ver la matriz de distribución
              </div>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setColoresDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveColores} 
              disabled={coloresSeleccionados.length === 0}
              data-testid="btn-guardar-colores"
            >
              Guardar Distribución
            </Button>
          </DialogFooter>
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

              {/* Tallas */}
              {viewingItem.tallas && viewingItem.tallas.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Tallas</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-3">
                      {viewingItem.tallas.map((t) => (
                        <div key={t.talla_id} className="flex items-center gap-2 px-3 py-2 bg-muted rounded-lg">
                          <span className="font-medium">{t.talla_nombre}:</span>
                          <span className="font-mono font-bold">{t.cantidad}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Distribución de colores */}
              {viewingItem.distribucion_colores && viewingItem.distribucion_colores.some(t => t.colores?.length > 0) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Distribución por Color</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse text-sm">
                        <thead>
                          <tr>
                            <th className="bg-muted/50 p-2 border text-left font-semibold">Color</th>
                            {viewingItem.tallas.map((t) => (
                              <th key={t.talla_id} className="bg-muted/50 p-2 border text-center font-semibold">
                                {t.talla_nombre}
                              </th>
                            ))}
                            <th className="bg-muted/70 p-2 border text-center font-semibold">Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(() => {
                            const coloresUnicos = new Map();
                            viewingItem.distribucion_colores.forEach(t => {
                              (t.colores || []).forEach(c => {
                                if (!coloresUnicos.has(c.color_id)) {
                                  coloresUnicos.set(c.color_id, c.color_nombre);
                                }
                              });
                            });
                            
                            return Array.from(coloresUnicos.entries()).map(([colorId, colorNombre]) => (
                              <tr key={colorId}>
                                <td className="bg-muted/30 p-2 border font-medium">{colorNombre}</td>
                                {viewingItem.tallas.map((t) => {
                                  const distTalla = viewingItem.distribucion_colores.find(d => d.talla_id === t.talla_id);
                                  const colorData = (distTalla?.colores || []).find(c => c.color_id === colorId);
                                  return (
                                    <td key={t.talla_id} className="p-2 border text-center font-mono">
                                      {colorData?.cantidad || 0}
                                    </td>
                                  );
                                })}
                                <td className="bg-muted/50 p-2 border text-center font-mono font-semibold">
                                  {viewingItem.distribucion_colores.reduce((sum, t) => {
                                    const colorData = (t.colores || []).find(c => c.color_id === colorId);
                                    return sum + (colorData?.cantidad || 0);
                                  }, 0)}
                                </td>
                              </tr>
                            ));
                          })()}
                          <tr>
                            <td className="bg-muted/70 p-2 border font-semibold">Total</td>
                            {viewingItem.tallas.map((t) => {
                              const distTalla = viewingItem.distribucion_colores.find(d => d.talla_id === t.talla_id);
                              return (
                                <td key={t.talla_id} className="bg-muted/50 p-2 border text-center font-mono font-semibold">
                                  {(distTalla?.colores || []).reduce((sum, c) => sum + (c.cantidad || 0), 0)}
                                </td>
                              );
                            })}
                            <td className="bg-primary/10 p-2 border text-center font-mono font-bold text-primary">
                              {viewingItem.distribucion_colores.reduce((sum, t) => 
                                sum + (t.colores || []).reduce((s, c) => s + (c.cantidad || 0), 0), 0
                              )}
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

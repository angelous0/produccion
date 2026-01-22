import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Separator } from '../components/ui/separator';
import { ArrowLeft, Save, AlertTriangle, Trash2, Tag, Layers, Shirt, Palette, Scissors, Package, Plus, ArrowUpCircle } from 'lucide-react';
import { toast } from 'sonner';
import { MultiSelectColors } from '../components/MultiSelectColors';
import { Textarea } from '../components/ui/textarea';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const RegistroForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEditing = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  
  const [formData, setFormData] = useState({
    n_corte: '',
    modelo_id: '',
    curva: '',
    estado: 'Para Corte',
    urgente: false,
  });

  // Datos del modelo seleccionado
  const [modeloSeleccionado, setModeloSeleccionado] = useState(null);

  // Tallas seleccionadas
  const [tallasSeleccionadas, setTallasSeleccionadas] = useState([]);

  // Datos para distribución de colores
  const [coloresDialogOpen, setColoresDialogOpen] = useState(false);
  const [coloresSeleccionados, setColoresSeleccionados] = useState([]);
  const [matrizCantidades, setMatrizCantidades] = useState({});
  const [distribucionColores, setDistribucionColores] = useState([]);

  // Datos del catálogo
  const [tallasCatalogo, setTallasCatalogo] = useState([]);
  const [coloresCatalogo, setColoresCatalogo] = useState([]);
  const [modelos, setModelos] = useState([]);
  const [estados, setEstados] = useState([]);

  // Cargar datos relacionados
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
      toast.error('Error al cargar datos');
    }
  };

  // Cargar registro existente si es edición
  const fetchRegistro = async () => {
    if (!id) {
      setLoadingData(false);
      return;
    }
    
    try {
      const response = await axios.get(`${API}/registros/${id}`);
      const registro = response.data;
      
      setFormData({
        n_corte: registro.n_corte,
        modelo_id: registro.modelo_id,
        curva: registro.curva || '',
        estado: registro.estado,
        urgente: registro.urgente,
      });
      
      setTallasSeleccionadas(registro.tallas || []);
      setDistribucionColores(registro.distribucion_colores || []);
      
      // Buscar modelo seleccionado
      const modelosRes = await axios.get(`${API}/modelos`);
      const modelo = modelosRes.data.find(m => m.id === registro.modelo_id);
      setModeloSeleccionado(modelo || null);
      
    } catch (error) {
      toast.error('Error al cargar registro');
      navigate('/registros');
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    fetchRelatedData();
    fetchRegistro();
  }, [id]);

  // Cuando cambia el modelo seleccionado
  const handleModeloChange = (modeloId) => {
    setFormData({ ...formData, modelo_id: modeloId });
    const modelo = modelos.find(m => m.id === modeloId);
    setModeloSeleccionado(modelo || null);
  };

  // Agregar talla
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

  const handleOpenColoresDialog = () => {
    // Reconstruir colores seleccionados y matriz desde distribución guardada
    if (distribucionColores && distribucionColores.length > 0) {
      const coloresUnicos = [];
      const matriz = {};
      
      distribucionColores.forEach(talla => {
        (talla.colores || []).forEach(c => {
          if (!coloresUnicos.find(cu => cu.id === c.color_id)) {
            const colorCat = coloresCatalogo.find(cc => cc.id === c.color_id);
            if (colorCat) {
              coloresUnicos.push(colorCat);
            }
          }
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

  const handleColoresChange = (nuevosColores) => {
    const coloresAgregados = nuevosColores.filter(
      nc => !coloresSeleccionados.find(cs => cs.id === nc.id)
    );
    
    const coloresRemovidos = coloresSeleccionados.filter(
      cs => !nuevosColores.find(nc => nc.id === cs.id)
    );
    
    if (coloresRemovidos.length > 0) {
      const nuevaMatriz = { ...matrizCantidades };
      coloresRemovidos.forEach(color => {
        Object.keys(nuevaMatriz).forEach(key => {
          if (key.startsWith(`${color.id}_`)) {
            delete nuevaMatriz[key];
          }
        });
      });
      setMatrizCantidades(nuevaMatriz);
    }
    
    if (coloresSeleccionados.length === 0 && coloresAgregados.length > 0 && tallasSeleccionadas.length > 0) {
      const primerColor = coloresAgregados[0];
      const nuevaMatriz = { ...matrizCantidades };
      tallasSeleccionadas.forEach(t => {
        nuevaMatriz[`${primerColor.id}_${t.talla_id}`] = t.cantidad;
      });
      setMatrizCantidades(nuevaMatriz);
    }
    
    setColoresSeleccionados(nuevosColores);
  };

  const getCantidadMatriz = (colorId, tallaId) => {
    return matrizCantidades[`${colorId}_${tallaId}`] || 0;
  };

  const handleMatrizChange = (colorId, tallaId, valor) => {
    const cantidad = parseInt(valor) || 0;
    const talla = tallasSeleccionadas.find(t => t.talla_id === tallaId);
    
    if (!talla) return;
    
    let sumaOtros = 0;
    coloresSeleccionados.forEach(c => {
      if (c.id !== colorId) {
        sumaOtros += getCantidadMatriz(c.id, tallaId);
      }
    });
    
    if (cantidad + sumaOtros > talla.cantidad) {
      toast.error(`La suma (${cantidad + sumaOtros}) excede el total de la talla ${talla.talla_nombre} (${talla.cantidad})`);
      return;
    }
    
    setMatrizCantidades({
      ...matrizCantidades,
      [`${colorId}_${tallaId}`]: cantidad
    });
  };

  const getTotalColor = (colorId) => {
    let total = 0;
    tallasSeleccionadas.forEach(t => {
      total += getCantidadMatriz(colorId, t.talla_id);
    });
    return total;
  };

  const getTotalTallaAsignado = (tallaId) => {
    let total = 0;
    coloresSeleccionados.forEach(c => {
      total += getCantidadMatriz(c.id, tallaId);
    });
    return total;
  };

  const getTotalGeneralAsignado = () => {
    let total = 0;
    coloresSeleccionados.forEach(c => {
      total += getTotalColor(c.id);
    });
    return total;
  };

  const handleSaveColores = () => {
    const distribucion = tallasSeleccionadas.map(t => ({
      talla_id: t.talla_id,
      talla_nombre: t.talla_nombre,
      cantidad_total: t.cantidad,
      colores: coloresSeleccionados.map(c => ({
        color_id: c.id,
        color_nombre: c.nombre,
        cantidad: getCantidadMatriz(c.id, t.talla_id)
      })).filter(c => c.cantidad > 0)
    }));
    
    setDistribucionColores(distribucion);
    setColoresDialogOpen(false);
    toast.success('Distribución de colores guardada');
  };

  // Verificar si tiene colores asignados
  const tieneColores = () => {
    return distribucionColores && 
           distribucionColores.some(t => t.colores && t.colores.length > 0);
  };

  // Guardar registro
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const payload = {
        ...formData,
        tallas: tallasSeleccionadas,
        distribucion_colores: distribucionColores,
      };
      
      if (isEditing) {
        await axios.put(`${API}/registros/${id}`, payload);
        toast.success('Registro actualizado');
      } else {
        await axios.post(`${API}/registros`, payload);
        toast.success('Registro creado');
      }
      
      navigate('/registros');
    } catch (error) {
      toast.error('Error al guardar registro');
    } finally {
      setLoading(false);
    }
  };

  // Tallas disponibles (no seleccionadas)
  const tallasDisponibles = tallasCatalogo.filter(
    t => !tallasSeleccionadas.find(ts => ts.talla_id === t.id)
  );

  if (loadingData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Cargando...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="registro-form-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button 
          variant="ghost" 
          size="icon"
          onClick={() => navigate('/registros')}
          data-testid="btn-volver"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            {isEditing ? 'Editar Registro' : 'Nuevo Registro'}
          </h2>
          <p className="text-muted-foreground">
            {isEditing ? `Editando registro ${formData.n_corte}` : 'Crear un nuevo registro de producción'}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Columna izquierda - Información general */}
          <div className="lg:col-span-2 space-y-6">
            {/* Información General */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Información General</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="n_corte">N° Corte *</Label>
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
                    <Label>Modelo *</Label>
                    <Select
                      value={formData.modelo_id}
                      onValueChange={handleModeloChange}
                    >
                      <SelectTrigger data-testid="select-modelo">
                        <SelectValue placeholder="Seleccionar modelo" />
                      </SelectTrigger>
                      <SelectContent>
                        {modelos.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
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

                <div className="flex items-center space-x-2 pt-2">
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
              </CardContent>
            </Card>

            {/* Tallas */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Tallas y Cantidades</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
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
                          <TableCell className="font-mono font-bold text-center text-lg">
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

                {/* Botón Agregar Colores */}
                {tallasSeleccionadas.length > 0 && (
                  <div className="pt-4">
                    <Separator className="mb-4" />
                    <Button
                      type="button"
                      variant={tieneColores() ? "default" : "outline"}
                      onClick={handleOpenColoresDialog}
                      className="w-full"
                      data-testid="btn-agregar-colores"
                    >
                      <Palette className="h-4 w-4 mr-2" />
                      {tieneColores() ? 'Editar Colores' : 'Agregar Colores'}
                      {tieneColores() && (
                        <Badge variant="secondary" className="ml-2">
                          {distribucionColores.reduce((sum, t) => sum + (t.colores?.length || 0), 0)} colores
                        </Badge>
                      )}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Columna derecha - Datos del modelo */}
          <div className="space-y-6">
            {/* Datos del Modelo Seleccionado */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Datos del Modelo</CardTitle>
              </CardHeader>
              <CardContent>
                {modeloSeleccionado ? (
                  <div className="space-y-4">
                    <div className="p-3 bg-primary/5 rounded-lg border border-primary/20">
                      <p className="text-xs text-muted-foreground uppercase tracking-wider">Modelo</p>
                      <p className="font-semibold text-lg">{modeloSeleccionado.nombre}</p>
                    </div>
                    
                    <Separator />
                    
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <Tag className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-xs text-muted-foreground">Marca</p>
                          <p className="font-medium">{modeloSeleccionado.marca_nombre || '-'}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <Layers className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-xs text-muted-foreground">Tipo</p>
                          <p className="font-medium">{modeloSeleccionado.tipo_nombre || '-'}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <Shirt className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-xs text-muted-foreground">Entalle</p>
                          <p className="font-medium">{modeloSeleccionado.entalle_nombre || '-'}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <Palette className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-xs text-muted-foreground">Tela</p>
                          <p className="font-medium">{modeloSeleccionado.tela_nombre || '-'}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <Scissors className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-xs text-muted-foreground">Hilo</p>
                          <p className="font-medium">{modeloSeleccionado.hilo_nombre || '-'}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    Selecciona un modelo para ver sus datos
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Botones de acción */}
            <div className="flex flex-col gap-3">
              <Button 
                type="submit" 
                size="lg" 
                className="w-full"
                disabled={loading}
                data-testid="btn-guardar-registro"
              >
                <Save className="h-4 w-4 mr-2" />
                {loading ? 'Guardando...' : (isEditing ? 'Actualizar Registro' : 'Crear Registro')}
              </Button>
              
              <Button 
                type="button"
                variant="outline" 
                size="lg"
                className="w-full"
                onClick={() => navigate('/registros')}
              >
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      </form>

      {/* Dialog para distribuir colores */}
      <Dialog open={coloresDialogOpen} onOpenChange={setColoresDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Distribución de Colores</DialogTitle>
            <DialogDescription>
              Selecciona colores y distribuye las cantidades por talla
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-4">
            {/* Selector de colores múltiple con buscador */}
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Seleccionar Colores
              </h3>
              <MultiSelectColors
                options={coloresCatalogo}
                selected={coloresSeleccionados}
                onChange={handleColoresChange}
                placeholder="Buscar y seleccionar colores..."
                searchPlaceholder="Buscar color..."
                emptyMessage="No se encontraron colores."
              />
              <p className="text-xs text-muted-foreground mt-2">
                El primer color seleccionado recibe todo el total automáticamente.
              </p>
            </div>

            <Separator />

            {/* Matriz de cantidades */}
            {tallasSeleccionadas.length > 0 && coloresSeleccionados.length > 0 ? (
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                  Distribución por Talla y Color
                </h3>
                
                <div className="border rounded-lg overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr>
                        <th className="bg-muted/50 p-3 text-left text-xs font-semibold uppercase tracking-wider border-b min-w-[120px]">
                          Color
                        </th>
                        {tallasSeleccionadas.map((t) => (
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
                          {tallasSeleccionadas.map((t) => (
                            <td key={t.talla_id} className="p-1 border-b">
                              <Input
                                type="number"
                                min="0"
                                value={getCantidadMatriz(color.id, t.talla_id) || ''}
                                onChange={(e) => handleMatrizChange(color.id, t.talla_id, e.target.value)}
                                className="w-full font-mono text-center h-10"
                                placeholder="0"
                                data-testid={`matriz-${color.id}-${t.talla_id}`}
                              />
                            </td>
                          ))}
                          <td className="p-2 border-b bg-muted/30 text-center font-mono font-semibold">
                            {getTotalColor(color.id)}
                          </td>
                        </tr>
                      ))}
                      <tr className="bg-muted/50">
                        <td className="p-3 font-semibold text-sm">Asignado</td>
                        {tallasSeleccionadas.map((t) => {
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
    </div>
  );
};

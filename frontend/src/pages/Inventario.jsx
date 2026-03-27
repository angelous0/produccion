import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { useSaving } from '../hooks/useSaving';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Plus, Pencil, Trash2, Package, AlertTriangle, Layers, Info, ChevronDown, ChevronUp, Search, X, PackageX, BookOpen } from 'lucide-react';
import { toast } from 'sonner';
import { ExportButton } from '../components/ExportButton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';
import { NumericInput } from '../components/ui/numeric-input';
import { useNavigate } from 'react-router-dom';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const UNIDADES = ['unidad', 'metro', 'kg', 'litro', 'rollo', 'caja', 'par', 'servicio'];
const CATEGORIAS = ['Telas', 'Avios', 'PT', 'Otros'];
const STOCK_STATUS_OPTIONS = [
  { value: 'todos', label: 'Todos' },
  { value: 'ok', label: 'OK' },
  { value: 'stock_bajo', label: 'Stock bajo' },
  { value: 'sin_stock', label: 'Sin stock' },
];

export const Inventario = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [pageSize] = useState(50);
  const { saving, guard } = useSaving();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [expandedItemId, setExpandedItemId] = useState(null);
  const [reservasDetalle, setReservasDetalle] = useState(null);
  const [loadingReservas, setLoadingReservas] = useState(false);
  const [alertasStock, setAlertasStock] = useState(null);
  const navigate = useNavigate();

  // Filtros server-side
  const [searchTerm, setSearchTerm] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');
  const [filtroCategoria, setFiltroCategoria] = useState('todos');
  const [filtroStock, setFiltroStock] = useState('todos');
  const [filtroLinea, setFiltroLinea] = useState('todos');

  // Opciones de filtro desde servidor
  const [categoriasOpciones, setCategoriasOpciones] = useState([]);
  const [lineasNegocio, setLineasNegocio] = useState([]);

  const [formData, setFormData] = useState({
    codigo: '', nombre: '', descripcion: '', categoria: 'Otros',
    unidad_medida: 'unidad', stock_minimo: 0, control_por_rollos: false,
    linea_negocio_id: '',
  });

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setSearchDebounced(searchTerm), 400);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const fetchItems = useCallback(async (append = false) => {
    if (!append) setLoading(true);
    try {
      const offset = append ? items.length : 0;
      const params = new URLSearchParams({ limit: pageSize, offset });
      if (searchDebounced) params.set('search', searchDebounced);
      if (filtroCategoria !== 'todos') params.set('categoria', filtroCategoria);
      if (filtroStock !== 'todos') params.set('stock_status', filtroStock);
      if (filtroLinea !== 'todos') params.set('linea_negocio_id', filtroLinea);
      const response = await axios.get(`${API}/inventario?${params.toString()}`);
      const data = response.data;
      if (append) {
        setItems(prev => [...prev, ...data.items]);
      } else {
        setItems(data.items);
      }
      setTotal(data.total);
    } catch (error) {
      toast.error('Error al cargar inventario');
    } finally {
      setLoading(false);
    }
  }, [searchDebounced, filtroCategoria, filtroStock, filtroLinea, pageSize, items.length]);

  const fetchFiltros = async () => {
    try {
      const [filtrosRes, alertasRes, lineasRes] = await Promise.allSettled([
        axios.get(`${API}/inventario-filtros`),
        axios.get(`${API}/inventario/alertas-stock`),
        axios.get(`${API}/lineas-negocio`),
      ]);
      if (filtrosRes.status === 'fulfilled') setCategoriasOpciones(filtrosRes.value.data.categorias);
      if (alertasRes.status === 'fulfilled') setAlertasStock(alertasRes.value.data);
      if (lineasRes.status === 'fulfilled') setLineasNegocio(lineasRes.value.data);
    } catch (e) {}
  };

  useEffect(() => { fetchFiltros(); }, []);

  useEffect(() => {
    fetchItems(false);
  }, [searchDebounced, filtroCategoria, filtroStock, filtroLinea]);

  const hayFiltrosActivos = searchTerm || filtroCategoria !== 'todos' || filtroStock !== 'todos' || filtroLinea !== 'todos';

  const limpiarFiltros = () => {
    setSearchTerm('');
    setFiltroCategoria('todos');
    setFiltroStock('todos');
    setFiltroLinea('todos');
  };

  const resetForm = () => {
    setFormData({
      codigo: '', nombre: '', descripcion: '', categoria: 'Otros',
      unidad_medida: 'unidad', stock_minimo: 0, control_por_rollos: false,
      linea_negocio_id: '',
    });
    setEditingItem(null);
  };

  const handleOpenDialog = (item = null) => {
    if (item) {
      setEditingItem(item);
      setFormData({
        codigo: item.codigo, nombre: item.nombre, descripcion: item.descripcion || '',
        categoria: item.categoria || 'Otros', unidad_medida: item.unidad_medida || 'unidad',
        stock_minimo: item.stock_minimo || 0, control_por_rollos: item.control_por_rollos || false,
        linea_negocio_id: item.linea_negocio_id ? String(item.linea_negocio_id) : '',
      });
    } else {
      resetForm();
    }
    setDialogOpen(true);
  };

  const handleSubmit = guard(async (e) => {
    e.preventDefault();
    try {
      const payload = { ...formData, linea_negocio_id: formData.linea_negocio_id ? parseInt(formData.linea_negocio_id) : null };
      if (editingItem) {
        await axios.put(`${API}/inventario/${editingItem.id}`, payload);
        toast.success('Item actualizado');
      } else {
        await axios.post(`${API}/inventario`, payload);
        toast.success('Item creado');
      }
      setDialogOpen(false);
      resetForm();
      fetchItems(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  });

  const getCategoriaColor = (categoria) => {
    switch (categoria) {
      case 'Telas': return 'bg-blue-500';
      case 'Avios': return 'bg-purple-500';
      case 'PT': return 'bg-green-600';
      case 'Rigido': return 'bg-slate-600';
      case 'Franela': return 'bg-pink-500';
      case 'Jean': return 'bg-indigo-500';
      case 'Drill': return 'bg-orange-500';
      case 'Polo': return 'bg-cyan-500';
      case 'Punto': return 'bg-teal-500';
      case 'Servicios': return 'bg-amber-500';
      default: return 'bg-gray-500';
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Eliminar este item? Tambien se eliminaran sus movimientos.')) return;
    try {
      await axios.delete(`${API}/inventario/${id}`);
      toast.success('Item eliminado');
      fetchItems(false);
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

  const toggleExpandItem = async (itemId) => {
    if (expandedItemId === itemId) {
      setExpandedItemId(null);
      setReservasDetalle(null);
      return;
    }
    setExpandedItemId(itemId);
    setLoadingReservas(true);
    try {
      const response = await axios.get(`${API}/inventario/${itemId}/reservas-detalle`);
      setReservasDetalle(response.data);
    } catch (error) {
      toast.error('Error al cargar detalle de reservas');
      setExpandedItemId(null);
    } finally {
      setLoadingReservas(false);
    }
  };

  const hasActiveReservas = (item) => {
    return !!(item.total_reservado && item.total_reservado > 0);
  };

  return (
    <div className="space-y-4" data-testid="inventario-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Inventario</h2>
          <p className="text-muted-foreground">Gestion de items de inventario (FIFO)</p>
        </div>
        <div className="flex gap-2">
          <ExportButton tabla="inventario" />
          <Button onClick={() => handleOpenDialog()} data-testid="btn-nuevo-item">
            <Plus className="h-4 w-4 mr-2" /> Nuevo Item
          </Button>
        </div>
      </div>

      {/* Barra de busqueda y filtros */}
      <div className="flex flex-wrap items-center gap-2" data-testid="filtros-inventario">
        <div className="relative flex-1 min-w-[220px] max-w-[320px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre o codigo..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 pr-8"
            data-testid="input-search-inventario"
          />
          {searchTerm && (
            <button onClick={() => setSearchTerm('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <Select value={filtroCategoria} onValueChange={setFiltroCategoria}>
          <SelectTrigger className="w-[160px]" data-testid="filtro-categoria-inventario">
            <SelectValue placeholder="Categoria" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todas categorias</SelectItem>
            {categoriasOpciones.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filtroStock} onValueChange={setFiltroStock}>
          <SelectTrigger className="w-[150px]" data-testid="filtro-stock-inventario">
            <SelectValue placeholder="Estado stock" />
          </SelectTrigger>
          <SelectContent>
            {STOCK_STATUS_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filtroLinea} onValueChange={setFiltroLinea}>
          <SelectTrigger className="w-[200px]" data-testid="filtro-linea-inventario">
            <SelectValue placeholder="Linea de negocio" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todas las lineas</SelectItem>
            <SelectItem value="global">Solo Global</SelectItem>
            {lineasNegocio.map(ln => <SelectItem key={ln.id} value={String(ln.id)}>{ln.nombre}</SelectItem>)}
          </SelectContent>
        </Select>
        {hayFiltrosActivos && (
          <Button variant="ghost" size="sm" onClick={limpiarFiltros} data-testid="btn-limpiar-filtros-inv">
            <X className="h-4 w-4 mr-1" /> Limpiar
          </Button>
        )}
        <span className="text-sm text-muted-foreground ml-auto" data-testid="count-inventario">
          {items.length} de {total}
        </span>
      </div>

      {/* Banner de alertas de stock */}
      {alertasStock && alertasStock.total > 0 && (
        <Card className="border-red-500/40 bg-red-500/5 cursor-pointer hover:bg-red-500/10 transition-colors"
          onClick={() => navigate('/inventario/alertas-stock')}
          data-testid="banner-alertas-stock"
        >
          <CardContent className="py-2.5 px-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PackageX className="h-4 w-4 text-red-500 shrink-0" />
                <span className="text-sm font-medium">
                  {alertasStock.total} item{alertasStock.total !== 1 ? 's' : ''} con stock bajo o agotado
                </span>
                {alertasStock.sin_stock > 0 && (
                  <Badge variant="destructive" className="text-xs">{alertasStock.sin_stock} sin stock</Badge>
                )}
                {alertasStock.stock_bajo > 0 && (
                  <Badge className="bg-yellow-500 text-xs">{alertasStock.stock_bajo} bajo</Badge>
                )}
              </div>
              <span className="text-xs text-primary font-medium">Ver reporte →</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabla */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="data-table-header">
                  <TableHead className="w-[40px]"></TableHead>
                  <TableHead>Codigo</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Linea</TableHead>
                  <TableHead>Categoria</TableHead>
                  <TableHead>Unidad</TableHead>
                  <TableHead className="text-right">Stock Actual</TableHead>
                  <TableHead className="text-right">Reservado</TableHead>
                  <TableHead className="text-right">Disponible</TableHead>
                  <TableHead className="text-right">Valorizado</TableHead>
                  <TableHead className="text-right">Stock Min</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="w-[80px]">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={12} className="text-center py-8">Cargando...</TableCell>
                  </TableRow>
                ) : items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={12} className="text-center py-8 text-muted-foreground">
                      {hayFiltrosActivos ? 'No hay items que coincidan con los filtros' : 'No hay items en inventario'}
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((item) => (
                    <React.Fragment key={item.id}>
                      <TableRow className="data-table-row" data-testid={`item-row-${item.id}`}>
                        <TableCell className="p-1">
                          {hasActiveReservas(item) && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button variant="ghost" size="icon" className="h-8 w-8"
                                    onClick={() => toggleExpandItem(item.id)}
                                    data-testid={`expand-reservas-${item.id}`}
                                  >
                                    {expandedItemId === item.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent><p>Ver detalle de reservas</p></TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
                        </TableCell>
                        <TableCell className="font-mono font-medium text-sm">{item.codigo}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Package className="h-4 w-4 text-muted-foreground shrink-0" />
                            <span className="text-sm">{item.nombre}</span>
                            {item.control_por_rollos && (
                              <Badge variant="outline" className="text-xs shrink-0">
                                <Layers className="h-3 w-3 mr-1" /> Rollos
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-xs">
                          {item.linea_negocio_id
                            ? <Badge variant="secondary" className="text-[10px]">{lineasNegocio.find(l => l.id === item.linea_negocio_id)?.nombre || `#${item.linea_negocio_id}`}</Badge>
                            : <span className="text-muted-foreground italic">Global</span>}
                        </TableCell>
                        <TableCell>
                          <Badge className={getCategoriaColor(item.categoria)}>{item.categoria || 'Otros'}</Badge>
                        </TableCell>
                        <TableCell className="capitalize text-sm">{item.unidad_medida}</TableCell>
                        {item.categoria === 'Servicios' ? (
                          <TableCell className="text-center text-muted-foreground" colSpan={5}>
                            <span className="text-xs italic">No aplica</span>
                          </TableCell>
                        ) : (
                          <>
                            <TableCell className="text-right font-mono font-semibold">{item.stock_actual}</TableCell>
                            <TableCell className="text-right font-mono">
                              {item.total_reservado > 0 ? (
                                <span className="text-orange-500 font-medium">{item.total_reservado}</span>
                              ) : (
                                <span className="text-muted-foreground">0</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right font-mono font-semibold">
                              <span className={item.stock_disponible <= item.stock_minimo ? 'text-red-500' : 'text-green-600'}>
                                {item.stock_disponible}
                              </span>
                            </TableCell>
                            <TableCell className="text-right font-mono" data-testid={`valorizado-${item.id}`}>
                              {item.valorizado > 0 ? (
                                <span className="font-semibold">
                                  {new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(item.valorizado)}
                                </span>
                              ) : (
                                <span className="text-muted-foreground">--</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground">{item.stock_minimo}</TableCell>
                          </>
                        )}
                        <TableCell>
                          {item.categoria === 'Servicios' ? (
                            <Badge className="bg-amber-500">Servicio</Badge>
                          ) : (
                            <Badge
                              variant={getStockStatus(item) === 'success' ? 'default' : getStockStatus(item)}
                              className={getStockStatus(item) === 'success' ? 'bg-green-600' : getStockStatus(item) === 'warning' ? 'bg-yellow-500' : ''}
                            >
                              {item.stock_actual <= item.stock_minimo && item.stock_actual > 0 && (
                                <AlertTriangle className="h-3 w-3 mr-1" />
                              )}
                              {getStockLabel(item)}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => navigate(`/inventario/kardex?item=${item.id}`)} title="Ver Kardex" data-testid={`kardex-item-${item.id}`}>
                              <BookOpen className="h-3.5 w-3.5 text-primary" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleOpenDialog(item)} data-testid={`edit-item-${item.id}`}>
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleDelete(item.id)} data-testid={`delete-item-${item.id}`}>
                              <Trash2 className="h-3.5 w-3.5 text-destructive" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                      {/* Fila expandible reservas */}
                      {expandedItemId === item.id && (
                        <TableRow key={`${item.id}-detail`} className="bg-muted/30">
                          <TableCell colSpan={12} className="p-0">
                            {loadingReservas ? (
                              <div className="p-4 text-center text-muted-foreground">Cargando reservas...</div>
                            ) : reservasDetalle && reservasDetalle.registros.length > 0 ? (
                              <div className="p-4 space-y-3">
                                <div className="flex items-center gap-2 text-sm font-medium">
                                  <Info className="h-4 w-4 text-blue-500" />
                                  Reservas activas: <span className="text-primary">{reservasDetalle.item_nombre}</span>
                                </div>
                                <Table>
                                  <TableHeader>
                                    <TableRow>
                                      <TableHead>N Corte</TableHead>
                                      <TableHead>Modelo</TableHead>
                                      <TableHead>Estado</TableHead>
                                      <TableHead className="text-right">Reservado</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {reservasDetalle.registros.map((reg) => (
                                      <TableRow key={reg.registro_id}>
                                        <TableCell className="font-mono font-medium">{reg.n_corte}</TableCell>
                                        <TableCell>{reg.modelo_nombre || '-'}</TableCell>
                                        <TableCell><Badge variant="outline">{reg.registro_estado}</Badge></TableCell>
                                        <TableCell className="text-right font-mono text-orange-500 font-semibold">{reg.total_reservado}</TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                                <div className="flex justify-end text-sm text-muted-foreground pt-2 border-t gap-4">
                                  <span>Total reservado: <strong className="text-orange-500">{reservasDetalle.total_reservado}</strong></span>
                                  <span>Stock actual: <strong>{reservasDetalle.stock_actual}</strong></span>
                                  <span>Disponible: <strong className="text-green-600">{reservasDetalle.stock_disponible}</strong></span>
                                </div>
                              </div>
                            ) : (
                              <div className="p-4 text-center text-muted-foreground">No hay reservas activas</div>
                            )}
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          {/* Cargar mas */}
          {items.length < total && !loading && (
            <div className="flex justify-center py-4 border-t">
              <Button variant="outline" size="sm" onClick={() => fetchItems(true)} data-testid="btn-cargar-mas-inventario">
                <ChevronDown className="h-4 w-4 mr-2" />
                Cargar mas ({items.length} de {total})
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog crear/editar */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingItem ? 'Editar Item' : 'Nuevo Item'}</DialogTitle>
            <DialogDescription>{editingItem ? 'Modifica los datos del item' : 'Agrega un nuevo item al inventario'}</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="codigo">Codigo *</Label>
                  <Input id="codigo" value={formData.codigo} onChange={(e) => setFormData({ ...formData, codigo: e.target.value })} placeholder="COD-001" required className="font-mono" data-testid="input-codigo" />
                </div>
                <div className="space-y-2">
                  <Label>Categoria</Label>
                  <Select value={formData.categoria} onValueChange={(value) => {
                    const isServicio = value === 'Servicios';
                    setFormData({ ...formData, categoria: value, control_por_rollos: value === 'Telas' ? formData.control_por_rollos : false, unidad_medida: isServicio ? 'servicio' : formData.unidad_medida, stock_minimo: isServicio ? 0 : formData.stock_minimo });
                  }}>
                    <SelectTrigger data-testid="select-categoria"><SelectValue /></SelectTrigger>
                    <SelectContent>{CATEGORIAS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre *</Label>
                <Input id="nombre" value={formData.nombre} onChange={(e) => setFormData({ ...formData, nombre: e.target.value })} placeholder="Nombre del item" required data-testid="input-nombre" />
              </div>
              <div className="space-y-2">
                <Label>Linea de Negocio</Label>
                <Select value={formData.linea_negocio_id || 'global'} onValueChange={(v) => setFormData({ ...formData, linea_negocio_id: v === 'global' ? '' : v })}>
                  <SelectTrigger data-testid="select-linea-item"><SelectValue placeholder="Global (compartida)" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="global">Global (compartida para todas las lineas)</SelectItem>
                    {lineasNegocio.map(ln => <SelectItem key={ln.id} value={String(ln.id)}>{ln.nombre}</SelectItem>)}
                  </SelectContent>
                </Select>
                <p className="text-[10px] text-muted-foreground">Global = disponible para todas las lineas.</p>
              </div>
              {formData.categoria !== 'Servicios' ? (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Unidad de Medida</Label>
                      <Select value={formData.unidad_medida} onValueChange={(value) => setFormData({ ...formData, unidad_medida: value })}>
                        <SelectTrigger data-testid="select-unidad"><SelectValue /></SelectTrigger>
                        <SelectContent>{UNIDADES.map((u) => <SelectItem key={u} value={u} className="capitalize">{u}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Stock Minimo</Label>
                      <NumericInput id="stock_minimo" min="0" value={formData.stock_minimo} onChange={(e) => setFormData({ ...formData, stock_minimo: e.target.value })} placeholder="0" className="font-mono" data-testid="input-stock-minimo" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Descripcion</Label>
                    <Textarea id="descripcion" value={formData.descripcion} onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })} placeholder="Descripcion del item..." rows={2} data-testid="input-descripcion" />
                  </div>
                  {formData.categoria === 'Telas' && (
                    <div className="flex items-center space-x-2 p-3 border rounded-lg bg-muted/30">
                      <Checkbox id="control_por_rollos" checked={formData.control_por_rollos} onCheckedChange={(checked) => setFormData({ ...formData, control_por_rollos: checked })} data-testid="checkbox-rollos" />
                      <div>
                        <Label htmlFor="control_por_rollos" className="cursor-pointer">Control por Rollos</Label>
                        <p className="text-xs text-muted-foreground">Permite registrar cada rollo con su metraje, ancho y tono individual</p>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="space-y-2">
                  <Label>Descripcion</Label>
                  <Textarea value={formData.descripcion} onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })} placeholder="Ej: Servicio de costura recta, overlock, etc." rows={2} data-testid="input-descripcion" />
                  <p className="text-xs text-muted-foreground">Los servicios no manejan stock fisico.</p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={saving} data-testid="btn-guardar-item">{editingItem ? 'Actualizar' : 'Crear'}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useSaving } from '../hooks/useSaving';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
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
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ModelosTallasTab, ModelosBOMTab } from './ModelosBOM';
import { Plus, Pencil, Trash2, Route, Search, X, ExternalLink, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { SearchableSelect } from '../components/SearchableSelect';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const Modelos = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [pageSize] = useState(50);
  const { saving, guard } = useSaving();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({
    nombre: '', marca_id: '', tipo_id: '', entalle_id: '',
    tela_id: '', hilo_id: '', ruta_produccion_id: '', servicios_ids: [], pt_item_id: '',
  });

  // Datos para los selects del dialog
  const [marcas, setMarcas] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [entalles, setEntalles] = useState([]);
  const [telas, setTelas] = useState([]);
  const [hilos, setHilos] = useState([]);
  const [rutas, setRutas] = useState([]);
  const [servicios, setServicios] = useState([]);
  const [itemsPT, setItemsPT] = useState([]);

  // Filtros server-side
  const [searchTerm, setSearchTerm] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');
  const [filtroMarca, setFiltroMarca] = useState('todos');
  const [filtroTipo, setFiltroTipo] = useState('todos');
  const [filtroEntalle, setFiltroEntalle] = useState('todos');
  const [filtroTela, setFiltroTela] = useState('todos');

  // Opciones de filtro desde el servidor
  const [filtroOpciones, setFiltroOpciones] = useState({ marcas: [], tipos: [], entalles: [], telas: [] });

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
      if (filtroMarca !== 'todos') params.set('marca', filtroMarca);
      if (filtroTipo !== 'todos') params.set('tipo', filtroTipo);
      if (filtroEntalle !== 'todos') params.set('entalle', filtroEntalle);
      if (filtroTela !== 'todos') params.set('tela', filtroTela);
      const response = await axios.get(`${API}/modelos?${params.toString()}`);
      const data = response.data;
      if (append) {
        setItems(prev => [...prev, ...data.items]);
      } else {
        setItems(data.items);
      }
      setTotal(data.total);
    } catch (error) {
      toast.error('Error al cargar modelos');
    } finally {
      setLoading(false);
    }
  }, [searchDebounced, filtroMarca, filtroTipo, filtroEntalle, filtroTela, pageSize, items.length]);

  const fetchFiltros = async () => {
    try {
      const res = await axios.get(`${API}/modelos-filtros`);
      setFiltroOpciones(res.data);
    } catch (e) {}
  };

  const fetchRelatedData = async () => {
    try {
      const [marcasRes, tiposRes, entallesRes, telasRes, hilosRes, rutasRes, srvRes, ptRes] = await Promise.all([
        axios.get(`${API}/marcas`),
        axios.get(`${API}/tipos`),
        axios.get(`${API}/entalles`),
        axios.get(`${API}/telas`),
        axios.get(`${API}/hilos`),
        axios.get(`${API}/rutas-produccion`),
        axios.get(`${API}/servicios-produccion`),
        axios.get(`${API}/items-pt`),
      ]);
      setMarcas(marcasRes.data);
      setTipos(tiposRes.data);
      setEntalles(entallesRes.data);
      setTelas(telasRes.data);
      setHilos(hilosRes.data);
      setRutas(rutasRes.data);
      setServicios(srvRes.data.sort((a, b) => (a.secuencia || 0) - (b.secuencia || 0)));
      setItemsPT(ptRes.data);
    } catch (error) {
      toast.error('Error al cargar datos relacionados');
    }
  };

  useEffect(() => {
    fetchFiltros();
  }, []);

  // Reload when filters change
  useEffect(() => {
    fetchItems(false);
  }, [searchDebounced, filtroMarca, filtroTipo, filtroEntalle, filtroTela]);

  const hayFiltrosActivos = searchTerm || filtroMarca !== 'todos' || filtroTipo !== 'todos' || filtroEntalle !== 'todos' || filtroTela !== 'todos';

  const limpiarFiltros = () => {
    setSearchTerm('');
    setFiltroMarca('todos');
    setFiltroTipo('todos');
    setFiltroEntalle('todos');
    setFiltroTela('todos');
  };

  const handleSubmit = guard(async (e) => {
    e.preventDefault();
    try {
      const payload = { ...formData, ruta_produccion_id: formData.ruta_produccion_id || null };
      if (editingItem) {
        await axios.put(`${API}/modelos/${editingItem.id}`, payload);
        toast.success('Modelo actualizado');
      } else {
        await axios.post(`${API}/modelos`, payload);
        toast.success('Modelo creado');
      }
      setDialogOpen(false);
      setEditingItem(null);
      resetForm();
      fetchItems(false);
    } catch (error) {
      toast.error('Error al guardar modelo');
    }
  });

  const resetForm = () => {
    setFormData({
      nombre: '', marca_id: '', tipo_id: '', entalle_id: '',
      tela_id: '', hilo_id: '', ruta_produccion_id: '', servicios_ids: [], pt_item_id: '',
    });
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({
      nombre: item.nombre, marca_id: item.marca_id, tipo_id: item.tipo_id,
      entalle_id: item.entalle_id, tela_id: item.tela_id, hilo_id: item.hilo_id,
      ruta_produccion_id: item.ruta_produccion_id || '', servicios_ids: item.servicios_ids || [],
      pt_item_id: item.pt_item_id || '',
    });
    fetchRelatedData();
    setDialogOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/modelos/${id}`);
      toast.success('Modelo eliminado');
      fetchItems(false);
    } catch (error) {
      toast.error('Error al eliminar modelo');
    }
  };

  const handleNew = () => {
    setEditingItem(null);
    resetForm();
    fetchRelatedData();
    setDialogOpen(true);
  };

  const handleToggleServicio = (servicioId) => {
    const exists = formData.servicios_ids.includes(servicioId);
    setFormData({
      ...formData,
      servicios_ids: exists
        ? formData.servicios_ids.filter(id => id !== servicioId)
        : [...formData.servicios_ids, servicioId],
    });
  };

  const handleCrearPT = async () => {
    if (!editingItem) { toast.error('Guarda el modelo primero antes de crear su PT'); return; }
    try {
      const res = await axios.post(`${API}/modelos/${editingItem.id}/crear-pt`);
      setFormData({ ...formData, pt_item_id: res.data.pt_item_id });
      const ptRes = await axios.get(`${API}/items-pt`);
      setItemsPT(ptRes.data);
      toast.success(`PT creado: ${res.data.pt_item_nombre} (${res.data.pt_item_codigo})`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear PT');
    }
  };

  const handleVerRegistros = (modeloId) => {
    navigate(`/registros?modelo=${modeloId}`);
  };

  return (
    <div className="space-y-4" data-testid="modelos-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Modelos</h2>
          <p className="text-muted-foreground">Gestion de modelos con BOM y rutas</p>
        </div>
        <Button onClick={handleNew} data-testid="btn-nuevo-modelo">
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Modelo
        </Button>
      </div>

      {/* Barra de busqueda y filtros */}
      <div className="flex flex-wrap items-center gap-2" data-testid="filtros-modelos">
        <div className="relative flex-1 min-w-[220px] max-w-[320px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar nombre, marca, tipo, entalle, tela..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 pr-8"
            data-testid="input-search-modelos"
          />
          {searchTerm && (
            <button onClick={() => setSearchTerm('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <Select value={filtroMarca} onValueChange={setFiltroMarca}>
          <SelectTrigger className="w-[150px]" data-testid="filtro-marca">
            <SelectValue placeholder="Marca" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todas marcas</SelectItem>
            {filtroOpciones.marcas.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filtroTipo} onValueChange={setFiltroTipo}>
          <SelectTrigger className="w-[150px]" data-testid="filtro-tipo">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos tipos</SelectItem>
            {filtroOpciones.tipos.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filtroEntalle} onValueChange={setFiltroEntalle}>
          <SelectTrigger className="w-[150px]" data-testid="filtro-entalle">
            <SelectValue placeholder="Entalle" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos entalles</SelectItem>
            {filtroOpciones.entalles.map(e => <SelectItem key={e} value={e}>{e}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filtroTela} onValueChange={setFiltroTela}>
          <SelectTrigger className="w-[150px]" data-testid="filtro-tela">
            <SelectValue placeholder="Tela" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todas telas</SelectItem>
            {filtroOpciones.telas.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
          </SelectContent>
        </Select>
        {hayFiltrosActivos && (
          <Button variant="ghost" size="sm" onClick={limpiarFiltros} data-testid="btn-limpiar-filtros">
            <X className="h-4 w-4 mr-1" /> Limpiar
          </Button>
        )}
        <span className="text-sm text-muted-foreground ml-auto" data-testid="count-modelos">
          {items.length} de {total}
        </span>
      </div>

      {/* Tabla tipo Excel */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="data-table-header">
                  <TableHead className="min-w-[160px]">Nombre</TableHead>
                  <TableHead>Marca</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Entalle</TableHead>
                  <TableHead>Tela</TableHead>
                  <TableHead>Hilo</TableHead>
                  <TableHead>Ruta Prod.</TableHead>
                  <TableHead className="text-center">Registros</TableHead>
                  <TableHead className="w-[80px]">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8">Cargando...</TableCell>
                  </TableRow>
                ) : items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      {hayFiltrosActivos ? 'No hay modelos que coincidan con los filtros' : 'No hay modelos registrados'}
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((item) => (
                    <TableRow key={item.id} className="data-table-row" data-testid={`modelo-row-${item.id}`}>
                      <TableCell className="font-medium">{item.nombre}</TableCell>
                      <TableCell className="text-sm">{item.marca_nombre || '-'}</TableCell>
                      <TableCell className="text-sm">{item.tipo_nombre || '-'}</TableCell>
                      <TableCell className="text-sm">{item.entalle_nombre || '-'}</TableCell>
                      <TableCell className="text-sm">{item.tela_nombre || '-'}</TableCell>
                      <TableCell className="text-sm">{item.hilo_nombre || '-'}</TableCell>
                      <TableCell>
                        {item.ruta_nombre ? (
                          <Badge variant="outline" className="text-xs whitespace-nowrap">
                            <Route className="h-3 w-3 mr-1" />
                            {item.ruta_nombre}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground text-xs">Sin ruta</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        {item.registros_count > 0 ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs font-semibold text-blue-600 hover:text-blue-800 hover:bg-blue-50"
                            onClick={() => handleVerRegistros(item.id)}
                            data-testid={`ver-registros-${item.id}`}
                          >
                            {item.registros_count}
                            <ExternalLink className="h-3 w-3 ml-1" />
                          </Button>
                        ) : (
                          <span className="text-muted-foreground text-xs">0</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleEdit(item)} data-testid={`edit-modelo-${item.id}`}>
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleDelete(item.id)} data-testid={`delete-modelo-${item.id}`}>
                            <Trash2 className="h-3.5 w-3.5 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          {/* Cargar mas */}
          {items.length < total && !loading && (
            <div className="flex justify-center py-4 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => fetchItems(true)}
                data-testid="btn-cargar-mas-modelos"
              >
                <ChevronDown className="h-4 w-4 mr-2" />
                Cargar mas ({items.length} de {total})
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog de edicion/creacion */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingItem ? 'Editar Modelo' : 'Nuevo Modelo'}</DialogTitle>
            <DialogDescription>Configura el modelo con sus materiales y servicios requeridos</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <Tabs defaultValue="general" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="general">General</TabsTrigger>
                <TabsTrigger value="tallas">Tallas</TabsTrigger>
                <TabsTrigger value="bom">BOM / Receta</TabsTrigger>
                <TabsTrigger value="produccion">Produccion</TabsTrigger>
              </TabsList>

              <TabsContent value="general" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="nombre">Nombre *</Label>
                  <Input id="nombre" value={formData.nombre} onChange={(e) => setFormData({ ...formData, nombre: e.target.value })} placeholder="Nombre del modelo" required data-testid="input-nombre-modelo" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Marca</Label>
                    <SearchableSelect
                      value={formData.marca_id}
                      onValueChange={(value) => setFormData({ ...formData, marca_id: value })}
                      options={marcas}
                      placeholder="Buscar marca..."
                      searchPlaceholder="Buscar marca..."
                      testId="select-marca"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Tipo</Label>
                    <SearchableSelect
                      value={formData.tipo_id}
                      onValueChange={(value) => setFormData({ ...formData, tipo_id: value })}
                      options={tipos}
                      placeholder="Buscar tipo..."
                      searchPlaceholder="Buscar tipo..."
                      testId="select-tipo"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Entalle</Label>
                    <SearchableSelect
                      value={formData.entalle_id}
                      onValueChange={(value) => setFormData({ ...formData, entalle_id: value })}
                      options={entalles}
                      placeholder="Buscar entalle..."
                      searchPlaceholder="Buscar entalle..."
                      testId="select-entalle"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Tela</Label>
                    <SearchableSelect
                      value={formData.tela_id}
                      onValueChange={(value) => setFormData({ ...formData, tela_id: value })}
                      options={telas}
                      placeholder="Buscar tela..."
                      searchPlaceholder="Buscar tela..."
                      testId="select-tela"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Hilo</Label>
                    <SearchableSelect
                      value={formData.hilo_id}
                      onValueChange={(value) => setFormData({ ...formData, hilo_id: value })}
                      options={hilos}
                      placeholder="Buscar hilo..."
                      searchPlaceholder="Buscar hilo..."
                      testId="select-hilo"
                    />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="tallas" className="space-y-4 mt-4">
                {editingItem ? <ModelosTallasTab modeloId={editingItem.id} /> : <p className="text-sm text-muted-foreground">Primero crea el modelo para poder asignarle tallas.</p>}
              </TabsContent>

              <TabsContent value="bom" className="space-y-4 mt-4">
                {editingItem ? <ModelosBOMTab modeloId={editingItem.id} /> : <p className="text-sm text-muted-foreground">Primero crea el modelo para poder definir su BOM.</p>}
              </TabsContent>

              <TabsContent value="produccion" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label>Ruta de Produccion</Label>
                  <p className="text-xs text-muted-foreground">Define la secuencia de estados para los registros de este modelo</p>
                  <Select value={formData.ruta_produccion_id} onValueChange={(value) => setFormData({ ...formData, ruta_produccion_id: value === 'none' ? '' : value })}>
                    <SelectTrigger data-testid="select-ruta"><SelectValue placeholder="Seleccionar ruta..." /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Sin ruta (estados globales)</SelectItem>
                      {rutas.map((r) => <SelectItem key={r.id} value={r.id}>{r.nombre} ({r.etapas?.length || 0} etapas)</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Servicios Requeridos</Label>
                  <p className="text-xs text-muted-foreground">Servicios que se usaran para este modelo (sin asignar persona aun)</p>
                  <div className="grid grid-cols-2 gap-2 border rounded-md p-3">
                    {servicios.map((srv) => (
                      <label key={srv.id} className="flex items-center gap-2 p-2 rounded hover:bg-muted cursor-pointer">
                        <Checkbox checked={formData.servicios_ids.includes(srv.id)} onCheckedChange={() => handleToggleServicio(srv.id)} data-testid={`checkbox-servicio-${srv.id}`} />
                        <span className="text-sm">{srv.nombre}</span>
                      </label>
                    ))}
                    {servicios.length === 0 && <p className="col-span-2 text-sm text-muted-foreground text-center py-2">No hay servicios disponibles</p>}
                  </div>
                </div>
                <div className="space-y-2 border-t pt-4">
                  <Label>Articulo PT (Producto Terminado)</Label>
                  <p className="text-xs text-muted-foreground">Item de inventario valorizado que se creara al cerrar la produccion</p>
                  <div className="flex gap-2">
                    <Select value={formData.pt_item_id || 'none'} onValueChange={(value) => setFormData({ ...formData, pt_item_id: value === 'none' ? '' : value })}>
                      <SelectTrigger data-testid="select-pt-item" className="flex-1"><SelectValue placeholder="Seleccionar PT..." /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Sin PT asignado</SelectItem>
                        {itemsPT.map((pt) => <SelectItem key={pt.id} value={pt.id}>{pt.codigo} - {pt.nombre}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Button type="button" variant="outline" size="sm" onClick={handleCrearPT} data-testid="btn-crear-pt" title="Crear PT automatico con el nombre del modelo">
                      <Plus className="h-4 w-4 mr-1" /> Crear PT
                    </Button>
                  </div>
                  {formData.pt_item_id && <p className="text-xs text-green-600">PT vinculado correctamente</p>}
                </div>
              </TabsContent>
            </Tabs>

            <DialogFooter className="mt-6">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
              <Button type="submit" disabled={saving} data-testid="btn-guardar-modelo">{editingItem ? 'Guardar Cambios' : 'Crear Modelo'}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

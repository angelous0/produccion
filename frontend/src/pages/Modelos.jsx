import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
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
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ModelosTallasTab, ModelosBOMTab } from './ModelosBOM';
import { Plus, Pencil, Trash2, Package, Route, Wrench, X } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const Modelos = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({
    nombre: '',
    marca_id: '',
    tipo_id: '',
    entalle_id: '',
    tela_id: '',
    hilo_id: '',
    ruta_produccion_id: '',
    materiales: [],
    servicios_ids: [],
  });

  // Datos para los selects
  const [marcas, setMarcas] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [entalles, setEntalles] = useState([]);
  const [telas, setTelas] = useState([]);
  const [hilos, setHilos] = useState([]);
  const [rutas, setRutas] = useState([]);
  const [servicios, setServicios] = useState([]);

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API}/modelos`);
      setItems(response.data);
    } catch (error) {
      toast.error('Error al cargar modelos');
    } finally {
      setLoading(false);
    }
  };

  const fetchRelatedData = async () => {
    try {
      const [marcasRes, tiposRes, entallesRes, telasRes, hilosRes, rutasRes, srvRes] = await Promise.all([
        axios.get(`${API}/marcas`),
        axios.get(`${API}/tipos`),
        axios.get(`${API}/entalles`),
        axios.get(`${API}/telas`),
        axios.get(`${API}/hilos`),
        axios.get(`${API}/rutas-produccion`),
        axios.get(`${API}/servicios-produccion`),
      ]);
      setMarcas(marcasRes.data);
      setTipos(tiposRes.data);
      setEntalles(entallesRes.data);
      setTelas(telasRes.data);
      setHilos(hilosRes.data);
      setRutas(rutasRes.data);
      setServicios(srvRes.data.sort((a, b) => (a.secuencia || 0) - (b.secuencia || 0)));
    } catch (error) {
      toast.error('Error al cargar datos relacionados');
    }
  };

  useEffect(() => {
    fetchItems();
    fetchRelatedData();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        ruta_produccion_id: formData.ruta_produccion_id || null,
      };
      
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
      fetchItems();
    } catch (error) {
      toast.error('Error al guardar modelo');
    }
  };

  const resetForm = () => {
    setFormData({
      nombre: '',
      marca_id: '',
      tipo_id: '',
      entalle_id: '',
      tela_id: '',
      hilo_id: '',
      ruta_produccion_id: '',
      servicios_ids: [],
    });
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({
      nombre: item.nombre,
      marca_id: item.marca_id,
      tipo_id: item.tipo_id,
      entalle_id: item.entalle_id,
      tela_id: item.tela_id,
      hilo_id: item.hilo_id,
      ruta_produccion_id: item.ruta_produccion_id || '',
      servicios_ids: item.servicios_ids || [],
    });
    setDialogOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/modelos/${id}`);
      toast.success('Modelo eliminado');
      fetchItems();
    } catch (error) {
      toast.error('Error al eliminar modelo');
    }
  };

  const handleNew = () => {
    setEditingItem(null);
    resetForm();
    setDialogOpen(true);
  };

  // Servicios handlers
  const handleToggleServicio = (servicioId) => {
    const exists = formData.servicios_ids.includes(servicioId);
    setFormData({
      ...formData,
      servicios_ids: exists
        ? formData.servicios_ids.filter(id => id !== servicioId)
        : [...formData.servicios_ids, servicioId],
    });
  };

  return (
    <div className="space-y-6" data-testid="modelos-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Modelos</h2>
          <p className="text-muted-foreground">Gestión de modelos con BOM y rutas</p>
        </div>
        <Button onClick={handleNew} data-testid="btn-nuevo-modelo">
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Modelo
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="data-table-header">
                  <TableHead>Nombre</TableHead>
                  <TableHead>Marca</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Ruta Producción</TableHead>
                  <TableHead>Servicios</TableHead>
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
                      No hay modelos registrados
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((item) => (
                    <TableRow key={item.id} className="data-table-row" data-testid={`modelo-row-${item.id}`}>
                      <TableCell className="font-medium">{item.nombre}</TableCell>
                      <TableCell>{item.marca_nombre || '-'}</TableCell>
                      <TableCell>{item.tipo_nombre || '-'}</TableCell>
                      <TableCell>
                        {item.ruta_nombre ? (
                          <Badge variant="outline" className="text-xs">
                            <Route className="h-3 w-3 mr-1" />
                            {item.ruta_nombre}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground text-sm">Sin ruta</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {item.servicios_ids?.length > 0 ? (
                          <Badge variant="secondary" className="text-xs">
                            <Wrench className="h-3 w-3 mr-1" />
                            {item.servicios_ids.length}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground text-sm">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(item)}
                            data-testid={`edit-modelo-${item.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(item.id)}
                            data-testid={`delete-modelo-${item.id}`}
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
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingItem ? 'Editar Modelo' : 'Nuevo Modelo'}</DialogTitle>
            <DialogDescription>
              Configura el modelo con sus materiales y servicios requeridos
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <Tabs defaultValue="general" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="general">General</TabsTrigger>
                <TabsTrigger value="tallas">Tallas</TabsTrigger>
                <TabsTrigger value="bom">BOM / Receta</TabsTrigger>
                <TabsTrigger value="produccion">Producción</TabsTrigger>
              </TabsList>

              <TabsContent value="general" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="nombre">Nombre *</Label>
                  <Input
                    id="nombre"
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    placeholder="Nombre del modelo"
                    required
                    data-testid="input-nombre-modelo"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Marca</Label>
                    <Select
                      value={formData.marca_id}
                      onValueChange={(value) => setFormData({ ...formData, marca_id: value })}
                    >
                      <SelectTrigger data-testid="select-marca">
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>
                      <SelectContent>
                        {marcas.map((m) => (
                          <SelectItem key={m.id} value={m.id}>{m.nombre}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Tipo</Label>
                    <Select
                      value={formData.tipo_id}
                      onValueChange={(value) => setFormData({ ...formData, tipo_id: value })}
                    >
                      <SelectTrigger data-testid="select-tipo">
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>
                      <SelectContent>
                        {tipos.map((t) => (
                          <SelectItem key={t.id} value={t.id}>{t.nombre}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Entalle</Label>
                    <Select
                      value={formData.entalle_id}
                      onValueChange={(value) => setFormData({ ...formData, entalle_id: value })}
                    >
                      <SelectTrigger data-testid="select-entalle">
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>
                      <SelectContent>
                        {entalles.map((e) => (
                          <SelectItem key={e.id} value={e.id}>{e.nombre}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Tela</Label>
                    <Select
                      value={formData.tela_id}
                      onValueChange={(value) => setFormData({ ...formData, tela_id: value })}
                    >
                      <SelectTrigger data-testid="select-tela">
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>
                      <SelectContent>
                        {telas.map((t) => (
                          <SelectItem key={t.id} value={t.id}>{t.nombre}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Hilo</Label>
                    <Select
                      value={formData.hilo_id}
                      onValueChange={(value) => setFormData({ ...formData, hilo_id: value })}
                    >
                      <SelectTrigger data-testid="select-hilo">
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>
                      <SelectContent>
                        {hilos.map((h) => (
                          <SelectItem key={h.id} value={h.id}>{h.nombre}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="materiales" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label>Lista de Materiales (BOM)</Label>
                  <p className="text-xs text-muted-foreground">
                    Items del inventario necesarios para este modelo
                  </p>
                </div>

                <div className="flex gap-2">
                  <Select
                    value={materialToAdd.item_id}
                    onValueChange={(value) => setMaterialToAdd({ ...materialToAdd, item_id: value })}
                  >
                    <SelectTrigger className="flex-1" data-testid="select-material-item">
                      <SelectValue placeholder="Seleccionar item..." />
                    </SelectTrigger>
                    <SelectContent>
                      {inventarioItems
                        .filter(i => !formData.materiales.some(m => m.item_id === i.id))
                        .map((item) => (
                          <SelectItem key={item.id} value={item.id}>
                            {item.codigo ? `${item.codigo} - ` : ''}{item.nombre}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={materialToAdd.cantidad_estimada || ''}
                    onChange={(e) => setMaterialToAdd({ ...materialToAdd, cantidad_estimada: parseFloat(e.target.value) || 0 })}
                    placeholder="Cant."
                    className="w-24 font-mono"
                    data-testid="input-material-cantidad"
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={handleAddMaterial}
                    data-testid="btn-agregar-material"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>

                {formData.materiales.length > 0 ? (
                  <div className="space-y-2 border rounded-md p-2">
                    {formData.materiales.map((mat) => (
                      <div key={mat.item_id} className="flex items-center justify-between p-2 bg-muted/50 rounded">
                        <span className="text-sm">{getItemName(mat.item_id)}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono">
                            {mat.cantidad_estimada} {getItemUnidad(mat.item_id)}
                          </span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => handleRemoveMaterial(mat.item_id)}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4 border-2 border-dashed rounded-md">
                    No hay materiales agregados
                  </p>
                )}
              </TabsContent>

              <TabsContent value="tallas" className="space-y-4 mt-4">
                {editingItem ? (
                  <ModelosTallasTab modeloId={editingItem.id} />
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Primero crea el modelo para poder asignarle tallas.
                  </p>
                )}
              </TabsContent>

              <TabsContent value="bom" className="space-y-4 mt-4">
                {editingItem ? (
                  <ModelosBOMTab modeloId={editingItem.id} />
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Primero crea el modelo para poder definir su BOM.
                  </p>
                )}
              </TabsContent>

              <TabsContent value="produccion" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label>Ruta de Producción</Label>
                  <p className="text-xs text-muted-foreground">
                    Define la secuencia de estados para los registros de este modelo
                  </p>
                  <Select
                    value={formData.ruta_produccion_id}
                    onValueChange={(value) => setFormData({ ...formData, ruta_produccion_id: value === 'none' ? '' : value })}
                  >
                    <SelectTrigger data-testid="select-ruta">
                      <SelectValue placeholder="Seleccionar ruta..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Sin ruta (estados globales)</SelectItem>
                      {rutas.map((r) => (
                        <SelectItem key={r.id} value={r.id}>
                          {r.nombre} ({r.etapas?.length || 0} etapas)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Servicios Requeridos</Label>
                  <p className="text-xs text-muted-foreground">
                    Servicios que se usarán para este modelo (sin asignar persona aún)
                  </p>
                  <div className="grid grid-cols-2 gap-2 border rounded-md p-3">
                    {servicios.map((srv) => (
                      <label
                        key={srv.id}
                        className="flex items-center gap-2 p-2 rounded hover:bg-muted cursor-pointer"
                      >
                        <Checkbox
                          checked={formData.servicios_ids.includes(srv.id)}
                          onCheckedChange={() => handleToggleServicio(srv.id)}
                          data-testid={`checkbox-servicio-${srv.id}`}
                        />
                        <span className="text-sm">{srv.nombre}</span>
                      </label>
                    ))}
                    {servicios.length === 0 && (
                      <p className="col-span-2 text-sm text-muted-foreground text-center py-2">
                        No hay servicios disponibles
                      </p>
                    )}
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            <DialogFooter className="mt-6">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" data-testid="btn-guardar-modelo">
                {editingItem ? 'Guardar Cambios' : 'Crear Modelo'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

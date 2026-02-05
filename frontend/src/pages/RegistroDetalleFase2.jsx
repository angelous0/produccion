import { useEffect, useState, useRef, useCallback } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { 
  Scissors, Package, BookmarkCheck, LogOut, RefreshCw, 
  AlertTriangle, CheckCircle2, Clock, Loader2 
} from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ==================== PESTAÑA TALLAS (CORTE) ====================
const TallasTab = ({ registroId, onTotalChange }) => {
  const [data, setData] = useState({ tallas: [], total_prendas: 0 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState({});
  const debounceTimers = useRef({});

  const fetchTallas = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/registros/${registroId}/tallas`);
      setData(res.data);
      onTotalChange?.(res.data.total_prendas);
    } catch (error) {
      toast.error('Error al cargar tallas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (registroId) fetchTallas();
    return () => {
      Object.values(debounceTimers.current).forEach(clearTimeout);
    };
  }, [registroId]);

  const handleCantidadChange = (tallaId, value) => {
    const cantidad = parseInt(value) || 0;
    
    // Actualizar localmente
    setData(prev => {
      const newTallas = prev.tallas.map(t => 
        t.talla_id === tallaId ? { ...t, cantidad_real: cantidad } : t
      );
      const newTotal = newTallas.reduce((sum, t) => sum + t.cantidad_real, 0);
      onTotalChange?.(newTotal);
      return { ...prev, tallas: newTallas, total_prendas: newTotal };
    });

    // Debounce para autosave
    if (debounceTimers.current[tallaId]) {
      clearTimeout(debounceTimers.current[tallaId]);
    }
    
    setSaving(prev => ({ ...prev, [tallaId]: true }));
    
    debounceTimers.current[tallaId] = setTimeout(async () => {
      try {
        await axios.put(`${API}/registros/${registroId}/tallas/${tallaId}`, {
          cantidad_real: cantidad
        });
      } catch (error) {
        toast.error('Error al guardar cantidad');
      } finally {
        setSaving(prev => ({ ...prev, [tallaId]: false }));
      }
    }, 500);
  };

  if (loading) {
    return <div className="text-center py-8"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></div>;
  }

  if (data.tallas.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-yellow-500" />
        <p>El modelo de este registro no tiene tallas asignadas.</p>
        <p className="text-sm">Asigna tallas al modelo desde la página de Modelos.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Cantidades por Talla (Corte)</h3>
          <p className="text-sm text-muted-foreground">Ingresa la cantidad real cortada por talla</p>
        </div>
        <Badge variant="outline" className="text-lg px-4 py-2">
          Total: {data.total_prendas} prendas
        </Badge>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {data.tallas.map(t => (
          <div key={t.talla_id} className="relative">
            <label className="text-sm font-medium text-muted-foreground">{t.talla_nombre}</label>
            <div className="relative">
              <Input
                type="number"
                min="0"
                value={t.cantidad_real || ''}
                onChange={(e) => handleCantidadChange(t.talla_id, e.target.value)}
                className="mt-1 text-center font-mono"
                data-testid={`talla-input-${t.talla_id}`}
              />
              {saving[t.talla_id] && (
                <Loader2 className="h-4 w-4 animate-spin absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground" />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};


// ==================== PESTAÑA REQUERIMIENTO ====================
const RequerimientoTab = ({ registroId, totalPrendas }) => {
  const [data, setData] = useState({ lineas: [], resumen: {} });
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const fetchRequerimiento = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/registros/${registroId}/requerimiento`);
      setData(res.data);
    } catch (error) {
      // Si no hay requerimiento, es normal
      setData({ lineas: [], resumen: {} });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (registroId) fetchRequerimiento();
  }, [registroId]);

  const handleGenerar = async () => {
    if (totalPrendas <= 0) {
      toast.error('Primero ingresa cantidades por talla en la pestaña "Tallas"');
      return;
    }
    
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/registros/${registroId}/generar-requerimiento`);
      toast.success(`Requerimiento generado: ${res.data.lineas_creadas} creadas, ${res.data.lineas_actualizadas} actualizadas`);
      fetchRequerimiento();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al generar requerimiento');
    } finally {
      setGenerating(false);
    }
  };

  const getEstadoBadge = (estado) => {
    switch (estado) {
      case 'COMPLETO':
        return <Badge className="bg-green-500"><CheckCircle2 className="h-3 w-3 mr-1" />Completo</Badge>;
      case 'PARCIAL':
        return <Badge className="bg-yellow-500"><Clock className="h-3 w-3 mr-1" />Parcial</Badge>;
      default:
        return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" />Pendiente</Badge>;
    }
  };

  if (loading) {
    return <div className="text-center py-8"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Requerimiento de Materia Prima</h3>
          <p className="text-sm text-muted-foreground">Explosión del BOM basada en {totalPrendas} prendas</p>
        </div>
        <Button onClick={handleGenerar} disabled={generating} data-testid="btn-generar-req">
          {generating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
          {data.lineas.length > 0 ? 'Regenerar' : 'Generar desde BOM'}
        </Button>
      </div>

      {data.lineas.length === 0 ? (
        <div className="text-center py-8 border-2 border-dashed rounded-lg">
          <Package className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
          <p className="text-muted-foreground">No hay requerimiento generado</p>
          <p className="text-sm text-muted-foreground">Haz clic en &quot;Generar desde BOM&quot; para calcular</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">{data.resumen.total_requerido?.toFixed(2)}</div>
                <p className="text-xs text-muted-foreground">Total Requerido</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-blue-600">{data.resumen.total_reservado?.toFixed(2)}</div>
                <p className="text-xs text-muted-foreground">Total Reservado</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-green-600">{data.resumen.total_consumido?.toFixed(2)}</div>
                <p className="text-xs text-muted-foreground">Total Consumido</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-orange-600">{data.resumen.pendiente_reservar?.toFixed(2)}</div>
                <p className="text-xs text-muted-foreground">Pendiente Reservar</p>
              </CardContent>
            </Card>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Item</TableHead>
                <TableHead>Talla</TableHead>
                <TableHead className="text-right">Requerido</TableHead>
                <TableHead className="text-right">Reservado</TableHead>
                <TableHead className="text-right">Consumido</TableHead>
                <TableHead className="text-right">Pend. Reservar</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.lineas.map(l => (
                <TableRow key={l.id}>
                  <TableCell>
                    <div className="font-medium">{l.item_nombre}</div>
                    <div className="text-xs text-muted-foreground">{l.item_codigo}</div>
                  </TableCell>
                  <TableCell>{l.talla_nombre || 'Todas'}</TableCell>
                  <TableCell className="text-right font-mono">{parseFloat(l.cantidad_requerida).toFixed(2)}</TableCell>
                  <TableCell className="text-right font-mono text-blue-600">{parseFloat(l.cantidad_reservada).toFixed(2)}</TableCell>
                  <TableCell className="text-right font-mono text-green-600">{parseFloat(l.cantidad_consumida).toFixed(2)}</TableCell>
                  <TableCell className="text-right font-mono text-orange-600">{parseFloat(l.pendiente_reservar).toFixed(2)}</TableCell>
                  <TableCell>{getEstadoBadge(l.estado)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      )}
    </div>
  );
};


// ==================== PESTAÑA RESERVAS ====================
const ReservasTab = ({ registroId }) => {
  const [requerimiento, setRequerimiento] = useState({ lineas: [] });
  const [reservas, setReservas] = useState([]);
  const [disponibilidad, setDisponibilidad] = useState({});
  const [loading, setLoading] = useState(true);
  const [reservando, setReservando] = useState(false);
  const [cantidadesReservar, setCantidadesReservar] = useState({});

  const fetchData = async () => {
    try {
      setLoading(true);
      const [reqRes, resRes] = await Promise.all([
        axios.get(`${API}/registros/${registroId}/requerimiento`).catch(() => ({ data: { lineas: [] } })),
        axios.get(`${API}/registros/${registroId}/reservas`).catch(() => ({ data: { reservas: [] } })),
      ]);
      setRequerimiento(reqRes.data);
      setReservas(resRes.data.reservas || []);

      // Obtener disponibilidad por item
      const itemIds = [...new Set(reqRes.data.lineas?.map(l => l.item_id) || [])];
      const dispMap = {};
      for (const itemId of itemIds) {
        try {
          const dispRes = await axios.get(`${API}/inventario/${itemId}/disponibilidad`);
          dispMap[itemId] = dispRes.data;
        } catch (e) {
          dispMap[itemId] = { disponible: 0 };
        }
      }
      setDisponibilidad(dispMap);

      // Inicializar cantidades a reservar con el pendiente
      const inicial = {};
      (reqRes.data.lineas || []).forEach(l => {
        const key = `${l.item_id}_${l.talla_id || 'null'}`;
        inicial[key] = Math.min(l.pendiente_reservar, dispMap[l.item_id]?.disponible || 0);
      });
      setCantidadesReservar(inicial);
    } catch (error) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (registroId) fetchData();
  }, [registroId]);

  const handleReservarTodo = async () => {
    const lineas = requerimiento.lineas
      .filter(l => {
        const key = `${l.item_id}_${l.talla_id || 'null'}`;
        return cantidadesReservar[key] > 0;
      })
      .map(l => ({
        item_id: l.item_id,
        talla_id: l.talla_id || null,
        cantidad: cantidadesReservar[`${l.item_id}_${l.talla_id || 'null'}`]
      }));

    if (lineas.length === 0) {
      toast.error('No hay cantidades para reservar');
      return;
    }

    setReservando(true);
    try {
      await axios.post(`${API}/registros/${registroId}/reservas`, { lineas });
      toast.success('Reserva creada exitosamente');
      fetchData();
    } catch (error) {
      const errores = error.response?.data?.detail?.errores;
      if (errores) {
        errores.forEach(e => toast.error(e));
      } else {
        toast.error(error.response?.data?.detail || 'Error al crear reserva');
      }
    } finally {
      setReservando(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></div>;
  }

  if (requerimiento.lineas.length === 0) {
    return (
      <div className="text-center py-8 border-2 border-dashed rounded-lg">
        <BookmarkCheck className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
        <p className="text-muted-foreground">Primero genera el requerimiento desde la pestaña anterior</p>
      </div>
    );
  }

  // Mostrar TODOS los items (no solo pendientes) para poder reservar más
  const itemsConDisponibilidad = requerimiento.lineas.filter(l => (disponibilidad[l.item_id]?.disponible || 0) > 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Reservar Materia Prima</h3>
          <p className="text-sm text-muted-foreground">Bloquea stock para este registro (puedes reservar más del requerimiento original)</p>
        </div>
        <Button onClick={handleReservarTodo} disabled={reservando || itemsConDisponibilidad.length === 0} data-testid="btn-reservar">
          {reservando ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <BookmarkCheck className="h-4 w-4 mr-2" />}
          Reservar Seleccionados
        </Button>
      </div>

      {itemsConDisponibilidad.length === 0 ? (
        <div className="text-center py-4 bg-yellow-50 rounded-lg">
          <AlertTriangle className="h-6 w-6 mx-auto mb-2 text-yellow-600" />
          <p className="text-yellow-700">No hay stock disponible para reservar</p>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Item</TableHead>
              <TableHead>Talla</TableHead>
              <TableHead className="text-right">Requerido</TableHead>
              <TableHead className="text-right">Ya Reservado</TableHead>
              <TableHead className="text-right">Disponible</TableHead>
              <TableHead className="text-right w-[150px]">A Reservar</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {itemsConDisponibilidad.map(l => {
              const key = `${l.item_id}_${l.talla_id || 'null'}`;
              const disp = disponibilidad[l.item_id]?.disponible || 0;
              return (
                <TableRow key={l.id}>
                  <TableCell>
                    <div className="font-medium">{l.item_nombre}</div>
                    <div className="text-xs text-muted-foreground">
                      {l.item_codigo}
                      {l.control_por_rollos && <Badge variant="outline" className="ml-2 text-xs">TELA</Badge>}
                    </div>
                  </TableCell>
                  <TableCell>{l.talla_nombre || 'Todas'}</TableCell>
                  <TableCell className="text-right font-mono">{parseFloat(l.cantidad_requerida).toFixed(2)}</TableCell>
                  <TableCell className="text-right font-mono text-blue-600">{parseFloat(l.cantidad_reservada).toFixed(2)}</TableCell>
                  <TableCell className="text-right font-mono">
                    <span className="text-green-600">{disp.toFixed(2)}</span>
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      min="0"
                      max={disp}
                      step="0.01"
                      value={cantidadesReservar[key] || 0}
                      onChange={(e) => setCantidadesReservar(prev => ({
                        ...prev,
                        [key]: Math.min(parseFloat(e.target.value) || 0, disp)
                      }))}
                      className="text-right font-mono"
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      {reservas.length > 0 && (
        <div className="mt-6">
          <h4 className="font-medium mb-2">Historial de Reservas</h4>
          <div className="space-y-2">
            {reservas.map(r => (
              <Card key={r.id}>
                <CardContent className="py-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <Badge variant={r.estado === 'ACTIVA' ? 'default' : 'secondary'}>{r.estado}</Badge>
                      <span className="ml-2 text-sm text-muted-foreground">
                        {new Date(r.fecha).toLocaleString()}
                      </span>
                    </div>
                    <span className="text-sm">{r.lineas?.length || 0} líneas</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};


// ==================== PESTAÑA SALIDAS ====================
const SalidasTab = ({ registroId }) => {
  const [requerimiento, setRequerimiento] = useState({ lineas: [] });
  const [salidas, setSalidas] = useState([]);
  const [inventario, setInventario] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creando, setCreando] = useState(false);
  const [modoExtra, setModoExtra] = useState(false);
  
  // Form state
  const [selectedItem, setSelectedItem] = useState(null);
  const [selectedRollo, setSelectedRollo] = useState('');
  const [cantidad, setCantidad] = useState('');
  const [rollosDisponibles, setRollosDisponibles] = useState([]);
  const [observaciones, setObservaciones] = useState('');
  const [motivoExtra, setMotivoExtra] = useState('Consumo adicional');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [reqRes, salRes, invRes] = await Promise.all([
        axios.get(`${API}/registros/${registroId}/requerimiento`).catch(() => ({ data: { lineas: [] } })),
        axios.get(`${API}/inventario-salidas?registro_id=${registroId}`).catch(() => ({ data: [] })),
        axios.get(`${API}/inventario`).catch(() => ({ data: [] })),
      ]);
      setRequerimiento(reqRes.data);
      setSalidas(salRes.data);
      setInventario(invRes.data);
    } catch (error) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (registroId) fetchData();
  }, [registroId]);

  const handleSelectItem = async (linea) => {
    setSelectedItem(linea);
    setSelectedRollo('');
    setCantidad('');
    setRollosDisponibles([]);

    if (linea.control_por_rollos) {
      try {
        const res = await axios.get(`${API}/inventario/${linea.item_id}`);
        setRollosDisponibles(res.data.rollos || []);
      } catch (error) {
        toast.error('Error al cargar rollos');
      }
    }
  };

  const handleSelectItemExtra = async (itemId) => {
    const item = inventario.find(i => i.id === itemId);
    if (!item) return;
    
    setSelectedItem({
      item_id: item.id,
      item_nombre: item.nombre,
      item_codigo: item.codigo,
      item_unidad: item.unidad_medida,
      control_por_rollos: item.control_por_rollos,
      talla_id: null,
      pendiente_consumir: item.stock_actual
    });
    setSelectedRollo('');
    setCantidad('');
    setRollosDisponibles([]);

    if (item.control_por_rollos) {
      try {
        const res = await axios.get(`${API}/inventario/${item.id}`);
        setRollosDisponibles(res.data.rollos || []);
      } catch (error) {
        toast.error('Error al cargar rollos');
      }
    }
  };

  const handleCrearSalida = async () => {
    if (!selectedItem) {
      toast.error('Selecciona un item');
      return;
    }
    
    const cant = parseFloat(cantidad);
    if (!cant || cant <= 0) {
      toast.error('Ingresa una cantidad válida');
      return;
    }

    if (selectedItem.control_por_rollos && !selectedRollo) {
      toast.error('Selecciona un rollo para este item');
      return;
    }

    setCreando(true);
    try {
      if (modoExtra) {
        // Salida Extra - sin validar reserva
        await axios.post(`${API}/inventario-salidas/extra`, {
          item_id: selectedItem.item_id,
          cantidad: cant,
          registro_id: registroId,
          talla_id: selectedItem.talla_id || null,
          rollo_id: selectedItem.control_por_rollos ? selectedRollo : null,
          observaciones,
          motivo: motivoExtra
        });
        toast.success('Salida extra registrada');
      } else {
        // Salida normal - valida reserva
        await axios.post(`${API}/inventario-salidas`, {
          item_id: selectedItem.item_id,
          cantidad: cant,
          registro_id: registroId,
          talla_id: selectedItem.talla_id || null,
          rollo_id: selectedItem.control_por_rollos ? selectedRollo : null,
          observaciones
        });
        toast.success('Salida registrada');
      }
      setSelectedItem(null);
      setCantidad('');
      setSelectedRollo('');
      setObservaciones('');
      setMotivoExtra('Consumo adicional');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear salida');
    } finally {
      setCreando(false);
    }
  };

  const usarTodoRollo = () => {
    const rollo = rollosDisponibles.find(r => r.id === selectedRollo);
    if (rollo) {
      setCantidad(rollo.metraje_disponible.toString());
    }
  };

  if (loading) {
    return <div className="text-center py-8"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></div>;
  }

  const pendientes = requerimiento.lineas.filter(l => l.pendiente_consumir > 0);

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold">Registrar Salida de MP</h3>
        <p className="text-sm text-muted-foreground">Consume material reservado</p>
      </div>

      {pendientes.length === 0 && requerimiento.lineas.length > 0 ? (
        <div className="text-center py-4 bg-green-50 rounded-lg">
          <CheckCircle2 className="h-6 w-6 mx-auto mb-2 text-green-600" />
          <p className="text-green-700">Todo el requerimiento ha sido consumido</p>
        </div>
      ) : requerimiento.lineas.length === 0 ? (
        <div className="text-center py-8 border-2 border-dashed rounded-lg">
          <LogOut className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
          <p className="text-muted-foreground">Primero genera y reserva el requerimiento</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {/* Lista de items pendientes */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Items con Reserva Pendiente</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 max-h-[300px] overflow-y-auto">
              {pendientes.map(l => (
                <div
                  key={l.id}
                  onClick={() => handleSelectItem(l)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedItem?.id === l.id ? 'border-primary bg-primary/5' : 'hover:bg-muted/50'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-medium">{l.item_nombre}</div>
                      <div className="text-xs text-muted-foreground">
                        {l.item_codigo}
                        {l.control_por_rollos && <Badge variant="outline" className="ml-1 text-xs">TELA</Badge>}
                      </div>
                    </div>
                    <Badge variant="secondary">
                      {parseFloat(l.pendiente_consumir).toFixed(2)} pend.
                    </Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Formulario de salida */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Nueva Salida</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedItem ? (
                <>
                  <div className="p-3 bg-muted/50 rounded-lg">
                    <div className="font-medium">{selectedItem.item_nombre}</div>
                    <div className="text-sm text-muted-foreground">
                      Reservado pendiente: {parseFloat(selectedItem.pendiente_consumir).toFixed(2)} {selectedItem.item_unidad}
                    </div>
                  </div>

                  {selectedItem.control_por_rollos && (
                    <div>
                      <label className="text-sm font-medium">Rollo *</label>
                      <Select value={selectedRollo} onValueChange={setSelectedRollo}>
                        <SelectTrigger data-testid="select-rollo">
                          <SelectValue placeholder="Seleccionar rollo..." />
                        </SelectTrigger>
                        <SelectContent>
                          {rollosDisponibles.map(r => (
                            <SelectItem key={r.id} value={r.id}>
                              {r.numero_rollo || r.id.slice(0, 8)} - {r.metraje_disponible}m disp.
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {selectedRollo && (
                        <Button
                          type="button"
                          variant="link"
                          size="sm"
                          className="mt-1 h-auto p-0"
                          onClick={usarTodoRollo}
                        >
                          Usar todo el rollo
                        </Button>
                      )}
                    </div>
                  )}

                  <div>
                    <label className="text-sm font-medium">Cantidad *</label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      max={selectedItem.pendiente_consumir}
                      value={cantidad}
                      onChange={(e) => setCantidad(e.target.value)}
                      placeholder={`Máx: ${parseFloat(selectedItem.pendiente_consumir).toFixed(2)}`}
                      className="font-mono"
                      data-testid="input-cantidad-salida"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium">Observaciones</label>
                    <Input
                      value={observaciones}
                      onChange={(e) => setObservaciones(e.target.value)}
                      placeholder="Opcional..."
                    />
                  </div>

                  <Button
                    onClick={handleCrearSalida}
                    disabled={creando}
                    className="w-full"
                    data-testid="btn-crear-salida"
                  >
                    {creando ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <LogOut className="h-4 w-4 mr-2" />}
                    Registrar Salida
                  </Button>
                </>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>Selecciona un item de la lista</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Historial de salidas */}
      {salidas.length > 0 && (
        <div className="mt-6">
          <h4 className="font-medium mb-2">Salidas Registradas</h4>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fecha</TableHead>
                <TableHead>Item</TableHead>
                <TableHead>Rollo</TableHead>
                <TableHead className="text-right">Cantidad</TableHead>
                <TableHead className="text-right">Costo</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {salidas.map(s => (
                <TableRow key={s.id}>
                  <TableCell className="text-sm">{new Date(s.fecha).toLocaleString()}</TableCell>
                  <TableCell>{s.item_nombre}</TableCell>
                  <TableCell>{s.rollo_numero || '-'}</TableCell>
                  <TableCell className="text-right font-mono">{parseFloat(s.cantidad).toFixed(2)}</TableCell>
                  <TableCell className="text-right font-mono">${parseFloat(s.costo_total).toFixed(2)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
};


// ==================== COMPONENTE PRINCIPAL ====================
export const RegistroDetalleFase2 = ({ registroId, registro }) => {
  const [totalPrendas, setTotalPrendas] = useState(0);

  if (!registroId) {
    return <div className="text-center py-8 text-muted-foreground">Selecciona un registro</div>;
  }

  return (
    <div className="space-y-4">
      {registro && (
        <div className="flex items-center gap-4 mb-4">
          <Badge variant="outline" className="text-lg">N° Corte: {registro.n_corte}</Badge>
          <Badge>{registro.estado}</Badge>
          {registro.urgente && <Badge variant="destructive">URGENTE</Badge>}
        </div>
      )}

      <Tabs defaultValue="tallas" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="tallas" data-testid="tab-tallas">
            <Scissors className="h-4 w-4 mr-2" />
            Tallas
          </TabsTrigger>
          <TabsTrigger value="requerimiento" data-testid="tab-requerimiento">
            <Package className="h-4 w-4 mr-2" />
            Requerimiento
          </TabsTrigger>
          <TabsTrigger value="reservas" data-testid="tab-reservas">
            <BookmarkCheck className="h-4 w-4 mr-2" />
            Reservas
          </TabsTrigger>
          <TabsTrigger value="salidas" data-testid="tab-salidas">
            <LogOut className="h-4 w-4 mr-2" />
            Salidas
          </TabsTrigger>
        </TabsList>

        <TabsContent value="tallas" className="mt-4">
          <TallasTab registroId={registroId} onTotalChange={setTotalPrendas} />
        </TabsContent>

        <TabsContent value="requerimiento" className="mt-4">
          <RequerimientoTab registroId={registroId} totalPrendas={totalPrendas} />
        </TabsContent>

        <TabsContent value="reservas" className="mt-4">
          <ReservasTab registroId={registroId} />
        </TabsContent>

        <TabsContent value="salidas" className="mt-4">
          <SalidasTab registroId={registroId} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default RegistroDetalleFase2;

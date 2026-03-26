import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from '../components/ui/collapsible';
import { SearchableSelect } from './SearchableSelect';
import {
  Package, PackageCheck, PackageMinus, PackageX, RefreshCw,
  ChevronDown, ChevronUp, Loader2, Plus, Trash2, BookOpen,
  ArrowDownCircle, ArrowUpCircle, AlertTriangle,
} from 'lucide-react';
import { toast } from 'sonner';
import { NumericInput } from './ui/numeric-input';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MaterialesTab = ({ registroId, totalPrendas }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generando, setGenerando] = useState(false);
  const [procesando, setProcesando] = useState(false);

  // Cantidades a reservar/dar salida por línea
  const [cantidades, setCantidades] = useState({});
  const [accion, setAccion] = useState('salida'); // 'reservar' o 'salida'

  // Modo extra: agregar items no incluidos en BOM
  const [modoExtra, setModoExtra] = useState(false);
  const [inventario, setInventario] = useState([]);
  const [extraItem, setExtraItem] = useState(null);
  const [extraCantidad, setExtraCantidad] = useState('');

  // Historial colapsable
  const [histReservasOpen, setHistReservasOpen] = useState(false);
  const [histSalidasOpen, setHistSalidasOpen] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/registros/${registroId}/materiales`);
      setData(res.data);
    } catch (err) {
      toast.error('Error al cargar materiales');
    } finally {
      setLoading(false);
    }
  }, [registroId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const generarRequerimiento = async () => {
    setGenerando(true);
    try {
      const res = await axios.post(`${API}/registros/${registroId}/generar-requerimiento`);
      toast.success(`Requerimiento generado: ${res.data.lineas_creadas} líneas creadas, ${res.data.lineas_actualizadas} actualizadas`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al generar requerimiento');
    } finally {
      setGenerando(false);
    }
  };

  const setCantidad = (lineaKey, value) => {
    setCantidades(prev => ({ ...prev, [lineaKey]: value }));
  };

  const getLineaKey = (l) => `${l.item_id}_${l.talla_id || 'null'}`;

  const ejecutarReserva = async () => {
    const lineas = Object.entries(cantidades)
      .filter(([, v]) => parseFloat(v) > 0)
      .map(([key, cantidad]) => {
        const [item_id, talla_id] = key.split('_');
        return { item_id, talla_id: talla_id === 'null' ? null : talla_id, cantidad: parseFloat(cantidad) };
      });
    if (!lineas.length) return toast.error('Ingresa cantidades a reservar');
    setProcesando(true);
    try {
      await axios.post(`${API}/registros/${registroId}/reservas`, { lineas });
      toast.success('Reserva creada');
      setCantidades({});
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al crear reserva');
    } finally {
      setProcesando(false);
    }
  };

  const ejecutarSalida = async () => {
    const lineas = Object.entries(cantidades)
      .filter(([, v]) => parseFloat(v) > 0)
      .map(([key, cantidad]) => {
        const [item_id, talla_id] = key.split('_');
        return { item_id, talla_id: talla_id === 'null' ? null : talla_id, cantidad: parseFloat(cantidad) };
      });
    if (!lineas.length) return toast.error('Ingresa cantidades para dar salida');
    setProcesando(true);
    try {
      for (const l of lineas) {
        await axios.post(`${API}/inventario-salidas`, {
          item_id: l.item_id,
          cantidad: l.cantidad,
          registro_id: registroId,
          talla_id: l.talla_id,
          fecha: new Date().toISOString(),
          observaciones: 'Salida desde Materiales OP',
        });
      }
      toast.success(`${lineas.length} salida(s) registrada(s)`);
      setCantidades({});
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al registrar salida');
    } finally {
      setProcesando(false);
    }
  };

  const ejecutarSalidaExtra = async () => {
    if (!extraItem || !extraCantidad) return toast.error('Selecciona item y cantidad');
    setProcesando(true);
    try {
      await axios.post(`${API}/inventario-salidas`, {
        item_id: extraItem,
        cantidad: parseFloat(extraCantidad),
        registro_id: registroId,
        fecha: new Date().toISOString(),
        observaciones: 'Salida extra (fuera de BOM)',
      });
      toast.success('Salida extra registrada');
      setExtraItem(null);
      setExtraCantidad('');
      setModoExtra(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al registrar salida extra');
    } finally {
      setProcesando(false);
    }
  };

  const anularReserva = async (reservaId) => {
    try {
      await axios.delete(`${API}/reservas/${reservaId}`);
      toast.success('Reserva anulada');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al anular reserva');
    }
  };

  const llenarPendientes = () => {
    if (!data?.lineas) return;
    const nuevas = {};
    data.lineas.forEach(l => {
      const pendiente = parseFloat(l.pendiente) || 0;
      if (pendiente > 0) {
        nuevas[getLineaKey(l)] = pendiente;
      }
    });
    setCantidades(nuevas);
  };

  // Cargar inventario para modo extra
  const loadInventarioExtra = async () => {
    if (inventario.length) { setModoExtra(true); return; }
    try {
      const res = await axios.get(`${API}/inventario?all=true`);
      const items = Array.isArray(res.data) ? res.data : res.data.items || [];
      setInventario(items);
      setModoExtra(true);
    } catch { toast.error('Error al cargar inventario'); }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /> <span className="ml-2">Cargando materiales...</span></div>;
  }

  const tieneReq = data?.tiene_requerimiento;
  const lineas = data?.lineas || [];
  const resumen = data?.resumen || {};
  const reservas = data?.reservas || [];
  const salidas = data?.salidas || [];
  const reservasActivas = reservas.filter(r => r.estado === 'ACTIVA');

  return (
    <div className="space-y-4" data-testid="materiales-tab">
      {/* Header con acciones */}
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-base">Materiales de la OP</h4>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={fetchData} data-testid="btn-refresh-materiales">
            <RefreshCw className="h-3.5 w-3.5 mr-1" /> Actualizar
          </Button>
          <Button type="button" size="sm" onClick={generarRequerimiento} disabled={generando || totalPrendas <= 0}
            data-testid="btn-generar-req"
          >
            {generando ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <BookOpen className="h-3.5 w-3.5 mr-1" />}
            {tieneReq ? 'Regenerar desde BOM' : 'Generar desde BOM'}
          </Button>
        </div>
      </div>

      {/* Resumen rápido */}
      {tieneReq && (
        <div className="grid grid-cols-4 gap-3">
          <Card className="py-2">
            <CardContent className="p-3 text-center">
              <p className="text-xs text-muted-foreground">Requerido</p>
              <p className="text-lg font-bold" data-testid="resumen-requerido">{resumen.total_requerido?.toFixed(1)}</p>
            </CardContent>
          </Card>
          <Card className="py-2">
            <CardContent className="p-3 text-center">
              <p className="text-xs text-muted-foreground">Reservado</p>
              <p className="text-lg font-bold text-blue-600" data-testid="resumen-reservado">{resumen.total_reservado?.toFixed(1)}</p>
            </CardContent>
          </Card>
          <Card className="py-2">
            <CardContent className="p-3 text-center">
              <p className="text-xs text-muted-foreground">Consumido</p>
              <p className="text-lg font-bold text-green-600" data-testid="resumen-consumido">{resumen.total_consumido?.toFixed(1)}</p>
            </CardContent>
          </Card>
          <Card className={`py-2 ${resumen.total_pendiente > 0 ? 'border-yellow-500/50' : 'border-green-500/50'}`}>
            <CardContent className="p-3 text-center">
              <p className="text-xs text-muted-foreground">Pendiente</p>
              <p className={`text-lg font-bold ${resumen.total_pendiente > 0 ? 'text-yellow-600' : 'text-green-600'}`}
                data-testid="resumen-pendiente">{resumen.total_pendiente?.toFixed(1)}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Sin requerimiento */}
      {!tieneReq && (
        <Card className="border-dashed">
          <CardContent className="py-8 text-center">
            <Package className="h-10 w-10 mx-auto text-muted-foreground mb-2" />
            <p className="font-medium">Sin requerimiento de materiales</p>
            <p className="text-sm text-muted-foreground mt-1">
              {totalPrendas > 0
                ? 'Haz click en "Generar desde BOM" para calcular los materiales necesarios.'
                : 'Primero define las cantidades por talla en la pestaña Tallas.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Tabla unificada */}
      {tieneReq && lineas.length > 0 && (
        <Card>
          <CardContent className="p-0">
            {/* Selector de acción y botón llenar */}
            <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
              <div className="flex items-center gap-2">
                <Label className="text-xs">Accion:</Label>
                <div className="flex rounded-md border overflow-hidden">
                  <button type="button"
                    className={`px-3 py-1 text-xs font-medium transition-colors ${accion === 'salida' ? 'bg-green-600 text-white' : 'bg-background hover:bg-muted'}`}
                    onClick={() => setAccion('salida')} data-testid="btn-modo-salida"
                  >
                    <ArrowUpCircle className="h-3 w-3 inline mr-1" />Dar Salida
                  </button>
                  <button type="button"
                    className={`px-3 py-1 text-xs font-medium transition-colors ${accion === 'reservar' ? 'bg-blue-600 text-white' : 'bg-background hover:bg-muted'}`}
                    onClick={() => setAccion('reservar')} data-testid="btn-modo-reservar"
                  >
                    <PackageCheck className="h-3 w-3 inline mr-1" />Reservar
                  </button>
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={llenarPendientes}
                  data-testid="btn-llenar-pendientes"
                >
                  Llenar pendientes
                </Button>
                <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setCantidades({})}
                  data-testid="btn-limpiar-cantidades"
                >
                  Limpiar
                </Button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Item</TableHead>
                    <TableHead>Talla</TableHead>
                    <TableHead className="text-right">Req.</TableHead>
                    <TableHead className="text-right">Reserv.</TableHead>
                    <TableHead className="text-right">Salido</TableHead>
                    <TableHead className="text-right">Pend.</TableHead>
                    <TableHead className="text-right">Disponible</TableHead>
                    <TableHead className="w-[120px] text-center">Cantidad</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lineas.map((l) => {
                    const key = getLineaKey(l);
                    const pendiente = parseFloat(l.pendiente) || 0;
                    const completo = pendiente <= 0;
                    return (
                      <TableRow key={key} className={completo ? 'opacity-50' : ''} data-testid={`material-row-${key}`}>
                        <TableCell>
                          <div>
                            <span className="text-sm font-medium">{l.item_nombre}</span>
                            <span className="block text-xs text-muted-foreground font-mono">{l.item_codigo} · {l.item_unidad}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {l.talla_nombre ? <Badge variant="outline" className="text-xs">{l.talla_nombre}</Badge> : <span className="text-xs text-muted-foreground">General</span>}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">{parseFloat(l.cantidad_requerida).toFixed(1)}</TableCell>
                        <TableCell className="text-right font-mono text-sm text-blue-600">{parseFloat(l.cantidad_reservada).toFixed(1)}</TableCell>
                        <TableCell className="text-right font-mono text-sm text-green-600">{parseFloat(l.cantidad_consumida).toFixed(1)}</TableCell>
                        <TableCell className={`text-right font-mono text-sm font-semibold ${completo ? 'text-green-600' : 'text-yellow-600'}`}>
                          {completo ? <PackageCheck className="h-4 w-4 inline text-green-600" /> : pendiente.toFixed(1)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-muted-foreground">{l.disponible?.toFixed(1) || '-'}</TableCell>
                        <TableCell className="text-center">
                          {!completo && (
                            <NumericInput
                              className="h-7 w-[100px] text-center font-mono text-sm"
                              min={0}
                              step={1}
                              value={cantidades[key] || ''}
                              onChange={(e) => setCantidad(key, e.target.value)}
                              placeholder="0"
                              data-testid={`input-cantidad-${key}`}
                            />
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
            {/* Botón de acción */}
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <Button type="button" variant="outline" size="sm" onClick={loadInventarioExtra} data-testid="btn-salida-extra">
                <Plus className="h-3.5 w-3.5 mr-1" /> Salida extra (fuera de BOM)
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={procesando || Object.values(cantidades).every(v => !v || parseFloat(v) <= 0)}
                onClick={accion === 'salida' ? ejecutarSalida : ejecutarReserva}
                className={accion === 'salida' ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'}
                data-testid="btn-ejecutar-accion"
              >
                {procesando && <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />}
                {accion === 'salida' ? (
                  <><ArrowUpCircle className="h-3.5 w-3.5 mr-1" /> Dar Salida</>
                ) : (
                  <><PackageCheck className="h-3.5 w-3.5 mr-1" /> Reservar</>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Salida Extra */}
      {modoExtra && (
        <Card className="border-dashed">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Salida extra (fuera de BOM)</CardTitle>
              <Button type="button" variant="ghost" size="sm" onClick={() => setModoExtra(false)}><Trash2 className="h-3.5 w-3.5" /></Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <Label className="text-xs">Item</Label>
                <SearchableSelect
                  value={extraItem}
                  onValueChange={setExtraItem}
                  options={inventario.filter(i => i.tipo_item === 'MP')}
                  placeholder="Buscar item..."
                  searchPlaceholder="Buscar por nombre o codigo..."
                  testId="combobox-extra-item"
                  renderOption={(o) => <><span className="font-mono text-xs mr-2 text-muted-foreground">{o.codigo}</span><span className="truncate">{o.nombre}</span></>}
                />
              </div>
              <div className="w-[120px]">
                <Label className="text-xs">Cantidad</Label>
                <NumericInput min={0} step={1} value={extraCantidad} onChange={(e) => setExtraCantidad(e.target.value)}
                  className="h-9" placeholder="0" data-testid="input-extra-cantidad" />
              </div>
              <Button type="button" size="sm" className="bg-green-600 hover:bg-green-700" disabled={procesando}
                onClick={ejecutarSalidaExtra} data-testid="btn-ejecutar-extra"
              >
                Dar Salida
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Historial Reservas */}
      {reservas.length > 0 && (
        <Collapsible open={histReservasOpen} onOpenChange={setHistReservasOpen}>
          <CollapsibleTrigger asChild>
            <Button type="button" variant="ghost" className="w-full justify-between px-3 h-9">
              <span className="text-sm font-medium">
                Reservas ({reservas.length}) {reservasActivas.length > 0 && <Badge className="ml-1 text-xs">{reservasActivas.length} activas</Badge>}
              </span>
              {histReservasOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="space-y-2 mt-2">
            {reservas.map(r => (
              <Card key={r.id} className={r.estado !== 'ACTIVA' ? 'opacity-50' : ''}>
                <CardContent className="py-2 px-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Badge variant={r.estado === 'ACTIVA' ? 'default' : 'secondary'} className="text-xs">{r.estado}</Badge>
                      <span className="text-xs text-muted-foreground">{r.fecha ? new Date(r.fecha).toLocaleString() : ''}</span>
                    </div>
                    {r.estado === 'ACTIVA' && (
                      <Button type="button" variant="outline" size="sm" className="text-destructive border-destructive/30 h-6 text-xs px-2"
                        onClick={() => anularReserva(r.id)} data-testid={`btn-anular-${r.id}`}
                      >
                        Anular
                      </Button>
                    )}
                  </div>
                  {r.lineas?.length > 0 && (
                    <div className="text-xs space-y-0.5 border-t pt-1 mt-1">
                      {r.lineas.map((l, i) => (
                        <div key={i} className="flex justify-between text-muted-foreground">
                          <span><span className="font-mono">{l.item_codigo}</span> — {l.item_nombre}{l.talla_nombre && ` (${l.talla_nombre})`}</span>
                          <span className="font-mono">{r.estado === 'ACTIVA' ? l.cantidad_activa : <span className="line-through">{parseFloat(l.cantidad_reservada).toFixed(1)}</span>} {l.item_unidad}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Historial Salidas */}
      {salidas.length > 0 && (
        <Collapsible open={histSalidasOpen} onOpenChange={setHistSalidasOpen}>
          <CollapsibleTrigger asChild>
            <Button type="button" variant="ghost" className="w-full justify-between px-3 h-9">
              <span className="text-sm font-medium">Salidas registradas ({salidas.length})</span>
              {histSalidasOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2">
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fecha</TableHead>
                      <TableHead>Item</TableHead>
                      <TableHead className="text-right">Cantidad</TableHead>
                      <TableHead className="text-right">Costo</TableHead>
                      <TableHead>Obs.</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {salidas.map(s => (
                      <TableRow key={s.id}>
                        <TableCell className="text-xs">{s.fecha ? new Date(s.fecha).toLocaleDateString() : '-'}</TableCell>
                        <TableCell className="text-sm">{s.item_nombre}</TableCell>
                        <TableCell className="text-right font-mono text-sm">{parseFloat(s.cantidad).toFixed(1)}</TableCell>
                        <TableCell className="text-right font-mono text-xs text-muted-foreground">
                          {s.costo_total ? `S/ ${parseFloat(s.costo_total).toFixed(2)}` : '-'}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground truncate max-w-[150px]">{s.observaciones || '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
};

export default MaterialesTab;

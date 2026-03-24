import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Separator } from './ui/separator';
import { Textarea } from './ui/textarea';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from './ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from './ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from './ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './ui/tabs';
import {
  AlertTriangle, Clock, CheckCircle2, XCircle, ArrowRight,
  Package, Wrench, Trash2, Plus, Eye, ChevronDown, ChevronUp,
  ArrowUpCircle, Shield, Timer, CircleDot,
} from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmtDate = (d) => {
  if (!d) return '-';
  const s = String(d).slice(0, 10);
  const [y, m, dd] = s.split('-');
  return `${dd}-${m}-${y?.slice(2)}`;
};

const BalanceCard = ({ label, value, color = 'default', sub }) => {
  const colors = {
    default: 'bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800',
    primary: 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800',
    danger: 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800',
    warning: 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800',
    success: 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800',
  };
  return (
    <div className={`rounded-lg border p-3 text-center ${colors[color] || colors.default}`} data-testid={`balance-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground truncate">{label}</p>
      <p className="text-lg font-bold font-mono">{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
};

const EventoIcon = ({ tipo }) => {
  const map = {
    MOVIMIENTO: <ArrowRight className="h-4 w-4 text-blue-500" />,
    MERMA: <AlertTriangle className="h-4 w-4 text-amber-500" />,
    FALLADO: <XCircle className="h-4 w-4 text-red-500" />,
    ARREGLO: <Wrench className="h-4 w-4 text-violet-500" />,
    DIVISION: <Package className="h-4 w-4 text-cyan-500" />,
  };
  return map[tipo] || <CircleDot className="h-4 w-4 text-muted-foreground" />;
};

const EventoBadge = ({ tipo }) => {
  const map = {
    MOVIMIENTO: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
    MERMA: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
    FALLADO: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
    ARREGLO: 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300',
    DIVISION: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-300',
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${map[tipo] || ''}`}>
      <EventoIcon tipo={tipo} />
      {tipo}
    </span>
  );
};

export const TrazabilidadPanel = ({ registroId, servicios = [], personas = [] }) => {
  const [balance, setBalance] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [fallados, setFallados] = useState([]);
  const [arreglos, setArreglos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('balance');

  // Dialogs
  const [falladoDialogOpen, setFalladoDialogOpen] = useState(false);
  const [arregloDialogOpen, setArregloDialogOpen] = useState(false);
  const [cierreArregloDialogOpen, setCierreArregloDialogOpen] = useState(false);
  const [selectedFallado, setSelectedFallado] = useState(null);
  const [selectedArreglo, setSelectedArreglo] = useState(null);

  const [falladoForm, setFalladoForm] = useState({
    cantidad_detectada: 0,
    cantidad_reparable: 0,
    cantidad_no_reparable: 0,
    destino_no_reparable: 'PENDIENTE',
    motivo: '',
    servicio_detectado_id: '',
    fecha_deteccion: '',
    observaciones: '',
  });

  const [arregloForm, setArregloForm] = useState({
    cantidad_enviada: 0,
    tipo: 'ARREGLO_EXTERNO',
    servicio_destino_id: '',
    persona_destino_id: '',
    fecha_envio: '',
    observaciones: '',
  });

  const [cierreForm, setCierreForm] = useState({
    cantidad_resuelta: 0,
    cantidad_no_resuelta: 0,
    resultado_final: 'BUENO',
    fecha_retorno: '',
    observaciones: '',
  });

  const getHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

  const fetchAll = useCallback(async () => {
    if (!registroId) return;
    setLoading(true);
    try {
      const hdrs = { Authorization: `Bearer ${localStorage.getItem('token')}` };
      const [balRes, tlRes, fRes, aRes] = await Promise.all([
        axios.get(`${API}/registros/${registroId}/resumen-cantidades`, { headers: hdrs }),
        axios.get(`${API}/registros/${registroId}/trazabilidad-completa`, { headers: hdrs }),
        axios.get(`${API}/fallados?registro_id=${registroId}`, { headers: hdrs }),
        axios.get(`${API}/arreglos?registro_id=${registroId}`, { headers: hdrs }),
      ]);
      setBalance(balRes.data);
      setTimeline(tlRes.data);
      setFallados(fRes.data);
      setArreglos(aRes.data);
    } catch (err) {
      console.error('Error fetching trazabilidad:', err);
    } finally {
      setLoading(false);
    }
  }, [registroId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ========== Handlers ==========
  const handleCreateFallado = async () => {
    try {
      await axios.post(`${API}/fallados`, {
        registro_id: registroId,
        ...falladoForm,
        servicio_detectado_id: falladoForm.servicio_detectado_id || null,
      }, { headers: getHeaders() });
      toast.success('Fallado registrado');
      setFalladoDialogOpen(false);
      resetFalladoForm();
      fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al crear fallado');
    }
  };

  const handleDeleteFallado = async (id) => {
    if (!window.confirm('Eliminar este registro de fallado?')) return;
    try {
      await axios.delete(`${API}/fallados/${id}`, { headers: getHeaders() });
      toast.success('Fallado eliminado');
      fetchAll();
    } catch (err) {
      toast.error('Error al eliminar');
    }
  };

  const handleCreateArreglo = async () => {
    if (!selectedFallado) return;
    try {
      await axios.post(`${API}/arreglos`, {
        fallado_id: selectedFallado.id,
        registro_id: registroId,
        ...arregloForm,
        servicio_destino_id: arregloForm.servicio_destino_id || null,
        persona_destino_id: arregloForm.persona_destino_id || null,
      }, { headers: getHeaders() });
      toast.success('Arreglo creado');
      setArregloDialogOpen(false);
      resetArregloForm();
      fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al crear arreglo');
    }
  };

  const handleCerrarArreglo = async () => {
    if (!selectedArreglo) return;
    try {
      await axios.put(`${API}/arreglos/${selectedArreglo.id}/cerrar`, cierreForm, { headers: getHeaders() });
      toast.success('Arreglo cerrado');
      setCierreArregloDialogOpen(false);
      fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al cerrar arreglo');
    }
  };

  const handleDeleteArreglo = async (id) => {
    if (!window.confirm('Eliminar este arreglo?')) return;
    try {
      await axios.delete(`${API}/arreglos/${id}`, { headers: getHeaders() });
      toast.success('Arreglo eliminado');
      fetchAll();
    } catch (err) {
      toast.error('Error al eliminar');
    }
  };

  const resetFalladoForm = () => setFalladoForm({
    cantidad_detectada: 0, cantidad_reparable: 0, cantidad_no_reparable: 0,
    destino_no_reparable: 'PENDIENTE', motivo: '', servicio_detectado_id: '',
    fecha_deteccion: '', observaciones: '',
  });

  const resetArregloForm = () => setArregloForm({
    cantidad_enviada: 0, tipo: 'ARREGLO_EXTERNO', servicio_destino_id: '',
    persona_destino_id: '', fecha_envio: '', observaciones: '',
  });

  const openArregloDialog = (fallado) => {
    setSelectedFallado(fallado);
    resetArregloForm();
    setArregloDialogOpen(true);
  };

  const openCierreDialog = (arreglo) => {
    setSelectedArreglo(arreglo);
    setCierreForm({
      cantidad_resuelta: 0, cantidad_no_resuelta: 0,
      resultado_final: 'BUENO', fecha_retorno: '', observaciones: '',
    });
    setCierreArregloDialogOpen(true);
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Cargando trazabilidad...
        </CardContent>
      </Card>
    );
  }

  const eventos = timeline?.eventos || [];
  const mermas = eventos.filter(e => e.tipo_evento === 'MERMA');
  const divisiones = eventos.filter(e => e.tipo_evento === 'DIVISION');

  return (
    <div className="space-y-4" data-testid="trazabilidad-panel">
      {/* Alertas */}
      {balance?.alertas?.length > 0 && (
        <div className="space-y-2">
          {balance.alertas.map((a, i) => (
            <div key={i} className={`flex items-center gap-2 p-3 rounded-lg border text-sm ${
              a.tipo === 'VENCIDO' ? 'bg-red-50 border-red-200 text-red-800 dark:bg-red-950/30 dark:border-red-800 dark:text-red-300' :
              a.tipo === 'MERMA' ? 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300' :
              'bg-orange-50 border-orange-200 text-orange-800 dark:bg-orange-950/30 dark:border-orange-800 dark:text-orange-300'
            }`} data-testid={`alerta-${a.tipo.toLowerCase()}`}>
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {a.mensaje}
            </div>
          ))}
        </div>
      )}

      {/* Balance del Lote */}
      {balance && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="h-4 w-4 text-blue-500" />
              Balance del Lote
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2">
              <BalanceCard label="Inicial" value={balance.cantidad_inicial} color="primary" />
              <BalanceCard label="Faltante" value={balance.extraviado_faltante} color={balance.extraviado_faltante > 0 ? 'warning' : 'default'} />
              <BalanceCard label="Fallados" value={balance.fallados_detectados} color={balance.fallados_detectados > 0 ? 'danger' : 'default'}
                sub={balance.fallados_detectados > 0 ? `${balance.reparables}R / ${balance.no_reparables}NR` : undefined} />
              <BalanceCard label="Reparados" value={balance.reparados_cerrados} color={balance.reparados_cerrados > 0 ? 'success' : 'default'} />
              <BalanceCard label="Pend. Arreglo" value={balance.pendientes_arreglo} color={balance.pendientes_arreglo > 0 ? 'warning' : 'default'}
                sub={balance.arreglos_vencidos > 0 ? `${balance.arreglos_vencidos} vencidos` : undefined} />
              <BalanceCard label="Liquidacion" value={balance.liquidacion + balance.segunda + balance.descarte}
                color={(balance.liquidacion + balance.segunda + balance.descarte) > 0 ? 'danger' : 'default'}
                sub={balance.liquidacion > 0 || balance.segunda > 0 || balance.descarte > 0
                  ? `L:${balance.liquidacion} S:${balance.segunda} D:${balance.descarte}` : undefined} />
            </div>

            {/* Padre / Hijos */}
            {(balance.padre || balance.hijos?.length > 0) && (
              <div className="mt-3 pt-3 border-t">
                <div className="flex flex-wrap gap-2 text-xs">
                  {balance.padre && (
                    <Badge variant="outline" className="gap-1">
                      <ArrowUpCircle className="h-3 w-3" /> Padre: {balance.padre.n_corte}
                    </Badge>
                  )}
                  {balance.hijos?.map(h => (
                    <Badge key={h.id} variant="outline" className="gap-1">
                      <Package className="h-3 w-3" /> {h.n_corte}: {h.prendas}p ({h.estado})
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full flex flex-wrap h-auto gap-1 p-1">
          <TabsTrigger value="balance" className="text-xs">Timeline</TabsTrigger>
          <TabsTrigger value="fallados" className="text-xs">
            Fallados {fallados.length > 0 && <Badge variant="destructive" className="ml-1 h-4 px-1 text-[10px]">{fallados.length}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="arreglos" className="text-xs">
            Arreglos {arreglos.length > 0 && <Badge className="ml-1 h-4 px-1 text-[10px] bg-violet-600">{arreglos.length}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="mermas" className="text-xs">
            Diferencias {mermas.length > 0 && <Badge variant="outline" className="ml-1 h-4 px-1 text-[10px]">{mermas.length}</Badge>}
          </TabsTrigger>
          {divisiones.length > 0 && (
            <TabsTrigger value="divisiones" className="text-xs">Divisiones</TabsTrigger>
          )}
        </TabsList>

        {/* Timeline Tab */}
        <TabsContent value="balance">
          <Card>
            <CardContent className="pt-4">
              {eventos.length > 0 ? (
                <div className="space-y-2">
                  {eventos.map((ev, i) => (
                    <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg border bg-card hover:bg-muted/30 transition-colors" data-testid={`evento-${i}`}>
                      <div className="mt-0.5"><EventoIcon tipo={ev.tipo_evento} /></div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <EventoBadge tipo={ev.tipo_evento} />
                          <span className="text-xs text-muted-foreground font-mono">{fmtDate(ev.fecha)}</span>
                        </div>
                        <div className="mt-1 text-sm">
                          {ev.tipo_evento === 'MOVIMIENTO' && (
                            <span>{ev.servicio} {ev.persona ? `(${ev.persona})` : ''} - Env: {ev.cantidad_enviada}, Rec: {ev.cantidad_recibida}{ev.diferencia > 0 ? `, Dif: -${ev.diferencia}` : ''}</span>
                          )}
                          {ev.tipo_evento === 'MERMA' && (
                            <span>-{ev.cantidad} prendas {ev.motivo ? `- ${ev.motivo}` : ''} {ev.servicio ? `en ${ev.servicio}` : ''}</span>
                          )}
                          {ev.tipo_evento === 'FALLADO' && (
                            <span>{ev.cantidad_detectada} detectados ({ev.cantidad_reparable}R / {ev.cantidad_no_reparable}NR) {ev.motivo ? `- ${ev.motivo}` : ''} - {ev.estado}</span>
                          )}
                          {ev.tipo_evento === 'ARREGLO' && (
                            <span>{ev.tipo}: {ev.cantidad_enviada} env. {ev.servicio ? `a ${ev.servicio}` : ''} {ev.persona ? `(${ev.persona})` : ''} - {ev.estado}{ev.vencido ? ' VENCIDO' : ''}</span>
                          )}
                          {ev.tipo_evento === 'DIVISION' && (
                            <span>Lote hijo: {ev.hijo_n_corte} ({ev.hijo_prendas} prendas) - {ev.hijo_estado}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <Clock className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">Sin eventos registrados</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Fallados Tab */}
        <TabsContent value="fallados">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm">Productos Fallados</CardTitle>
              <Button size="sm" type="button" onClick={() => { resetFalladoForm(); setFalladoDialogOpen(true); }} data-testid="btn-nuevo-fallado">
                <Plus className="h-3.5 w-3.5 mr-1" /> Registrar Fallado
              </Button>
            </CardHeader>
            <CardContent>
              {fallados.length > 0 ? (
                <div className="space-y-3">
                  {fallados.map(f => {
                    const arreglosDeFallado = arreglos.filter(a => a.fallado_id === f.id);
                    return (
                      <div key={f.id} className="rounded-lg border p-3 space-y-2" data-testid={`fallado-${f.id}`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <XCircle className="h-4 w-4 text-red-500" />
                            <span className="font-medium text-sm">{f.cantidad_detectada} fallados</span>
                            <Badge variant={f.estado === 'CERRADO' ? 'default' : f.estado === 'EN_PROCESO' ? 'secondary' : 'destructive'} className="text-[10px]">
                              {f.estado}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-1">
                            <Button type="button" size="icon" variant="ghost" className="h-7 w-7" onClick={() => openArregloDialog(f)}
                              title="Enviar a arreglo" data-testid={`btn-arreglo-${f.id}`}>
                              <Wrench className="h-3.5 w-3.5 text-violet-500" />
                            </Button>
                            <Button type="button" size="icon" variant="ghost" className="h-7 w-7" onClick={() => handleDeleteFallado(f.id)} data-testid={`btn-del-fallado-${f.id}`}>
                              <Trash2 className="h-3.5 w-3.5 text-destructive" />
                            </Button>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                          <div><span className="text-muted-foreground">Reparables:</span> <span className="font-medium">{f.cantidad_reparable}</span></div>
                          <div><span className="text-muted-foreground">No Reparables:</span> <span className="font-medium">{f.cantidad_no_reparable}</span></div>
                          <div><span className="text-muted-foreground">Destino NR:</span> <span className="font-medium">{f.destino_no_reparable}</span></div>
                          <div><span className="text-muted-foreground">Fecha:</span> <span className="font-mono">{fmtDate(f.fecha_deteccion)}</span></div>
                        </div>
                        {f.motivo && <p className="text-xs text-muted-foreground">Motivo: {f.motivo}</p>}
                        {f.servicio_detectado_nombre && <p className="text-xs text-muted-foreground">Servicio: {f.servicio_detectado_nombre}</p>}

                        {/* Arreglos anidados */}
                        {arreglosDeFallado.length > 0 && (
                          <div className="pl-4 border-l-2 border-violet-200 dark:border-violet-800 space-y-2 mt-2">
                            {arreglosDeFallado.map(a => (
                              <div key={a.id} className={`rounded border p-2 text-xs ${a.vencido ? 'bg-red-50 border-red-200 dark:bg-red-950/20 dark:border-red-800' : 'bg-violet-50/50 dark:bg-violet-950/10'}`} data-testid={`arreglo-${a.id}`}>
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <Wrench className="h-3 w-3 text-violet-500" />
                                    <span className="font-medium">{a.tipo}</span>
                                    <Badge variant={a.estado === 'RESUELTO' ? 'default' : 'secondary'} className="text-[9px] h-4">
                                      {a.estado}{a.vencido ? ' - VENCIDO' : ''}
                                    </Badge>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    {a.estado === 'PENDIENTE' && (
                                      <Button type="button" size="icon" variant="ghost" className="h-6 w-6" onClick={() => openCierreDialog(a)} title="Cerrar arreglo" data-testid={`btn-cerrar-arreglo-${a.id}`}>
                                        <CheckCircle2 className="h-3 w-3 text-green-600" />
                                      </Button>
                                    )}
                                    <Button type="button" size="icon" variant="ghost" className="h-6 w-6" onClick={() => handleDeleteArreglo(a.id)} data-testid={`btn-del-arreglo-${a.id}`}>
                                      <Trash2 className="h-3 w-3 text-destructive" />
                                    </Button>
                                  </div>
                                </div>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-1 mt-1">
                                  <span>Enviadas: {a.cantidad_enviada}</span>
                                  {a.estado === 'RESUELTO' && <span>Resueltas: {a.cantidad_resuelta}</span>}
                                  {a.estado === 'RESUELTO' && <span>No resueltas: {a.cantidad_no_resuelta}</span>}
                                  <span>Envio: {fmtDate(a.fecha_envio)}</span>
                                  <span>Limite: {fmtDate(a.fecha_limite)}</span>
                                  {a.fecha_retorno && <span>Retorno: {fmtDate(a.fecha_retorno)}</span>}
                                  {a.servicio_destino_nombre && <span>Serv: {a.servicio_destino_nombre}</span>}
                                  {a.persona_destino_nombre && <span>Pers: {a.persona_destino_nombre}</span>}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">Sin productos fallados</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Arreglos Tab */}
        <TabsContent value="arreglos">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Arreglos</CardTitle>
            </CardHeader>
            <CardContent>
              {arreglos.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="text-xs">Tipo</TableHead>
                        <TableHead className="text-xs">Servicio/Persona</TableHead>
                        <TableHead className="text-xs text-center">Env.</TableHead>
                        <TableHead className="text-xs text-center">Res.</TableHead>
                        <TableHead className="text-xs text-center">Envio</TableHead>
                        <TableHead className="text-xs text-center">Limite</TableHead>
                        <TableHead className="text-xs text-center">Estado</TableHead>
                        <TableHead className="text-xs text-right">Acc.</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {arreglos.map(a => (
                        <TableRow key={a.id} className={a.vencido ? 'bg-red-50 dark:bg-red-950/10' : ''} data-testid={`arreglo-row-${a.id}`}>
                          <TableCell className="text-xs font-medium">{a.tipo}</TableCell>
                          <TableCell className="text-xs">{a.servicio_destino_nombre || a.persona_destino_nombre || '-'}</TableCell>
                          <TableCell className="text-xs text-center font-mono">{a.cantidad_enviada}</TableCell>
                          <TableCell className="text-xs text-center font-mono">{a.estado === 'RESUELTO' ? a.cantidad_resuelta : '-'}</TableCell>
                          <TableCell className="text-xs text-center font-mono">{fmtDate(a.fecha_envio)}</TableCell>
                          <TableCell className={`text-xs text-center font-mono ${a.vencido ? 'text-red-600 font-semibold' : ''}`}>{fmtDate(a.fecha_limite)}</TableCell>
                          <TableCell className="text-xs text-center">
                            <Badge variant={a.estado === 'RESUELTO' ? 'default' : a.vencido ? 'destructive' : 'secondary'} className="text-[10px]">
                              {a.estado}{a.vencido ? ' VENC.' : ''}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              {a.estado === 'PENDIENTE' && (
                                <Button type="button" size="icon" variant="ghost" className="h-7 w-7" onClick={() => openCierreDialog(a)} data-testid={`btn-cerrar-arreglo-tbl-${a.id}`}>
                                  <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                                </Button>
                              )}
                              <Button type="button" size="icon" variant="ghost" className="h-7 w-7" onClick={() => handleDeleteArreglo(a.id)} data-testid={`btn-del-arreglo-tbl-${a.id}`}>
                                <Trash2 className="h-3.5 w-3.5 text-destructive" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <Wrench className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">Sin arreglos registrados</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Mermas / Diferencias Tab */}
        <TabsContent value="mermas">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Diferencias / Mermas de Proceso</CardTitle>
            </CardHeader>
            <CardContent>
              {mermas.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="text-xs">Fecha</TableHead>
                        <TableHead className="text-xs">Servicio</TableHead>
                        <TableHead className="text-xs text-center">Cantidad</TableHead>
                        <TableHead className="text-xs">Motivo</TableHead>
                        <TableHead className="text-xs">Tipo</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {mermas.map((m, i) => (
                        <TableRow key={i} data-testid={`merma-row-${i}`}>
                          <TableCell className="text-xs font-mono">{fmtDate(m.fecha)}</TableCell>
                          <TableCell className="text-xs">{m.servicio || '-'}</TableCell>
                          <TableCell className="text-xs text-center font-mono font-semibold text-amber-600">-{m.cantidad}</TableCell>
                          <TableCell className="text-xs">{m.motivo || '-'}</TableCell>
                          <TableCell className="text-xs"><Badge variant="outline" className="text-[10px]">{m.tipo || 'FALTANTE'}</Badge></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">Sin diferencias registradas</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Divisiones Tab */}
        {divisiones.length > 0 && (
          <TabsContent value="divisiones">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Lotes Derivados (Divisiones)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="text-xs">Lote Hijo</TableHead>
                        <TableHead className="text-xs text-center">Prendas</TableHead>
                        <TableHead className="text-xs text-center">Estado</TableHead>
                        <TableHead className="text-xs">Fecha</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {divisiones.map((d, i) => (
                        <TableRow key={i} data-testid={`division-row-${i}`}>
                          <TableCell className="text-xs font-medium">{d.hijo_n_corte}</TableCell>
                          <TableCell className="text-xs text-center font-mono">{d.hijo_prendas}</TableCell>
                          <TableCell className="text-xs text-center"><Badge variant="outline" className="text-[10px]">{d.hijo_estado}</Badge></TableCell>
                          <TableCell className="text-xs font-mono">{fmtDate(d.fecha)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>

      {/* ========== DIALOGS ========== */}

      {/* Dialog: Nuevo Fallado */}
      <Dialog open={falladoDialogOpen} onOpenChange={setFalladoDialogOpen}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Registrar Productos Fallados</DialogTitle>
            <DialogDescription>Indica la cantidad detectada y clasifica en reparables / no reparables.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Detectados *</Label>
                <Input type="number" min="1" value={falladoForm.cantidad_detectada}
                  onChange={e => setFalladoForm(p => ({ ...p, cantidad_detectada: parseInt(e.target.value) || 0 }))}
                  data-testid="input-fallado-detectados" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Reparables</Label>
                <Input type="number" min="0" value={falladoForm.cantidad_reparable}
                  onChange={e => setFalladoForm(p => ({ ...p, cantidad_reparable: parseInt(e.target.value) || 0 }))}
                  data-testid="input-fallado-reparables" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">No Reparables</Label>
                <Input type="number" min="0" value={falladoForm.cantidad_no_reparable}
                  onChange={e => setFalladoForm(p => ({ ...p, cantidad_no_reparable: parseInt(e.target.value) || 0 }))}
                  data-testid="input-fallado-no-reparables" />
              </div>
            </div>
            {falladoForm.cantidad_no_reparable > 0 && (
              <div className="space-y-1">
                <Label className="text-xs">Destino No Reparables</Label>
                <Select value={falladoForm.destino_no_reparable} onValueChange={v => setFalladoForm(p => ({ ...p, destino_no_reparable: v }))}>
                  <SelectTrigger data-testid="select-destino-nr"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PENDIENTE">Pendiente</SelectItem>
                    <SelectItem value="LIQUIDACION">Liquidacion</SelectItem>
                    <SelectItem value="SEGUNDA">Segunda</SelectItem>
                    <SelectItem value="DESCARTE">Descarte</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-1">
              <Label className="text-xs">Servicio donde se detecto</Label>
              <Select value={falladoForm.servicio_detectado_id} onValueChange={v => setFalladoForm(p => ({ ...p, servicio_detectado_id: v }))}>
                <SelectTrigger data-testid="select-servicio-fallado"><SelectValue placeholder="Seleccionar..." /></SelectTrigger>
                <SelectContent>
                  {servicios.map(s => <SelectItem key={s.id} value={s.id}>{s.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Fecha deteccion</Label>
              <Input type="date" value={falladoForm.fecha_deteccion}
                onChange={e => setFalladoForm(p => ({ ...p, fecha_deteccion: e.target.value }))}
                data-testid="input-fallado-fecha" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Motivo</Label>
              <Input value={falladoForm.motivo} onChange={e => setFalladoForm(p => ({ ...p, motivo: e.target.value }))}
                placeholder="Costura torcida, manchas, etc." data-testid="input-fallado-motivo" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Observaciones</Label>
              <Textarea value={falladoForm.observaciones} onChange={e => setFalladoForm(p => ({ ...p, observaciones: e.target.value }))}
                rows={2} data-testid="input-fallado-obs" />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setFalladoDialogOpen(false)}>Cancelar</Button>
            <Button type="button" onClick={handleCreateFallado}
              disabled={falladoForm.cantidad_detectada < 1 || (falladoForm.cantidad_reparable + falladoForm.cantidad_no_reparable) > falladoForm.cantidad_detectada}
              data-testid="btn-guardar-fallado">
              Registrar Fallado
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Nuevo Arreglo */}
      <Dialog open={arregloDialogOpen} onOpenChange={setArregloDialogOpen}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Enviar a Arreglo</DialogTitle>
            <DialogDescription>
              Fallado: {selectedFallado?.cantidad_detectada} detectados ({selectedFallado?.cantidad_reparable} reparables)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Cantidad a enviar *</Label>
                <Input type="number" min="1" value={arregloForm.cantidad_enviada}
                  onChange={e => setArregloForm(p => ({ ...p, cantidad_enviada: parseInt(e.target.value) || 0 }))}
                  data-testid="input-arreglo-cantidad" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Tipo</Label>
                <Select value={arregloForm.tipo} onValueChange={v => setArregloForm(p => ({ ...p, tipo: v }))}>
                  <SelectTrigger data-testid="select-arreglo-tipo"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ARREGLO_INTERNO">Interno</SelectItem>
                    <SelectItem value="ARREGLO_EXTERNO">Externo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Servicio destino</Label>
              <Select value={arregloForm.servicio_destino_id} onValueChange={v => setArregloForm(p => ({ ...p, servicio_destino_id: v }))}>
                <SelectTrigger data-testid="select-arreglo-servicio"><SelectValue placeholder="Seleccionar..." /></SelectTrigger>
                <SelectContent>
                  {servicios.map(s => <SelectItem key={s.id} value={s.id}>{s.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Persona destino</Label>
              <Select value={arregloForm.persona_destino_id} onValueChange={v => setArregloForm(p => ({ ...p, persona_destino_id: v }))}>
                <SelectTrigger data-testid="select-arreglo-persona"><SelectValue placeholder="Seleccionar..." /></SelectTrigger>
                <SelectContent>
                  {personas.map(p => <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Fecha envio</Label>
              <Input type="date" value={arregloForm.fecha_envio}
                onChange={e => setArregloForm(p => ({ ...p, fecha_envio: e.target.value }))}
                data-testid="input-arreglo-fecha" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Observaciones</Label>
              <Textarea value={arregloForm.observaciones} onChange={e => setArregloForm(p => ({ ...p, observaciones: e.target.value }))}
                rows={2} data-testid="input-arreglo-obs" />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setArregloDialogOpen(false)}>Cancelar</Button>
            <Button type="button" onClick={handleCreateArreglo} disabled={arregloForm.cantidad_enviada < 1} data-testid="btn-guardar-arreglo">
              Crear Arreglo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Cerrar Arreglo */}
      <Dialog open={cierreArregloDialogOpen} onOpenChange={setCierreArregloDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Cerrar Arreglo</DialogTitle>
            <DialogDescription>
              Enviadas: {selectedArreglo?.cantidad_enviada} - Registra el resultado del arreglo.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Resueltas</Label>
                <Input type="number" min="0" value={cierreForm.cantidad_resuelta}
                  onChange={e => setCierreForm(p => ({ ...p, cantidad_resuelta: parseInt(e.target.value) || 0 }))}
                  data-testid="input-cierre-resueltas" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">No Resueltas</Label>
                <Input type="number" min="0" value={cierreForm.cantidad_no_resuelta}
                  onChange={e => setCierreForm(p => ({ ...p, cantidad_no_resuelta: parseInt(e.target.value) || 0 }))}
                  data-testid="input-cierre-no-resueltas" />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Resultado final</Label>
              <Select value={cierreForm.resultado_final} onValueChange={v => setCierreForm(p => ({ ...p, resultado_final: v }))}>
                <SelectTrigger data-testid="select-cierre-resultado"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="BUENO">Bueno (reintegrado)</SelectItem>
                  <SelectItem value="LIQUIDACION">Liquidacion</SelectItem>
                  <SelectItem value="SEGUNDA">Segunda</SelectItem>
                  <SelectItem value="DESCARTE">Descarte</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Fecha retorno</Label>
              <Input type="date" value={cierreForm.fecha_retorno}
                onChange={e => setCierreForm(p => ({ ...p, fecha_retorno: e.target.value }))}
                data-testid="input-cierre-fecha" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Observaciones</Label>
              <Textarea value={cierreForm.observaciones} onChange={e => setCierreForm(p => ({ ...p, observaciones: e.target.value }))}
                rows={2} data-testid="input-cierre-obs" />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setCierreArregloDialogOpen(false)}>Cancelar</Button>
            <Button type="button" onClick={handleCerrarArreglo}
              disabled={(cierreForm.cantidad_resuelta + cierreForm.cantidad_no_resuelta) > (selectedArreglo?.cantidad_enviada || 0)}
              data-testid="btn-confirmar-cierre-arreglo">
              Cerrar Arreglo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

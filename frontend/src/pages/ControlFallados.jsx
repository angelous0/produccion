import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '../components/ui/tooltip';
import {
  AlertTriangle, CheckCircle2, Clock, XCircle, Filter, Package, Wrench, RefreshCw,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const estadoBadge = (estado) => {
  const map = {
    VENCIDO: { cls: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/40 dark:text-red-300', icon: <AlertTriangle className="h-3 w-3" /> },
    PENDIENTE: { cls: 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/40 dark:text-amber-300', icon: <Clock className="h-3 w-3" /> },
    EN_PROCESO: { cls: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300', icon: <Wrench className="h-3 w-3" /> },
    COMPLETADO: { cls: 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300', icon: <CheckCircle2 className="h-3 w-3" /> },
  };
  const { cls, icon } = map[estado] || map.PENDIENTE;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${cls}`} data-testid={`badge-${estado}`}>
      {icon} {estado}
    </span>
  );
};

export const ControlFallados = () => {
  const navigate = useNavigate();
  const [data, setData] = useState({ registros: [], kpis: {} });
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  const [filtros, setFiltros] = useState({
    estado: '',
    servicio_id: '',
    persona_id: '',
    fecha_desde: '',
    fecha_hasta: '',
    solo_vencidos: false,
    solo_pendientes: false,
    linea_negocio_id: '',
  });

  const [servicios, setServicios] = useState([]);
  const [personas, setPersonas] = useState([]);
  const [lineas, setLineas] = useState([]);

  const hdrs = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filtros.estado) params.set('estado', filtros.estado);
      if (filtros.servicio_id) params.set('servicio_id', filtros.servicio_id);
      if (filtros.persona_id) params.set('persona_id', filtros.persona_id);
      if (filtros.fecha_desde) params.set('fecha_desde', filtros.fecha_desde);
      if (filtros.fecha_hasta) params.set('fecha_hasta', filtros.fecha_hasta);
      if (filtros.solo_vencidos) params.set('solo_vencidos', 'true');
      if (filtros.solo_pendientes) params.set('solo_pendientes', 'true');
      if (filtros.linea_negocio_id) params.set('linea_negocio_id', filtros.linea_negocio_id);

      const res = await axios.get(`${API}/fallados-control?${params.toString()}`, { headers: hdrs() });
      setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [filtros]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    const h = hdrs();
    Promise.allSettled([
      axios.get(`${API}/servicios-produccion`, { headers: h }),
      axios.get(`${API}/personas-produccion`, { headers: h }),
      axios.get(`${API}/lineas-negocio`, { headers: h }),
    ]).then(([s, p, l]) => {
      if (s.status === 'fulfilled') setServicios(s.value.data || []);
      if (p.status === 'fulfilled') setPersonas(p.value.data || []);
      if (l.status === 'fulfilled') setLineas(l.value.data || []);
    });
  }, []);

  const k = data.kpis || {};
  const registros = data.registros || [];

  const clearFilters = () => {
    setFiltros({ estado: '', servicio_id: '', persona_id: '', fecha_desde: '', fecha_hasta: '', solo_vencidos: false, solo_pendientes: false, linea_negocio_id: '' });
  };

  const hasActiveFilters = filtros.estado || filtros.servicio_id || filtros.persona_id || filtros.fecha_desde || filtros.fecha_hasta || filtros.solo_vencidos || filtros.solo_pendientes || filtros.linea_negocio_id;

  return (
    <div className="space-y-4" data-testid="control-fallados-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold">Control de Fallados</h1>
          <p className="text-xs text-muted-foreground">Vista operativa diaria de fallados, arreglos y resoluciones</p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)} className="h-8 text-xs" data-testid="btn-filtros">
            <Filter className="h-3 w-3 mr-1" /> Filtros {hasActiveFilters && <Badge variant="secondary" className="ml-1 h-4 text-[9px]">ON</Badge>}
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={fetchData} className="h-8 text-xs" data-testid="btn-refresh">
            <RefreshCw className="h-3 w-3 mr-1" /> Actualizar
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2" data-testid="kpi-section">
        <KpiCard label="Total Fallados" value={k.total_fallados || 0} icon={<XCircle className="h-4 w-4" />} color="zinc" />
        <KpiCard label="Pendientes" value={k.total_pendiente || 0} icon={<Clock className="h-4 w-4" />} color={k.total_pendiente > 0 ? 'amber' : 'zinc'} />
        <KpiCard label="Vencidos" value={k.total_vencidos || 0} icon={<AlertTriangle className="h-4 w-4" />} color={k.total_vencidos > 0 ? 'red' : 'zinc'} />
        <KpiCard label="Recuperado" value={k.total_recuperado || 0} icon={<CheckCircle2 className="h-4 w-4" />} color={k.total_recuperado > 0 ? 'emerald' : 'zinc'} />
        <KpiCard label="Liquidacion" value={k.total_liquidacion || 0} icon={<Package className="h-4 w-4" />} color={k.total_liquidacion > 0 ? 'orange' : 'zinc'} />
        <KpiCard label="Merma" value={k.total_merma || 0} icon={<AlertTriangle className="h-4 w-4" />} color={k.total_merma > 0 ? 'red' : 'zinc'} />
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <Card data-testid="filtros-panel">
          <CardContent className="p-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 items-end">
              <div>
                <Label className="text-[10px]">Estado</Label>
                <Select value={filtros.estado || '_all'} onValueChange={v => setFiltros({ ...filtros, estado: v === '_all' ? '' : v })}>
                  <SelectTrigger className="h-7 text-xs" data-testid="filter-estado"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_all">Todos</SelectItem>
                    <SelectItem value="VENCIDO">Vencido</SelectItem>
                    <SelectItem value="PENDIENTE">Pendiente</SelectItem>
                    <SelectItem value="EN_PROCESO">En Proceso</SelectItem>
                    <SelectItem value="COMPLETADO">Completado</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-[10px]">Servicio</Label>
                <Select value={filtros.servicio_id || '_all'} onValueChange={v => setFiltros({ ...filtros, servicio_id: v === '_all' ? '' : v })}>
                  <SelectTrigger className="h-7 text-xs" data-testid="filter-servicio"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_all">Todos</SelectItem>
                    {servicios.map(s => <SelectItem key={s.id} value={s.id}>{s.nombre}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-[10px]">Persona</Label>
                <Select value={filtros.persona_id || '_all'} onValueChange={v => setFiltros({ ...filtros, persona_id: v === '_all' ? '' : v })}>
                  <SelectTrigger className="h-7 text-xs" data-testid="filter-persona"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_all">Todos</SelectItem>
                    {personas.map(p => <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {lineas.length > 0 && (
                <div>
                  <Label className="text-[10px]">Linea Negocio</Label>
                  <Select value={filtros.linea_negocio_id || '_all'} onValueChange={v => setFiltros({ ...filtros, linea_negocio_id: v === '_all' ? '' : v })}>
                    <SelectTrigger className="h-7 text-xs" data-testid="filter-linea"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="_all">Todas</SelectItem>
                      {lineas.map(l => <SelectItem key={l.id} value={l.id}>{l.nombre}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              )}
              <div>
                <Label className="text-[10px]">Desde</Label>
                <Input type="date" className="h-7 text-xs" value={filtros.fecha_desde} onChange={e => setFiltros({ ...filtros, fecha_desde: e.target.value })} data-testid="filter-desde" />
              </div>
              <div>
                <Label className="text-[10px]">Hasta</Label>
                <Input type="date" className="h-7 text-xs" value={filtros.fecha_hasta} onChange={e => setFiltros({ ...filtros, fecha_hasta: e.target.value })} data-testid="filter-hasta" />
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-1.5">
                  <Checkbox id="solo_vencidos" checked={filtros.solo_vencidos} onCheckedChange={v => setFiltros({ ...filtros, solo_vencidos: v })} data-testid="filter-solo-vencidos" />
                  <Label htmlFor="solo_vencidos" className="text-[10px] cursor-pointer">Solo vencidos</Label>
                </div>
                <div className="flex items-center gap-1.5">
                  <Checkbox id="solo_pendientes" checked={filtros.solo_pendientes} onCheckedChange={v => setFiltros({ ...filtros, solo_pendientes: v })} data-testid="filter-solo-pendientes" />
                  <Label htmlFor="solo_pendientes" className="text-[10px] cursor-pointer">Solo pendientes</Label>
                </div>
              </div>
              <div>
                <Button type="button" variant="ghost" size="sm" onClick={clearFilters} className="h-7 text-xs w-full" data-testid="btn-clear-filters">Limpiar</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Table */}
      <Card data-testid="tabla-fallados">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground text-sm">Cargando...</div>
          ) : registros.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <CheckCircle2 className="h-8 w-8 mb-2 text-emerald-400" />
              <p className="text-sm font-medium">Sin fallados pendientes</p>
              <p className="text-xs">Todos los lotes estan al dia</p>
            </div>
          ) : (
            <TooltipProvider delayDuration={200}>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-[11px] font-semibold w-20">Corte</TableHead>
                    <TableHead className="text-[11px] font-semibold">Modelo</TableHead>
                    <TableHead className="text-[11px] font-semibold text-center">Fallados</TableHead>
                    <TableHead className="text-[11px] font-semibold text-center">Enviado</TableHead>
                    <TableHead className="text-[11px] font-semibold text-center">Recuperado</TableHead>
                    <TableHead className="text-[11px] font-semibold text-center">Pendiente</TableHead>
                    <TableHead className="text-[11px] font-semibold text-center">Estado</TableHead>
                    <TableHead className="text-[11px] font-semibold text-center">Vencidos</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {registros.map(r => (
                    <Tooltip key={r.id}>
                      <TooltipTrigger asChild>
                        <TableRow
                          className={`cursor-pointer transition-colors hover:bg-muted/50 ${
                            r.estado_control === 'VENCIDO' ? 'bg-red-50/40 dark:bg-red-950/10' :
                            r.estado_control === 'COMPLETADO' ? 'bg-emerald-50/30 dark:bg-emerald-950/10' : ''
                          }`}
                          onClick={() => navigate(`/registros/editar/${r.id}`)}
                          data-testid={`row-${r.n_corte}`}
                        >
                          <TableCell className="font-mono font-bold text-sm">{r.n_corte}</TableCell>
                          <TableCell>
                            <div className="text-xs">{r.modelo}</div>
                            {r.marca && <div className="text-[10px] text-muted-foreground">{r.marca}</div>}
                          </TableCell>
                          <TableCell className="text-center font-mono font-semibold text-red-600">{r.total_fallados}</TableCell>
                          <TableCell className="text-center font-mono">{r.total_enviado || '-'}</TableCell>
                          <TableCell className="text-center font-mono text-emerald-600">{r.recuperado || '-'}</TableCell>
                          <TableCell className="text-center">
                            <span className={`font-mono font-semibold ${r.pendiente > 0 ? 'text-amber-600' : 'text-zinc-400'}`}>
                              {r.pendiente}
                            </span>
                          </TableCell>
                          <TableCell className="text-center">{estadoBadge(r.estado_control)}</TableCell>
                          <TableCell className="text-center">
                            {r.arreglos_vencidos > 0 ? (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 text-[10px] font-bold">
                                <AlertTriangle className="h-3 w-3" /> {r.arreglos_vencidos}
                              </span>
                            ) : (
                              <span className="text-zinc-300">-</span>
                            )}
                          </TableCell>
                        </TableRow>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="text-[10px] max-w-xs">
                        <div className="space-y-0.5">
                          <div className="font-semibold">Corte {r.n_corte} - {r.modelo}</div>
                          <div>Estado OP: {r.estado_op} {r.linea_negocio ? `| Linea: ${r.linea_negocio}` : ''}</div>
                          <div>Fallados: {r.total_fallados} | Enviado: {r.total_enviado} | Sin enviar: {r.sin_enviar}</div>
                          <div>Rec: {r.recuperado} | Liq: {r.liquidacion} | Merma: {r.merma_arreglos}</div>
                        </div>
                      </TooltipContent>
                    </Tooltip>
                  ))}
                </TableBody>
              </Table>
            </TooltipProvider>
          )}
          {!loading && registros.length > 0 && (
            <div className="px-3 py-2 border-t bg-muted/30 text-[10px] text-muted-foreground flex justify-between">
              <span>{k.total_registros} registros con fallados</span>
              <span>
                {k.total_completados} completados | {k.total_vencidos} vencidos | {k.total_pendiente} prendas pendientes
              </span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

const KpiCard = ({ label, value, icon, color = 'zinc' }) => {
  const colors = {
    zinc: 'bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300',
    amber: 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300',
    red: 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300',
    emerald: 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300',
    orange: 'bg-orange-50 dark:bg-orange-950/30 border-orange-200 dark:border-orange-800 text-orange-700 dark:text-orange-300',
    blue: 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300',
  };
  return (
    <Card className={`border ${colors[color]}`} data-testid={`kpi-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <CardContent className="p-3 flex items-center gap-2">
        <div className="opacity-70">{icon}</div>
        <div>
          <p className="text-[9px] uppercase tracking-wider opacity-70">{label}</p>
          <p className="text-xl font-bold font-mono leading-tight">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
};

export default ControlFallados;

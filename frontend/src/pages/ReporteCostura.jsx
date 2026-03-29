import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
  ChevronDown, ChevronRight, Users, Package, AlertTriangle, Clock, FileWarning,
  ExternalLink, Plus, Pencil, Filter, X, RefreshCw, History
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const RIESGO_CONFIG = {
  normal:   { label: 'Normal',   color: 'bg-emerald-100 text-emerald-800 border-emerald-200', dot: 'bg-emerald-500', rowClass: '' },
  atencion: { label: 'Atención', color: 'bg-amber-100 text-amber-800 border-amber-200', dot: 'bg-amber-500', rowClass: 'bg-amber-50/50' },
  critico:  { label: 'Crítico',  color: 'bg-red-100 text-red-800 border-red-200', dot: 'bg-red-500', rowClass: 'bg-red-50/50' },
  vencido:  { label: 'Vencido',  color: 'bg-zinc-800 text-white border-zinc-700', dot: 'bg-zinc-800', rowClass: 'bg-red-50/70' },
};

const KpiCard = ({ label, value, icon: Icon, accent }) => (
  <div className={`rounded-lg border p-3 ${accent || 'bg-card'}`}>
    <div className="flex items-center gap-2 mb-1">
      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{label}</span>
    </div>
    <p className="text-2xl font-bold font-mono leading-none">{value}</p>
  </div>
);

// Inline avance editor
const AvanceEditor = ({ movimientoId, currentValue, onSaved, nCorte }) => {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(currentValue ?? 0);
  const [saving, setSaving] = useState(false);
  const [historial, setHistorial] = useState(null);
  const [showHist, setShowHist] = useState(false);

  const fetchHistorial = async () => {
    try {
      const resp = await axios.get(`${API}/api/reportes-produccion/costura/avance-historial/${movimientoId}`);
      setHistorial(resp.data);
      setShowHist(true);
    } catch { toast.error('Error al cargar historial'); }
  };

  if (!editing) {
    return (
      <>
        <div className="flex items-center gap-0.5 justify-center">
          <button
            onClick={() => { setVal(currentValue ?? 0); setEditing(true); }}
            className="flex items-center gap-1 hover:bg-muted rounded px-1 py-0.5 transition-colors group"
            title="Actualizar avance"
          >
            <span className="font-mono text-sm font-semibold">{currentValue ?? '—'}%</span>
            <Pencil className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
          <button
            onClick={fetchHistorial}
            className="h-5 w-5 flex items-center justify-center rounded hover:bg-muted transition-colors"
            title="Ver historial de avances"
          >
            <History className="h-3 w-3 text-muted-foreground" />
          </button>
        </div>
        <Dialog open={showHist} onOpenChange={setShowHist}>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle className="text-sm">Historial de Avance — Corte {nCorte}</DialogTitle>
            </DialogHeader>
            {!historial || historial.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">Sin registros de avance</p>
            ) : (
              <div className="space-y-0 max-h-64 overflow-y-auto">
                {historial.map((h, i) => {
                  const prev = i > 0 ? historial[i - 1].avance_porcentaje : 0;
                  const diff = h.avance_porcentaje - prev;
                  return (
                    <div key={i} className="flex items-center justify-between py-2 px-1 border-b border-border/50 last:border-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm w-10 text-right">{h.avance_porcentaje}%</span>
                        {diff > 0 && <Badge variant="outline" className="text-[10px] text-emerald-600 border-emerald-300">+{diff}%</Badge>}
                        {diff < 0 && <Badge variant="outline" className="text-[10px] text-red-600 border-red-300">{diff}%</Badge>}
                      </div>
                      <div className="text-right">
                        <p className="text-xs">{h.fecha ? new Date(h.fecha).toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '-'}</p>
                        <p className="text-[10px] text-muted-foreground">{h.usuario} · {h.fecha ? new Date(h.fecha).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' }) : ''}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </>
    );
  }

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/api/reportes-produccion/costura/avance/${movimientoId}`, { avance_porcentaje: parseInt(val) || 0 });
      toast.success(`Avance actualizado: ${val}%`);
      onSaved();
      setEditing(false);
    } catch { toast.error('Error al guardar'); }
    setSaving(false);
  };

  return (
    <div className="flex items-center gap-1">
      <Input type="number" min={0} max={100} value={val} onChange={e => setVal(e.target.value)} className="w-16 h-7 text-sm font-mono text-center p-1" autoFocus onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setEditing(false); }} />
      <span className="text-xs">%</span>
      <Button size="icon" variant="ghost" className="h-6 w-6" onClick={handleSave} disabled={saving}><RefreshCw className={`h-3 w-3 ${saving ? 'animate-spin' : ''}`} /></Button>
      <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => setEditing(false)}><X className="h-3 w-3" /></Button>
    </div>
  );
};

export const ReporteCostura = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedPersonas, setExpandedPersonas] = useState({});
  const [showFilters, setShowFilters] = useState(false);

  // Filtros
  const [filtroPersona, setFiltroPersona] = useState('__all__');
  const [filtroRiesgo, setFiltroRiesgo] = useState('__all__');
  const [filtroConIncidencias, setFiltroConIncidencias] = useState('__all__');
  const [filtroVencidos, setFiltroVencidos] = useState('__all__');
  const [filtroSinActualizar, setFiltroSinActualizar] = useState('__all__');
  const [filtroTerminados, setFiltroTerminados] = useState('en_curso');
  const [filtroBusqueda, setFiltroBusqueda] = useState('');

  // Incidencia rápida
  const [incDialog, setIncDialog] = useState(null);
  const [incComentario, setIncComentario] = useState('');
  const [incSaving, setIncSaving] = useState(false);
  const [motivos, setMotivos] = useState([]);
  const [incMotivo, setIncMotivo] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filtroPersona !== '__all__') params.append('persona_id', filtroPersona);
      if (filtroRiesgo !== '__all__') params.append('riesgo', filtroRiesgo);
      if (filtroConIncidencias === 'si') params.append('con_incidencias', 'true');
      if (filtroConIncidencias === 'no') params.append('con_incidencias', 'false');
      if (filtroVencidos === 'si') params.append('vencidos', 'true');
      if (filtroSinActualizar === 'si') params.append('sin_actualizar', 'true');
      if (filtroTerminados === 'todos') params.append('incluir_terminados', 'true');
      const resp = await axios.get(`${API}/api/reportes-produccion/costura?${params.toString()}`);
      setData(resp.data);
    } catch (err) {
      toast.error('Error al cargar reporte');
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, [filtroPersona, filtroRiesgo, filtroConIncidencias, filtroVencidos, filtroSinActualizar, filtroTerminados]);

  useEffect(() => {
    axios.get(`${API}/api/motivos-incidencia`).then(r => setMotivos(r.data)).catch(() => {});
  }, []);

  // Agrupar items por persona
  const grouped = useMemo(() => {
    if (!data) return [];
    let items = data.items;
    if (filtroBusqueda.trim()) {
      const q = filtroBusqueda.toLowerCase();
      items = items.filter(i =>
        (i.n_corte || '').toLowerCase().includes(q) ||
        (i.modelo_nombre || '').toLowerCase().includes(q) ||
        (i.tipo_nombre || '').toLowerCase().includes(q) ||
        (i.entalle_nombre || '').toLowerCase().includes(q) ||
        (i.tela_nombre || '').toLowerCase().includes(q) ||
        (i.persona_nombre || '').toLowerCase().includes(q)
      );
    }
    const map = {};
    for (const item of items) {
      if (!map[item.persona_id]) {
        map[item.persona_id] = {
          persona_id: item.persona_id,
          persona_nombre: item.persona_nombre,
          persona_tipo: item.persona_tipo,
          items: [],
          total_prendas: 0,
          total_criticos: 0,
          total_vencidos: 0,
          total_incidencias: 0,
          avance_sum: 0,
          avance_count: 0,
        };
      }
      const g = map[item.persona_id];
      g.items.push(item);
      g.total_prendas += item.cantidad_enviada || 0;
      if (item.nivel_riesgo === 'critico') g.total_criticos++;
      if (item.nivel_riesgo === 'vencido') g.total_vencidos++;
      g.total_incidencias += item.incidencias_abiertas;
      if (item.avance_porcentaje != null) { g.avance_sum += item.avance_porcentaje; g.avance_count++; }
    }
    return Object.values(map).sort((a, b) => (b.total_criticos + b.total_vencidos) - (a.total_criticos + a.total_vencidos) || a.persona_nombre.localeCompare(b.persona_nombre));
  }, [data, filtroBusqueda]);

  const togglePersona = (pid) => {
    setExpandedPersonas(prev => ({ ...prev, [pid]: !prev[pid] }));
  };

  const handleIncidenciaRapida = async () => {
    if (!incDialog || !incMotivo) return;
    setIncSaving(true);
    try {
      await axios.post(`${API}/api/incidencias`, {
        registro_id: incDialog.registro_id,
        motivo_id: incMotivo,
        comentario: incComentario,
        paraliza: false,
      });
      toast.success('Incidencia creada');
      setIncDialog(null);
      setIncComentario('');
      setIncMotivo('');
      fetchData();
    } catch { toast.error('Error al crear incidencia'); }
    setIncSaving(false);
  };

  const kpis = data?.kpis || {};
  const personas = data?.filtros?.personas || [];

  const hasActiveFilters = filtroPersona !== '__all__' || filtroRiesgo !== '__all__' || filtroConIncidencias !== '__all__' || filtroVencidos !== '__all__' || filtroSinActualizar !== '__all__' || filtroTerminados !== 'en_curso' || filtroBusqueda.trim();

  const clearFilters = () => {
    setFiltroPersona('__all__');
    setFiltroRiesgo('__all__');
    setFiltroConIncidencias('__all__');
    setFiltroVencidos('__all__');
    setFiltroSinActualizar('__all__');
    setFiltroTerminados('en_curso');
    setFiltroBusqueda('');
  };

  return (
    <div className="space-y-4 pb-8 min-w-0" data-testid="reporte-costura">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Reporte Operativo — Costura</h2>
          <p className="text-sm text-muted-foreground">Seguimiento diario por costurero</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg border text-sm overflow-hidden" data-testid="toggle-estado-rapido">
            <button type="button" onClick={() => setFiltroTerminados('en_curso')} className={`px-3 py-1.5 text-xs font-medium transition-colors ${filtroTerminados === 'en_curso' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}>En curso</button>
            <button type="button" onClick={() => setFiltroTerminados('todos')} className={`px-3 py-1.5 text-xs font-medium transition-colors ${filtroTerminados === 'todos' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}>Todos</button>
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowFilters(f => !f)} data-testid="toggle-filtros">
            <Filter className="h-3.5 w-3.5 mr-1" />
            Filtros
            {hasActiveFilters && <Badge variant="secondary" className="ml-1 h-4 px-1 text-[10px]">ON</Badge>}
          </Button>
          <Button variant="outline" size="sm" onClick={fetchData} data-testid="btn-refresh">
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} /> Actualizar
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2" data-testid="kpis-costura">
        <KpiCard label="Costureros" value={kpis.costureros_activos || 0} icon={Users} />
        <KpiCard label="Registros" value={kpis.registros_activos || 0} icon={Package} />
        <KpiCard label="Prendas" value={(kpis.total_prendas || 0).toLocaleString()} icon={Package} />
        <KpiCard label="Vencidos" value={kpis.registros_vencidos || 0} icon={Clock} accent={kpis.registros_vencidos > 0 ? 'bg-zinc-100 border-zinc-300' : ''} />
        <KpiCard label="Críticos" value={kpis.registros_criticos || 0} icon={AlertTriangle} accent={kpis.registros_criticos > 0 ? 'bg-red-50 border-red-200' : ''} />
        <KpiCard label="Sin actualizar" value={kpis.registros_sin_actualizar || 0} icon={FileWarning} accent={kpis.registros_sin_actualizar > 0 ? 'bg-amber-50 border-amber-200' : ''} />
        <KpiCard label="Incidencias" value={kpis.incidencias_abiertas || 0} icon={AlertTriangle} accent={kpis.incidencias_abiertas > 0 ? 'bg-orange-50 border-orange-200' : ''} />
      </div>

      {/* Filtros */}
      {showFilters && (
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Filtros</span>
              {hasActiveFilters && <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={clearFilters}>Limpiar filtros</Button>}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-2">
              <div>
                <label className="text-[10px] text-muted-foreground uppercase">Estado</label>
                <Select value={filtroTerminados} onValueChange={setFiltroTerminados}>
                  <SelectTrigger className="h-8 text-sm" data-testid="filtro-terminados"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en_curso">En curso</SelectItem>
                    <SelectItem value="todos">Todos (+ historial)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase">Buscar</label>
                <Input value={filtroBusqueda} onChange={e => setFiltroBusqueda(e.target.value)} placeholder="Corte, modelo..." className="h-8 text-sm" data-testid="filtro-busqueda" />
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase">Persona</label>
                <Select value={filtroPersona} onValueChange={setFiltroPersona}>
                  <SelectTrigger className="h-8 text-sm" data-testid="filtro-persona"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">Todos</SelectItem>
                    {personas.map(p => <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase">Riesgo</label>
                <Select value={filtroRiesgo} onValueChange={setFiltroRiesgo}>
                  <SelectTrigger className="h-8 text-sm" data-testid="filtro-riesgo"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">Todos</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="atencion">Atención</SelectItem>
                    <SelectItem value="critico">Crítico</SelectItem>
                    <SelectItem value="vencido">Vencido</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase">Incidencias</label>
                <Select value={filtroConIncidencias} onValueChange={setFiltroConIncidencias}>
                  <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">Todas</SelectItem>
                    <SelectItem value="si">Con incidencias</SelectItem>
                    <SelectItem value="no">Sin incidencias</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase">Vencidos</label>
                <Select value={filtroVencidos} onValueChange={setFiltroVencidos}>
                  <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">Todos</SelectItem>
                    <SelectItem value="si">Solo vencidos</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase">Sin actualizar</label>
                <Select value={filtroSinActualizar} onValueChange={setFiltroSinActualizar}>
                  <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">Todos</SelectItem>
                    <SelectItem value="si">3+ días sin actualizar</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabla agrupada */}
      {loading ? (
        <div className="text-center py-12 text-muted-foreground">Cargando reporte...</div>
      ) : grouped.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">No hay movimientos de costura registrados</div>
      ) : (
        <div className="space-y-2" data-testid="tabla-costura">
          {grouped.map((grupo) => {
            const isExpanded = expandedPersonas[grupo.persona_id] !== false; // default expanded
            const avgAvance = grupo.avance_count > 0 ? Math.round(grupo.avance_sum / grupo.avance_count) : null;
            return (
              <div key={grupo.persona_id} className="rounded-lg border bg-card overflow-hidden">
                {/* Fila persona */}
                <button
                  type="button"
                  onClick={() => togglePersona(grupo.persona_id)}
                  className="w-full flex items-center gap-3 p-3 hover:bg-muted/50 transition-colors text-left"
                  data-testid={`persona-row-${grupo.persona_id}`}
                >
                  {isExpanded ? <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />}
                  <div className="flex-1 min-w-0 flex items-center gap-3 flex-wrap">
                    <span className="font-semibold text-sm">{grupo.persona_nombre}</span>
                    <Badge variant="outline" className="text-[10px]">{grupo.persona_tipo}</Badge>
                    <span className="text-xs text-muted-foreground">{grupo.items.length} registro{grupo.items.length !== 1 ? 's' : ''}</span>
                    <Separator orientation="vertical" className="h-4" />
                    <span className="text-xs font-mono">{grupo.total_prendas.toLocaleString()} prendas</span>
                    {avgAvance !== null && <span className="text-xs font-mono text-muted-foreground">~{avgAvance}%</span>}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {grupo.total_vencidos > 0 && <Badge className={RIESGO_CONFIG.vencido.color + ' text-[10px]'}>{grupo.total_vencidos} venc.</Badge>}
                    {grupo.total_criticos > 0 && <Badge className={RIESGO_CONFIG.critico.color + ' text-[10px]'}>{grupo.total_criticos} crít.</Badge>}
                    {grupo.total_incidencias > 0 && <Badge variant="destructive" className="text-[10px]">{grupo.total_incidencias} inc.</Badge>}
                  </div>
                </button>

                {/* Tabla de registros expandida */}
                {isExpanded && (
                  <div className="border-t overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-muted/60">
                          <th className="text-left p-2 font-medium text-muted-foreground whitespace-nowrap">Corte</th>
                          <th className="text-left p-2 font-medium text-muted-foreground whitespace-nowrap">Modelo</th>
                          <th className="text-left p-2 font-medium text-muted-foreground whitespace-nowrap">Tipo</th>
                          <th className="text-left p-2 font-medium text-muted-foreground whitespace-nowrap">Entalle</th>
                          <th className="text-left p-2 font-medium text-muted-foreground whitespace-nowrap">Tela</th>
                          <th className="text-right p-2 font-medium text-muted-foreground whitespace-nowrap">Cant.</th>
                          <th className="text-center p-2 font-medium text-muted-foreground whitespace-nowrap">Inicio</th>
                          <th className="text-center p-2 font-medium text-muted-foreground whitespace-nowrap">F. Esperada</th>
                          <th className="text-center p-2 font-medium text-muted-foreground whitespace-nowrap">Días</th>
                          <th className="text-center p-2 font-medium text-muted-foreground whitespace-nowrap">Avance</th>
                          <th className="text-center p-2 font-medium text-muted-foreground whitespace-nowrap">Últ. Act.</th>
                          <th className="text-center p-2 font-medium text-muted-foreground whitespace-nowrap">D/s Act.</th>
                          <th className="text-center p-2 font-medium text-muted-foreground whitespace-nowrap">Inc.</th>
                          <th className="text-center p-2 font-medium text-muted-foreground whitespace-nowrap">Riesgo</th>
                          <th className="text-center p-2 font-medium text-muted-foreground whitespace-nowrap">Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        {grupo.items.map((item) => {
                          const cfg = RIESGO_CONFIG[item.nivel_riesgo] || RIESGO_CONFIG.normal;
                          const diasSinAct = item.dias_sin_actualizar;
                          return (
                            <tr key={item.movimiento_id} className={`border-t hover:bg-muted/30 transition-colors ${cfg.rowClass}`} data-testid={`row-${item.movimiento_id}`}>
                              <td className="p-2 font-mono font-semibold whitespace-nowrap">
                                {item.n_corte}
                                {item.urgente && <span className="ml-1 text-[9px] text-red-600 font-bold">URG</span>}
                              </td>
                              <td className="p-2 whitespace-nowrap max-w-[120px] truncate" title={item.modelo_nombre}>{item.modelo_nombre || '-'}</td>
                              <td className="p-2 whitespace-nowrap">{item.tipo_nombre || '-'}</td>
                              <td className="p-2 whitespace-nowrap">{item.entalle_nombre || '-'}</td>
                              <td className="p-2 whitespace-nowrap">{item.tela_nombre || '-'}</td>
                              <td className="p-2 text-right font-mono">{item.cantidad_enviada?.toLocaleString() || '-'}</td>
                              <td className="p-2 text-center whitespace-nowrap">{item.fecha_inicio ? new Date(item.fecha_inicio + 'T00:00:00').toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit' }) : '-'}</td>
                              <td className="p-2 text-center whitespace-nowrap">{item.fecha_esperada ? new Date(item.fecha_esperada + 'T00:00:00').toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit' }) : (item.fecha_fin ? new Date(item.fecha_fin + 'T00:00:00').toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit' }) : '-')}</td>
                              <td className="p-2 text-center font-mono">{item.dias_transcurridos ?? '-'}</td>
                              <td className="p-2 text-center">
                                <AvanceEditor movimientoId={item.movimiento_id} currentValue={item.avance_porcentaje} onSaved={fetchData} nCorte={item.n_corte} />
                              </td>
                              <td className="p-2 text-center whitespace-nowrap text-muted-foreground">
                                {item.avance_updated_at ? new Date(item.avance_updated_at).toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit' }) : '-'}
                              </td>
                              <td className={`p-2 text-center font-mono ${diasSinAct != null && diasSinAct >= 5 ? 'text-red-600 font-bold' : diasSinAct != null && diasSinAct >= 3 ? 'text-amber-600 font-semibold' : ''}`}>
                                {diasSinAct ?? '-'}
                              </td>
                              <td className="p-2 text-center">
                                {item.incidencias_abiertas > 0 ? (
                                  <Badge variant="destructive" className="text-[10px] px-1.5">{item.incidencias_abiertas}</Badge>
                                ) : <span className="text-muted-foreground">0</span>}
                              </td>
                              <td className="p-2 text-center">
                                <Badge className={`${cfg.color} text-[10px] border`}>{cfg.label}</Badge>
                              </td>
                              <td className="p-2 text-center">
                                <div className="flex items-center justify-center gap-0.5">
                                  <Button
                                    type="button" variant="ghost" size="icon" className="h-6 w-6"
                                    onClick={() => navigate(`/registros/${item.registro_id}`)}
                                    title="Abrir registro"
                                    data-testid={`open-registro-${item.movimiento_id}`}
                                  >
                                    <ExternalLink className="h-3 w-3" />
                                  </Button>
                                  <Button
                                    type="button" variant="ghost" size="icon" className="h-6 w-6"
                                    onClick={() => setIncDialog(item)}
                                    title="Agregar incidencia"
                                    data-testid={`add-incidencia-${item.movimiento_id}`}
                                  >
                                    <Plus className="h-3 w-3" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Dialog incidencia rápida */}
      <Dialog open={!!incDialog} onOpenChange={(open) => { if (!open) setIncDialog(null); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Incidencia rápida — Corte {incDialog?.n_corte}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground">Motivo</label>
              <Select value={incMotivo} onValueChange={setIncMotivo}>
                <SelectTrigger className="h-9" data-testid="inc-rapida-motivo"><SelectValue placeholder="Seleccionar motivo" /></SelectTrigger>
                <SelectContent>
                  {motivos.map(m => <SelectItem key={m.id} value={m.id}>{m.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Comentario (opcional)</label>
              <Textarea value={incComentario} onChange={e => setIncComentario(e.target.value)} rows={2} className="text-sm" data-testid="inc-rapida-comentario" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setIncDialog(null)}>Cancelar</Button>
            <Button onClick={handleIncidenciaRapida} disabled={!incMotivo || incSaving} data-testid="inc-rapida-guardar">
              {incSaving ? 'Guardando...' : 'Crear Incidencia'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ReporteCostura;

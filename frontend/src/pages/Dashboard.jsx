import { useEffect, useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
  Activity, AlertTriangle, Clock, Package, PauseCircle, PackageX,
  ArrowRight, Layers, TrendingUp, Plus, ArrowDownCircle,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getEtapaColor = (estado) => {
  const e = (estado || '').toLowerCase();
  if (e.includes('corte')) return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
  if (e.includes('costura') || e.includes('atraque')) return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
  if (e.includes('lavand')) return 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300';
  if (e.includes('acabado')) return 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300';
  if (e.includes('almac') || e.includes('tienda')) return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300';
  if (e.includes('estampado')) return 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300';
  if (e.includes('bordado')) return 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300';
  return 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300';
};

const FILTROS_LOTES = [
  { key: 'todos', label: 'Todos' },
  { key: 'corte', label: 'Corte' },
  { key: 'costura', label: 'Costura' },
  { key: 'acabado', label: 'Acabado' },
  { key: 'atrasados', label: 'Atrasados' },
];

export const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [alertas, setAlertas] = useState(null);
  const [lotes, setLotes] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filtroLote, setFiltroLote] = useState('todos');
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const get = (path) => fetch(`${API}${path}`, { headers }).then(r => r.ok ? r.json() : null).catch(() => null);

    Promise.all([
      get('/stats'),
      get('/reportes-produccion/dashboard'),
      get('/reportes-produccion/alertas-produccion'),
      get('/reportes-produccion/en-proceso'),
    ])
      .then(([s, d, a, l]) => { setStats(s); setDashboard(d); setAlertas(a); setLotes(l); })
      .finally(() => setLoading(false));
  }, []);

  // IDs de registros con alertas (para filtro "Atrasados")
  const alertaIds = useMemo(() => {
    if (!alertas?.alertas) return new Set();
    return new Set(alertas.alertas.map(a => a.registro_id));
  }, [alertas]);

  // Lotes filtrados
  const lotesFiltrados = useMemo(() => {
    const all = lotes?.registros || [];
    if (filtroLote === 'todos') return all;
    if (filtroLote === 'atrasados') return all.filter(l => alertaIds.has(l.id));
    return all.filter(l => (l.estado || '').toLowerCase().includes(filtroLote));
  }, [lotes, filtroLote, alertaIds]);

  // Saludo
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Buenos días' : hour < 18 ? 'Buenas tardes' : 'Buenas noches';
  const today = new Date().toLocaleDateString('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  const nombre = user?.nombre_completo || user?.username || '';

  if (loading) return (
    <div className="flex items-center justify-center h-64" data-testid="dashboard">
      <div className="animate-pulse text-muted-foreground">Cargando dashboard...</div>
    </div>
  );

  const atrasados = dashboard?.atrasados || 0;

  return (
    <div className="space-y-5 max-w-6xl" data-testid="dashboard">
      {/* Saludo */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight" data-testid="dashboard-greeting">
          {greeting}, {nombre}
        </h2>
        <p className="text-sm text-muted-foreground capitalize">{today}</p>
      </div>

      {/* KPIs */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <Card className="cursor-pointer hover:shadow-md transition-shadow border-l-4 border-l-blue-500" onClick={() => navigate('/reportes/seguimiento')} data-testid="kpi-en-proceso">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">En Proceso</span>
              <Activity className="h-4 w-4 text-blue-500" />
            </div>
            <p className="text-3xl font-bold tracking-tight">{dashboard?.total_en_proceso || stats?.registros || 0}</p>
            <p className="text-xs text-muted-foreground mt-0.5">lotes activos</p>
          </CardContent>
        </Card>

        <Card data-testid="kpi-prendas" className="border-l-4 border-l-emerald-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Prendas</span>
              <Package className="h-4 w-4 text-emerald-500" />
            </div>
            <p className="text-3xl font-bold tracking-tight">{(dashboard?.total_prendas_proceso || 0).toLocaleString()}</p>
            <p className="text-xs text-muted-foreground mt-0.5">en producción</p>
          </CardContent>
        </Card>

        <Card className={`cursor-pointer hover:shadow-md transition-shadow border-l-4 ${atrasados > 0 ? 'border-l-red-500' : 'border-l-zinc-300 dark:border-l-zinc-600'}`}
          onClick={() => navigate('/reportes/seguimiento?tab=atrasados')} data-testid="kpi-atrasados">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Atrasados</span>
              <AlertTriangle className={`h-4 w-4 ${atrasados > 0 ? 'text-red-500' : 'text-muted-foreground'}`} />
            </div>
            <p className={`text-3xl font-bold tracking-tight ${atrasados > 0 ? 'text-red-600 dark:text-red-400' : ''}`}>{atrasados}</p>
            <p className="text-xs text-muted-foreground mt-0.5">requieren atención</p>
          </CardContent>
        </Card>

        <Card data-testid="kpi-movs" className="border-l-4 border-l-amber-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Movimientos</span>
              <Clock className="h-4 w-4 text-amber-500" />
            </div>
            <p className="text-3xl font-bold tracking-tight">{dashboard?.movimientos_abiertos || 0}</p>
            <p className="text-xs text-muted-foreground mt-0.5">abiertos</p>
          </CardContent>
        </Card>
      </div>

      {/* Acciones Rapidas */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" data-testid="dashboard-acciones">
        <Button variant="default" className="h-11 text-sm font-medium gap-2" onClick={() => navigate('/registros/nuevo')} data-testid="btn-nuevo-registro">
          <Plus className="h-4 w-4" /> Nuevo Registro
        </Button>
        <Button variant="outline" className="h-11 text-sm font-medium gap-2" onClick={() => navigate('/reportes/seguimiento')} data-testid="btn-ver-seguimiento">
          <Activity className="h-4 w-4" /> Ver Seguimiento
        </Button>
        <Button variant="outline" className="h-11 text-sm font-medium gap-2" onClick={() => navigate('/inventario/ingresos')} data-testid="btn-ingresar-stock">
          <ArrowDownCircle className="h-4 w-4" /> Ingresar Stock
        </Button>
      </div>

      {/* Lotes Activos */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Layers className="h-4 w-4" /> Lotes Activos
              {lotes?.total > 0 && <Badge variant="secondary" className="text-[10px] font-mono">{lotes.total}</Badge>}
            </CardTitle>
          </div>
          {/* Pills */}
          <div className="flex flex-wrap gap-1.5 mt-2" data-testid="lotes-filtros">
            {FILTROS_LOTES.map(f => (
              <button key={f.key} onClick={() => setFiltroLote(f.key)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  filtroLote === f.key
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground hover:text-foreground hover:bg-muted/80'
                }`}
                data-testid={`filtro-${f.key}`}>
                {f.label}
                {f.key === 'atrasados' && atrasados > 0 && (
                  <span className="ml-1 text-[9px] bg-red-500 text-white rounded-full px-1">{atrasados}</span>
                )}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {lotesFiltrados.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">Sin lotes en esta categoría</p>
          ) : (
            <div className="space-y-1.5">
              {lotesFiltrados.slice(0, 8).map(l => (
                <div key={l.id}
                  className="flex items-center gap-3 p-2.5 rounded-lg border hover:bg-accent/50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/registros/editar/${l.id}`)}
                  data-testid={`lote-${l.n_corte}`}>
                  <span className="text-sm font-bold w-12 shrink-0 text-center">{l.n_corte}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold shrink-0 ${getEtapaColor(l.estado)}`}>
                    {l.estado}
                  </span>
                  <span className="text-sm truncate flex-1 text-muted-foreground">{l.modelo_nombre}</span>
                  {l.urgente && <Badge variant="destructive" className="text-[9px] px-1.5 py-0 shrink-0">URG</Badge>}
                  <span className="text-xs text-muted-foreground shrink-0 tabular-nums font-mono">{l.dias_proceso}d</span>
                </div>
              ))}
              {lotesFiltrados.length > 8 && (
                <button className="w-full text-center text-xs text-primary hover:underline py-2" onClick={() => navigate('/reportes/seguimiento')} data-testid="ver-todos-lotes">
                  Ver todos ({lotesFiltrados.length}) <ArrowRight className="inline h-3 w-3 ml-0.5" />
                </button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* WIP por Etapa */}
      {dashboard?.distribucion_estado?.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2"><TrendingUp className="h-4 w-4" /> WIP por Etapa</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 grid-cols-2 md:grid-cols-4 lg:grid-cols-6">
              {dashboard.distribucion_estado.map((d) => (
                <div key={d.estado} className="rounded-lg border p-3 text-center hover:shadow-sm transition-shadow">
                  <p className="text-xs text-muted-foreground truncate">{d.estado}</p>
                  <p className="text-2xl font-bold mt-1">{d.cantidad}</p>
                  <p className="text-[10px] text-muted-foreground">{(d.prendas || 0).toLocaleString()} prendas</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Carga por Servicio */}
      {dashboard?.por_servicio?.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2"><TrendingUp className="h-4 w-4" /> Carga por Servicio</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {dashboard.por_servicio.map((s) => {
                const maxVal = Math.max(...dashboard.por_servicio.map(x => x.enviadas || 0), 1);
                const pct = Math.round(((s.enviadas || 0) / maxVal) * 100);
                return (
                  <div key={s.servicio} className="flex items-center gap-3">
                    <span className="text-xs w-24 shrink-0 truncate text-right text-muted-foreground">{s.servicio}</span>
                    <div className="flex-1 h-6 bg-muted rounded-full overflow-hidden relative">
                      <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                      <span className="absolute inset-0 flex items-center justify-center text-[10px] font-mono font-semibold">{s.enviadas || 0} env / {s.recibidas || 0} rec</span>
                    </div>
                    <span className="text-xs font-mono text-muted-foreground w-12 shrink-0">{s.lotes}L</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Alertas de Produccion */}
      {alertas && alertas.resumen?.total > 0 && (
        <Card className="border-red-200/60 dark:border-red-900/40" data-testid="dashboard-alertas">
          <CardHeader className="pb-2 pt-3 px-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-500" />
                <CardTitle className="text-sm font-semibold">Alertas</CardTitle>
                <Badge variant="destructive" className="text-[10px]">{alertas.resumen.total}</Badge>
              </div>
              <div className="flex gap-1.5">
                {alertas.resumen.vencidos > 0 && <Badge className="bg-zinc-800 text-white text-[10px]">{alertas.resumen.vencidos} vencidos</Badge>}
                {alertas.resumen.criticos > 0 && <Badge variant="destructive" className="text-[10px]">{alertas.resumen.criticos} críticos</Badge>}
                {alertas.resumen.paralizados > 0 && <Badge className="bg-amber-500 text-white text-[10px]">{alertas.resumen.paralizados} paralizados</Badge>}
              </div>
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-3 pt-1">
            <div className="space-y-1.5">
              {alertas.alertas.slice(0, 3).map((a) => (
                <div key={a.movimiento_id} className="flex items-center gap-2 p-2 rounded-md border hover:bg-accent/50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/registros/editar/${a.registro_id}`)} data-testid={`alerta-${a.n_corte}`}>
                  {a.paralizado ? <PauseCircle className="h-4 w-4 text-amber-500 shrink-0" /> : <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />}
                  <span className="font-semibold text-xs shrink-0">Corte {a.n_corte}</span>
                  {a.urgente && <span className="text-[9px] font-bold text-red-600">URG</span>}
                  <span className="text-xs text-muted-foreground truncate flex-1">{a.servicio} - {a.persona}</span>
                  <Badge variant="outline" className="text-[9px] px-1 shrink-0">{a.dias}d</Badge>
                </div>
              ))}
            </div>
            {alertas.alertas.length > 3 && (
              <button className="mt-2 text-xs text-primary hover:underline w-full text-center" onClick={() => navigate('/reportes/seguimiento?tab=atrasados')}>
                Ver todas ({alertas.alertas.length}) <ArrowRight className="inline h-3 w-3 ml-0.5" />
              </button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Alerta Stock */}
      {stats?.alertas_stock_total > 0 && (
        <Card className="border-amber-300/50 bg-amber-50/30 dark:bg-amber-950/10 cursor-pointer hover:shadow-sm transition-shadow"
          onClick={() => navigate('/inventario/alertas-stock')} data-testid="dashboard-alerta-stock">
          <CardContent className="py-2.5 px-4">
            <div className="flex items-center gap-3">
              <PackageX className="h-5 w-5 text-amber-600 shrink-0" />
              <div className="flex-1">
                <span className="text-sm font-medium">{stats.alertas_stock_total} items requieren atención</span>
                <span className="text-xs text-muted-foreground ml-2">
                  {stats.sin_stock > 0 && <span className="text-red-500">{stats.sin_stock} sin stock</span>}
                  {stats.sin_stock > 0 && stats.stock_bajo > 0 && ' | '}
                  {stats.stock_bajo > 0 && <span className="text-amber-600">{stats.stock_bajo} stock bajo</span>}
                </span>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

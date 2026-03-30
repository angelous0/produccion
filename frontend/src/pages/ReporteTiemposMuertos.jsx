import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import {
  Clock, AlertTriangle, PauseCircle, ExternalLink, RefreshCw,
  Search, ChevronDown, ChevronRight, Timer,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const NIVEL_CONFIG = {
  critico:  { label: 'Crítico',   color: 'bg-red-100 text-red-800 border-red-200', rowClass: 'bg-red-50/50' },
  atencion: { label: 'Atención',  color: 'bg-amber-100 text-amber-800 border-amber-200', rowClass: 'bg-amber-50/50' },
  espera:   { label: 'En espera', color: 'bg-blue-100 text-blue-800 border-blue-200', rowClass: '' },
  ok:       { label: 'OK',        color: 'bg-transparent text-muted-foreground border-transparent', rowClass: '' },
};

const KpiCard = ({ label, value, icon: Icon, danger }) => (
  <Card className={danger && value > 0 ? 'border-red-200 bg-red-50/30' : ''}>
    <CardContent className="p-4 flex items-center gap-3">
      <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${danger && value > 0 ? 'bg-red-100' : 'bg-muted'}`}>
        <Icon className={`h-4 w-4 ${danger && value > 0 ? 'text-red-600' : 'text-muted-foreground'}`} />
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{label}</p>
        <p className={`text-xl font-bold ${danger && value > 0 ? 'text-red-700' : ''}`}>{value}</p>
      </div>
    </CardContent>
  </Card>
);

const fmtDate = (d) => {
  if (!d) return '-';
  const dt = new Date(d + (d.includes('T') ? '' : 'T00:00:00'));
  return `${String(dt.getDate()).padStart(2, '0')}-${String(dt.getMonth() + 1).padStart(2, '0')}-${dt.getFullYear()}`;
};

export const ReporteTiemposMuertos = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState('en_curso');
  const [busqueda, setBusqueda] = useState('');
  const [sortDesc, setSortDesc] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = filtro === 'todos' ? '?incluir_resueltos=true' : '';
      const res = await axios.get(`${API}/api/reportes-produccion/tiempos-muertos${params}`);
      setData(res.data);
    } catch {
      toast.error('Error al cargar reporte');
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, [filtro]);

  const filtered = useMemo(() => {
    if (!data) return [];
    let items = data.items;
    if (busqueda.trim()) {
      const q = busqueda.toLowerCase();
      items = items.filter(b =>
        (b.n_corte || '').toLowerCase().includes(q) ||
        (b.modelo || '').toLowerCase().includes(q) ||
        (b.ultimo_servicio || '').toLowerCase().includes(q) ||
        (b.ultima_persona || '').toLowerCase().includes(q) ||
        (b.estado_actual || '').toLowerCase().includes(q)
      );
    }
    items = [...items].sort((a, b) => sortDesc ? b.dias_parado - a.dias_parado : a.dias_parado - b.dias_parado);
    return items;
  }, [data, busqueda, sortDesc]);

  const resumen = data?.resumen || {};

  return (
    <div className="space-y-4" data-testid="reporte-tiempos-muertos">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Tiempos Muertos</h2>
          <p className="text-sm text-muted-foreground">Lotes parados sin avanzar al siguiente servicio</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center rounded-lg border text-sm overflow-hidden">
            <button type="button" onClick={() => setFiltro('en_curso')} className={`px-3 py-1.5 text-xs font-medium transition-colors ${filtro === 'en_curso' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}>En espera</button>
            <button type="button" onClick={() => setFiltro('todos')} className={`px-3 py-1.5 text-xs font-medium transition-colors ${filtro === 'todos' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}>Todos</button>
          </div>
          <Button variant="outline" size="sm" onClick={fetchData} data-testid="btn-refresh-tm">
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} /> Actualizar
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Lotes parados" value={resumen.total || 0} icon={Timer} />
        <KpiCard label="En espera" value={resumen.en_espera || 0} icon={PauseCircle} danger />
        <KpiCard label="Críticos (7+ días)" value={resumen.criticos || 0} icon={AlertTriangle} danger />
        <KpiCard label="Días acumulados" value={resumen.dias_perdidos || 0} icon={Clock} danger />
      </div>

      {/* Búsqueda */}
      <div className="relative max-w-xs">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          placeholder="Buscar corte, modelo, servicio, estado..."
          value={busqueda}
          onChange={e => setBusqueda(e.target.value)}
          className="h-8 pl-8 text-xs"
          data-testid="busqueda-tm"
        />
      </div>

      {/* Tabla */}
      {loading ? (
        <div className="text-center py-12 text-muted-foreground">Cargando...</div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {filtro === 'en_curso'
              ? 'Sin lotes parados entre servicios'
              : 'No se encontraron registros'}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-muted/60 border-b">
                  <th className="text-left p-2.5 font-medium text-muted-foreground">Corte</th>
                  <th className="text-left p-2.5 font-medium text-muted-foreground">Modelo</th>
                  <th className="text-left p-2.5 font-medium text-muted-foreground">Último Servicio</th>
                  <th className="text-left p-2.5 font-medium text-muted-foreground">Persona</th>
                  <th className="text-center p-2.5 font-medium text-muted-foreground">Terminó</th>
                  <th className="text-left p-2.5 font-medium text-muted-foreground">Estado Actual</th>
                  <th
                    className="text-center p-2.5 font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground group"
                    onClick={() => setSortDesc(p => !p)}
                  >
                    Días parado {sortDesc ? <ChevronDown className="inline h-3 w-3" /> : <ChevronRight className="inline h-3 w-3 rotate-[-90deg]" />}
                  </th>
                  <th className="text-center p-2.5 font-medium text-muted-foreground">Nivel</th>
                  <th className="text-center p-2.5 font-medium text-muted-foreground">Acción</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item, idx) => {
                  const cfg = NIVEL_CONFIG[item.nivel] || NIVEL_CONFIG.ok;
                  return (
                    <tr key={`${item.registro_id}-${idx}`} className={`border-t hover:bg-muted/30 transition-colors ${cfg.rowClass}`} data-testid={`tm-row-${item.n_corte}`}>
                      <td className="p-2.5 font-mono font-semibold whitespace-nowrap">
                        {item.n_corte}
                        {item.urgente && <span className="ml-1 text-[9px] text-red-600 font-bold">URG</span>}
                      </td>
                      <td className="p-2.5 whitespace-nowrap">{item.modelo || '-'}</td>
                      <td className="p-2.5 whitespace-nowrap font-medium">{item.ultimo_servicio}</td>
                      <td className="p-2.5 whitespace-nowrap text-muted-foreground">{item.ultima_persona || '-'}</td>
                      <td className="p-2.5 text-center whitespace-nowrap">{fmtDate(item.fecha_termino)}</td>
                      <td className="p-2.5 whitespace-nowrap">
                        <Badge variant="outline" className="text-[10px]">{item.estado_actual}</Badge>
                      </td>
                      <td className={`p-2.5 text-center font-mono font-bold whitespace-nowrap ${
                        item.dias_parado >= 7 ? 'bg-red-100 text-red-700' :
                        item.dias_parado >= 3 ? 'bg-amber-100 text-amber-700' : ''
                      }`}>
                        {item.dias_parado}
                      </td>
                      <td className="p-2.5 text-center">
                        {item.nivel === 'ok' ? (
                          <span className="text-[10px] text-muted-foreground">—</span>
                        ) : (
                          <Badge className={`${cfg.color} text-[10px] border`}>{cfg.label}</Badge>
                        )}
                      </td>
                      <td className="p-2.5 text-center">
                        <Button
                          type="button" variant="ghost" size="icon" className="h-6 w-6"
                          onClick={() => navigate(`/registros/${item.registro_id}`)}
                          title="Abrir registro"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};

export default ReporteTiemposMuertos;

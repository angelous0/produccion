import { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  LineChart, Line, Area, AreaChart
} from 'recharts';
import { 
  Tag, 
  Layers, 
  Shirt, 
  Palette, 
  Scissors, 
  Box, 
  ClipboardList,
  AlertTriangle,
  Ruler,
  Droplets,
  TrendingUp,
  Package,
  PackageX,
  Users,
  Activity,
  Clock,
  PauseCircle,
  ExternalLink,
} from 'lucide-react';
import { getStatusClass } from '../lib/utils';
import { useNavigate } from 'react-router-dom';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Colores para gráficos
const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
const STATUS_COLORS = {
  'Para Corte': '#3b82f6',
  'En Corte': '#f59e0b', 
  'En Proceso': '#8b5cf6',
  'Terminado': '#10b981',
  'Entregado': '#06b6d4',
  'Cancelado': '#ef4444',
};

const StatCard = ({ title, value, icon: Icon, description, trend }) => (
  <Card className="dashboard-widget">
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium text-muted-foreground">
        {title}
      </CardTitle>
      <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
        <Icon className="h-4 w-4 text-primary" />
      </div>
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value}</div>
      {description && (
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      )}
      {trend && (
        <div className="flex items-center gap-1 mt-1">
          <TrendingUp className="h-3 w-3 text-green-500" />
          <span className="text-xs text-green-500">{trend}</span>
        </div>
      )}
    </CardContent>
  </Card>
);

export const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [alertas, setAlertas] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, chartRes, alertasRes] = await Promise.all([
          axios.get(`${API}/stats`),
          axios.get(`${API}/stats/charts`),
          axios.get(`${API}/reportes-produccion/alertas-produccion`).catch(() => ({ data: null })),
        ]);
        setStats(statsRes.data);
        setChartData(chartRes.data);
        setAlertas(alertasRes.data);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="dashboard-loading">
        <div className="text-muted-foreground">Cargando...</div>
      </div>
    );
  }

  // Preparar datos para gráficos
  const estadosData = stats?.estados_count ? 
    Object.entries(stats.estados_count).map(([name, value]) => ({ 
      name, 
      value,
      fill: STATUS_COLORS[name] || '#6b7280'
    })) : [];

  const marcasData = chartData?.registros_por_marca || [];
  const produccionMensual = chartData?.produccion_mensual || [];

  return (
    <div className="space-y-6" data-testid="dashboard">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Resumen del módulo de producción textil</p>
      </div>

      {/* Alertas de Producción */}
      {alertas && alertas.resumen?.total > 0 && (
        <Card className="border-red-200 bg-red-50/30" data-testid="dashboard-alertas">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-red-100 flex items-center justify-center">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                </div>
                <div>
                  <CardTitle className="text-base">Alertas de Producción</CardTitle>
                  <CardDescription className="text-xs">{alertas.resumen.total} lotes requieren atención</CardDescription>
                </div>
              </div>
              <div className="flex gap-2">
                {alertas.resumen.vencidos > 0 && (
                  <div className="text-center px-3 py-1 rounded-md bg-zinc-800 text-white">
                    <p className="text-lg font-bold leading-tight">{alertas.resumen.vencidos}</p>
                    <p className="text-[10px] opacity-80">Vencidos</p>
                  </div>
                )}
                {alertas.resumen.criticos > 0 && (
                  <div className="text-center px-3 py-1 rounded-md bg-red-100 text-red-800">
                    <p className="text-lg font-bold leading-tight">{alertas.resumen.criticos}</p>
                    <p className="text-[10px]">Críticos</p>
                  </div>
                )}
                {alertas.resumen.paralizados > 0 && (
                  <div className="text-center px-3 py-1 rounded-md bg-amber-100 text-amber-800">
                    <p className="text-lg font-bold leading-tight">{alertas.resumen.paralizados}</p>
                    <p className="text-[10px]">Paralizados</p>
                  </div>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {alertas.alertas.slice(0, 6).map((a) => (
                <div
                  key={a.movimiento_id}
                  className="flex items-start gap-2.5 p-3 rounded-lg border bg-white hover:shadow-sm cursor-pointer transition-all"
                  onClick={() => navigate(`/registros/editar/${a.registro_id}`)}
                  data-testid={`dashboard-alerta-${a.n_corte}`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {a.paralizado ? (
                      <PauseCircle className="h-5 w-5 text-amber-500" />
                    ) : a.nivel === 'vencido' ? (
                      <Clock className="h-5 w-5 text-zinc-700" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-semibold text-sm">Corte {a.n_corte}</span>
                      {a.urgente && <span className="text-[10px] font-bold text-red-600">URG</span>}
                      <Badge variant="outline" className={`text-[10px] px-1 ${
                        a.nivel === 'vencido' ? 'bg-zinc-800 text-white border-zinc-700' : 'bg-red-100 text-red-700 border-red-200'
                      }`}>{a.nivel === 'vencido' ? 'Vencido' : 'Crítico'}</Badge>
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate mt-0.5">{a.servicio} · {a.persona}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{a.motivo_texto}</p>
                    <div className="flex gap-3 mt-1">
                      <span className="text-[10px] text-muted-foreground">{a.dias}d</span>
                      <span className="text-[10px] text-muted-foreground">Avance: {a.avance}%</span>
                    </div>
                  </div>
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                </div>
              ))}
            </div>
            {alertas.alertas.length > 6 && (
              <button
                className="mt-3 text-xs text-primary hover:underline w-full text-center"
                onClick={() => navigate('/reportes/costura')}
              >
                Ver todas las alertas ({alertas.alertas.length})
              </button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Stats principales */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard 
          title="Total Registros" 
          value={stats?.registros || 0} 
          icon={ClipboardList}
          description="Registros de producción"
        />
        <StatCard 
          title="Urgentes" 
          value={stats?.registros_urgentes || 0} 
          icon={AlertTriangle}
          description="Requieren atención"
        />
        <StatCard 
          title="Modelos" 
          value={stats?.modelos || 0} 
          icon={Box}
          description="Modelos registrados"
        />
        <StatCard 
          title="Items Inventario" 
          value={stats?.inventario || 0} 
          icon={Package}
          description="Items en stock"
        />
      </div>

      {/* Alerta de Stock Bajo */}
      {stats?.alertas_stock_total > 0 && (
        <Card className="border-red-500/40 bg-red-500/5 cursor-pointer hover:bg-red-500/10 transition-colors"
          onClick={() => navigate('/inventario/alertas-stock')}
          data-testid="dashboard-alerta-stock"
        >
          <CardContent className="py-3 px-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-red-500/15 flex items-center justify-center">
                  <PackageX className="h-5 w-5 text-red-500" />
                </div>
                <div>
                  <p className="font-semibold text-sm">
                    {stats.alertas_stock_total} item{stats.alertas_stock_total !== 1 ? 's' : ''} de materia prima requiere{stats.alertas_stock_total === 1 ? '' : 'n'} atencion
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {stats.sin_stock > 0 && <span className="text-red-500 font-medium">{stats.sin_stock} sin stock</span>}
                    {stats.sin_stock > 0 && stats.stock_bajo > 0 && ' · '}
                    {stats.stock_bajo > 0 && <span className="text-yellow-600 font-medium">{stats.stock_bajo} con stock bajo</span>}
                  </p>
                </div>
              </div>
              <Badge variant="destructive" className="shrink-0">Ver reporte</Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Gráficos principales */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Gráfico de barras - Estados */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Registros por Estado
            </CardTitle>
            <CardDescription>Distribución actual de registros</CardDescription>
          </CardHeader>
          <CardContent>
            {estadosData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={estadosData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                  <XAxis type="number" />
                  <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--card))', 
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {estadosData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                Sin datos
              </div>
            )}
          </CardContent>
        </Card>

        {/* Gráfico circular - Por Marca */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Tag className="h-5 w-5" />
              Registros por Marca
            </CardTitle>
            <CardDescription>Distribución por marca</CardDescription>
          </CardHeader>
          <CardContent>
            {marcasData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={marcasData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    labelLine={false}
                  >
                    {marcasData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--card))', 
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                Sin datos
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Gráfico de línea - Producción mensual */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Producción Mensual
          </CardTitle>
          <CardDescription>Registros creados por mes</CardDescription>
        </CardHeader>
        <CardContent>
          {produccionMensual.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={produccionMensual}>
                <defs>
                  <linearGradient id="colorRegistros" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="mes" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Area 
                  type="monotone" 
                  dataKey="registros" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorRegistros)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-muted-foreground">
              Sin datos de producción mensual
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats secundarios */}
      <div className="grid gap-4 md:grid-cols-5">
        <StatCard title="Marcas" value={stats?.marcas || 0} icon={Tag} />
        <StatCard title="Tipos" value={stats?.tipos || 0} icon={Layers} />
        <StatCard title="Telas" value={stats?.telas || 0} icon={Palette} />
        <StatCard title="Tallas" value={stats?.tallas || 0} icon={Ruler} />
        <StatCard title="Colores" value={stats?.colores || 0} icon={Droplets} />
      </div>

      {/* Estados con badges */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Estados de Producción</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {estadosData.map(({ name, value, fill }) => (
              <div key={name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: fill }} />
                <span className="text-sm">{name}</span>
                <Badge variant="secondary" className="font-mono">{value}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

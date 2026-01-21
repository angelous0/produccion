import { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
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
  Droplets
} from 'lucide-react';
import { getStatusClass } from '../lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const StatCard = ({ title, value, icon: Icon, color = "primary" }) => (
  <Card className="dashboard-widget" data-testid={`stat-${title.toLowerCase().replace(/\s/g, '-')}`}>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
        {title}
      </CardTitle>
      <Icon className={`h-5 w-5 text-${color}`} />
    </CardHeader>
    <CardContent>
      <div className="text-3xl font-bold tracking-tight">{value}</div>
    </CardContent>
  </Card>
);

export const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get(`${API}/stats`);
        setStats(response.data);
      } catch (error) {
        console.error('Error fetching stats:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="dashboard-loading">
        <div className="text-muted-foreground">Cargando...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="dashboard">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Resumen del módulo de producción textil</p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <StatCard title="Marcas" value={stats?.marcas || 0} icon={Tag} />
        <StatCard title="Tipos" value={stats?.tipos || 0} icon={Layers} />
        <StatCard title="Entalles" value={stats?.entalles || 0} icon={Shirt} />
        <StatCard title="Telas" value={stats?.telas || 0} icon={Palette} />
        <StatCard title="Hilos" value={stats?.hilos || 0} icon={Scissors} />
        <StatCard title="Tallas" value={stats?.tallas || 0} icon={Ruler} />
        <StatCard title="Colores" value={stats?.colores || 0} icon={Droplets} />
        <StatCard title="Modelos" value={stats?.modelos || 0} icon={Box} />
        <StatCard title="Registros" value={stats?.registros || 0} icon={ClipboardList} />
        <StatCard 
          title="Urgentes" 
          value={stats?.registros_urgentes || 0} 
          icon={AlertTriangle} 
          color="destructive"
        />
      </div>

      {/* Estados de Producción */}
      <Card data-testid="estados-produccion">
        <CardHeader>
          <CardTitle className="text-lg font-semibold tracking-tight">Estados de Producción</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {stats?.estados_count && Object.entries(stats.estados_count).map(([estado, count]) => (
              <div 
                key={estado}
                className="flex items-center gap-2"
              >
                <Badge 
                  variant="outline" 
                  className={`${getStatusClass(estado)} px-3 py-1`}
                >
                  {estado}
                </Badge>
                <span className="font-mono text-sm font-medium">{count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

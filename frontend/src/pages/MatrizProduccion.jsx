import { useEffect, useState, useMemo, useCallback, Fragment } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import {
  Popover, PopoverContent, PopoverTrigger,
} from '../components/ui/popover';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Settings2, GripVertical, ChevronDown, ChevronRight,
  ExternalLink, Eye, EyeOff, ArrowLeftRight, MoveLeft, MoveRight,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const STORAGE_KEY = 'matriz-produccion-prefs';

// ── Helpers ───────────────────────────────────────────────────
function loadPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}
function savePrefs(prefs) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch {}
}

// ── Filtro individual ─────────────────────────────────────────
const FilterSelect = ({ label, value, onChange, options, testId }) => (
  <div className="flex flex-col gap-1">
    <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</Label>
    <Select value={value || '_all'} onValueChange={v => onChange(v === '_all' ? '' : v)}>
      <SelectTrigger className="h-8 text-xs w-[150px]" data-testid={testId}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="_all">Todos</SelectItem>
        {options.map(o => (
          <SelectItem key={o.id} value={o.id}>{o.nombre}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
);

// ── Componente principal ──────────────────────────────────────
export const MatrizProduccion = () => {
  const navigate = useNavigate();

  // Data
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Filtros
  const [filters, setFilters] = useState({
    ruta_id: '', marca_id: '', tipo_id: '', entalle_id: '',
    tela_id: '', hilo_id: '', modelo_id: '', estado: '',
    solo_atrasados: false, solo_activos: true, solo_fraccionados: false,
  });

  // Métrica
  const [metrica, setMetrica] = useState('registros'); // 'registros' | 'prendas'

  // Columnas visibles y orden
  const [visibleCols, setVisibleCols] = useState(null);  // null = all
  const [colOrder, setColOrder] = useState(null);         // null = default

  // Expandidos
  const [expanded, setExpanded] = useState({});

  // ── Cargar datos ────────────────────────────────────────────
  const fetchData = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== '' && v !== false) {
        params.append(k, String(v));
      }
    });
    axios.get(`${API}/reportes-produccion/matriz?${params}`)
      .then(res => {
        setData(res.data);
        // Initialize column prefs from saved or API defaults
        const apiCols = res.data.columnas || [];
        const saved = loadPrefs();
        if (saved && saved.ruta === (filters.ruta_id || '__global__')) {
          // Restore saved prefs for same ruta context
          const savedVisible = saved.visible?.filter(c => apiCols.includes(c));
          const savedOrder = saved.order?.filter(c => apiCols.includes(c));
          // Add any new cols from API not in saved
          const missing = apiCols.filter(c => !savedOrder?.includes(c));
          setVisibleCols(savedVisible?.length ? savedVisible : apiCols);
          setColOrder(savedOrder?.length ? [...savedOrder, ...missing] : apiCols);
        } else {
          setVisibleCols(apiCols);
          setColOrder(apiCols);
        }
      })
      .catch(err => console.error('Error loading matriz:', err))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── Guardar prefs cuando cambian ────────────────────────────
  useEffect(() => {
    if (visibleCols && colOrder) {
      savePrefs({
        ruta: filters.ruta_id || '__global__',
        visible: visibleCols,
        order: colOrder,
      });
    }
  }, [visibleCols, colOrder, filters.ruta_id]);

  // ── Columnas efectivas (visibles + ordenadas) ───────────────
  const effectiveCols = useMemo(() => {
    if (!colOrder || !visibleCols) return data?.columnas || [];
    return colOrder.filter(c => visibleCols.includes(c));
  }, [colOrder, visibleCols, data]);

  // ── Handlers filtros ────────────────────────────────────────
  const setFilter = (key, val) => {
    setFilters(prev => ({ ...prev, [key]: val }));
    setExpanded({});
  };
  const clearFilters = () => {
    setFilters({
      ruta_id: '', marca_id: '', tipo_id: '', entalle_id: '',
      tela_id: '', hilo_id: '', modelo_id: '', estado: '',
      solo_atrasados: false, solo_activos: true, solo_fraccionados: false,
    });
    setExpanded({});
  };

  // ── Handlers columnas ───────────────────────────────────────
  const toggleCol = (col) => {
    setVisibleCols(prev => {
      if (!prev) return [];
      return prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col];
    });
  };
  const moveCol = (col, direction) => {
    setColOrder(prev => {
      if (!prev) return prev;
      const idx = prev.indexOf(col);
      if (idx < 0) return prev;
      const newIdx = direction === 'left' ? idx - 1 : idx + 1;
      if (newIdx < 0 || newIdx >= prev.length) return prev;
      const arr = [...prev];
      [arr[idx], arr[newIdx]] = [arr[newIdx], arr[idx]];
      return arr;
    });
  };
  const showAllCols = () => setVisibleCols(data?.columnas || []);

  // ── Toggle expand ───────────────────────────────────────────
  const toggleExpand = (key) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // ── Valor de celda según métrica ────────────────────────────
  const cellVal = (celdas, col) => {
    const c = celdas?.[col];
    if (!c) return 0;
    return metrica === 'prendas' ? c.prendas : c.registros;
  };
  const totalVal = (total) => {
    if (!total) return 0;
    return metrica === 'prendas' ? total.prendas : total.registros;
  };

  const filtrosDisp = data?.filtros_disponibles || {};
  const allCols = data?.columnas || [];
  const hasActiveFilters = Object.entries(filters).some(([k, v]) => {
    if (k === 'solo_activos') return !v;
    return v !== '' && v !== false;
  });

  return (
    <div className="space-y-3" data-testid="matriz-produccion">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate('/reportes/dashboard')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h2 className="text-2xl font-bold tracking-tight">Matriz de Producción</h2>
          <p className="text-muted-foreground text-sm">Vista global por Item × Estado</p>
        </div>
      </div>

      {/* ── Filtros ──────────────────────────────────────────── */}
      <Card>
        <CardContent className="pt-4 pb-3">
          <div className="flex flex-wrap gap-3 items-end">
            <FilterSelect label="Ruta" value={filters.ruta_id} onChange={v => setFilter('ruta_id', v)} options={filtrosDisp.rutas || []} testId="filter-ruta" />
            <FilterSelect label="Marca" value={filters.marca_id} onChange={v => setFilter('marca_id', v)} options={filtrosDisp.marcas || []} testId="filter-marca" />
            <FilterSelect label="Tipo" value={filters.tipo_id} onChange={v => setFilter('tipo_id', v)} options={filtrosDisp.tipos || []} testId="filter-tipo" />
            <FilterSelect label="Entalle" value={filters.entalle_id} onChange={v => setFilter('entalle_id', v)} options={filtrosDisp.entalles || []} testId="filter-entalle" />
            <FilterSelect label="Tela" value={filters.tela_id} onChange={v => setFilter('tela_id', v)} options={filtrosDisp.telas || []} testId="filter-tela" />
            <FilterSelect label="Hilo" value={filters.hilo_id} onChange={v => setFilter('hilo_id', v)} options={filtrosDisp.hilos || []} testId="filter-hilo" />
            <FilterSelect label="Modelo" value={filters.modelo_id} onChange={v => setFilter('modelo_id', v)} options={filtrosDisp.modelos || []} testId="filter-modelo" />
          </div>
          <div className="flex flex-wrap gap-4 mt-3 items-center">
            <div className="flex items-center gap-2">
              <Switch id="solo-activos" checked={filters.solo_activos} onCheckedChange={v => setFilter('solo_activos', v)} />
              <Label htmlFor="solo-activos" className="text-xs">Solo activos</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch id="solo-atrasados" checked={filters.solo_atrasados} onCheckedChange={v => setFilter('solo_atrasados', v)} />
              <Label htmlFor="solo-atrasados" className="text-xs">Solo atrasados</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch id="solo-fraccionados" checked={filters.solo_fraccionados} onCheckedChange={v => setFilter('solo_fraccionados', v)} />
              <Label htmlFor="solo-fraccionados" className="text-xs">Solo fraccionados</Label>
            </div>
            {hasActiveFilters && (
              <Button variant="outline" size="sm" className="text-xs h-7" onClick={clearFilters}>
                Limpiar filtros
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* ── Toolbar: Métrica + Columnas ──────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        {/* Métrica */}
        <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5" data-testid="metrica-toggle">
          <button
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${metrica === 'registros' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setMetrica('registros')}
            data-testid="metrica-registros"
          >
            Registros
          </button>
          <button
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${metrica === 'prendas' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setMetrica('prendas')}
            data-testid="metrica-prendas"
          >
            Prendas
          </button>
        </div>

        {/* Panel de columnas */}
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="text-xs">
            {effectiveCols.length}/{allCols.length} columnas
          </Badge>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" className="text-xs h-8 gap-1" data-testid="btn-config-columnas">
                <Settings2 className="h-3.5 w-3.5" /> Columnas
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80 max-h-[400px] overflow-y-auto" align="end">
              <div className="space-y-1">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium">Columnas visibles</p>
                  <Button variant="ghost" size="sm" className="text-xs h-6" onClick={showAllCols}>
                    Mostrar todas
                  </Button>
                </div>
                {(colOrder || allCols).map((col, idx) => {
                  const isVisible = visibleCols?.includes(col);
                  return (
                    <div key={col} className="flex items-center gap-1.5 py-1 px-1 rounded hover:bg-muted/50 group">
                      <GripVertical className="h-3 w-3 text-muted-foreground/40" />
                      <button
                        className="flex-1 text-left text-xs flex items-center gap-1.5"
                        onClick={() => toggleCol(col)}
                        data-testid={`col-toggle-${col}`}
                      >
                        {isVisible ? (
                          <Eye className="h-3 w-3 text-primary" />
                        ) : (
                          <EyeOff className="h-3 w-3 text-muted-foreground" />
                        )}
                        <span className={isVisible ? '' : 'text-muted-foreground line-through'}>{col}</span>
                      </button>
                      <div className="flex opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          className="p-0.5 hover:bg-muted rounded"
                          onClick={() => moveCol(col, 'left')}
                          disabled={idx === 0}
                          title="Mover izquierda"
                        >
                          <MoveLeft className="h-3 w-3" />
                        </button>
                        <button
                          className="p-0.5 hover:bg-muted rounded"
                          onClick={() => moveCol(col, 'right')}
                          disabled={idx === (colOrder || allCols).length - 1}
                          title="Mover derecha"
                        >
                          <MoveRight className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* ── Resumen ──────────────────────────────────────────── */}
      {data && !loading && (
        <div className="flex gap-3 text-xs">
          <Badge variant="outline">{data.filas.length} items</Badge>
          <Badge variant="outline">{data.total_general.registros} registros</Badge>
          <Badge variant="outline">{data.total_general.prendas.toLocaleString()} prendas</Badge>
        </div>
      )}

      {/* ── Matriz ───────────────────────────────────────────── */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
              Cargando matriz...
            </div>
          ) : !data || data.filas.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
              Sin datos para los filtros seleccionados
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse" data-testid="matriz-table">
                {/* Header */}
                <thead>
                  <tr className="bg-muted/60">
                    <th className="text-left p-2.5 font-semibold sticky left-0 bg-muted/60 z-10 min-w-[280px] border-r">
                      Item
                    </th>
                    <th className="text-left p-2.5 font-semibold sticky left-[280px] bg-muted/60 z-10 min-w-[90px] border-r">
                      Hilo
                    </th>
                    {effectiveCols.map(col => (
                      <th key={col} className="text-center p-2.5 font-medium min-w-[70px] border-r whitespace-nowrap">
                        {col}
                      </th>
                    ))}
                    <th className="text-center p-2.5 font-semibold min-w-[80px] bg-muted/40">
                      Total
                    </th>
                  </tr>
                </thead>

                {/* Body */}
                <tbody>
                  {data.filas.map((fila, idx) => {
                    const key = `${fila.marca}-${fila.tipo}-${fila.entalle}-${fila.tela}-${fila.hilo}`;
                    const isExpanded = expanded[key];

                    return (
                      <Fragment key={key}>
                        <tr
                          className={`border-b hover:bg-muted/20 transition-colors ${isExpanded ? 'bg-muted/10' : ''}`}
                          data-testid={`fila-${idx}`}
                        >
                          {/* Item (sticky) */}
                          <td className="p-2.5 sticky left-0 bg-background z-10 border-r">
                            <button
                              className="flex items-center gap-1.5 text-left w-full group"
                              onClick={() => toggleExpand(key)}
                              data-testid={`expand-${idx}`}
                            >
                              {isExpanded ? (
                                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                              ) : (
                                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                              )}
                              <span className="font-medium truncate">{fila.item}</span>
                            </button>
                          </td>
                          {/* Hilo (sticky) */}
                          <td className="p-2.5 sticky left-[280px] bg-background z-10 border-r text-muted-foreground">
                            {fila.hilo}
                          </td>
                          {/* Celdas */}
                          {effectiveCols.map(col => {
                            const val = cellVal(fila.celdas, col);
                            return (
                              <td key={col} className={`text-center p-2.5 font-mono border-r ${val > 0 ? 'font-medium' : 'text-muted-foreground/40'}`}>
                                {val > 0 ? val.toLocaleString() : '-'}
                              </td>
                            );
                          })}
                          {/* Total */}
                          <td className="text-center p-2.5 font-mono font-bold bg-muted/20">
                            {totalVal(fila.total).toLocaleString()}
                          </td>
                        </tr>

                        {/* Detalle expandido */}
                        {isExpanded && (
                          <tr className="bg-muted/5">
                            <td colSpan={effectiveCols.length + 3} className="p-0">
                              <div className="px-4 py-2 border-b">
                                <table className="w-full text-xs">
                                  <thead>
                                    <tr className="text-muted-foreground">
                                      <th className="text-left p-1.5 font-medium">Corte</th>
                                      <th className="text-left p-1.5 font-medium">Estado</th>
                                      <th className="text-right p-1.5 font-medium">Prendas</th>
                                      <th className="text-left p-1.5 font-medium">Modelo</th>
                                      <th className="text-left p-1.5 font-medium">Ruta</th>
                                      <th className="text-left p-1.5 font-medium">Entrega</th>
                                      <th className="text-center p-1.5 font-medium">Info</th>
                                      <th className="text-center p-1.5 font-medium">Acción</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {fila.detalle.map(d => (
                                      <tr key={d.id} className="border-t border-dashed hover:bg-muted/30" data-testid={`detalle-${d.n_corte}`}>
                                        <td className="p-1.5 font-mono font-semibold">{d.n_corte}</td>
                                        <td className="p-1.5"><Badge variant="outline" className="text-[10px] px-1">{d.estado}</Badge></td>
                                        <td className="p-1.5 text-right font-mono">{d.prendas.toLocaleString()}</td>
                                        <td className="p-1.5 text-muted-foreground">{d.modelo}</td>
                                        <td className="p-1.5 text-muted-foreground">{d.ruta || '-'}</td>
                                        <td className="p-1.5">
                                          {d.fecha_entrega ? (
                                            <span className={new Date(d.fecha_entrega) < new Date() ? 'text-destructive' : ''}>
                                              {d.fecha_entrega}
                                            </span>
                                          ) : '-'}
                                        </td>
                                        <td className="p-1.5 text-center">
                                          {d.urgente && <Badge variant="destructive" className="text-[9px] px-1">URG</Badge>}
                                          {d.es_hijo && <Badge variant="outline" className="text-[9px] px-1 ml-0.5">DIV</Badge>}
                                        </td>
                                        <td className="p-1.5 text-center">
                                          <div className="flex justify-center gap-0.5">
                                            <Button variant="ghost" size="sm" className="h-6 text-[10px] px-1.5" onClick={() => navigate(`/reportes/trazabilidad/${d.id}`)}>
                                              Traza
                                            </Button>
                                            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => navigate(`/registros/editar/${d.id}`)}>
                                              <ExternalLink className="h-3 w-3" />
                                            </Button>
                                          </div>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>

                {/* Footer totals */}
                <tfoot>
                  <tr className="bg-muted/40 font-semibold border-t-2">
                    <td className="p-2.5 sticky left-0 bg-muted/40 z-10 border-r" colSpan={2}>
                      TOTALES
                    </td>
                    {effectiveCols.map(col => {
                      const t = data.totales_columna[col];
                      const val = t ? (metrica === 'prendas' ? t.prendas : t.registros) : 0;
                      return (
                        <td key={col} className={`text-center p-2.5 font-mono border-r ${val > 0 ? '' : 'text-muted-foreground/40'}`}>
                          {val > 0 ? val.toLocaleString() : '-'}
                        </td>
                      );
                    })}
                    <td className="text-center p-2.5 font-mono font-bold bg-muted/30">
                      {totalVal(data.total_general).toLocaleString()}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

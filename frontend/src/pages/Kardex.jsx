import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Label } from '../components/ui/label';
import { Separator } from '../components/ui/separator';
import { 
  BookOpen, 
  Package,
  ArrowDownCircle,
  ArrowUpCircle,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const Kardex = () => {
  const [items, setItems] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState('');
  const [kardexData, setKardexData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingItems, setLoadingItems] = useState(true);

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API}/inventario`);
      setItems(response.data);
    } catch (error) {
      toast.error('Error al cargar items');
    } finally {
      setLoadingItems(false);
    }
  };

  const fetchKardex = async (itemId) => {
    if (!itemId) {
      setKardexData(null);
      return;
    }
    
    setLoading(true);
    try {
      const response = await axios.get(`${API}/inventario-kardex/${itemId}`);
      setKardexData(response.data);
    } catch (error) {
      toast.error('Error al cargar kardex');
      setKardexData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  useEffect(() => {
    if (selectedItemId) {
      fetchKardex(selectedItemId);
    }
  }, [selectedItemId]);

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN',
    }).format(value);
  };

  const getTipoIcon = (tipo) => {
    if (tipo.includes('Ingreso')) {
      return <ArrowDownCircle className="h-4 w-4 text-green-600" />;
    } else if (tipo.includes('Salida')) {
      return <ArrowUpCircle className="h-4 w-4 text-red-500" />;
    } else if (tipo.includes('Ajuste')) {
      return <RefreshCw className="h-4 w-4 text-blue-500" />;
    }
    return null;
  };

  const getTipoBadge = (tipo) => {
    if (tipo.includes('Ingreso')) {
      return <Badge className="bg-green-600">{tipo}</Badge>;
    } else if (tipo === 'Salida') {
      return <Badge variant="destructive">{tipo}</Badge>;
    } else if (tipo.includes('entrada')) {
      return <Badge className="bg-blue-500">{tipo}</Badge>;
    } else if (tipo.includes('salida')) {
      return <Badge className="bg-orange-500">{tipo}</Badge>;
    }
    return <Badge>{tipo}</Badge>;
  };

  // Calcular totales - el backend devuelve cantidad (positiva/negativa) y tipo
  const totales = kardexData?.movimientos?.reduce((acc, m) => {
    if (m.tipo === 'ingreso') {
      acc.entradas += Math.abs(m.cantidad || 0);
      acc.costoEntradas += m.costo_total || 0;
    } else if (m.tipo === 'salida' || m.tipo === 'ajuste_salida') {
      acc.salidas += Math.abs(m.cantidad || 0);
      acc.costoSalidas += m.costo_total || 0;
    } else if (m.tipo === 'ajuste_entrada') {
      acc.entradas += Math.abs(m.cantidad || 0);
    }
    return acc;
  }, { entradas: 0, salidas: 0, costoEntradas: 0, costoSalidas: 0 }) || { entradas: 0, salidas: 0, costoEntradas: 0, costoSalidas: 0 };

  return (
    <div className="space-y-6" data-testid="kardex-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <BookOpen className="h-6 w-6" />
            Kardex de Inventario
          </h2>
          <p className="text-muted-foreground">Historial detallado de movimientos por item</p>
        </div>
      </div>

      {/* Selector de Item */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Seleccionar Item</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-w-md">
            <Label className="mb-2 block">Item de Inventario</Label>
            <Select 
              value={selectedItemId} 
              onValueChange={setSelectedItemId}
              disabled={loadingItems}
            >
              <SelectTrigger data-testid="select-item-kardex">
                <SelectValue placeholder={loadingItems ? "Cargando..." : "Seleccionar item..."} />
              </SelectTrigger>
              <SelectContent>
                {items.map((item) => (
                  <SelectItem key={item.id} value={item.id}>
                    <span className="font-mono mr-2">{item.codigo}</span>
                    {item.nombre}
                    <span className="ml-2 text-muted-foreground">(Stock: {item.stock_actual})</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Contenido del Kardex */}
      {loading ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            Cargando kardex...
          </CardContent>
        </Card>
      ) : kardexData ? (
        <>
          {/* Info del Item */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-primary/10 rounded-lg">
                  <Package className="h-8 w-8 text-primary" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm text-muted-foreground">{kardexData.item.codigo}</span>
                    <Badge variant="outline">{kardexData.item.unidad_medida}</Badge>
                  </div>
                  <h3 className="text-xl font-semibold">{kardexData.item.nombre}</h3>
                </div>
                <div className="text-right">
                  <p className="text-sm text-muted-foreground">Stock Actual</p>
                  <p className="text-3xl font-bold text-primary">{kardexData.item.stock_actual}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Resumen */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <TrendingUp className="h-6 w-6 text-green-600" />
                  <div>
                    <p className="text-sm text-muted-foreground">Total Entradas</p>
                    <p className="text-xl font-bold text-green-600">+{totales.entradas}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <TrendingDown className="h-6 w-6 text-red-500" />
                  <div>
                    <p className="text-sm text-muted-foreground">Total Salidas</p>
                    <p className="text-xl font-bold text-red-500">-{totales.salidas}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <ArrowDownCircle className="h-6 w-6 text-green-600" />
                  <div>
                    <p className="text-sm text-muted-foreground">Costo Entradas</p>
                    <p className="text-lg font-bold">{formatCurrency(totales.costoEntradas)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <ArrowUpCircle className="h-6 w-6 text-red-500" />
                  <div>
                    <p className="text-sm text-muted-foreground">Costo Salidas</p>
                    <p className="text-lg font-bold">{formatCurrency(totales.costoSalidas)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Tabla Kardex */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Movimientos</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="data-table-header">
                      <TableHead>Fecha</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Documento</TableHead>
                      <TableHead className="text-right">Entrada</TableHead>
                      <TableHead className="text-right">Salida</TableHead>
                      <TableHead className="text-right">Saldo</TableHead>
                      <TableHead className="text-right">Costo Unit.</TableHead>
                      <TableHead className="text-right">Costo Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {kardexData.movimientos.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                          No hay movimientos registrados
                        </TableCell>
                      </TableRow>
                    ) : (
                      kardexData.movimientos.map((mov, index) => (
                        <TableRow key={mov.id || index} className="data-table-row" data-testid={`kardex-row-${index}`}>
                          <TableCell className="font-mono text-sm">
                            {formatDate(mov.fecha)}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              {getTipoIcon(mov.tipo)}
                              {getTipoBadge(mov.tipo)}
                            </div>
                          </TableCell>
                          <TableCell>
                            {mov.documento || (
                              <span className="text-muted-foreground text-sm truncate max-w-[150px] block">
                                {mov.observaciones || '-'}
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {mov.entrada > 0 ? (
                              <span className="text-green-600 font-semibold">+{mov.entrada}</span>
                            ) : (
                              <Minus className="h-4 w-4 text-muted-foreground mx-auto" />
                            )}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {mov.salida > 0 ? (
                              <span className="text-red-500 font-semibold">-{mov.salida}</span>
                            ) : (
                              <Minus className="h-4 w-4 text-muted-foreground mx-auto" />
                            )}
                          </TableCell>
                          <TableCell className="text-right font-mono font-bold bg-muted/30">
                            {mov.saldo}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {mov.costo_unitario > 0 ? formatCurrency(mov.costo_unitario) : '-'}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {mov.costo_total > 0 ? formatCurrency(mov.costo_total) : '-'}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      ) : selectedItemId ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            Error al cargar el kardex
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <BookOpen className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">Selecciona un item para ver su kardex</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

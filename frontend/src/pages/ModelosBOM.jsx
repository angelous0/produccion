import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { SortableRow, SortableTableWrapper, useSortableTable } from '../components/SortableTable';
import { Label } from '../components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Switch } from '../components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

import { InventarioCombobox } from '../components/InventarioCombobox';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ModelosTallasTab = ({ modeloId }) => {
  const [catalogoTallas, setCatalogoTallas] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const [newTallaId, setNewTallaId] = useState('');

  const { sensors, handleDragEnd, isSaving, modifiers } = useSortableTable(
    rows,
    setRows,
    `modelos/${modeloId}/tallas/reorder`
  );


  const fetchAll = async () => {
    setLoading(true);
    try {
      const [catRes, relRes] = await Promise.all([
        axios.get(`${API}/tallas-catalogo`),
        axios.get(`${API}/modelos/${modeloId}/tallas?activo=all`),
      ]);
      setCatalogoTallas(catRes.data || []);
      setRows(relRes.data || []);
    } catch (e) {
      toast.error('Error al cargar tallas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (modeloId) fetchAll();
  }, [modeloId]);

  const availableTallas = useMemo(() => {
    const used = new Set(rows.filter((r) => r.activo).map((r) => r.talla_id));
    return (catalogoTallas || []).filter((t) => !used.has(t.id));
  }, [catalogoTallas, rows]);

  const addTalla = async (e) => {
    e?.preventDefault?.();

    if (!newTallaId) {
      toast.error('Selecciona una talla');
      return;
    }
    try {
      await axios.post(`${API}/modelos/${modeloId}/tallas`, {
        talla_id: newTallaId,
        orden: 10,
        activo: true,
      });
      toast.success('Talla agregada');
      setNewTallaId('');
      fetchAll();
    } catch (e2) {
      toast.error(e2?.response?.data?.detail || 'Error al agregar talla');
    }
  };

  const saveRow = async (r, e) => {
    e?.preventDefault?.();

    try {
      await axios.put(`${API}/modelos/${modeloId}/tallas/${r.id}`, {
        activo: Boolean(r.activo),
      });
      toast.success('Guardado');
      fetchAll();
    } catch (e2) {
      toast.error(e2?.response?.data?.detail || 'Error al guardar');
    }
  };

  const deactivate = async (r, e) => {
    e?.preventDefault?.();

    try {
      await axios.delete(`${API}/modelos/${modeloId}/tallas/${r.id}`);
      toast.success('Desactivado');
      fetchAll();
    } catch (e2) {
      toast.error(e2?.response?.data?.detail || 'Error al desactivar');
    }
  };

  const hardDelete = async (r, e) => {
    e?.preventDefault?.();

    try {
      await axios.delete(`${API}/modelos/${modeloId}/tallas/${r.id}/hard`);
      toast.success('Eliminado');
      fetchAll();
    } catch (e2) {
      toast.error(e2?.response?.data?.detail || 'No se pudo borrar');
    }
  };

  return (
    <div className="space-y-4" data-testid="tab-modelo-tallas">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Tallas del modelo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
            <div className="space-y-2">
              <Label>Talla</Label>
              <Select value={newTallaId || 'none'} onValueChange={(v) => setNewTallaId(v === 'none' ? '' : v)}>
                <SelectTrigger data-testid="select-new-talla">
                  <SelectValue placeholder="Seleccionar" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Seleccionar</SelectItem>
                  {availableTallas.map((t) => (
                    <SelectItem key={t.id} value={t.id}>{t.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button type="button" onClick={addTalla} data-testid="btn-add-talla">Agregar</Button>
          </div>

          <div className="overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]"></TableHead>
                  <TableHead>Talla</TableHead>
                  <TableHead className="w-[120px]">Activo</TableHead>
                  <TableHead className="w-[260px]">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={4} className="text-center py-8">Cargando...</TableCell></TableRow>
                ) : rows.length === 0 ? (
                  <TableRow><TableCell colSpan={4} className="text-center py-8 text-muted-foreground">Sin tallas</TableCell></TableRow>
                ) : (
                      <TableRow key={r.id}>
                        <TableCell className="font-medium">{r.talla_nombre || r.talla_id}</TableCell>
                        <TableCell>
                          <Switch
                            checked={Boolean(r.activo)}
                            onCheckedChange={(checked) => setRows((prev) => prev.map((x) => x.id === r.id ? { ...x, activo: checked } : x))}
                            data-testid={`talla-activo-${r.id}`}
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button type="button" size="sm" variant="outline" onClick={() => saveRow(r)}>Guardar</Button>
                            <Button type="button" size="sm" variant="destructive" onClick={() => deactivate(r)}>Desactivar</Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => hardDelete(r)}
                            >
                              Borrar
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};


export const ModelosBOMTab = ({ modeloId }) => {
  const [inventario, setInventario] = useState([]);
  const [tallas, setTallas] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [verInactivos, setVerInactivos] = useState(false);

  const emptyRow = {
    id: null,
    inventario_id: '',
    talla_id: null,
    cantidad_base: '',
    merma_pct: 0,
    orden: 10,
    activo: true,
    notas: '',
  };

  const [drafts, setDrafts] = useState([emptyRow]);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [invRes, tallasRes, bomRes] = await Promise.all([
        axios.get(`${API}/inventario`),
        axios.get(`${API}/modelos/${modeloId}/tallas?activo=true`),
        axios.get(`${API}/modelos/${modeloId}/bom?activo=${verInactivos ? 'all' : 'true'}`),
      ]);
      setInventario(invRes.data || []);
      setTallas(tallasRes.data || []);
      setRows(bomRes.data || []);
    } catch (e) {
      toast.error('Error al cargar BOM');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (modeloId) fetchAll();
  }, [modeloId, verInactivos]);

  const resumen = useMemo(() => {
    const act = (rows || []).filter((r) => r.activo);
    const itemsUnicos = new Set(act.map((r) => r.inventario_id)).size;
    const porTalla = act.filter((r) => r.talla_id).length;
    const generales = act.filter((r) => !r.talla_id).length;
    return {
      lineasActivas: act.length,
      itemsUnicos,
      porTalla,
      generales,
    };
  }, [rows]);

  const validate = (r) => {
    const cantidad = Number(r.cantidad_base);
    const merma = Number(r.merma_pct);
    if (!r.inventario_id) return 'Selecciona un item de inventario';
    if (!(cantidad > 0)) return 'Cantidad base debe ser > 0';
    if (merma < 0 || merma > 100) return 'Merma % debe estar entre 0 y 100';
    if (r.talla_id) {
      const ok = tallas.some((t) => t.talla_id === r.talla_id);
      if (!ok) return 'La talla debe pertenecer al modelo';
    }
    return null;
  };

  const addDraftRow = () => {
    setDrafts((prev) => [...prev, { ...emptyRow, orden: 10 }]);
  };

  const saveDraft = async (idx) => {
    const r = drafts[idx];
    const err = validate(r);
    if (err) {
      toast.error(err);
      return;
    }

    try {
      await axios.post(`${API}/modelos/${modeloId}/bom`, {
        inventario_id: r.inventario_id,
        talla_id: r.talla_id || null,
        cantidad_base: Number(r.cantidad_base),
        merma_pct: Number(r.merma_pct) || 0,
        orden: Number(r.orden) || 10,
        activo: Boolean(r.activo),
        notas: r.notas || null,
      });
      toast.success('Línea creada');
      setDrafts((prev) => prev.filter((_, i) => i !== idx));
      fetchAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Error al crear línea');
    }
  };

  const saveExisting = async (r) => {
    const err = validate(r);
    if (err) {
      toast.error(err);
      return;
    }

    try {
      await axios.put(`${API}/modelos/${modeloId}/bom/${r.id}`, {
        inventario_id: r.inventario_id,
        talla_id: r.talla_id || null,
        cantidad_base: Number(r.cantidad_base),
        merma_pct: Number(r.merma_pct) || 0,
        orden: Number(r.orden) || 10,
        activo: Boolean(r.activo),
        notas: r.notas || null,
      });
      toast.success('Guardado');
      fetchAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Error al guardar');
    }
  };

  const deactivate = async (r) => {
    try {
      await axios.delete(`${API}/modelos/${modeloId}/bom/${r.id}`);
      toast.success('Desactivado');
      fetchAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Error al desactivar');
    }
  };

  return (
    <div className="space-y-4" data-testid="tab-modelo-bom">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <CardTitle className="text-base">BOM / Receta (por prenda)</CardTitle>
            <div className="flex items-center gap-2">
              <Label className="text-sm">Ver inactivos</Label>
              <Switch checked={verInactivos} onCheckedChange={setVerInactivos} data-testid="toggle-ver-inactivos-bom" />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="text-sm text-muted-foreground">Líneas activas: <span className="font-medium text-foreground">{resumen.lineasActivas}</span></div>
            <div className="text-sm text-muted-foreground">Items únicos: <span className="font-medium text-foreground">{resumen.itemsUnicos}</span></div>
            <div className="text-sm text-muted-foreground">Líneas por talla: <span className="font-medium text-foreground">{resumen.porTalla}</span></div>
            <div className="text-sm text-muted-foreground">Líneas generales: <span className="font-medium text-foreground">{resumen.generales}</span></div>
          </div>

          <div className="overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[320px]">Item</TableHead>
                  <TableHead className="min-w-[160px]">Talla</TableHead>
                  <TableHead className="w-[140px] text-right">Cant. por prenda</TableHead>
                  <TableHead className="w-[110px] text-right">Merma %</TableHead>
                  <TableHead className="w-[110px] text-right">Orden</TableHead>
                  <TableHead className="w-[90px]">Activo</TableHead>
                  <TableHead className="min-w-[220px]">Notas</TableHead>
                  <TableHead className="w-[220px]">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={8} className="text-center py-8">Cargando...</TableCell></TableRow>
                ) : (
                  <>
                    {rows.map((r) => (
                      <TableRow key={r.id} className={!r.activo ? 'opacity-60' : ''}>
                        <TableCell>
                          <InventarioCombobox
                            options={inventario}
                            value={r.inventario_id}
                            onChange={(id) => setRows((prev) => prev.map((x) => x.id === r.id ? { ...x, inventario_id: id } : x))}
                          />
                        </TableCell>
                        <TableCell>
                          <Select
                            value={r.talla_id || 'all'}
                            onValueChange={(v) => setRows((prev) => prev.map((x) => x.id === r.id ? { ...x, talla_id: v === 'all' ? null : v } : x))}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Todas" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="all">Todas</SelectItem>
                              {tallas.map((t) => (
                                <SelectItem key={t.talla_id} value={t.talla_id}>{t.talla_nombre}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min="0"
                            step="0.0001"
                            className="text-right font-mono"
                            value={r.cantidad_base}
                            onChange={(e) => setRows((prev) => prev.map((x) => x.id === r.id ? { ...x, cantidad_base: e.target.value } : x))}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min="0"
                            max="100"
                            step="0.01"
                            className="text-right font-mono"
                            value={r.merma_pct ?? 0}
                            onChange={(e) => setRows((prev) => prev.map((x) => x.id === r.id ? { ...x, merma_pct: e.target.value } : x))}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            className="text-right font-mono"
                            value={r.orden ?? 10}
                            onChange={(e) => setRows((prev) => prev.map((x) => x.id === r.id ? { ...x, orden: e.target.value } : x))}
                          />
                        </TableCell>
                        <TableCell>
                          <Switch
                            checked={Boolean(r.activo)}
                            onCheckedChange={(checked) => setRows((prev) => prev.map((x) => x.id === r.id ? { ...x, activo: checked } : x))}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            value={r.notas || ''}
                            onChange={(e) => setRows((prev) => prev.map((x) => x.id === r.id ? { ...x, notas: e.target.value } : x))}
                            placeholder="Opcional"
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button size="sm" variant="outline" onClick={() => saveExisting(r)}>Guardar</Button>
                            <Button size="sm" variant="destructive" onClick={() => deactivate(r)}>Desactivar</Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}

                    {drafts.map((r, idx) => (
                      <TableRow key={`draft-${idx}`}>
                        <TableCell>
                          <InventarioCombobox
                            options={inventario}
                            value={r.inventario_id}
                            onChange={(id) => setDrafts((prev) => prev.map((x, i) => i === idx ? { ...x, inventario_id: id } : x))}
                          />
                        </TableCell>
                        <TableCell>
                          <Select
                            value={r.talla_id || 'all'}
                            onValueChange={(v) => setDrafts((prev) => prev.map((x, i) => i === idx ? { ...x, talla_id: v === 'all' ? null : v } : x))}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Todas" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="all">Todas</SelectItem>
                              {tallas.map((t) => (
                                <SelectItem key={t.talla_id} value={t.talla_id}>{t.talla_nombre}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min="0"
                            step="0.0001"
                            className="text-right font-mono"
                            value={r.cantidad_base}
                            onChange={(e) => setDrafts((prev) => prev.map((x, i) => i === idx ? { ...x, cantidad_base: e.target.value } : x))}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min="0"
                            max="100"
                            step="0.01"
                            className="text-right font-mono"
                            value={r.merma_pct ?? 0}
                            onChange={(e) => setDrafts((prev) => prev.map((x, i) => i === idx ? { ...x, merma_pct: e.target.value } : x))}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            className="text-right font-mono"
                            value={r.orden ?? 10}
                            onChange={(e) => setDrafts((prev) => prev.map((x, i) => i === idx ? { ...x, orden: e.target.value } : x))}
                          />
                        </TableCell>
                        <TableCell>
                          <Switch
                            checked={Boolean(r.activo)}
                            onCheckedChange={(checked) => setDrafts((prev) => prev.map((x, i) => i === idx ? { ...x, activo: checked } : x))}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            value={r.notas || ''}
                            onChange={(e) => setDrafts((prev) => prev.map((x, i) => i === idx ? { ...x, notas: e.target.value } : x))}
                            placeholder="Opcional"
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button size="sm" onClick={() => saveDraft(idx)} data-testid="btn-guardar-linea-draft">Guardar</Button>
                            <Button size="sm" variant="outline" onClick={() => setDrafts((prev) => prev.filter((_, i) => i !== idx))}>Quitar</Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </>
                )}
              </TableBody>
            </Table>
          </div>

          <Button onClick={addDraftRow} variant="secondary" data-testid="btn-add-bom-linea">Agregar línea</Button>
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Regla: si la línea tiene <span className="font-medium">Talla = Todas</span> (talla_id = NULL) aplica a todas las tallas.
        Si tiene una talla específica, aplica solo a esa talla.
      </p>
    </div>
  );
};

export default ModelosBOMTab;

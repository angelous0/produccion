import { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
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

import { SortableRow, SortableTableWrapper, useSortableTable } from '../components/SortableTable';
import { InventarioCombobox } from '../components/InventarioCombobox';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const DEBOUNCE_MS = 800; // recomendado (balance entre UX y carga)

const mkTempId = () => `draft_${Math.random().toString(36).slice(2, 10)}`;

export const ModelosTallasTab = ({ modeloId }) => {
  const [catalogoTallas, setCatalogoTallas] = useState([]);
  const [rows, setRows] = useState([]); // incluye activas e inactivas
  const [loading, setLoading] = useState(true);

  const [newTallaId, setNewTallaId] = useState('');
  const [verInactivas, setVerInactivas] = useState(false);

  // Autosave por fila (solo activo por ahora)
  const timersRef = useRef({});
  const [rowState, setRowState] = useState({}); // { [id]: 'idle'|'saving'|'saved'|'error' }

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
    } catch {
      toast.error('Error al cargar tallas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (modeloId) fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modeloId]);

  const availableTallas = useMemo(() => {
    const used = new Set(rows.filter((r) => r.activo).map((r) => r.talla_id));
    return (catalogoTallas || []).filter((t) => !used.has(t.id));
  }, [catalogoTallas, rows]);

  const visibleRows = useMemo(() => {
    const list = verInactivas ? rows : rows.filter((r) => r.activo);
    // mantener orden ya calculado (drag&drop)
    return list;
  }, [rows, verInactivas]);

  const addTalla = async (e) => {
    e?.preventDefault?.();

    if (!newTallaId) {
      toast.error('Selecciona una talla');
      return;
    }
    try {
      const res = await axios.post(`${API}/modelos/${modeloId}/tallas`, {
        talla_id: newTallaId,
        orden: rows.length + 1,
        activo: true,
      });
      const created = res.data;
      setRows((prev) => [...prev, created]);
      setNewTallaId('');
      toast.success('Talla agregada');
    } catch (e2) {
      toast.error(e2?.response?.data?.detail || 'Error al agregar talla');
    }
  };

  const scheduleAutosave = (relId, payload) => {
    if (!relId) return;

    if (timersRef.current[relId]) clearTimeout(timersRef.current[relId]);
    setRowState((prev) => ({ ...prev, [relId]: 'saving' }));

    timersRef.current[relId] = setTimeout(async () => {
      try {
        await axios.put(`${API}/modelos/${modeloId}/tallas/${relId}`, payload);
        setRowState((prev) => ({ ...prev, [relId]: 'saved' }));
        setTimeout(() => {
          setRowState((prev) => ({ ...prev, [relId]: 'idle' }));
        }, 900);
      } catch (e2) {
        setRowState((prev) => ({ ...prev, [relId]: 'error' }));
        toast.error(e2?.response?.data?.detail || 'Error al guardar');
      }
    }, DEBOUNCE_MS);
  };

  const hardDelete = async (r, e) => {
    e?.preventDefault?.();
    try {
      await axios.delete(`${API}/modelos/${modeloId}/tallas/${r.id}/hard`);
      setRows((prev) => prev.filter((x) => x.id !== r.id));
      toast.success('Eliminado');
    } catch (e2) {
      toast.error(e2?.response?.data?.detail || 'No se pudo borrar');
    }
  };

  const rowStatusLabel = (id) => {
    const s = rowState[id];
    if (s === 'saving') return 'Guardando…';
    if (s === 'saved') return 'Guardado';
    if (s === 'error') return 'Error';
    return '';
  };

  return (
    <div className="space-y-4" data-testid="tab-modelo-tallas">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <CardTitle className="text-base">Tallas del modelo</CardTitle>
            <div className="flex items-center gap-2">
              <Label className="text-sm">Ver inactivas</Label>
              <Switch checked={verInactivas} onCheckedChange={setVerInactivas} data-testid="toggle-ver-inactivas-tallas" />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
            <div className="space-y-2">
              <Label>Talla</Label>
              <Select
                value={newTallaId || 'none'}
                onValueChange={(v) => setNewTallaId(v === 'none' ? '' : v)}
              >
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
            {isSaving && (
              <div className="text-xs text-muted-foreground pb-2">Guardando orden...</div>
            )}

            <SortableTableWrapper items={visibleRows} sensors={sensors} handleDragEnd={handleDragEnd} modifiers={modifiers}>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[40px]"></TableHead>
                    <TableHead>Talla</TableHead>
                    <TableHead className="w-[120px]">Activo</TableHead>
                    <TableHead className="w-[140px]">Estado</TableHead>
                    <TableHead className="w-[120px]">Borrar</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8">Cargando...</TableCell>
                    </TableRow>
                  ) : visibleRows.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">Sin tallas</TableCell>
                    </TableRow>
                  ) : (
                    visibleRows.map((r) => (
                      <SortableRow key={r.id} id={r.id}>
                        <TableCell className="font-medium">{r.talla_nombre || r.talla_id}</TableCell>
                        <TableCell>
                          <Switch
                            checked={Boolean(r.activo)}
                            onCheckedChange={(checked) => {
                              setRows((prev) => prev.map((x) => x.id === r.id ? { ...x, activo: checked } : x));
                              scheduleAutosave(r.id, { activo: Boolean(checked) });
                            }}
                            data-testid={`talla-activo-${r.id}`}
                          />
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {rowStatusLabel(r.id)}
                        </TableCell>
                        <TableCell>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={(e) => hardDelete(r, e)}
                            data-testid={`talla-borrar-${r.id}`}
                          >
                            Borrar
                          </Button>
                        </TableCell>
                      </SortableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </SortableTableWrapper>
          </div>

          <p className="text-xs text-muted-foreground">
            Arrastra las filas para reordenar. Los cambios se guardan automáticamente.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};


export const ModelosBOMTab = ({ modeloId }) => {
  const [inventario, setInventario] = useState([]);
  const [tallas, setTallas] = useState([]); // solo activas del modelo
  const [rows, setRows] = useState([]); // incluye activas/inactivas
  const [loading, setLoading] = useState(true);

  const [verInactivos, setVerInactivos] = useState(false);

  const timersRef = useRef({});
  const [rowState, setRowState] = useState({}); // { [key]: 'idle'|'saving'|'saved'|'error'|'draft' }

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [invRes, tallasRes, bomRes] = await Promise.all([
        axios.get(`${API}/inventario`),
        axios.get(`${API}/modelos/${modeloId}/tallas?activo=true`),
        axios.get(`${API}/modelos/${modeloId}/bom?activo=all`),
      ]);
      setInventario(invRes.data || []);
      setTallas(tallasRes.data || []);
      setRows(bomRes.data || []);
    } catch {
      toast.error('Error al cargar BOM');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (modeloId) fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modeloId]);

  const visibleRows = useMemo(() => {
    const list = verInactivos ? rows : rows.filter((r) => r.activo);
    // ordenar estable
    return [...list].sort((a, b) => {
      const ao = a.orden ?? 10;
      const bo = b.orden ?? 10;
      if (ao !== bo) return ao - bo;
      return String(a.created_at || '').localeCompare(String(b.created_at || ''));
    });
  }, [rows, verInactivos]);

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

    if (!r.inventario_id) return 'Selecciona un item de inventario';
    if (!(cantidad > 0)) return 'Cantidad por prenda debe ser > 0';

    if (r.talla_id) {
      const ok = tallas.some((t) => t.talla_id === r.talla_id);
      if (!ok) return 'La talla debe pertenecer al modelo';
    }
    return null;
  };

  const keyOf = (r) => r.id || r.__tempId;

  const setStatus = (key, status) => {
    setRowState((prev) => ({ ...prev, [key]: status }));
  };

  const rowStatusLabel = (key) => {
    const s = rowState[key];
    if (s === 'saving') return 'Guardando…';
    if (s === 'saved') return 'Guardado';
    if (s === 'error') return 'Error';
    if (s === 'draft') return 'DRAFT';
    return '';
  };

  const scheduleSave = (row) => {
    const key = keyOf(row);
    if (!key) return;

    const err = validate(row);
    if (err) {
      setStatus(key, 'draft');
      return;
    }

    if (timersRef.current[key]) clearTimeout(timersRef.current[key]);
    setStatus(key, 'saving');

    timersRef.current[key] = setTimeout(async () => {
      try {
        if (!row.id) {
          // Create (POST) desde draft
          const res = await axios.post(`${API}/modelos/${modeloId}/bom`, {
            inventario_id: row.inventario_id,
            talla_id: row.talla_id || null,
            cantidad_base: Number(row.cantidad_base),
            activo: Boolean(row.activo),
          });
          const created = res.data;

          setRows((prev) => prev.map((x) => (x.__tempId && x.__tempId === row.__tempId ? created : x)));
          setRowState((prev) => {
            const next = { ...prev };
            delete next[key];
            next[created.id] = 'saved';
            return next;
          });
          setTimeout(() => setStatus(created.id, 'idle'), 900);
          return;
        }

        // Update (PUT parcial)
        await axios.put(`${API}/modelos/${modeloId}/bom/${row.id}`, {
          inventario_id: row.inventario_id,
          talla_id: row.talla_id || null,
          cantidad_base: Number(row.cantidad_base),
          activo: Boolean(row.activo),
        });

        setStatus(key, 'saved');
        setTimeout(() => setStatus(key, 'idle'), 900);
      } catch (e2) {
        setStatus(key, 'error');
        toast.error(e2?.response?.data?.detail || 'Error al guardar');
      }
    }, DEBOUNCE_MS);
  };

  const addDraftRow = () => {
    const r = {
      __tempId: mkTempId(),
      inventario_id: '',
      talla_id: null,
      cantidad_base: '',
      activo: true,
    };
    setRows((prev) => [r, ...prev]);
    setStatus(r.__tempId, 'draft');
  };

  const updateRow = (rowKey, patch) => {
    setRows((prev) => {
      const next = prev.map((r) => {
        const k = keyOf(r);
        if (k !== rowKey) return r;
        const merged = { ...r, ...patch };
        // schedule save with merged snapshot
        setTimeout(() => scheduleSave(merged), 0);
        return merged;
      });
      return next;
    });
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
                  <TableHead className="min-w-[340px]">Item</TableHead>
                  <TableHead className="min-w-[160px]">Talla</TableHead>
                  <TableHead className="w-[160px] text-right">Cant. por prenda</TableHead>
                  <TableHead className="w-[110px] text-right">Merma %</TableHead>
                  <TableHead className="w-[110px] text-right">Orden</TableHead>
                  <TableHead className="w-[90px]">Activo</TableHead>
                  <TableHead className="min-w-[220px]">Notas</TableHead>
                  <TableHead className="w-[120px]">Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8">Cargando...</TableCell>
                  </TableRow>
                ) : visibleRows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">Sin líneas</TableCell>
                  </TableRow>
                ) : (
                  visibleRows.map((r) => {
                    const k = keyOf(r);
                    const isDraft = !r.id;
                    return (
                      <TableRow key={k} className={!r.activo ? 'opacity-60' : ''} data-testid="bom-row">
                        <TableCell>
                          <InventarioCombobox
                            options={inventario}
                            value={r.inventario_id}
                            onChange={(id) => updateRow(k, { inventario_id: id })}
                          />
                        </TableCell>
                        <TableCell>
                          <Select
                            value={r.talla_id || 'all'}
                            onValueChange={(v) => updateRow(k, { talla_id: v === 'all' ? null : v })}
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
                            onChange={(e) => updateRow(k, { cantidad_base: e.target.value })}
                            data-testid={isDraft ? 'input-draft-cantidad' : undefined}
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
                            onChange={(e) => updateRow(k, { merma_pct: e.target.value })}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            className="text-right font-mono"
                            value={r.orden ?? 10}
                            onChange={(e) => updateRow(k, { orden: e.target.value })}
                          />
                        </TableCell>
                        <TableCell>
                          <Switch
                            checked={Boolean(r.activo)}
                            onCheckedChange={(checked) => updateRow(k, { activo: checked })}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            value={r.notas || ''}
                            onChange={(e) => updateRow(k, { notas: e.target.value })}
                            placeholder="Opcional"
                          />
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {rowStatusLabel(k)}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>

          <Button onClick={addDraftRow} variant="secondary" data-testid="btn-add-bom-linea">Agregar línea</Button>

          <p className="text-xs text-muted-foreground">
            Regla: si la línea tiene <span className="font-medium">Talla = Todas</span> (talla_id = NULL) aplica a todas las tallas.
            Si tiene una talla específica, aplica solo a esa talla.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ModelosBOMTab;

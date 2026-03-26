import { useEffect, useState } from 'react';
import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useSaving } from '../hooks/useSaving';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Separator } from '../components/ui/separator';
import { ArrowLeft, Save, AlertTriangle, Trash2, Tag, Layers, Shirt, Palette, Scissors, Package, Plus, ArrowUpCircle, Cog, Users, Calendar, Play, Pencil, FileText, ChevronDown, ChevronUp, Divide, ArrowRight, Check, ChevronsUpDown, Search } from 'lucide-react';
import { toast } from 'sonner';
import { NumericInput } from '../components/ui/numeric-input';
import { SalidaRollosDialog } from '../components/SalidaRollosDialog';
import { MultiSelectColors } from '../components/MultiSelectColors';
import { Textarea } from '../components/ui/textarea';
import { TrazabilidadPanel } from '../components/TrazabilidadPanel';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '../components/ui/command';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const RegistroForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEditing = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const { saving, guard } = useSaving();
  
  const [formData, setFormData] = useState({
    n_corte: '',
    modelo_id: '',
    curva: '',
    estado: 'Para Corte',
    urgente: false,
    hilo_especifico_id: '',
    pt_item_id: '',
    id_odoo: '',
    observaciones: '',
  });

  // Datos del modelo seleccionado
  const [modeloSeleccionado, setModeloSeleccionado] = useState(null);

  // Tallas seleccionadas
  const [tallasSeleccionadas, setTallasSeleccionadas] = useState([]);

  // Datos para distribución de colores
  const [coloresDialogOpen, setColoresDialogOpen] = useState(false);
  const [coloresSeleccionados, setColoresSeleccionados] = useState([]);
  const [matrizCantidades, setMatrizCantidades] = useState({});
  const [distribucionColores, setDistribucionColores] = useState([]);

  // Datos del catálogo
  const [tallasCatalogo, setTallasCatalogo] = useState([]);
  const [coloresCatalogo, setColoresCatalogo] = useState([]);
  const [modelos, setModelos] = useState([]);
  const [estados, setEstados] = useState([]);
  const [estadosGlobales, setEstadosGlobales] = useState([]);
  const [usaRuta, setUsaRuta] = useState(false);
  const [rutaNombre, setRutaNombre] = useState('');
  const [siguienteEstado, setSiguienteEstado] = useState(null);

  // Datos de inventario y salidas
  const [itemsInventario, setItemsInventario] = useState([]);
  const [salidasRegistro, setSalidasRegistro] = useState([]);
  const [salidaDialogOpen, setSalidaDialogOpen] = useState(false);
  const [selectedItemInventario, setSelectedItemInventario] = useState(null);
  const [rollosDisponibles, setRollosDisponibles] = useState([]);
  const [selectedRollo, setSelectedRollo] = useState(null);
  const [salidaFormData, setSalidaFormData] = useState({
    item_id: '',
    cantidad: 1,
    rollo_id: '',
    observaciones: '',
  });
  const [rollosDialogOpen, setRollosDialogOpen] = useState(false);
  const [busquedaItem, setBusquedaItem] = useState('');
  const [itemSelectorOpen, setItemSelectorOpen] = useState(false);

  // Datos para movimientos de producción
  const [movimientosProduccion, setMovimientosProduccion] = useState([]);
  const [serviciosProduccion, setServiciosProduccion] = useState([]);
  const [personasProduccion, setPersonasProduccion] = useState([]);
  const [movimientoDialogOpen, setMovimientoDialogOpen] = useState(false);
  const [editingMovimiento, setEditingMovimiento] = useState(null);
  const [personasFiltradas, setPersonasFiltradas] = useState([]);

  // Cierre de producción
  const [cierrePreview, setCierrePreview] = useState(null);
  const [cierreLoading, setCierreLoading] = useState(false);
  const [cierreExistente, setCierreExistente] = useState(null);
  const [ejecutandoCierre, setEjecutandoCierre] = useState(false);

  // Análisis de estado vs movimientos
  const [analisisEstado, setAnalisisEstado] = useState(null);
  const [sugerenciaEstadoDialog, setSugerenciaEstadoDialog] = useState(null); // {tipo, mensaje, estadoSugerido}
  const [sugerenciaMovDialog, setSugerenciaMovDialog] = useState(null); // {servicio_id, servicio_nombre, etapa_nombre}
  const [forzarEstadoDialog, setForzarEstadoDialog] = useState(null); // {nuevo_estado, bloqueos}
  const [etapasCompletas, setEtapasCompletas] = useState([]);

  // División de lote
  const [divisionDialogOpen, setDivisionDialogOpen] = useState(false);
  const [divisionTallas, setDivisionTallas] = useState([]);
  const [divisionInfo, setDivisionInfo] = useState(null);

  const esUltimaEtapa = estados.length > 0 && formData.estado === estados[estados.length - 1];
  const [movimientoFormData, setMovimientoFormData] = useState({
    servicio_id: '',
    persona_id: '',
    fecha_inicio: '',
    fecha_fin: '',
    cantidad_enviada: 0,
    cantidad_recibida: 0,
    tarifa_aplicada: 0,
    fecha_esperada_movimiento: '',
    observaciones: '',
  });

  // Hilos específicos disponibles
  const [hilosEspecificos, setHilosEspecificos] = useState([]);

  // Combobox modelo
  const [modeloPopoverOpen, setModeloPopoverOpen] = useState(false);
  const [modeloSearch, setModeloSearch] = useState('');
  const [servicioPopoverOpen, setServicioPopoverOpen] = useState(false);
  const [personaPopoverOpen, setPersonaPopoverOpen] = useState(false);

  // Incidencias
  const [incidencias, setIncidencias] = useState([]);
  const [motivosIncidencia, setMotivosIncidencia] = useState([]);
  const [incidenciaDialogOpen, setIncidenciaDialogOpen] = useState(false);
  const [incidenciaForm, setIncidenciaForm] = useState({ motivo_id: '', comentario: '', paraliza: false });
  const [nuevoMotivoNombre, setNuevoMotivoNombre] = useState('');

  // Salidas agrupadas: items expandidos
  const [salidasExpandidas, setSalidasExpandidas] = useState({});

  // Cargar datos relacionados - cada catálogo se carga independientemente
  const fetchWithRetry = async (url, retries = 2) => {
    for (let i = 0; i <= retries; i++) {
      try {
        const res = await axios.get(url, { timeout: 15000 });
        return res.data;
      } catch (e) {
        if (i === retries) return null;
        await new Promise(r => setTimeout(r, 800));
      }
    }
    return null;
  };

  const fetchRelatedData = () => {
    // Cada catálogo se carga y setea independientemente
    fetchWithRetry(`${API}/modelos?all=true`).then(d => { if (d) setModelos(d); });
    fetchWithRetry(`${API}/hilos-especificos`).then(d => { if (d) setHilosEspecificos(d); });
    axios.get(`${API}/estados`).then(r => { setEstados(r.data.estados); setEstadosGlobales(r.data.estados); }).catch(() => {});
    axios.get(`${API}/tallas-catalogo`).then(r => setTallasCatalogo(r.data)).catch(() => {});
    axios.get(`${API}/colores-catalogo`).then(r => setColoresCatalogo(r.data)).catch(() => {});
    axios.get(`${API}/inventario?all=true`).then(r => setItemsInventario(r.data)).catch(() => {});
    axios.get(`${API}/servicios-produccion`).then(r => setServiciosProduccion(r.data)).catch(() => {});
    axios.get(`${API}/personas-produccion?activo=true`).then(r => setPersonasProduccion(r.data)).catch(() => {});
  };

  // Cargar estados dinámicos según el registro o modelo
  const fetchEstadosDisponibles = async (registroId) => {
    if (!registroId) {
      setEstados(estadosGlobales);
      setUsaRuta(false);
      setRutaNombre('');
      setSiguienteEstado(null);
      setEtapasCompletas([]);
      return;
    }
    try {
      const response = await axios.get(`${API}/registros/${registroId}/estados-disponibles`);
      const data = response.data;
      setEstados(data.estados || estadosGlobales);
      setUsaRuta(data.usa_ruta || false);
      setRutaNombre(data.ruta_nombre || '');
      setSiguienteEstado(data.siguiente_estado || null);
      setEtapasCompletas(data.etapas_completas || []);
    } catch (error) {
      console.error('Error fetching estados disponibles:', error);
      setEstados(estadosGlobales);
    }
  };

  // Cargar análisis estado vs movimientos
  const fetchAnalisisEstado = async () => {
    if (!id || !usaRuta) return;
    try {
      const response = await axios.get(`${API}/registros/${id}/analisis-estado`);
      setAnalisisEstado(response.data);
    } catch (error) {
      console.error('Error fetching analisis estado:', error);
    }
  };

  // Cargar salidas del registro
  const fetchSalidasRegistro = async () => {
    if (!id) return;
    try {
      const response = await axios.get(`${API}/inventario-salidas?registro_id=${id}`);
      setSalidasRegistro(response.data);
    } catch (error) {
      console.error('Error fetching salidas:', error);
    }
  };

  // Cargar movimientos de producción del registro
  const fetchMovimientosProduccion = async () => {
    if (!id) return;
    try {
      const response = await axios.get(`${API}/movimientos-produccion?registro_id=${id}&all=true`);
      setMovimientosProduccion(response.data);
    } catch (error) {
      console.error('Error fetching movimientos:', error);
    }
  };

  const fetchIncidencias = async () => {
    if (!id) return;
    try {
      const res = await axios.get(`${API}/incidencias/${id}`);
      setIncidencias(res.data);
    } catch (e) { console.error('Error fetching incidencias:', e); }
  };

  const fetchMotivosIncidencia = async () => {
    try {
      const res = await axios.get(`${API}/motivos-incidencia`);
      setMotivosIncidencia(res.data);
    } catch (e) {}
  };

  const handleCrearIncidencia = async () => {
    if (!incidenciaForm.motivo_id) { toast.error('Selecciona un motivo'); return; }
    try {
      await axios.post(`${API}/incidencias`, {
        registro_id: id,
        motivo_id: incidenciaForm.motivo_id,
        comentario: incidenciaForm.comentario,
        paraliza: incidenciaForm.paraliza,
        usuario: 'eduard',
      });
      toast.success('Incidencia registrada');
      setIncidenciaDialogOpen(false);
      setIncidenciaForm({ motivo_id: '', comentario: '', paraliza: false });
      fetchIncidencias();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear incidencia');
    }
  };

  const handleResolverIncidencia = async (incId) => {
    try {
      await axios.put(`${API}/incidencias/${incId}`, { estado: 'RESUELTA' });
      toast.success('Incidencia resuelta');
      fetchIncidencias();
    } catch (error) {
      toast.error('Error al resolver incidencia');
    }
  };

  const handleEliminarIncidencia = async (incId) => {
    try {
      await axios.delete(`${API}/incidencias/${incId}`);
      toast.success('Incidencia eliminada');
      fetchIncidencias();
    } catch (error) {
      toast.error('Error al eliminar incidencia');
    }
  };

  const handleCrearMotivo = async () => {
    if (!nuevoMotivoNombre.trim()) return;
    try {
      const res = await axios.post(`${API}/motivos-incidencia`, { nombre: nuevoMotivoNombre.trim() });
      setMotivosIncidencia(prev => [...prev, res.data].sort((a, b) => a.nombre.localeCompare(b.nombre)));
      setIncidenciaForm(prev => ({ ...prev, motivo_id: res.data.id }));
      setNuevoMotivoNombre('');
      toast.success(`Motivo "${res.data.nombre}" creado`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear motivo');
    }
  };


  // Cargar registro existente si es edición
  const fetchRegistro = async () => {
    if (!id) {
      setLoadingData(false);
      return;
    }
    
    try {
      const response = await axios.get(`${API}/registros/${id}`);
      const registro = response.data;
      
      setFormData({
        n_corte: registro.n_corte,
        modelo_id: registro.modelo_id,
        curva: registro.curva || '',
        estado: registro.estado,
        urgente: registro.urgente,
        hilo_especifico_id: registro.hilo_especifico_id || '',
        pt_item_id: registro.pt_item_id || '',
        id_odoo: registro.id_odoo || '',
        observaciones: registro.observaciones || '',
        skip_validacion_estado: registro.skip_validacion_estado || false,
      });
      
      setTallasSeleccionadas(registro.tallas || []);
      setDistribucionColores(registro.distribucion_colores || []);
      
      // Buscar modelo seleccionado
      try {
        const modelosRes = await axios.get(`${API}/modelos?all=true`);
        const modelo = modelosRes.data.find(m => m.id === registro.modelo_id);
        setModeloSeleccionado(modelo || null);
        if (!registro.pt_item_id && modelo?.pt_item_id) {
          setFormData(prev => ({ ...prev, pt_item_id: modelo.pt_item_id }));
        }
      } catch (e) {
        console.warn('No se pudo cargar modelos para auto-fill');
      }
      
      // Cargar estados disponibles para este registro
      try {
        await fetchEstadosDisponibles(id);
      } catch (e) {
        console.warn('No se pudo cargar estados disponibles');
      }
      
    } catch (error) {
      toast.error('Error al cargar registro');
      navigate('/registros');
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    fetchRelatedData();
    if (id) {
      fetchRegistro();
    } else {
      setLoadingData(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchSalidasRegistro();
      fetchMovimientosProduccion();
      fetchDivisionInfo();
      fetchIncidencias();
      fetchMotivosIncidencia();
    }
  }, [id]);

  // Cargar info de divisiones
  const fetchDivisionInfo = async () => {
    if (!id) return;
    try {
      const response = await axios.get(`${API}/registros/${id}/divisiones`);
      setDivisionInfo(response.data);
    } catch (error) {
      // No es crítico
    }
  };

  const handleOpenDivision = () => {
    // Preparar tallas para el diálogo de división (cantidad 0 por defecto)
    setDivisionTallas(tallasSeleccionadas.map(t => ({
      talla_id: t.talla_id,
      talla_nombre: t.talla_nombre,
      cantidad_disponible: t.cantidad,
      cantidad_dividir: 0,
    })));
    setDivisionDialogOpen(true);
  };

  const handleDividirLote = async () => {
    const tallasConCantidad = divisionTallas.filter(t => t.cantidad_dividir > 0);
    if (tallasConCantidad.length === 0) {
      toast.error('Asigna al menos una cantidad a dividir');
      return;
    }
    // Validar que no exceda
    for (const t of tallasConCantidad) {
      if (t.cantidad_dividir > t.cantidad_disponible) {
        toast.error(`La cantidad para ${t.talla_nombre} excede lo disponible`);
        return;
      }
    }
    try {
      const resp = await axios.post(`${API}/registros/${id}/dividir`, {
        tallas_hijo: tallasConCantidad.map(t => ({ talla_id: t.talla_id, cantidad: t.cantidad_dividir })),
      });
      toast.success(resp.data.mensaje);
      setDivisionDialogOpen(false);
      // Refrescar datos del registro actual (tallas cambiaron)
      const regResp = await axios.get(`${API}/registros/${id}`);
      const regData = regResp.data;
      const nuevasTallas = regData.tallas || [];
      setTallasSeleccionadas(nuevasTallas);
      fetchDivisionInfo();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al dividir lote');
    }
  };

  const handleReunificar = async (hijoId) => {
    try {
      const resp = await axios.post(`${API}/registros/${hijoId}/reunificar`);
      toast.success('Lote reunificado exitosamente');
      // Refrescar datos
      const regResp = await axios.get(`${API}/registros/${id}`);
      setTallasSeleccionadas(regResp.data.tallas || []);
      fetchDivisionInfo();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al reunificar');
    }
  };

  // Cargar análisis de estado cuando cambian los movimientos o la ruta
  useEffect(() => {
    if (id && usaRuta) {
      fetchAnalisisEstado();
    }
  }, [id, usaRuta, movimientosProduccion.length]);

  // Cargar preview de cierre cuando estado es última etapa
  useEffect(() => {
    if (!id || !esUltimaEtapa) {
      setCierrePreview(null);
      return;
    }
    const fetchCierre = async () => {
      setCierreLoading(true);
      try {
        const token = localStorage.getItem('token');
        const headers = { Authorization: `Bearer ${token}` };
        // Check if already closed
        const cierreRes = await axios.get(`${API}/registros/${id}/cierre-produccion`, { headers }).catch(() => ({ data: null }));
        if (cierreRes.data) {
          setCierreExistente(cierreRes.data);
        } else {
          const previewRes = await axios.get(`${API}/registros/${id}/preview-cierre`, { headers });
          setCierrePreview(previewRes.data);
        }
      } catch (err) {
        console.error('Error loading cierre:', err);
      } finally {
        setCierreLoading(false);
      }
    };
    fetchCierre();
  }, [id, esUltimaEtapa]);


  // Cuando cambia el modelo seleccionado
  const handleModeloChange = async (modeloId) => {
    const modelo = modelos.find(m => m.id === modeloId);
    setModeloSeleccionado(modelo || null);
    
    if (modelo?.pt_item_id) {
      // Modelo ya tiene PT, auto-completar
      setFormData({ ...formData, modelo_id: modeloId, pt_item_id: modelo.pt_item_id });
    } else if (modelo) {
      // Modelo sin PT, crear automáticamente
      setFormData({ ...formData, modelo_id: modeloId });
      try {
        const token = localStorage.getItem('token');
        const res = await axios.post(`${API}/modelos/${modelo.id}/crear-pt`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setFormData(prev => ({ ...prev, pt_item_id: res.data.pt_item_id }));
        // Refresh modelos to get updated pt_item_id
        const modelosRes = await axios.get(`${API}/modelos?all=true`);
        setModelos(modelosRes.data);
        setModeloSeleccionado(modelosRes.data.find(m => m.id === modeloId) || null);
        // Refresh items inventario for PT selector
        const itemsRes = await axios.get(`${API}/inventario?all=true`);
        setItemsInventario(itemsRes.data);
        toast.success(`PT creado automáticamente: ${res.data.pt_item_nombre}`);
      } catch (err) {
        console.error('Error creating PT:', err);
      }
    } else {
      setFormData({ ...formData, modelo_id: modeloId });
    }
  };

  const handleEjecutarCierre = async () => {
    if (!window.confirm('¿Estás seguro de ejecutar el cierre de producción? Esta acción creará el ingreso de PT y cerrará la orden.')) return;
    setEjecutandoCierre(true);
    try {
      const token = localStorage.getItem('token');
      // First save the current state to make sure pt_item_id is persisted
      await handleSubmit(null, true);
      await axios.post(`${API}/registros/${id}/cierre-produccion`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Cierre de producción ejecutado exitosamente');
      navigate('/registros');
    } catch (err) {
      toast.error(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Error al ejecutar cierre');
    } finally {
      setEjecutandoCierre(false);
    }
  };


  // Agregar talla
  const handleAddTalla = (tallaId) => {
    const talla = tallasCatalogo.find(t => t.id === tallaId);
    if (!talla || tallasSeleccionadas.find(t => t.talla_id === tallaId)) return;
    
    setTallasSeleccionadas([...tallasSeleccionadas, {
      talla_id: talla.id,
      talla_nombre: talla.nombre,
      cantidad: 0
    }]);
  };

  // Actualizar cantidad de talla
  const handleTallaCantidadChange = (tallaId, cantidad) => {
    setTallasSeleccionadas(tallasSeleccionadas.map(t => 
      t.talla_id === tallaId ? { ...t, cantidad: parseInt(cantidad) || 0 } : t
    ));
  };

  // Remover talla
  const handleRemoveTalla = (tallaId) => {
    setTallasSeleccionadas(tallasSeleccionadas.filter(t => t.talla_id !== tallaId));
  };

  // ========== LÓGICA DE COLORES ==========

  const handleOpenColoresDialog = () => {
    // Reconstruir colores seleccionados y matriz desde distribución guardada
    if (distribucionColores && distribucionColores.length > 0) {
      const coloresUnicos = [];
      const matriz = {};
      
      distribucionColores.forEach(talla => {
        (talla.colores || []).forEach(c => {
          if (!coloresUnicos.find(cu => cu.id === c.color_id)) {
            const colorCat = coloresCatalogo.find(cc => cc.id === c.color_id);
            if (colorCat) {
              coloresUnicos.push(colorCat);
            }
          }
          const key = `${c.color_id}_${talla.talla_id}`;
          matriz[key] = c.cantidad;
        });
      });
      
      setColoresSeleccionados(coloresUnicos);
      setMatrizCantidades(matriz);
    } else {
      setColoresSeleccionados([]);
      setMatrizCantidades({});
    }
    
    setColoresDialogOpen(true);
  };

  const handleColoresChange = (nuevosColores) => {
    const coloresAgregados = nuevosColores.filter(
      nc => !coloresSeleccionados.find(cs => cs.id === nc.id)
    );
    
    const coloresRemovidos = coloresSeleccionados.filter(
      cs => !nuevosColores.find(nc => nc.id === cs.id)
    );
    
    if (coloresRemovidos.length > 0) {
      const nuevaMatriz = { ...matrizCantidades };
      coloresRemovidos.forEach(color => {
        Object.keys(nuevaMatriz).forEach(key => {
          if (key.startsWith(`${color.id}_`)) {
            delete nuevaMatriz[key];
          }
        });
      });
      setMatrizCantidades(nuevaMatriz);
    }
    
    if (coloresSeleccionados.length === 0 && coloresAgregados.length > 0 && tallasSeleccionadas.length > 0) {
      const primerColor = coloresAgregados[0];
      const nuevaMatriz = { ...matrizCantidades };
      tallasSeleccionadas.forEach(t => {
        nuevaMatriz[`${primerColor.id}_${t.talla_id}`] = t.cantidad;
      });
      setMatrizCantidades(nuevaMatriz);
    }
    
    setColoresSeleccionados(nuevosColores);
  };

  const getCantidadMatriz = (colorId, tallaId) => {
    return matrizCantidades[`${colorId}_${tallaId}`] || 0;
  };

  const handleMatrizChange = (colorId, tallaId, valor) => {
    const cantidad = parseInt(valor) || 0;
    const talla = tallasSeleccionadas.find(t => t.talla_id === tallaId);
    
    if (!talla) return;
    
    let sumaOtros = 0;
    coloresSeleccionados.forEach(c => {
      if (c.id !== colorId) {
        sumaOtros += getCantidadMatriz(c.id, tallaId);
      }
    });
    
    if (cantidad + sumaOtros > talla.cantidad) {
      toast.error(`La suma (${cantidad + sumaOtros}) excede el total de la talla ${talla.talla_nombre} (${talla.cantidad})`);
      return;
    }
    
    setMatrizCantidades({
      ...matrizCantidades,
      [`${colorId}_${tallaId}`]: cantidad
    });
  };

  const getTotalColor = (colorId) => {
    let total = 0;
    tallasSeleccionadas.forEach(t => {
      total += getCantidadMatriz(colorId, t.talla_id);
    });
    return total;
  };

  const getTotalTallaAsignado = (tallaId) => {
    let total = 0;
    coloresSeleccionados.forEach(c => {
      total += getCantidadMatriz(c.id, tallaId);
    });
    return total;
  };

  const getTotalGeneralAsignado = () => {
    let total = 0;
    coloresSeleccionados.forEach(c => {
      total += getTotalColor(c.id);
    });
    return total;
  };

  const handleProrratear = () => {
    if (coloresSeleccionados.length === 0 || tallasSeleccionadas.length === 0) return;
    
    const nuevaMatriz = {};
    tallasSeleccionadas.forEach(t => {
      const totalTalla = t.cantidad || 0;
      const numColores = coloresSeleccionados.length;
      const base = Math.floor(totalTalla / numColores);
      const resto = totalTalla % numColores;
      
      coloresSeleccionados.forEach((color, index) => {
        nuevaMatriz[`${color.id}_${t.talla_id}`] = base + (index < resto ? 1 : 0);
      });
    });
    
    setMatrizCantidades(nuevaMatriz);
    toast.success('Cantidades prorrateadas equitativamente');
  };

  const handleSaveColores = () => {
    const distribucion = tallasSeleccionadas.map(t => ({
      talla_id: t.talla_id,
      talla_nombre: t.talla_nombre,
      cantidad_total: t.cantidad,
      colores: coloresSeleccionados.map(c => ({
        color_id: c.id,
        color_nombre: c.nombre,
        cantidad: getCantidadMatriz(c.id, t.talla_id)
      })).filter(c => c.cantidad > 0)
    }));
    
    setDistribucionColores(distribucion);
    setColoresDialogOpen(false);
    toast.success('Distribución de colores guardada');
  };

  // Verificar si tiene colores asignados
  const tieneColores = () => {
    return distribucionColores && 
           distribucionColores.some(t => t.colores && t.colores.length > 0);
  };

  // ========== LÓGICA DE SALIDAS DE INVENTARIO ==========

  const handleOpenSalidaDialog = () => {
    setSalidaFormData({
      item_id: '',
      cantidad: 1,
      rollo_id: '',
      observaciones: '',
    });
    setSelectedItemInventario(null);
    setRollosDisponibles([]);
    setSelectedRollo(null);
    setBusquedaItem('');
    setItemSelectorOpen(false);
    setSalidaDialogOpen(true);
  };

  const handleItemInventarioChange = async (itemId) => {
    const item = itemsInventario.find(i => i.id === itemId);
    setSelectedItemInventario(item);
    setSelectedRollo(null);
    setSalidaFormData({ ...salidaFormData, item_id: itemId, rollo_id: '', cantidad: 1 });
    
    // Si tiene control por rollos, cargar rollos disponibles
    if (item?.control_por_rollos) {
      try {
        const response = await axios.get(`${API}/inventario-rollos?item_id=${itemId}&activo=true`);
        setRollosDisponibles(response.data.filter(r => r.metraje_disponible > 0));
      } catch (error) {
        console.error('Error loading rollos:', error);
        setRollosDisponibles([]);
      }
    } else {
      setRollosDisponibles([]);
    }
  };

  const handleRolloChange = (rolloId) => {
    const rollo = rollosDisponibles.find(r => r.id === rolloId);
    setSelectedRollo(rollo);
    setSalidaFormData({ ...salidaFormData, rollo_id: rolloId, cantidad: 1 });
  };

  const handleCreateSalida = guard(async () => {
    if (!salidaFormData.item_id || salidaFormData.cantidad < 0.01) {
      toast.error('Selecciona un item y cantidad válida');
      return;
    }
    
    if (selectedItemInventario?.control_por_rollos && !salidaFormData.rollo_id) {
      toast.error('Debes seleccionar un rollo');
      return;
    }

    try {
      const payload = {
        ...salidaFormData,
        registro_id: id,
      };
      if (!payload.rollo_id) {
        delete payload.rollo_id;
      }
      await axios.post(`${API}/inventario-salidas`, payload);
      toast.success('Salida registrada');
      setSalidaDialogOpen(false);
      fetchSalidasRegistro();
      const inventarioRes = await axios.get(`${API}/inventario?all=true`);
      setItemsInventario(inventarioRes.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear salida');
    }
  });

  const handleDeleteSalida = async (salidaId) => {
    try {
      await axios.delete(`${API}/inventario-salidas/${salidaId}`);
      toast.success('Salida eliminada');
      fetchSalidasRegistro();
      // Refrescar inventario
      const inventarioRes = await axios.get(`${API}/inventario?all=true`);
      setItemsInventario(inventarioRes.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar salida');
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN',
    }).format(value);
  };

  const getTotalCostoSalidas = () => {
    return salidasRegistro.reduce((sum, s) => sum + (s.costo_total || 0), 0);
  };

  // Agrupar salidas por item para vista resumen
  const salidasAgrupadas = salidasRegistro.reduce((acc, salida) => {
    const key = salida.item_id || salida.item_nombre;
    if (!acc[key]) {
      acc[key] = {
        item_id: salida.item_id,
        item_nombre: salida.item_nombre,
        item_codigo: salida.item_codigo,
        cantidad_total: 0,
        costo_total: 0,
        salidas: [],
      };
    }
    acc[key].cantidad_total += salida.cantidad || 0;
    acc[key].costo_total += salida.costo_total || 0;
    acc[key].salidas.push(salida);
    return acc;
  }, {});

  const toggleSalidaExpandida = (itemKey) => {
    setSalidasExpandidas(prev => ({ ...prev, [itemKey]: !prev[itemKey] }));
  };

  // ========== LÓGICA DE MOVIMIENTOS DE PRODUCCIÓN ==========

  // Helper para obtener tarifa de la combinación persona-servicio
  const getTarifaPersonaServicio = (personaId, servicioId) => {
    const persona = personasProduccion.find(p => p.id === personaId);
    if (!persona) return 0;
    
    // Buscar en servicios_detalle (estructura nueva con detalles)
    const servicioDetalle = (persona.servicios_detalle || []).find(s => s.servicio_id === servicioId);
    if (servicioDetalle) return servicioDetalle.tarifa || 0;
    
    // Buscar en servicios (estructura nueva sin detalles)
    const servicio = (persona.servicios || []).find(s => s.servicio_id === servicioId);
    if (servicio) return servicio.tarifa || 0;
    
    return 0;
  };

  // Helper para calcular costo (usa cantidad_recibida y tarifa_aplicada)
  const calcularCostoMovimiento = () => {
    return (movimientoFormData.tarifa_aplicada || 0) * (movimientoFormData.cantidad_recibida || 0);
  };

  // Helper para calcular diferencia/merma
  const calcularDiferenciaMovimiento = () => {
    return (movimientoFormData.cantidad_enviada || 0) - (movimientoFormData.cantidad_recibida || 0);
  };

  // Helper para calcular cantidad total del registro (tallas + colores)
  const calcularCantidadTotalRegistro = () => {
    // Si hay distribución de colores, sumar toda la matriz
    if (distribucionColores && distribucionColores.length > 0) {
      let total = 0;
      distribucionColores.forEach(talla => {
        (talla.colores || []).forEach(color => {
          total += color.cantidad || 0;
        });
      });
      return total;
    }
    // Si solo hay tallas, sumar cantidades de tallas
    if (tallasSeleccionadas && tallasSeleccionadas.length > 0) {
      return tallasSeleccionadas.reduce((sum, t) => sum + (t.cantidad || 0), 0);
    }
    return 0;
  };

  const handleOpenMovimientoDialog = (movimiento = null) => {
    const cantidadTotal = calcularCantidadTotalRegistro();
    
    if (movimiento) {
      // Modo edición
      setEditingMovimiento(movimiento);
      setMovimientoFormData({
        servicio_id: movimiento.servicio_id,
        persona_id: movimiento.persona_id,
        fecha_inicio: movimiento.fecha_inicio || '',
        fecha_fin: movimiento.fecha_fin || '',
        cantidad_enviada: movimiento.cantidad_enviada || movimiento.cantidad || 0,
        cantidad_recibida: movimiento.cantidad_recibida || movimiento.cantidad || 0,
        tarifa_aplicada: movimiento.tarifa_aplicada || 0,
        fecha_esperada_movimiento: movimiento.fecha_esperada_movimiento || '',
        observaciones: movimiento.observaciones || '',
      });
      // Filtrar personas por el servicio del movimiento (nueva estructura)
      const filtradas = personasProduccion.filter(p => {
        const tieneEnDetalle = (p.servicios_detalle || []).some(s => s.servicio_id === movimiento.servicio_id);
        const tieneEnServicios = (p.servicios || []).some(s => s.servicio_id === movimiento.servicio_id);
        const tieneEnIds = (p.servicio_ids || []).includes(movimiento.servicio_id);
        return tieneEnDetalle || tieneEnServicios || tieneEnIds;
      });
      setPersonasFiltradas(filtradas);
    } else {
      // Modo creación - pre-llenar cantidad con el total del registro
      setEditingMovimiento(null);
      setMovimientoFormData({
        servicio_id: '',
        persona_id: '',
        fecha_inicio: new Date().toISOString().split('T')[0],
        fecha_fin: '',
        cantidad_enviada: cantidadTotal,
        cantidad_recibida: cantidadTotal,
        tarifa_aplicada: 0,
        fecha_esperada_movimiento: '',
        responsable_movimiento: '',
        observaciones: '',
      });
      setPersonasFiltradas([]);
    }
    setMovimientoDialogOpen(true);
  };

  const handleServicioChange = (servicioId) => {
    // Filtrar personas que tienen asignado este servicio (nueva estructura)
    const filtradas = personasProduccion.filter(p => {
      const tieneEnDetalle = (p.servicios_detalle || []).some(s => s.servicio_id === servicioId);
      const tieneEnServicios = (p.servicios || []).some(s => s.servicio_id === servicioId);
      const tieneEnIds = (p.servicio_ids || []).includes(servicioId);
      return tieneEnDetalle || tieneEnServicios || tieneEnIds;
    });
    setPersonasFiltradas(filtradas);
    
    // Auto-sugerir fecha_inicio basada en la etapa anterior de la ruta
    let fechaInicioSugerida = movimientoFormData.fecha_inicio;
    if (usaRuta && etapasCompletas.length > 0 && !editingMovimiento) {
      const etapaIdx = etapasCompletas.findIndex(e => e.servicio_id === servicioId);
      if (etapaIdx > 0) {
        // Buscar la etapa anterior más cercana que tenga movimiento con fecha_fin
        for (let i = etapaIdx - 1; i >= 0; i--) {
          const etapaAnterior = etapasCompletas[i];
          if (!etapaAnterior.servicio_id) continue;
          const movsAnteriores = movimientosProduccion.filter(m => m.servicio_id === etapaAnterior.servicio_id && m.fecha_fin);
          if (movsAnteriores.length > 0) {
            // Tomar la fecha_fin más reciente
            const fechas = movsAnteriores.map(m => m.fecha_fin).sort();
            fechaInicioSugerida = fechas[fechas.length - 1];
            break;
          }
        }
      }
    }
    
    setMovimientoFormData({ 
      ...movimientoFormData, 
      servicio_id: servicioId,
      persona_id: '',
      tarifa_aplicada: 0,
      fecha_inicio: fechaInicioSugerida,
    });
  };

  // Handler para cuando se selecciona una persona
  const handlePersonaChange = (personaId) => {
    // Obtener tarifa de la combinación persona-servicio
    const tarifa = getTarifaPersonaServicio(personaId, movimientoFormData.servicio_id);
    setMovimientoFormData({
      ...movimientoFormData,
      persona_id: personaId,
      tarifa_aplicada: tarifa  // Pre-llenar con tarifa de persona-servicio (editable)
    });
  };

  const handleSaveMovimiento = guard(async () => {
    if (!movimientoFormData.servicio_id || !movimientoFormData.persona_id) {
      toast.error('Selecciona servicio y persona');
      return;
    }

    try {
      if (editingMovimiento) {
        const payload = {
          ...movimientoFormData,
          registro_id: id,
        };
        await axios.put(`${API}/movimientos-produccion/${editingMovimiento.id}`, payload);
        toast.success('Movimiento actualizado');
      } else {
        const payload = {
          ...movimientoFormData,
          registro_id: id,
        };
        await axios.post(`${API}/movimientos-produccion`, payload);
        toast.success('Movimiento registrado');
      }
      setMovimientoDialogOpen(false);
      setEditingMovimiento(null);
      await fetchMovimientosProduccion();

      // Sugerencia bidireccional: movimiento -> estado
      if (usaRuta && etapasCompletas.length > 0) {
        const servicioMov = movimientoFormData.servicio_id;
        const etapaVinculada = etapasCompletas.find(e => e.servicio_id === servicioMov && e.aparece_en_estado !== false);
        if (etapaVinculada) {
          const etapaNombre = etapaVinculada.nombre;
          const idxEtapaMov = etapasCompletas.indexOf(etapaVinculada);
          const idxEstadoActual = etapasCompletas.findIndex(e => e.nombre === formData.estado);

          if (movimientoFormData.fecha_inicio && !movimientoFormData.fecha_fin && etapaNombre !== formData.estado && idxEtapaMov > idxEstadoActual) {
            // Se inició el movimiento y la etapa está ADELANTE del estado actual
            setSugerenciaEstadoDialog({
              tipo: 'inicio',
              mensaje: `Se inició ${etapaVinculada.nombre}. ¿Deseas actualizar el estado del registro?`,
              estadoSugerido: etapaNombre,
            });
          } else if (movimientoFormData.fecha_fin) {
            // Se finalizó el movimiento - sugerir avanzar al siguiente estado
            const siguientes = etapasCompletas.slice(idxEtapaMov + 1);
            const sigEstado = siguientes.find(e => e.aparece_en_estado !== false);
            if (sigEstado && sigEstado.nombre !== formData.estado) {
              const idxSig = etapasCompletas.findIndex(e => e.nombre === sigEstado.nombre);
              // Solo sugerir si el siguiente estado está ADELANTE del actual
              if (idxSig > idxEstadoActual) {
                setSugerenciaEstadoDialog({
                  tipo: 'fin',
                  mensaje: `${etapaVinculada.nombre} fue finalizada. ¿Deseas avanzar el estado del registro?`,
                  estadoSugerido: sigEstado.nombre,
                });
              }
            }
          }
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar movimiento');
    }
  });

  const handleDeleteMovimiento = async (movimientoId) => {
    try {
      await axios.delete(`${API}/movimientos-produccion/${movimientoId}`);
      toast.success('Movimiento eliminado');
      fetchMovimientosProduccion();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const handleGenerarGuia = async (movimientoId) => {
    try {
      const response = await axios.post(`${API}/guias-remision/from-movimiento/${movimientoId}`);
      const guia = response.data.guia;
      toast.success(`Guía ${guia.numero_guia} lista para imprimir`);
      
      // Abrir en nueva ventana para imprimir
      const printWindow = window.open('', '_blank');
      printWindow.document.write(`
        <html>
          <head>
            <title>Guía de Remisión ${guia.numero_guia}</title>
            <style>
              body { font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
              .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 15px; margin-bottom: 30px; }
              .header h1 { margin: 0; font-size: 28px; }
              .header .numero { font-size: 24px; font-family: monospace; margin-top: 10px; }
              .header .fecha { color: #666; margin-top: 5px; }
              .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
              .info-box { border: 1px solid #ddd; padding: 15px; border-radius: 8px; }
              .info-box h3 { margin: 0 0 10px 0; font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; }
              .info-box p { margin: 5px 0; }
              .info-box .nombre { font-size: 18px; font-weight: bold; }
              .cantidad-box { text-align: center; padding: 30px; background: #f5f5f5; border-radius: 8px; margin-bottom: 30px; }
              .cantidad-box .numero { font-size: 64px; font-weight: bold; color: #333; }
              .cantidad-box .label { color: #666; font-size: 14px; text-transform: uppercase; }
              .observaciones { border: 1px solid #ddd; padding: 15px; border-radius: 8px; min-height: 60px; margin-bottom: 30px; }
              .observaciones h3 { margin: 0 0 10px 0; font-size: 12px; color: #666; text-transform: uppercase; }
              .firmas { display: grid; grid-template-columns: 1fr 1fr; gap: 60px; margin-top: 60px; }
              .firma-box { text-align: center; }
              .firma-linea { border-top: 1px solid #000; padding-top: 8px; margin-top: 80px; font-size: 14px; }
              @media print { body { padding: 20px; } }
            </style>
          </head>
          <body>
            <div class="header">
              <h1>GUÍA DE REMISIÓN</h1>
              <div class="numero">${guia.numero_guia}</div>
              <div class="fecha">Fecha: ${guia.fecha ? new Date(guia.fecha).toLocaleDateString('es-PE') : ''}</div>
            </div>
            
            <div class="info-grid">
              <div class="info-box">
                <h3>Registro de Producción</h3>
                <p class="nombre">${guia.modelo_nombre || 'N/A'}</p>
                <p>N° Corte: ${guia.registro_n_corte || 'N/A'}</p>
                <p style="margin-top: 10px; color: #666;">Servicio: ${guia.servicio_nombre || 'N/A'}</p>
              </div>
              <div class="info-box">
                <h3>Destinatario</h3>
                <p class="nombre">${guia.persona_nombre || 'N/A'}</p>
                ${guia.persona_telefono ? `<p>Tel: ${guia.persona_telefono}</p>` : ''}
                ${guia.persona_direccion ? `<p>${guia.persona_direccion}</p>` : ''}
              </div>
            </div>
            
            <div class="cantidad-box">
              <div class="numero">${guia.cantidad}</div>
              <div class="label">Prendas</div>
            </div>
            
            ${guia.observaciones ? `
              <div class="observaciones">
                <h3>Observaciones</h3>
                <p>${guia.observaciones}</p>
              </div>
            ` : ''}
            
            <div class="firmas">
              <div class="firma-box">
                <div class="firma-linea">Firma Remitente</div>
              </div>
              <div class="firma-box">
                <div class="firma-linea">Firma Destinatario</div>
              </div>
            </div>
          </body>
        </html>
      `);
      printWindow.document.close();
      printWindow.print();
    } catch (error) {
      if (error.response?.status === 400) {
        toast.error('Ya existe una guía para este movimiento');
      } else {
        toast.error(error.response?.data?.detail || 'Error al generar guía');
      }
    }
  };

  const getTotalCantidadMovimientos = () => {
    return movimientosProduccion.reduce((sum, m) => sum + (m.cantidad_recibida || m.cantidad || 0), 0);
  };

  // Guardar registro
  // Auto-guardar estado sin requerir click en "Actualizar Registro"
  const autoGuardarEstado = async (nuevoEstado) => {
    if (!id || !isEditing) return;
    try {
      const payload = {
        ...formData,
        estado: nuevoEstado,
        tallas: tallasSeleccionadas,
        distribucion_colores: distribucionColores,
      };
      await axios.put(`${API}/registros/${id}`, payload);
      setFormData(prev => ({ ...prev, estado: nuevoEstado }));
      toast.success(`Estado actualizado a "${nuevoEstado}"`);
      // Refrescar análisis de inconsistencias
      fetchAnalisisEstado();
    } catch (error) {
      toast.error('Error al guardar estado');
    }
  };

  const handleSubmit = async (e, silentMode = false) => {
    if (e) e.preventDefault();
    setLoading(true);
    
    try {
      const payload = {
        ...formData,
        tallas: tallasSeleccionadas,
        distribucion_colores: distribucionColores,
      };
      
      if (isEditing) {
        await axios.put(`${API}/registros/${id}`, payload);
        if (!silentMode) toast.success('Registro actualizado');
      } else {
        const res = await axios.post(`${API}/registros`, payload);
        if (silentMode && res.data?.id) {
          navigate(`/registros/editar/${res.data.id}`, { replace: true });
        }
        if (!silentMode) toast.success('Registro creado');
      }
      
      if (!silentMode) navigate('/registros');
    } catch (error) {
      toast.error('Error al guardar registro');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Tallas disponibles (no seleccionadas)
  const tallasDisponibles = tallasCatalogo.filter(
    t => !tallasSeleccionadas.find(ts => ts.talla_id === t.id)
  );

  if (loadingData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Cargando...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="registro-form-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button 
          variant="ghost" 
          size="icon"
          onClick={() => navigate('/registros')}
          data-testid="btn-volver"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h2 className="text-2xl font-bold tracking-tight">
            {isEditing ? 'Editar Registro' : 'Nuevo Registro'}
          </h2>
          <p className="text-muted-foreground">
            {isEditing ? `Editando registro ${formData.n_corte}` : 'Crear un nuevo registro de produccion'}
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          disabled={loading}
          onClick={async () => {
            await handleSubmit(null, true);
            toast.success('Guardado');
          }}
          data-testid="btn-guardar-rapido"
        >
          {loading ? 'Guardando...' : 'Guardar'}
        </Button>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Columna izquierda - Información general */}
          <div className="lg:col-span-2 space-y-6">
            {/* Información General */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Información General</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* ESTADO - Campo dominante */}
                <div className="rounded-lg border-2 border-primary/30 bg-primary/5 p-4" data-testid="estado-banner">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="h-10 w-10 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
                        <Play className="h-5 w-5 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <Label className="text-xs uppercase tracking-wider text-muted-foreground">Estado actual</Label>
                        {usaRuta && rutaNombre && (
                          <p className="text-xs text-muted-foreground truncate">Ruta: {rutaNombre}</p>
                        )}
                      </div>
                    </div>
                    <Select
                      key={estados.length > 0 && formData.estado ? formData.estado : 'est-loading'}
                      value={formData.estado}
                      onValueChange={async (value) => {
                        if (usaRuta && id) {
                          try {
                            const resp = await axios.post(`${API}/registros/${id}/validar-cambio-estado`, { nuevo_estado: value });
                            const data = resp.data;
                            if (!data.permitido) {
                              setForzarEstadoDialog({ nuevo_estado: value, bloqueos: data.bloqueos });
                              return;
                            }
                            await autoGuardarEstado(value);
                            if (data.sugerencia_movimiento) {
                              setSugerenciaMovDialog(data.sugerencia_movimiento);
                            }
                          } catch {
                            await autoGuardarEstado(value);
                          }
                        } else {
                          await autoGuardarEstado(value);
                        }
                      }}
                    >
                      <SelectTrigger data-testid="select-estado" className="w-[260px] h-11 text-base font-semibold border-primary/40 bg-white dark:bg-zinc-900">
                        <SelectValue placeholder="Seleccionar estado" />
                      </SelectTrigger>
                      <SelectContent>
                        {estados.map((e, idx) => (
                          <SelectItem key={e} value={e}>
                            <span className="flex items-center gap-2">
                              <span className="text-xs text-muted-foreground font-mono w-5">{idx + 1}.</span>
                              {e}
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {id && (
                      <label className="flex items-center gap-2 cursor-pointer select-none ml-3" title="Desactiva las validaciones de movimientos para cambiar de estado libremente">
                        <input
                          type="checkbox"
                          checked={formData.skip_validacion_estado || false}
                          onChange={async (ev) => {
                            const newVal = ev.target.checked;
                            setFormData(prev => ({ ...prev, skip_validacion_estado: newVal }));
                            try {
                              await axios.put(`${API}/registros/${id}/skip-validacion`, { skip_validacion_estado: newVal });
                              toast.success(newVal ? 'Validacion de estados desactivada' : 'Validacion de estados activada');
                            } catch {
                              toast.error('Error al cambiar configuracion');
                              setFormData(prev => ({ ...prev, skip_validacion_estado: !newVal }));
                            }
                          }}
                          className="rounded border-gray-300"
                          data-testid="toggle-skip-validacion"
                        />
                        <span className="text-xs text-muted-foreground whitespace-nowrap">Sin restricciones</span>
                      </label>
                    )}
                  </div>
                  {estados.length > 1 && (
                    <div className="flex items-center gap-1 mt-3 overflow-x-auto pb-1">
                      {estados.map((e, idx) => {
                        const currentIdx = estados.indexOf(formData.estado);
                        const isPast = idx < currentIdx;
                        const isCurrent = idx === currentIdx;
                        return (
                          <div key={e} className="flex items-center gap-1 shrink-0">
                            {idx > 0 && <div className={`w-4 h-0.5 ${isPast ? 'bg-primary' : 'bg-muted'}`} />}
                            <div
                              className={`text-[10px] px-2 py-0.5 rounded-full whitespace-nowrap cursor-pointer transition-colors ${
                                isCurrent ? 'bg-primary text-primary-foreground font-semibold' :
                                isPast ? 'bg-primary/20 text-primary' :
                                'bg-muted text-muted-foreground'
                              }`}
                              onClick={async () => {
                                if (usaRuta && id) {
                                  try {
                                    const resp = await axios.post(`${API}/registros/${id}/validar-cambio-estado`, { nuevo_estado: e });
                                    const data = resp.data;
                                    if (!data.permitido) {
                                      setForzarEstadoDialog({ nuevo_estado: e, bloqueos: data.bloqueos });
                                      return;
                                    }
                                    await autoGuardarEstado(e);
                                    if (data.sugerencia_movimiento) {
                                      setSugerenciaMovDialog(data.sugerencia_movimiento);
                                    }
                                  } catch {
                                    await autoGuardarEstado(e);
                                  }
                                } else {
                                  await autoGuardarEstado(e);
                                }
                              }}
                            >
                              {e}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Banner de inconsistencias estado vs movimientos */}
                {analisisEstado && analisisEstado.inconsistencias && analisisEstado.inconsistencias.length > 0 && !formData.skip_validacion_estado && (
                  <div className="rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-700 p-3 space-y-1" data-testid="inconsistencias-banner">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                      <span className="text-sm font-medium text-amber-800 dark:text-amber-300">Estado y movimientos no coinciden completamente</span>
                    </div>
                    {analisisEstado.inconsistencias.map((inc, i) => (
                      <p key={i} className={`text-xs ml-6 ${inc.severidad === 'error' ? 'text-red-600 font-medium' : inc.severidad === 'warning' ? 'text-amber-700 dark:text-amber-400' : 'text-muted-foreground'}`}>
                        {inc.mensaje}
                      </p>
                    ))}
                    {analisisEstado.estado_sugerido && analisisEstado.estado_sugerido !== formData.estado && (
                      <div className="ml-6 mt-1">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-6 text-xs border-amber-400 text-amber-700 hover:bg-amber-100"
                          onClick={async () => {
                            await autoGuardarEstado(analisisEstado.estado_sugerido);
                          }}
                          data-testid="btn-aplicar-estado-sugerido"
                        >
                          Aplicar estado sugerido: {analisisEstado.estado_sugerido}
                        </Button>
                      </div>
                    )}
                  </div>
                )}

                {/* Banner de división de lote */}
                {divisionInfo && (divisionInfo.es_hijo || divisionInfo.hijos.length > 0) && (
                  <div className="rounded-lg border border-blue-300 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-700 p-3 space-y-2" data-testid="division-banner">
                    <div className="flex items-center gap-2">
                      <Scissors className="h-4 w-4 text-blue-600 shrink-0" />
                      <span className="text-sm font-medium text-blue-800 dark:text-blue-300">
                        {divisionInfo.es_hijo
                          ? `Dividido desde Corte ${divisionInfo.padre?.n_corte}`
                          : `Lote con ${divisionInfo.hijos.length} división(es)`}
                      </span>
                    </div>
                    {divisionInfo.es_hijo && divisionInfo.padre && (
                      <div className="ml-6 flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">Registro padre:</span>
                        <Button variant="link" size="sm" className="h-5 px-0 text-xs text-blue-600"
                          onClick={() => navigate(`/registros/editar/${divisionInfo.padre.id}`)}
                          data-testid="link-padre"
                        >
                          Corte {divisionInfo.padre.n_corte} ({divisionInfo.padre.estado})
                        </Button>
                      </div>
                    )}
                    {divisionInfo.hijos.length > 0 && divisionInfo.hijos.map(h => {
                      const totalHijo = (h.tallas || []).reduce((s, t) => s + (t.cantidad || 0), 0);
                      return (
                        <div key={h.id} className="ml-6 flex items-center gap-2">
                          <Button variant="link" size="sm" className="h-5 px-0 text-xs text-blue-600"
                            onClick={() => navigate(`/registros/editar/${h.id}`)}
                          >
                            Corte {h.n_corte}
                          </Button>
                          <Badge variant="outline" className="text-[10px]">{h.estado}</Badge>
                          <span className="text-[10px] text-muted-foreground">{totalHijo} prendas</span>
                          <Button variant="ghost" size="sm" className="h-5 px-1 text-[10px] text-red-600 hover:text-red-700"
                            onClick={() => handleReunificar(h.id)}
                            title="Reunificar con este lote"
                            data-testid={`btn-reunificar-${h.id}`}
                          >
                            Reunificar
                          </Button>
                        </div>
                      );
                    })}
                    {divisionInfo.hermanos.length > 0 && (
                      <div className="ml-6 text-xs text-muted-foreground">
                        Hermanos: {divisionInfo.hermanos.map(h => (
                          <Button key={h.id} variant="link" size="sm" className="h-5 px-1 text-xs text-blue-600"
                            onClick={() => navigate(`/registros/editar/${h.id}`)}
                          >
                            {h.n_corte}
                          </Button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Panel de Cierre de Producción */}
                {esUltimaEtapa && (
                  <div className="rounded-lg border-2 border-green-500/40 bg-green-50 dark:bg-green-950/20 p-5 space-y-4" data-testid="cierre-panel">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-green-500/15 flex items-center justify-center shrink-0">
                        <Package className="h-5 w-5 text-green-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-green-800 dark:text-green-400">Cierre de Producción</h3>
                        <p className="text-xs text-green-600 dark:text-green-500">El registro está en la etapa final. Puedes ejecutar el cierre para generar el ingreso de PT.</p>
                      </div>
                    </div>

                    {cierreExistente ? (
                      <div className="rounded-md bg-green-100 dark:bg-green-900/30 p-4 text-center">
                        <p className="font-semibold text-green-800 dark:text-green-300">Producción ya cerrada</p>
                        <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                          Costo total: S/ {parseFloat(cierreExistente.costo_total || 0).toFixed(2)}
                        </p>
                      </div>
                    ) : cierreLoading ? (
                      <div className="text-center py-4 text-green-600">Calculando costos...</div>
                    ) : cierrePreview ? (
                      <>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                          <div className="rounded-md bg-white dark:bg-zinc-900 p-3 text-center border">
                            <p className="text-[10px] uppercase text-muted-foreground">Costo MP</p>
                            <p className="text-base font-bold font-mono">S/ {cierrePreview.costo_mp.toFixed(2)}</p>
                          </div>
                          <div className="rounded-md bg-white dark:bg-zinc-900 p-3 text-center border">
                            <p className="text-[10px] uppercase text-muted-foreground">Servicios</p>
                            <p className="text-base font-bold font-mono">S/ {cierrePreview.costo_servicios.toFixed(2)}</p>
                          </div>
                          <div className="rounded-md bg-white dark:bg-zinc-900 p-3 text-center border">
                            <p className="text-[10px] uppercase text-muted-foreground">Otros Costos</p>
                            <p className="text-base font-bold font-mono">S/ {(cierrePreview.otros_costos || 0).toFixed(2)}</p>
                          </div>
                          <div className="rounded-md bg-white dark:bg-zinc-900 p-3 text-center border border-green-300">
                            <p className="text-[10px] uppercase text-muted-foreground">Total</p>
                            <p className="text-lg font-bold font-mono text-green-700">S/ {cierrePreview.costo_total.toFixed(2)}</p>
                          </div>
                          <div className="rounded-md bg-white dark:bg-zinc-900 p-3 text-center border border-green-300">
                            <p className="text-[10px] uppercase text-muted-foreground">Unit. PT</p>
                            <p className="text-lg font-bold font-mono text-green-700">S/ {cierrePreview.costo_unit_pt.toFixed(4)}</p>
                          </div>
                        </div>

                        {!cierrePreview.puede_cerrar && (
                          <p className="text-sm text-amber-600 text-center">
                            {!formData.pt_item_id ? 'Falta asignar un Artículo PT para poder cerrar.' : 'No hay prendas registradas.'}
                          </p>
                        )}

                        <Button
                          type="button"
                          className="w-full h-12 text-base bg-green-600 hover:bg-green-700"
                          disabled={!cierrePreview.puede_cerrar || ejecutandoCierre}
                          onClick={handleEjecutarCierre}
                          data-testid="btn-ejecutar-cierre"
                        >
                          {ejecutandoCierre ? 'Ejecutando cierre...' : 'Ejecutar Cierre de Producción'}
                        </Button>
                      </>
                    ) : null}
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="n_corte">N° Corte *</Label>
                    <Input
                      id="n_corte"
                      value={formData.n_corte}
                      onChange={(e) => setFormData({ ...formData, n_corte: e.target.value })}
                      placeholder="Número de corte"
                      required
                      className="font-mono"
                      data-testid="input-n-corte"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="curva">Curva</Label>
                    <Input
                      id="curva"
                      value={formData.curva}
                      onChange={(e) => setFormData({ ...formData, curva: e.target.value })}
                      placeholder="Curva"
                      className="font-mono"
                      data-testid="input-curva"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Modelo *</Label>
                    <Popover open={modeloPopoverOpen} onOpenChange={(open) => { setModeloPopoverOpen(open); if (!open) setModeloSearch(''); }}>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          role="combobox"
                          aria-expanded={modeloPopoverOpen}
                          className="w-full justify-between font-normal"
                          data-testid="select-modelo"
                        >
                          {modelos.length === 0
                            ? <span className="flex items-center gap-2 text-muted-foreground"><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Cargando modelos...</span>
                            : (formData.modelo_id
                              ? modelos.find(m => m.id === formData.modelo_id)?.nombre || 'Seleccionar modelo'
                              : 'Seleccionar modelo')
                          }
                          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                        <Command shouldFilter={false}>
                          <CommandInput placeholder="Buscar modelo..." value={modeloSearch} onValueChange={setModeloSearch} />
                          <CommandList>
                            {modelos.length === 0 ? (
                              <div className="py-6 text-center text-sm text-muted-foreground">Cargando modelos...</div>
                            ) : (() => {
                              const term = modeloSearch.toLowerCase();
                              const filtered = term
                                ? modelos.filter(m => m.nombre.toLowerCase().includes(term))
                                : modelos;
                              const limited = filtered.slice(0, 50);
                              if (limited.length === 0) return <CommandEmpty>No se encontró modelo.</CommandEmpty>;
                              return (
                                <CommandGroup>
                                  {limited.map((m) => (
                                    <CommandItem
                                      key={m.id}
                                      value={m.id}
                                      onSelect={() => {
                                        handleModeloChange(m.id);
                                        setModeloPopoverOpen(false);
                                        setModeloSearch('');
                                      }}
                                    >
                                      <Check className={`mr-2 h-4 w-4 ${formData.modelo_id === m.id ? 'opacity-100' : 'opacity-0'}`} />
                                      {m.nombre}
                                    </CommandItem>
                                  ))}
                                  {filtered.length > 50 && (
                                    <div className="px-2 py-1.5 text-xs text-muted-foreground text-center">
                                      +{filtered.length - 50} más. Escribe para filtrar...
                                    </div>
                                  )}
                                </CommandGroup>
                              );
                            })()}
                          </CommandList>
                        </Command>
                      </PopoverContent>
                    </Popover>
                  </div>

                  <div className="space-y-2">
                    <Label>Hilo Específico</Label>
                    <Select
                      key={hilosEspecificos.length > 0 && formData.hilo_especifico_id ? formData.hilo_especifico_id : 'hilo-loading'}
                      value={formData.hilo_especifico_id || ""}
                      onValueChange={(value) => setFormData({ ...formData, hilo_especifico_id: value === "none" ? "" : value })}
                    >
                      <SelectTrigger data-testid="select-hilo-especifico">
                        <SelectValue placeholder="Sin hilo específico" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Sin hilo específico</SelectItem>
                        {hilosEspecificos.map((h) => (
                          <SelectItem key={h.id} value={h.id}>
                            {h.nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Artículo PT (Producto Terminado)</Label>
                    {modeloSeleccionado?.pt_item_id && formData.pt_item_id === modeloSeleccionado.pt_item_id && (
                      <p className="text-xs text-green-600">Auto-completado desde el modelo</p>
                    )}
                    <Select
                      value={formData.pt_item_id || ""}
                      onValueChange={(value) => setFormData({ ...formData, pt_item_id: value === "none" ? "" : value })}
                    >
                      <SelectTrigger data-testid="select-pt-item">
                        <SelectValue placeholder="Seleccionar artículo PT" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Sin artículo PT</SelectItem>
                        {itemsInventario.filter(i => i.tipo_item === 'PT').map((item) => (
                          <SelectItem key={item.id} value={item.id}>
                            {item.codigo} - {item.nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex items-center space-x-2 pt-2">
                  <Checkbox
                    id="urgente"
                    checked={formData.urgente}
                    onCheckedChange={(checked) => setFormData({ ...formData, urgente: checked })}
                    data-testid="checkbox-urgente"
                  />
                  <Label htmlFor="urgente" className="flex items-center gap-2 cursor-pointer">
                    <AlertTriangle className="h-4 w-4 text-destructive" />
                    Marcar como Urgente
                  </Label>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="space-y-2">
                    <Label htmlFor="id_odoo">ID Odoo</Label>
                    <Input
                      id="id_odoo"
                      value={formData.id_odoo}
                      onChange={(e) => setFormData({ ...formData, id_odoo: e.target.value })}
                      placeholder="ID del sistema Odoo"
                      data-testid="input-id-odoo"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="observaciones">Observaciones</Label>
                    <Input
                      id="observaciones"
                      value={formData.observaciones}
                      onChange={(e) => setFormData({ ...formData, observaciones: e.target.value })}
                      placeholder="Notas u observaciones"
                      data-testid="input-observaciones"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Tallas */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Tallas y Cantidades</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Select onValueChange={handleAddTalla}>
                    <SelectTrigger className="w-[200px]" data-testid="select-agregar-talla">
                      <SelectValue placeholder="Agregar talla..." />
                    </SelectTrigger>
                    <SelectContent>
                      {tallasDisponibles.map((t) => (
                        <SelectItem key={t.id} value={t.id}>
                          {t.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {tallasSeleccionadas.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/50">
                          <TableHead className="font-semibold">Talla</TableHead>
                          <TableHead className="font-semibold w-[150px]">Cantidad</TableHead>
                          <TableHead className="w-[60px]"></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {tallasSeleccionadas.map((t) => (
                          <TableRow key={t.talla_id}>
                            <TableCell className="font-medium">{t.talla_nombre}</TableCell>
                            <TableCell>
                              <NumericInput
                                min="0"
                                value={t.cantidad}
                                onChange={(e) => handleTallaCantidadChange(t.talla_id, e.target.value)}
                                className="w-full font-mono text-center"
                                placeholder="0"
                                data-testid={`input-cantidad-talla-${t.talla_id}`}
                              />
                            </TableCell>
                            <TableCell>
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                onClick={() => handleRemoveTalla(t.talla_id)}
                                data-testid={`remove-talla-${t.talla_id}`}
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                        <TableRow className="bg-muted/30">
                          <TableCell className="font-semibold">Total</TableCell>
                          <TableCell className="font-mono font-bold text-center text-lg">
                            {tallasSeleccionadas.reduce((sum, t) => sum + (t.cantidad || 0), 0)}
                          </TableCell>
                          <TableCell></TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground border rounded-lg bg-muted/20">
                    Selecciona tallas del catálogo para agregar cantidades
                  </div>
                )}

                {/* Botón Agregar Colores */}
                {tallasSeleccionadas.length > 0 && (
                  <div className="pt-4">
                    <Separator className="mb-4" />
                    <Button
                      type="button"
                      variant={tieneColores() ? "default" : "outline"}
                      onClick={handleOpenColoresDialog}
                      className="w-full"
                      data-testid="btn-agregar-colores"
                    >
                      <Palette className="h-4 w-4 mr-2" />
                      {tieneColores() ? 'Editar Colores' : 'Agregar Colores'}
                      {tieneColores() && (
                        <Badge variant="secondary" className="ml-2">
                          {distribucionColores.reduce((sum, t) => sum + (t.colores?.length || 0), 0)} colores
                        </Badge>
                      )}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Salidas de Inventario (solo en modo edición) */}
            {isEditing && (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Package className="h-5 w-5" />
                    Salidas de Inventario
                  </CardTitle>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => setRollosDialogOpen(true)}
                      data-testid="btn-salida-rollos"
                    >
                      <Layers className="h-4 w-4 mr-1" />
                      Rollos
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleOpenSalidaDialog}
                      data-testid="btn-nueva-salida"
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Agregar Salida
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {salidasRegistro.length > 0 ? (
                    <>
                      <div className="border rounded-lg overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/50">
                              <TableHead>Item</TableHead>
                              <TableHead className="text-right">Cantidad</TableHead>
                              <TableHead className="text-right">Costo FIFO</TableHead>
                              <TableHead className="w-[60px]"></TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {Object.entries(salidasAgrupadas).map(([key, grupo]) => {
                              const isExpanded = salidasExpandidas[key];
                              return (
                                <React.Fragment key={key}>
                                  {/* Fila resumen del grupo */}
                                  <TableRow
                                    className="cursor-pointer hover:bg-muted/40 transition-colors"
                                    onClick={() => toggleSalidaExpandida(key)}
                                    data-testid={`salida-grupo-${key}`}
                                  >
                                    <TableCell>
                                      <div className="flex items-center gap-2">
                                        {isExpanded
                                          ? <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
                                          : <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                                        }
                                        <div>
                                          <p className="font-medium">{grupo.item_nombre}</p>
                                          <p className="text-xs text-muted-foreground font-mono">{grupo.item_codigo} &middot; {grupo.salidas.length} salida{grupo.salidas.length > 1 ? 's' : ''}</p>
                                        </div>
                                      </div>
                                    </TableCell>
                                    <TableCell className="text-right font-mono font-semibold">
                                      {grupo.cantidad_total}
                                    </TableCell>
                                    <TableCell className="text-right font-mono">
                                      {formatCurrency(grupo.costo_total)}
                                    </TableCell>
                                    <TableCell></TableCell>
                                  </TableRow>
                                  {/* Filas individuales expandidas */}
                                  {isExpanded && grupo.salidas.map((salida) => (
                                    <TableRow key={salida.id} className="bg-muted/10" data-testid={`salida-row-${salida.id}`}>
                                      <TableCell className="pl-10">
                                        <div className="flex items-center gap-2">
                                          <ArrowUpCircle className="h-3.5 w-3.5 text-red-400" />
                                          <span className="text-sm text-muted-foreground">
                                            {salida.observaciones || `Salida #${salida.id?.slice(0,8)}`}
                                          </span>
                                        </div>
                                      </TableCell>
                                      <TableCell className="text-right font-mono text-sm">
                                        {salida.cantidad}
                                      </TableCell>
                                      <TableCell className="text-right font-mono text-sm">
                                        {formatCurrency(salida.costo_total)}
                                      </TableCell>
                                      <TableCell>
                                        <Button
                                          type="button"
                                          variant="ghost"
                                          size="icon"
                                          className="h-7 w-7"
                                          onClick={(e) => { e.stopPropagation(); handleDeleteSalida(salida.id); }}
                                          data-testid={`delete-salida-${salida.id}`}
                                        >
                                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                                        </Button>
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </React.Fragment>
                              );
                            })}
                            <TableRow className="bg-muted/30">
                              <TableCell colSpan={2} className="font-semibold">Total Costo</TableCell>
                              <TableCell className="text-right font-mono font-bold text-primary">
                                {formatCurrency(getTotalCostoSalidas())}
                              </TableCell>
                              <TableCell></TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {salidasRegistro.length} salida{salidasRegistro.length !== 1 ? 's' : ''} vinculada{salidasRegistro.length !== 1 ? 's' : ''} a este registro
                      </p>
                    </>
                  ) : (
                    <div className="text-center py-6 text-muted-foreground border rounded-lg bg-muted/20">
                      <Package className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>No hay salidas de inventario</p>
                      <p className="text-xs mt-1">Agrega materiales utilizados en este registro</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Movimientos de Producción (solo en modo edición) */}
            {isEditing && (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Play className="h-5 w-5" />
                    Movimientos de Producción
                  </CardTitle>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => handleOpenMovimientoDialog()}
                    data-testid="btn-nuevo-movimiento"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Agregar Movimiento
                  </Button>
                </CardHeader>
                <CardContent className="space-y-4">
                  {movimientosProduccion.length > 0 ? (
                    <>
                      <div className="border rounded-lg overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/50">
                              <TableHead>Servicio</TableHead>
                              <TableHead>Persona</TableHead>
                              <TableHead className="text-center">F. Esperada</TableHead>
                              <TableHead className="text-center">Fechas</TableHead>
                              <TableHead className="text-right">Enviada</TableHead>
                              <TableHead className="text-right">Recibida</TableHead>
                              <TableHead className="text-right">Merma</TableHead>
                              <TableHead className="w-[100px] text-right">Acciones</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {movimientosProduccion.map((mov) => {
                              const enviada = mov.cantidad_enviada || mov.cantidad || 0;
                              const recibida = mov.cantidad_recibida || mov.cantidad || 0;
                              const diferencia = enviada - recibida;
                              // Alerta visual fecha esperada
                              let fechaAlerta = '';
                              let fechaClase = '';
                              if (mov.fecha_esperada_movimiento) {
                                const hoy = new Date(); hoy.setHours(0,0,0,0);
                                const esp = new Date(mov.fecha_esperada_movimiento + 'T00:00:00');
                                const diff = Math.ceil((esp - hoy) / (1000*60*60*24));
                                if (diff < 0) { fechaAlerta = 'Vencido'; fechaClase = 'text-red-600 font-semibold'; }
                                else if (diff <= 3) { fechaAlerta = `${diff}d`; fechaClase = 'text-amber-600 font-semibold'; }
                              }
                              return (
                                <TableRow key={mov.id} className={fechaAlerta === 'Vencido' ? 'bg-red-50 dark:bg-red-950/10' : ''} data-testid={`movimiento-row-${mov.id}`}>
                                  <TableCell>
                                    <div className="flex items-center gap-2">
                                      <Cog className="h-4 w-4 text-blue-500" />
                                      <span className="font-medium">{mov.servicio_nombre}</span>
                                    </div>
                                  </TableCell>
                                  <TableCell>
                                    <div className="flex items-center gap-2">
                                      <Users className="h-4 w-4 text-muted-foreground" />
                                      <div>
                                        <span>{mov.persona_nombre}</span>
                                        <div className="flex items-center gap-1 mt-0.5">
                                          <Badge variant={mov.persona_tipo === 'INTERNO' ? 'default' : 'outline'} className={`text-[10px] px-1 py-0 ${mov.persona_tipo === 'INTERNO' ? 'bg-blue-600' : ''}`} data-testid={`persona-tipo-badge-${mov.id}`}>
                                            {mov.persona_tipo === 'INTERNO' ? 'Interno' : 'Externo'}
                                          </Badge>
                                          {mov.unidad_interna_nombre && (
                                            <span className="text-[10px] text-muted-foreground" data-testid={`unidad-interna-label-${mov.id}`}>{mov.unidad_interna_nombre}</span>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </TableCell>
                                  <TableCell className="text-center">
                                    {mov.fecha_esperada_movimiento ? (
                                      <div className={`text-xs font-mono ${fechaClase}`}>
                                        {mov.fecha_esperada_movimiento.split('-').reverse().join('/')}
                                        {fechaAlerta && <span className="ml-1 text-[10px]">({fechaAlerta})</span>}
                                      </div>
                                    ) : <span className="text-muted-foreground text-xs">-</span>}
                                  </TableCell>
                                  <TableCell className="text-center">
                                    <div className="text-xs">
                                      {mov.fecha_inicio && (
                                        <div className="flex items-center justify-center gap-1">
                                          <Calendar className="h-3 w-3" />
                                          {mov.fecha_inicio.split('-').reverse().join('/')}
                                        </div>
                                      )}
                                      {mov.fecha_fin && (
                                        <div className="text-muted-foreground">
                                          → {mov.fecha_fin.split('-').reverse().join('/')}
                                        </div>
                                      )}
                                    </div>
                                  </TableCell>
                                  <TableCell className="text-right font-mono">
                                    {enviada}
                                  </TableCell>
                                  <TableCell className="text-right font-mono font-semibold">
                                    {recibida}
                                  </TableCell>
                                  <TableCell className="text-right font-mono">
                                    {diferencia > 0 ? (
                                      <Badge variant="destructive" className="text-xs">
                                        -{diferencia}
                                      </Badge>
                                    ) : (
                                      <span className="text-muted-foreground">-</span>
                                    )}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    <div className="flex justify-end gap-1">
                                      <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => handleOpenMovimientoDialog(mov)}
                                        data-testid={`edit-movimiento-${mov.id}`}
                                      >
                                        <Pencil className="h-4 w-4" />
                                      </Button>
                                      <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => handleGenerarGuia(mov.id)}
                                        title="Generar Guía de Remisión"
                                        data-testid={`guia-movimiento-${mov.id}`}
                                      >
                                        <FileText className="h-4 w-4 text-blue-500" />
                                      </Button>
                                      <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => handleDeleteMovimiento(mov.id)}
                                        data-testid={`delete-movimiento-${mov.id}`}
                                      >
                                        <Trash2 className="h-4 w-4 text-destructive" />
                                      </Button>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                            <TableRow className="bg-muted/30">
                              <TableCell colSpan={6} className="font-semibold">Total Recibidas</TableCell>
                              <TableCell className="text-right font-mono font-bold text-primary" colSpan={2}>
                                {getTotalCantidadMovimientos()}
                              </TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {movimientosProduccion.length} movimiento{movimientosProduccion.length !== 1 ? 's' : ''} registrado{movimientosProduccion.length !== 1 ? 's' : ''}
                      </p>
                    </>
                  ) : (
                    <div className="text-center py-6 text-muted-foreground border rounded-lg bg-muted/20">
                      <Play className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>No hay movimientos de producción</p>
                      <p className="text-xs mt-1">Registra los servicios realizados</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Incidencias (solo en modo edición) */}
            {isEditing && (
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5" />
                      Incidencias
                      {incidencias.filter(i => i.estado === 'ABIERTA').length > 0 && (
                        <Badge variant="destructive" className="ml-1">{incidencias.filter(i => i.estado === 'ABIERTA').length} abiertas</Badge>
                      )}
                    </CardTitle>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setIncidenciaForm({ motivo_id: '', comentario: '', paraliza: false });
                        setIncidenciaDialogOpen(true);
                      }}
                      data-testid="btn-nueva-incidencia"
                    >
                      <Plus className="h-4 w-4 mr-1" /> Nueva
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {incidencias.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">Sin incidencias registradas</p>
                  ) : (
                    <div className="space-y-2">
                      {incidencias.map((inc) => (
                        <div key={inc.id} className={`flex items-start gap-3 p-3 rounded-lg border ${inc.estado === 'ABIERTA' ? 'bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800' : 'bg-muted/30 border-border'}`} data-testid={`incidencia-${inc.id}`}>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant={inc.estado === 'ABIERTA' ? 'destructive' : 'secondary'} className="text-xs">
                                {inc.estado}
                              </Badge>
                              <span className="font-medium text-sm">{inc.motivo_nombre || inc.tipo}</span>
                              {inc.paraliza && (
                                <Badge variant="outline" className="text-xs border-red-300 text-red-600">
                                  Paraliza
                                </Badge>
                              )}
                              {inc.paralizacion_activa && (
                                <Badge className="bg-red-600 text-xs">En pausa</Badge>
                              )}
                              {inc.paralizacion_fin && !inc.paralizacion_activa && inc.paraliza && (
                                <Badge variant="outline" className="text-xs text-green-600 border-green-300">Reanudada</Badge>
                              )}
                            </div>
                            {inc.comentario && <p className="text-xs text-muted-foreground mt-1">{inc.comentario}</p>}
                            {inc.movimiento_servicio && <p className="text-xs text-muted-foreground">Mov: {inc.movimiento_servicio}</p>}
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {inc.fecha_hora ? new Date(inc.fecha_hora).toLocaleString('es-PE', { day:'2-digit', month:'2-digit', year:'2-digit', hour:'2-digit', minute:'2-digit' }) : ''}
                              {inc.paraliza && inc.paralizacion_inicio && (
                                <span className="ml-2">
                                  Paralizada: {new Date(inc.paralizacion_inicio).toLocaleString('es-PE', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' })}
                                  {inc.paralizacion_fin ? ` → ${new Date(inc.paralizacion_fin).toLocaleString('es-PE', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' })}` : ' (activa)'}
                                </span>
                              )}
                            </p>
                          </div>
                          <div className="flex gap-1 shrink-0">
                            {inc.estado === 'ABIERTA' && (
                              <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleResolverIncidencia(inc.id)} title="Resolver" data-testid={`resolver-incidencia-${inc.id}`}>
                                <Check className="h-4 w-4 text-green-600" />
                              </Button>
                            )}
                            <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleEliminarIncidencia(inc.id)} title="Eliminar" data-testid={`eliminar-incidencia-${inc.id}`}>
                              <Trash2 className="h-3.5 w-3.5 text-destructive" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}


            {/* Trazabilidad Unificada (solo en modo edición) */}
            {isEditing && (
              <div className="pt-2 border-t-2 border-dashed border-muted-foreground/20">
                <TrazabilidadPanel
                  registroId={id}
                  servicios={serviciosProduccion}
                  personas={personasProduccion}
                />
              </div>
            )}
          </div>

          {/* Columna derecha - Datos del modelo */}
          <div className="space-y-6">
            {/* Datos del Modelo Seleccionado */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Datos del Modelo</CardTitle>
              </CardHeader>
              <CardContent>
                {modeloSeleccionado ? (
                  <div className="space-y-4">
                    <div className="p-3 bg-primary/5 rounded-lg border border-primary/20">
                      <p className="text-xs text-muted-foreground uppercase tracking-wider">Modelo</p>
                      <p className="font-semibold text-lg">{modeloSeleccionado.nombre}</p>
                    </div>
                    
                    <Separator />
                    
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <Tag className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-xs text-muted-foreground">Marca</p>
                          <p className="font-medium">{modeloSeleccionado.marca_nombre || '-'}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <Layers className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-xs text-muted-foreground">Tipo</p>
                          <p className="font-medium">{modeloSeleccionado.tipo_nombre || '-'}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <Shirt className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-xs text-muted-foreground">Entalle</p>
                          <p className="font-medium">{modeloSeleccionado.entalle_nombre || '-'}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <Palette className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-xs text-muted-foreground">Tela</p>
                          <p className="font-medium">{modeloSeleccionado.tela_nombre || '-'}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                        <Scissors className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-xs text-muted-foreground">Hilo</p>
                          <p className="font-medium">{modeloSeleccionado.hilo_nombre || '-'}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    Selecciona un modelo para ver sus datos
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Botones de acción */}
            <div className="flex flex-col gap-3">
              <Button 
                type="submit" 
                size="lg" 
                className="w-full"
                disabled={loading}
                data-testid="btn-guardar-registro"
              >
                <Save className="h-4 w-4 mr-2" />
                {loading ? 'Guardando...' : (isEditing ? 'Actualizar Registro' : 'Crear Registro')}
              </Button>
              
              {isEditing && tallasSeleccionadas.some(t => t.cantidad > 0) && (
                <Button 
                  type="button"
                  variant="outline" 
                  size="lg"
                  className="w-full border-blue-300 text-blue-700 hover:bg-blue-50"
                  onClick={handleOpenDivision}
                  data-testid="btn-dividir-lote"
                >
                  <Scissors className="h-4 w-4 mr-2" />
                  Dividir Lote
                </Button>
              )}
              
              <Button 
                type="button"
                variant="outline" 
                size="lg"
                className="w-full"
                onClick={() => navigate('/registros')}
              >
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      </form>

      {/* Dialog para distribuir colores */}
      <Dialog open={coloresDialogOpen} onOpenChange={setColoresDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Distribución de Colores</DialogTitle>
            <DialogDescription>
              Selecciona colores y distribuye las cantidades por talla
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-4">
            {/* Selector de colores múltiple con buscador */}
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Seleccionar Colores
              </h3>
              <MultiSelectColors
                options={coloresCatalogo}
                selected={coloresSeleccionados}
                onChange={handleColoresChange}
                placeholder="Buscar y seleccionar colores..."
                searchPlaceholder="Buscar color..."
                emptyMessage="No se encontraron colores."
              />
              <p className="text-xs text-muted-foreground mt-2">
                El primer color seleccionado recibe todo el total automáticamente.
              </p>
            </div>

            <Separator />

            {/* Matriz de cantidades */}
            {tallasSeleccionadas.length > 0 && coloresSeleccionados.length > 0 ? (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                    Distribución por Talla y Color
                  </h3>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleProrratear}
                    data-testid="btn-prorratear-colores"
                  >
                    <Divide className="h-4 w-4 mr-1" />
                    Prorratear
                  </Button>
                </div>
                
                <div className="border rounded-lg overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr>
                        <th className="bg-muted/50 p-3 text-left text-xs font-semibold uppercase tracking-wider border-b min-w-[120px]">
                          Color
                        </th>
                        {tallasSeleccionadas.map((t) => (
                          <th key={t.talla_id} className="bg-muted/50 p-3 text-center text-xs font-semibold uppercase tracking-wider border-b min-w-[100px]">
                            <div>{t.talla_nombre}</div>
                            <div className="text-muted-foreground font-normal mt-1">
                              Total: {t.cantidad}
                            </div>
                          </th>
                        ))}
                        <th className="bg-muted/70 p-3 text-center text-xs font-semibold uppercase tracking-wider border-b min-w-[80px]">
                          Total
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {coloresSeleccionados.map((color, colorIndex) => (
                        <tr key={color.id} className={colorIndex % 2 === 0 ? 'bg-background' : 'bg-muted/20'}>
                          <td className="p-2 border-b">
                            <div className="flex items-center gap-2">
                              <div 
                                className="w-5 h-5 rounded border shrink-0"
                                style={{ backgroundColor: color.codigo_hex || '#ccc' }}
                              />
                              <span className="font-medium text-sm">{color.nombre}</span>
                            </div>
                          </td>
                          {tallasSeleccionadas.map((t) => (
                            <td key={t.talla_id} className="p-1 border-b">
                              <NumericInput
                                min="0"
                                value={getCantidadMatriz(color.id, t.talla_id)}
                                onChange={(e) => handleMatrizChange(color.id, t.talla_id, e.target.value)}
                                className="w-full font-mono text-center h-10"
                                placeholder="0"
                                data-testid={`matriz-${color.id}-${t.talla_id}`}
                              />
                            </td>
                          ))}
                          <td className="p-2 border-b bg-muted/30 text-center font-mono font-semibold">
                            {getTotalColor(color.id)}
                          </td>
                        </tr>
                      ))}
                      <tr className="bg-muted/50">
                        <td className="p-3 font-semibold text-sm">Asignado</td>
                        {tallasSeleccionadas.map((t) => {
                          const asignado = getTotalTallaAsignado(t.talla_id);
                          const completo = asignado === t.cantidad;
                          return (
                            <td key={t.talla_id} className="p-3 text-center font-mono font-semibold">
                              <span className={completo ? 'text-green-600' : 'text-orange-500'}>
                                {asignado}
                              </span>
                              <span className="text-muted-foreground">/{t.cantidad}</span>
                            </td>
                          );
                        })}
                        <td className="p-3 text-center font-mono font-bold bg-primary/10 text-primary">
                          {getTotalGeneralAsignado()}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground border rounded-lg bg-muted/20">
                Selecciona al menos un color para ver la matriz de distribución
              </div>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setColoresDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveColores} 
              disabled={coloresSeleccionados.length === 0}
              data-testid="btn-guardar-colores"
            >
              Guardar Distribución
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog para crear salida de inventario */}
      <Dialog open={salidaDialogOpen} onOpenChange={setSalidaDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Nueva Salida de Inventario</DialogTitle>
            <DialogDescription>
              Registrar una salida de inventario vinculada a este registro
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Item de Inventario *</Label>
              <div className="relative">
                <Input
                  placeholder="Buscar item por código o nombre..."
                  value={busquedaItem}
                  onChange={(e) => { setBusquedaItem(e.target.value); setItemSelectorOpen(true); }}
                  onFocus={() => setItemSelectorOpen(true)}
                  data-testid="search-item-inventario"
                  className="w-full"
                />
                {salidaFormData.item_id && !busquedaItem && (
                  <div className="absolute inset-0 flex items-center px-3 pointer-events-none bg-background rounded-md border">
                    <span className="font-mono mr-2 text-sm">{selectedItemInventario?.codigo}</span>
                    <span className="text-sm">{selectedItemInventario?.nombre}</span>
                    <span className="ml-auto text-xs text-muted-foreground">Stock: {selectedItemInventario?.stock_actual}</span>
                  </div>
                )}
                {salidaFormData.item_id && !busquedaItem && (
                  <button
                    type="button"
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground z-10"
                    onClick={() => { setSalidaFormData({ ...salidaFormData, item_id: '', rollo_id: '' }); setSelectedItemInventario(null); setBusquedaItem(''); }}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              {itemSelectorOpen && busquedaItem !== undefined && (
                <div className="border rounded-lg max-h-[200px] overflow-y-auto bg-background shadow-md">
                  {itemsInventario
                    .filter(item => {
                      // Excluir servicios
                      const cat = (item.categoria || item.tipo_item || '').toLowerCase();
                      if (cat === 'servicios' || cat === 'servicio') return false;
                      // Filtrar por búsqueda
                      if (!busquedaItem) return true;
                      const q = busquedaItem.toLowerCase();
                      return (item.codigo || '').toLowerCase().includes(q) || (item.nombre || '').toLowerCase().includes(q);
                    })
                    .map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center gap-2 px-3 py-2 hover:bg-muted/60 cursor-pointer text-sm transition-colors"
                        onClick={() => {
                          handleItemInventarioChange(item.id);
                          setBusquedaItem('');
                          setItemSelectorOpen(false);
                        }}
                        data-testid={`item-option-${item.id}`}
                      >
                        <span className="font-mono text-xs shrink-0">{item.codigo}</span>
                        <span className="truncate">{item.nombre}</span>
                        <span className="ml-auto text-xs text-muted-foreground shrink-0">
                          Stock: {item.stock_actual}
                        </span>
                        {item.control_por_rollos && (
                          <span className="text-xs bg-blue-100 text-blue-700 px-1 rounded shrink-0">Rollos</span>
                        )}
                      </div>
                    ))
                  }
                  {itemsInventario.filter(item => {
                    const cat = (item.categoria || item.tipo_item || '').toLowerCase();
                    if (cat === 'servicios' || cat === 'servicio') return false;
                    if (!busquedaItem) return true;
                    const q = busquedaItem.toLowerCase();
                    return (item.codigo || '').toLowerCase().includes(q) || (item.nombre || '').toLowerCase().includes(q);
                  }).length === 0 && (
                    <div className="px-3 py-4 text-center text-sm text-muted-foreground">
                      No se encontraron items
                    </div>
                  )}
                </div>
              )}
              {selectedItemInventario && !selectedItemInventario.control_por_rollos && (
                <p className="text-sm text-muted-foreground">
                  Stock disponible: <span className="font-mono font-semibold">{selectedItemInventario.stock_actual}</span> {selectedItemInventario.unidad_medida}
                </p>
              )}
            </div>
            
            {/* Selector de Rollo si aplica */}
            {selectedItemInventario?.control_por_rollos && (
              <div className="space-y-2">
                <Label>Rollo *</Label>
                <Select
                  value={salidaFormData.rollo_id}
                  onValueChange={handleRolloChange}
                >
                  <SelectTrigger data-testid="select-rollo">
                    <SelectValue placeholder="Seleccionar rollo..." />
                  </SelectTrigger>
                  <SelectContent>
                    {rollosDisponibles.length === 0 ? (
                      <SelectItem value="none" disabled>No hay rollos disponibles</SelectItem>
                    ) : (
                      rollosDisponibles.map((rollo) => (
                        <SelectItem key={rollo.id} value={rollo.id}>
                          <span className="font-mono font-semibold">{rollo.numero_rollo}</span>
                          <span className="mx-1">|</span>
                          <span>{rollo.tono || 'Sin tono'}</span>
                          <span className="mx-1">|</span>
                          <span className="font-mono text-green-600">{rollo.metraje_disponible?.toFixed(2)}m</span>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
                {selectedRollo && (
                  <div className="p-3 bg-muted/30 rounded-lg text-sm grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-muted-foreground">Rollo:</span>
                      <span className="font-mono font-semibold ml-2">{selectedRollo.numero_rollo}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Tono:</span>
                      <span className="ml-2">{selectedRollo.tono || '-'}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Ancho:</span>
                      <span className="font-mono ml-2">{selectedRollo.ancho}cm</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Disponible:</span>
                      <span className="font-mono font-semibold text-green-600 ml-2">{selectedRollo.metraje_disponible?.toFixed(2)}m</span>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            <div className="space-y-2">
              <Label htmlFor="cantidad-salida">Cantidad ({selectedItemInventario?.unidad_medida || 'unidad'}) *</Label>
              <NumericInput
                id="cantidad-salida"
                min="0.01"
                step="0.01"
                max={selectedRollo?.metraje_disponible || selectedItemInventario?.stock_actual || 999999}
                value={salidaFormData.cantidad}
                onChange={(e) => setSalidaFormData({ ...salidaFormData, cantidad: e.target.value })}
                className="font-mono"
                data-testid="input-cantidad-salida"
              />
              {selectedRollo && (
                <p className="text-xs text-muted-foreground">
                  Máximo del rollo: {selectedRollo.metraje_disponible?.toFixed(2)}m
                </p>
              )}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="observaciones-salida">Observaciones</Label>
              <Textarea
                id="observaciones-salida"
                value={salidaFormData.observaciones}
                onChange={(e) => setSalidaFormData({ ...salidaFormData, observaciones: e.target.value })}
                placeholder="Notas adicionales..."
                rows={2}
                data-testid="input-observaciones-salida"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setSalidaDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleCreateSalida}
              disabled={saving || !salidaFormData.item_id || salidaFormData.cantidad < 0.01 || (selectedItemInventario?.control_por_rollos && !salidaFormData.rollo_id)}
              data-testid="btn-guardar-salida"
            >
              {saving ? 'Guardando...' : 'Registrar Salida'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog para salida masiva de rollos */}
      <SalidaRollosDialog
        open={rollosDialogOpen}
        onOpenChange={setRollosDialogOpen}
        registroId={id}
        onSuccess={() => {
          fetchSalidasRegistro();
          axios.get(`${API}/inventario?all=true`).then(res => setItemsInventario(res.data));
        }}
      />

      {/* Dialog para crear/editar movimiento de producción */}
      <Dialog open={movimientoDialogOpen} onOpenChange={setMovimientoDialogOpen}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingMovimiento ? 'Editar Movimiento' : 'Nuevo Movimiento de Producción'}</DialogTitle>
            <DialogDescription>
              {editingMovimiento ? 'Modifica los datos del movimiento' : 'Registrar un movimiento de producción para este corte'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Servicio *</Label>
              <Popover open={servicioPopoverOpen} onOpenChange={setServicioPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={servicioPopoverOpen}
                    className="w-full justify-between font-normal"
                    data-testid="select-servicio-movimiento"
                  >
                    {movimientoFormData.servicio_id
                      ? (serviciosProduccion.find(s => s.id === movimientoFormData.servicio_id)?.nombre || 'Servicio seleccionado')
                      : 'Seleccionar servicio...'}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Buscar servicio..." />
                    <CommandList>
                      <CommandEmpty>No se encontro servicio</CommandEmpty>
                      <CommandGroup>
                        {(modeloSeleccionado?.servicios_ids?.length > 0
                          ? serviciosProduccion.filter(s => modeloSeleccionado.servicios_ids.includes(s.id))
                          : serviciosProduccion
                        ).map((servicio) => (
                          <CommandItem
                            key={servicio.id}
                            value={servicio.nombre}
                            onSelect={() => {
                              handleServicioChange(servicio.id);
                              setServicioPopoverOpen(false);
                            }}
                          >
                            <Check className={`mr-2 h-4 w-4 ${movimientoFormData.servicio_id === servicio.id ? 'opacity-100' : 'opacity-0'}`} />
                            {servicio.nombre}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
              {modeloSeleccionado?.servicios_ids?.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Mostrando servicios configurados en el modelo
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Persona *</Label>
              <Popover open={personaPopoverOpen} onOpenChange={setPersonaPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={personaPopoverOpen}
                    className="w-full justify-between font-normal"
                    disabled={!movimientoFormData.servicio_id}
                    data-testid="select-persona-movimiento"
                  >
                    {movimientoFormData.persona_id
                      ? (personasFiltradas.find(p => p.id === movimientoFormData.persona_id)?.nombre || 'Persona seleccionada')
                      : (movimientoFormData.servicio_id ? 'Seleccionar persona...' : 'Selecciona servicio primero')}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Buscar persona..." />
                    <CommandList>
                      <CommandEmpty>No se encontro persona</CommandEmpty>
                      <CommandGroup>
                        {personasFiltradas.map((persona) => {
                          const tarifaPersona = getTarifaPersonaServicio(persona.id, movimientoFormData.servicio_id);
                          return (
                            <CommandItem
                              key={persona.id}
                              value={persona.nombre}
                              onSelect={() => {
                                handlePersonaChange(persona.id);
                                setPersonaPopoverOpen(false);
                              }}
                            >
                              <Check className={`mr-2 h-4 w-4 ${movimientoFormData.persona_id === persona.id ? 'opacity-100' : 'opacity-0'}`} />
                              <span className="flex items-center gap-2">
                                {persona.nombre}
                                <span className={`text-[10px] px-1 rounded ${persona.tipo_persona === 'INTERNO' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'}`}>
                                  {persona.tipo_persona === 'INTERNO' ? 'INT' : 'EXT'}
                                </span>
                                {tarifaPersona > 0 && (
                                  <span className="text-green-600 text-xs">({formatCurrency(tarifaPersona)}/prenda)</span>
                                )}
                              </span>
                            </CommandItem>
                          );
                        })}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
              {movimientoFormData.servicio_id && personasFiltradas.length === 0 && (
                <p className="text-xs text-orange-500">
                  No hay personas asignadas a este servicio. Asígnalas en Maestros → Personas.
                </p>
              )}
              {movimientoFormData.persona_id && (() => {
                const personaSel = personasFiltradas.find(p => p.id === movimientoFormData.persona_id);
                if (!personaSel) return null;
                return (
                  <div className={`p-2 rounded-lg border text-xs ${personaSel.tipo_persona === 'INTERNO' ? 'bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800' : 'bg-gray-50 border-gray-200 dark:bg-gray-900 dark:border-gray-700'}`} data-testid="persona-tipo-info">
                    <div className="flex items-center gap-2">
                      <Badge variant={personaSel.tipo_persona === 'INTERNO' ? 'default' : 'outline'} className={`text-[10px] px-1 py-0 ${personaSel.tipo_persona === 'INTERNO' ? 'bg-blue-600' : ''}`}>
                        {personaSel.tipo_persona === 'INTERNO' ? 'Interno' : 'Externo'}
                      </Badge>
                      {personaSel.tipo_persona === 'INTERNO' && personaSel.unidad_interna_nombre && (
                        <span className="text-muted-foreground">Unidad: <strong>{personaSel.unidad_interna_nombre}</strong></span>
                      )}
                      {personaSel.tipo_persona === 'EXTERNO' && (
                        <span className="text-muted-foreground">Costo externo - sin unidad interna</span>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="fecha-inicio">Fecha Inicio</Label>
                <Input
                  id="fecha-inicio"
                  type="date"
                  value={movimientoFormData.fecha_inicio}
                  min={(() => {
                    if (!usaRuta || !etapasCompletas.length || !movimientoFormData.servicio_id) return undefined;
                    const etapaIdx = etapasCompletas.findIndex(e => e.servicio_id === movimientoFormData.servicio_id);
                    if (etapaIdx <= 0) return undefined;
                    for (let i = etapaIdx - 1; i >= 0; i--) {
                      const ea = etapasCompletas[i];
                      if (!ea.servicio_id) continue;
                      const movsAnt = movimientosProduccion.filter(m => m.servicio_id === ea.servicio_id && m.fecha_fin);
                      if (movsAnt.length > 0) {
                        return movsAnt.map(m => m.fecha_fin).sort().pop();
                      }
                    }
                    return undefined;
                  })()}
                  onChange={(e) => {
                    const val = e.target.value;
                    const updates = { fecha_inicio: val };
                    if (movimientoFormData.fecha_fin && val && movimientoFormData.fecha_fin < val) {
                      updates.fecha_fin = '';
                    }
                    if (movimientoFormData.fecha_esperada_movimiento && val && movimientoFormData.fecha_esperada_movimiento < val) {
                      updates.fecha_esperada_movimiento = '';
                    }
                    setMovimientoFormData({ ...movimientoFormData, ...updates });
                  }}
                  data-testid="input-fecha-inicio"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="fecha-fin">Fecha Fin</Label>
                <Input
                  id="fecha-fin"
                  type="date"
                  value={movimientoFormData.fecha_fin}
                  min={movimientoFormData.fecha_inicio || undefined}
                  onChange={(e) => setMovimientoFormData({ ...movimientoFormData, fecha_fin: e.target.value })}
                  data-testid="input-fecha-fin"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="fecha-esperada">Fecha Esperada</Label>
                <Input
                  id="fecha-esperada"
                  type="date"
                  value={movimientoFormData.fecha_esperada_movimiento}
                  min={movimientoFormData.fecha_inicio || undefined}
                  onChange={(e) => setMovimientoFormData({ ...movimientoFormData, fecha_esperada_movimiento: e.target.value })}
                  data-testid="input-fecha-esperada-movimiento"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="observaciones-mov">Observaciones</Label>
                <Input
                  id="observaciones-mov"
                  value={movimientoFormData.observaciones}
                  onChange={(e) => setMovimientoFormData({ ...movimientoFormData, observaciones: e.target.value })}
                  placeholder="Observaciones..."
                  data-testid="input-observaciones-movimiento"
                />
              </div>
            </div>

            {/* Cantidad enviada y recibida */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="cantidad-enviada">Cantidad Enviada</Label>
                <NumericInput
                  id="cantidad-enviada"
                  min="0"
                  value={movimientoFormData.cantidad_enviada}
                  onChange={(e) => {
                    const enviada = e.target.value;
                    setMovimientoFormData({ 
                      ...movimientoFormData, 
                      cantidad_enviada: enviada,
                      cantidad_recibida: movimientoFormData.cantidad_recibida === movimientoFormData.cantidad_enviada 
                        ? enviada 
                        : movimientoFormData.cantidad_recibida
                    });
                  }}
                  className="font-mono"
                  data-testid="input-cantidad-enviada"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cantidad-recibida">Cantidad Recibida</Label>
                <NumericInput
                  id="cantidad-recibida"
                  min="0"
                  value={movimientoFormData.cantidad_recibida}
                  onChange={(e) => setMovimientoFormData({ ...movimientoFormData, cantidad_recibida: e.target.value })}
                  className="font-mono"
                  data-testid="input-cantidad-recibida"
                />
              </div>
            </div>

            {/* Mostrar diferencia/merma si existe */}
            {calcularDiferenciaMovimiento() > 0 && (
              <div className="p-3 bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-orange-700 dark:text-orange-300">Diferencia (Merma):</span>
                  <span className="text-lg font-bold text-orange-700 dark:text-orange-300">
                    {calcularDiferenciaMovimiento()} prendas
                  </span>
                </div>
                <p className="text-xs text-orange-600 dark:text-orange-400 mt-1">
                  Esta diferencia se registrará automáticamente en Calidad/Merma
                </p>
              </div>
            )}

            {/* Tarifa editable */}
            <div className="space-y-2">
              <Label htmlFor="tarifa-movimiento">Tarifa por Prenda (S/)</Label>
              <NumericInput
                id="tarifa-movimiento"
                min="0"
                step="0.01"
                value={movimientoFormData.tarifa_aplicada}
                onChange={(e) => setMovimientoFormData({ ...movimientoFormData, tarifa_aplicada: e.target.value })}
                className="font-mono"
                placeholder="0.00"
                data-testid="input-tarifa-movimiento"
              />
              {movimientoFormData.persona_id && movimientoFormData.servicio_id && (
                <p className="text-xs text-muted-foreground">
                  Tarifa configurada para esta persona: {formatCurrency(getTarifaPersonaServicio(movimientoFormData.persona_id, movimientoFormData.servicio_id))}
                </p>
              )}
            </div>

            {/* Mostrar costo calculado */}
            {movimientoFormData.cantidad_recibida > 0 && movimientoFormData.tarifa_aplicada > 0 && (
              <div className="p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-green-700 dark:text-green-300">Costo calculado:</span>
                  <span className="text-lg font-bold text-green-700 dark:text-green-300">
                    {formatCurrency(calcularCostoMovimiento())}
                  </span>
                </div>
                <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                  {movimientoFormData.cantidad_recibida} prendas × {formatCurrency(movimientoFormData.tarifa_aplicada)}
                </p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="observaciones-movimiento">Observaciones</Label>
              <Textarea
                id="observaciones-movimiento"
                value={movimientoFormData.observaciones}
                onChange={(e) => setMovimientoFormData({ ...movimientoFormData, observaciones: e.target.value })}
                placeholder="Notas adicionales..."
                rows={2}
                data-testid="input-observaciones-movimiento"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setMovimientoDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveMovimiento}
              disabled={saving || !movimientoFormData.servicio_id || !movimientoFormData.persona_id}
              data-testid="btn-guardar-movimiento"
            >
              {saving ? 'Guardando...' : (editingMovimiento ? 'Actualizar' : 'Registrar Movimiento')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Sugerencia de cambio de estado (después de guardar movimiento) */}
      <Dialog open={!!sugerenciaEstadoDialog} onOpenChange={() => setSugerenciaEstadoDialog(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Sugerencia de Estado</DialogTitle>
            <DialogDescription>{sugerenciaEstadoDialog?.mensaje}</DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
            <Badge variant="outline">{formData.estado}</Badge>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <Badge className="bg-primary">{sugerenciaEstadoDialog?.estadoSugerido}</Badge>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSugerenciaEstadoDialog(null)} data-testid="btn-rechazar-sugerencia-estado">
              No, mantener estado
            </Button>
            <Button
              onClick={async () => {
                const estadoNuevo = sugerenciaEstadoDialog.estadoSugerido;
                setSugerenciaEstadoDialog(null);
                await autoGuardarEstado(estadoNuevo);
              }}
              data-testid="btn-aceptar-sugerencia-estado"
            >
              Sí, actualizar estado
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Sugerencia de crear movimiento (después de cambiar estado) */}
      <Dialog open={!!sugerenciaMovDialog} onOpenChange={() => setSugerenciaMovDialog(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Movimiento Faltante</DialogTitle>
            <DialogDescription>
              El estado "{formData.estado}" está vinculado al servicio "{sugerenciaMovDialog?.servicio_nombre}" y no existe un movimiento registrado. ¿Deseas crearlo ahora?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSugerenciaMovDialog(null)} data-testid="btn-rechazar-sugerencia-mov">
              No, solo cambiar estado
            </Button>
            <Button
              onClick={() => {
                const sug = sugerenciaMovDialog;
                setSugerenciaMovDialog(null);
                // Abrir diálogo de movimiento pre-llenado con el servicio
                const cantidadTotal = calcularCantidadTotalRegistro();
                setEditingMovimiento(null);
                setMovimientoFormData({
                  servicio_id: sug.servicio_id,
                  persona_id: '',
                  fecha_inicio: new Date().toISOString().split('T')[0],
                  fecha_fin: '',
                  cantidad_enviada: cantidadTotal,
                  cantidad_recibida: cantidadTotal,
                  tarifa_aplicada: 0,
                  fecha_esperada_movimiento: '',
                  observaciones: '',
                });
                // Filtrar personas por servicio
                const filtradas = personasProduccion.filter(p => {
                  const tieneEnDetalle = (p.servicios_detalle || []).some(s => s.servicio_id === sug.servicio_id);
                  const tieneEnServicios = (p.servicios || []).some(s => s.servicio_id === sug.servicio_id);
                  const tieneEnIds = (p.servicio_ids || []).includes(sug.servicio_id);
                  return tieneEnDetalle || tieneEnServicios || tieneEnIds;
                });
                setPersonasFiltradas(filtradas);
                setMovimientoDialogOpen(true);
              }}
              data-testid="btn-aceptar-sugerencia-mov"
            >
              Sí, crear movimiento
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: División de Lote */}
      {/* Dialog: Nueva Incidencia */}
      <Dialog open={incidenciaDialogOpen} onOpenChange={setIncidenciaDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Nueva Incidencia</DialogTitle>
            <DialogDescription>Registra un evento que afecta la produccion de este registro</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Motivo *</Label>
              <Select value={incidenciaForm.motivo_id} onValueChange={(v) => setIncidenciaForm(prev => ({ ...prev, motivo_id: v }))}>
                <SelectTrigger data-testid="select-motivo-incidencia"><SelectValue placeholder="Seleccionar motivo..." /></SelectTrigger>
                <SelectContent>
                  {motivosIncidencia.map(m => <SelectItem key={m.id} value={m.id}>{m.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
              {/* Crear motivo inline */}
              <div className="flex gap-2">
                <Input
                  placeholder="Nuevo motivo..."
                  value={nuevoMotivoNombre}
                  onChange={(e) => setNuevoMotivoNombre(e.target.value)}
                  className="text-sm"
                  data-testid="input-nuevo-motivo"
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleCrearMotivo(); } }}
                />
                <Button type="button" variant="outline" size="sm" onClick={handleCrearMotivo} disabled={!nuevoMotivoNombre.trim()} data-testid="btn-crear-motivo">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Comentario</Label>
              <Textarea
                value={incidenciaForm.comentario}
                onChange={(e) => setIncidenciaForm(prev => ({ ...prev, comentario: e.target.value }))}
                placeholder="Descripcion del problema..."
                rows={2}
                data-testid="input-comentario-incidencia"
              />
            </div>
            <div className="flex items-center space-x-2 p-3 border rounded-lg bg-red-50 dark:bg-red-950/20">
              <Checkbox
                id="paraliza-check"
                checked={incidenciaForm.paraliza}
                onCheckedChange={(checked) => setIncidenciaForm(prev => ({ ...prev, paraliza: checked }))}
                data-testid="checkbox-paraliza"
              />
              <div>
                <Label htmlFor="paraliza-check" className="cursor-pointer font-medium">Paraliza produccion</Label>
                <p className="text-xs text-muted-foreground">Detiene la produccion hasta que se resuelva esta incidencia</p>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIncidenciaDialogOpen(false)}>Cancelar</Button>
            <Button type="button" onClick={handleCrearIncidencia} data-testid="btn-guardar-incidencia">Registrar Incidencia</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>


      {/* Dialog: Forzar cambio de estado */}
      <Dialog open={!!forzarEstadoDialog} onOpenChange={() => setForzarEstadoDialog(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Cambio de Estado Bloqueado</DialogTitle>
            <DialogDescription>
              No se puede cambiar al estado "{forzarEstadoDialog?.nuevo_estado}" por las siguientes razones:
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 my-2">
            {(forzarEstadoDialog?.bloqueos || []).map((b, i) => (
              <p key={i} className="text-sm text-red-600 flex items-start gap-2">
                <span className="mt-0.5 shrink-0">&#x26A0;</span>
                {b}
              </p>
            ))}
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setForzarEstadoDialog(null)} data-testid="btn-cancelar-forzar-estado">
              Cancelar
            </Button>
            <Button
              variant="destructive"
              data-testid="btn-forzar-cambio-estado"
              onClick={async () => {
                const nuevoEstado = forzarEstadoDialog.nuevo_estado;
                setForzarEstadoDialog(null);
                try {
                  await axios.post(`${API}/registros/${id}/validar-cambio-estado`, { nuevo_estado: nuevoEstado, forzar: true });
                  await autoGuardarEstado(nuevoEstado);
                  toast.success(`Estado forzado a "${nuevoEstado}"`);
                } catch {
                  await autoGuardarEstado(nuevoEstado);
                }
              }}
            >
              Forzar Cambio
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={divisionDialogOpen} onOpenChange={setDivisionDialogOpen}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Dividir Lote - Corte {formData.n_corte}</DialogTitle>
            <DialogDescription>
              Asigna las cantidades que irán al nuevo lote. El registro actual se quedará con el resto.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2 text-xs font-medium text-muted-foreground border-b pb-2">
              <span>Talla</span>
              <span className="text-center">Disponible</span>
              <span className="text-center">Dividir</span>
            </div>
            {divisionTallas.map((t, idx) => (
              <div key={t.talla_id} className="grid grid-cols-3 gap-2 items-center">
                <span className="text-sm font-medium">{t.talla_nombre}</span>
                <span className="text-sm text-center text-muted-foreground">{t.cantidad_disponible}</span>
                <Input
                  type="number"
                  min="0"
                  max={t.cantidad_disponible}
                  value={t.cantidad_dividir}
                  onChange={(e) => {
                    const val = Math.min(Math.max(0, parseInt(e.target.value) || 0), t.cantidad_disponible);
                    setDivisionTallas(prev => prev.map((dt, i) => i === idx ? { ...dt, cantidad_dividir: val } : dt));
                  }}
                  className="h-8 text-sm text-center"
                  data-testid={`input-division-${t.talla_nombre}`}
                />
              </div>
            ))}
            <div className="border-t pt-2 flex justify-between text-sm">
              <span className="font-medium">Total a dividir:</span>
              <span className="font-bold text-blue-600">
                {divisionTallas.reduce((s, t) => s + t.cantidad_dividir, 0)} prendas
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="font-medium">Queda en este lote:</span>
              <span className="font-bold">
                {divisionTallas.reduce((s, t) => s + (t.cantidad_disponible - t.cantidad_dividir), 0)} prendas
              </span>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDivisionDialogOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleDividirLote}
              disabled={divisionTallas.every(t => t.cantidad_dividir === 0)}
              data-testid="btn-confirmar-division"
            >
              <Scissors className="h-4 w-4 mr-2" />
              Confirmar División
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

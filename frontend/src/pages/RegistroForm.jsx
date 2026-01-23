import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
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
import { ArrowLeft, Save, AlertTriangle, Trash2, Tag, Layers, Shirt, Palette, Scissors, Package, Plus, ArrowUpCircle, Cog, Users, Calendar, Play, Pencil, FileText, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { SalidaRollosDialog } from '../components/SalidaRollosDialog';
import { MultiSelectColors } from '../components/MultiSelectColors';
import { Textarea } from '../components/ui/textarea';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const RegistroForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEditing = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  
  const [formData, setFormData] = useState({
    n_corte: '',
    modelo_id: '',
    curva: '',
    estado: 'Para Corte',
    urgente: false,
    hilo_especifico_id: '',
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

  // Datos para movimientos de producción
  const [movimientosProduccion, setMovimientosProduccion] = useState([]);
  const [serviciosProduccion, setServiciosProduccion] = useState([]);
  const [personasProduccion, setPersonasProduccion] = useState([]);
  const [movimientoDialogOpen, setMovimientoDialogOpen] = useState(false);
  const [editingMovimiento, setEditingMovimiento] = useState(null);
  const [personasFiltradas, setPersonasFiltradas] = useState([]);
  const [movimientoFormData, setMovimientoFormData] = useState({
    servicio_id: '',
    persona_id: '',
    fecha_inicio: '',
    fecha_fin: '',
    cantidad_enviada: 0,
    cantidad_recibida: 0,
    tarifa_aplicada: 0,
    observaciones: '',
  });

  // Hilos específicos disponibles
  const [hilosEspecificos, setHilosEspecificos] = useState([]);

  // Cargar datos relacionados
  const fetchRelatedData = async () => {
    try {
      const [modelosRes, estadosRes, tallasRes, coloresRes, inventarioRes, serviciosRes, personasRes, hilosEspRes] = await Promise.all([
        axios.get(`${API}/modelos`),
        axios.get(`${API}/estados`),
        axios.get(`${API}/tallas-catalogo`),
        axios.get(`${API}/colores-catalogo`),
        axios.get(`${API}/inventario`),
        axios.get(`${API}/servicios-produccion`),
        axios.get(`${API}/personas-produccion?activo=true`),
        axios.get(`${API}/hilos-especificos`),
      ]);
      setModelos(modelosRes.data);
      setEstados(estadosRes.data.estados);
      setEstadosGlobales(estadosRes.data.estados);
      setTallasCatalogo(tallasRes.data);
      setColoresCatalogo(coloresRes.data);
      setItemsInventario(inventarioRes.data);
      setServiciosProduccion(serviciosRes.data);
      setPersonasProduccion(personasRes.data);
      setHilosEspecificos(hilosEspRes.data);
    } catch (error) {
      toast.error('Error al cargar datos');
    }
  };

  // Cargar estados dinámicos según el registro o modelo
  const fetchEstadosDisponibles = async (registroId) => {
    if (!registroId) {
      setEstados(estadosGlobales);
      setUsaRuta(false);
      setRutaNombre('');
      setSiguienteEstado(null);
      return;
    }
    try {
      const response = await axios.get(`${API}/registros/${registroId}/estados-disponibles`);
      const data = response.data;
      setEstados(data.estados || estadosGlobales);
      setUsaRuta(data.usa_ruta || false);
      setRutaNombre(data.ruta_nombre || '');
      setSiguienteEstado(data.siguiente_estado || null);
    } catch (error) {
      console.error('Error fetching estados disponibles:', error);
      setEstados(estadosGlobales);
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
      const response = await axios.get(`${API}/movimientos-produccion?registro_id=${id}`);
      setMovimientosProduccion(response.data);
    } catch (error) {
      console.error('Error fetching movimientos:', error);
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
      });
      
      setTallasSeleccionadas(registro.tallas || []);
      setDistribucionColores(registro.distribucion_colores || []);
      
      // Buscar modelo seleccionado
      const modelosRes = await axios.get(`${API}/modelos`);
      const modelo = modelosRes.data.find(m => m.id === registro.modelo_id);
      setModeloSeleccionado(modelo || null);
      
      // Cargar estados disponibles para este registro
      await fetchEstadosDisponibles(id);
      
    } catch (error) {
      toast.error('Error al cargar registro');
      navigate('/registros');
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    fetchRelatedData();
    fetchRegistro();
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchSalidasRegistro();
      fetchMovimientosProduccion();
    }
  }, [id]);

  // Cuando cambia el modelo seleccionado
  const handleModeloChange = (modeloId) => {
    setFormData({ ...formData, modelo_id: modeloId });
    const modelo = modelos.find(m => m.id === modeloId);
    setModeloSeleccionado(modelo || null);
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

  const handleCreateSalida = async () => {
    if (!salidaFormData.item_id || salidaFormData.cantidad < 0.01) {
      toast.error('Selecciona un item y cantidad válida');
      return;
    }
    
    // Si es item con rollos, debe seleccionar un rollo
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
      // Refrescar inventario para actualizar stock
      const inventarioRes = await axios.get(`${API}/inventario`);
      setItemsInventario(inventarioRes.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear salida');
    }
  };

  const handleDeleteSalida = async (salidaId) => {
    try {
      await axios.delete(`${API}/inventario-salidas/${salidaId}`);
      toast.success('Salida eliminada');
      fetchSalidasRegistro();
      // Refrescar inventario
      const inventarioRes = await axios.get(`${API}/inventario`);
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
        observaciones: '',
      });
      setPersonasFiltradas([]);
    }
    setMovimientoDialogOpen(true);
  };

  const handleServicioChange = (servicioId) => {
    // Filtrar personas que tienen asignado este servicio (nueva estructura)
    const filtradas = personasProduccion.filter(p => {
      // Verificar en servicios_detalle (formato con detalles)
      const tieneEnDetalle = (p.servicios_detalle || []).some(s => s.servicio_id === servicioId);
      // Verificar en servicios (formato nuevo)
      const tieneEnServicios = (p.servicios || []).some(s => s.servicio_id === servicioId);
      // Formato antiguo (servicio_ids)
      const tieneEnIds = (p.servicio_ids || []).includes(servicioId);
      return tieneEnDetalle || tieneEnServicios || tieneEnIds;
    });
    setPersonasFiltradas(filtradas);
    
    setMovimientoFormData({ 
      ...movimientoFormData, 
      servicio_id: servicioId,
      persona_id: '',
      tarifa_aplicada: 0  // Se pre-llenará cuando se seleccione persona
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

  const handleSaveMovimiento = async () => {
    if (!movimientoFormData.servicio_id || !movimientoFormData.persona_id) {
      toast.error('Selecciona servicio y persona');
      return;
    }

    try {
      if (editingMovimiento) {
        // Actualizar
        const payload = {
          ...movimientoFormData,
          registro_id: id,
        };
        await axios.put(`${API}/movimientos-produccion/${editingMovimiento.id}`, payload);
        toast.success('Movimiento actualizado');
      } else {
        // Crear
        const payload = {
          ...movimientoFormData,
          registro_id: id,
        };
        await axios.post(`${API}/movimientos-produccion`, payload);
        toast.success('Movimiento registrado');
      }
      setMovimientoDialogOpen(false);
      setEditingMovimiento(null);
      fetchMovimientosProduccion();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar movimiento');
    }
  };

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
      const response = await axios.post(`${API}/guias-remision/desde-movimiento/${movimientoId}`);
      const guia = response.data;
      toast.success(`Guía ${guia.numero} lista para imprimir`);
      
      // Abrir en nueva ventana para imprimir
      const printWindow = window.open('', '_blank');
      printWindow.document.write(`
        <html>
          <head>
            <title>Guía de Remisión ${guia.numero}</title>
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
              <div class="numero">${guia.numero}</div>
              <div class="fecha">Fecha: ${guia.fecha_emision}</div>
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
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const payload = {
        ...formData,
        tallas: tallasSeleccionadas,
        distribucion_colores: distribucionColores,
      };
      
      if (isEditing) {
        await axios.put(`${API}/registros/${id}`, payload);
        toast.success('Registro actualizado');
      } else {
        await axios.post(`${API}/registros`, payload);
        toast.success('Registro creado');
      }
      
      navigate('/registros');
    } catch (error) {
      toast.error('Error al guardar registro');
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
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            {isEditing ? 'Editar Registro' : 'Nuevo Registro'}
          </h2>
          <p className="text-muted-foreground">
            {isEditing ? `Editando registro ${formData.n_corte}` : 'Crear un nuevo registro de producción'}
          </p>
        </div>
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
                    <Select
                      value={formData.modelo_id}
                      onValueChange={handleModeloChange}
                    >
                      <SelectTrigger data-testid="select-modelo">
                        <SelectValue placeholder="Seleccionar modelo" />
                      </SelectTrigger>
                      <SelectContent>
                        {modelos.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      Estado
                      {usaRuta && rutaNombre && (
                        <Badge variant="outline" className="text-xs font-normal">
                          Ruta: {rutaNombre}
                        </Badge>
                      )}
                    </Label>
                    <Select
                      value={formData.estado}
                      onValueChange={(value) => setFormData({ ...formData, estado: value })}
                    >
                      <SelectTrigger data-testid="select-estado">
                        <SelectValue placeholder="Seleccionar estado" />
                      </SelectTrigger>
                      <SelectContent>
                        {estados.map((e) => (
                          <SelectItem key={e} value={e}>
                            {e}
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

                {/* Hilos Asignados (solo en modo edición) */}
                {isEditing && (
                  <>
                    <Separator className="my-4" />
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label className="flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-primary" />
                          Hilos Específicos Asignados
                        </Label>
                      </div>
                      
                      <div className="flex gap-2">
                        <Select onValueChange={handleAddHilo}>
                          <SelectTrigger className="flex-1" data-testid="select-agregar-hilo">
                            <SelectValue placeholder="Agregar hilo específico..." />
                          </SelectTrigger>
                          <SelectContent>
                            {hilosEspecificos
                              .filter(h => !hilosAsignados.find(ha => ha.hilo_especifico_id === h.id))
                              .map((h) => (
                                <SelectItem key={h.id} value={h.id}>
                                  {h.nombre}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                      </div>

                      {hilosAsignados.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {hilosAsignados.map((ha) => (
                            <Badge 
                              key={ha.id} 
                              variant="secondary" 
                              className="flex items-center gap-1 px-3 py-1"
                            >
                              <Sparkles className="h-3 w-3" />
                              {ha.hilo_especifico_nombre}
                              <button
                                type="button"
                                onClick={() => handleRemoveHilo(ha.id)}
                                className="ml-1 hover:text-destructive"
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          No hay hilos específicos asignados a este registro
                        </p>
                      )}
                    </div>
                  </>
                )}
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
                              <Input
                                type="number"
                                min="0"
                                value={t.cantidad || ''}
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
                            {salidasRegistro.map((salida) => (
                              <TableRow key={salida.id} data-testid={`salida-row-${salida.id}`}>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    <ArrowUpCircle className="h-4 w-4 text-red-500" />
                                    <div>
                                      <p className="font-medium">{salida.item_nombre}</p>
                                      <p className="text-xs text-muted-foreground font-mono">{salida.item_codigo}</p>
                                    </div>
                                  </div>
                                </TableCell>
                                <TableCell className="text-right font-mono font-semibold">
                                  {salida.cantidad}
                                </TableCell>
                                <TableCell className="text-right font-mono">
                                  {formatCurrency(salida.costo_total)}
                                </TableCell>
                                <TableCell>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleDeleteSalida(salida.id)}
                                    data-testid={`delete-salida-${salida.id}`}
                                  >
                                    <Trash2 className="h-4 w-4 text-destructive" />
                                  </Button>
                                </TableCell>
                              </TableRow>
                            ))}
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
                              return (
                                <TableRow key={mov.id} data-testid={`movimiento-row-${mov.id}`}>
                                  <TableCell>
                                    <div className="flex items-center gap-2">
                                      <Cog className="h-4 w-4 text-blue-500" />
                                      <span className="font-medium">{mov.servicio_nombre}</span>
                                    </div>
                                  </TableCell>
                                  <TableCell>
                                    <div className="flex items-center gap-2">
                                      <Users className="h-4 w-4 text-muted-foreground" />
                                      <span>{mov.persona_nombre}</span>
                                    </div>
                                  </TableCell>
                                  <TableCell className="text-center">
                                    <div className="text-xs">
                                      {mov.fecha_inicio && (
                                        <div className="flex items-center justify-center gap-1">
                                          <Calendar className="h-3 w-3" />
                                          {mov.fecha_inicio}
                                        </div>
                                      )}
                                      {mov.fecha_fin && (
                                        <div className="text-muted-foreground">
                                          → {mov.fecha_fin}
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
                              <TableCell colSpan={5} className="font-semibold">Total Recibidas</TableCell>
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
                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                  Distribución por Talla y Color
                </h3>
                
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
                              <Input
                                type="number"
                                min="0"
                                value={getCantidadMatriz(color.id, t.talla_id) || ''}
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
              <Select
                value={salidaFormData.item_id}
                onValueChange={handleItemInventarioChange}
              >
                <SelectTrigger data-testid="select-item-inventario">
                  <SelectValue placeholder="Seleccionar item..." />
                </SelectTrigger>
                <SelectContent>
                  {itemsInventario.map((item) => (
                    <SelectItem key={item.id} value={item.id}>
                      <span className="font-mono mr-2">{item.codigo}</span>
                      {item.nombre}
                      <span className="ml-2 text-muted-foreground">(Stock: {item.stock_actual})</span>
                      {item.control_por_rollos && (
                        <span className="ml-1 text-xs bg-blue-100 text-blue-700 px-1 rounded">Rollos</span>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
              <Input
                id="cantidad-salida"
                type="number"
                min="0.01"
                step="0.01"
                max={selectedRollo?.metraje_disponible || selectedItemInventario?.stock_actual || 999999}
                value={salidaFormData.cantidad}
                onChange={(e) => setSalidaFormData({ ...salidaFormData, cantidad: parseFloat(e.target.value) || 1 })}
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
              disabled={!salidaFormData.item_id || salidaFormData.cantidad < 0.01 || (selectedItemInventario?.control_por_rollos && !salidaFormData.rollo_id)}
              data-testid="btn-guardar-salida"
            >
              Registrar Salida
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
          axios.get(`${API}/inventario`).then(res => setItemsInventario(res.data));
        }}
      />

      {/* Dialog para crear/editar movimiento de producción */}
      <Dialog open={movimientoDialogOpen} onOpenChange={setMovimientoDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingMovimiento ? 'Editar Movimiento' : 'Nuevo Movimiento de Producción'}</DialogTitle>
            <DialogDescription>
              {editingMovimiento ? 'Modifica los datos del movimiento' : 'Registrar un movimiento de producción para este corte'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Servicio *</Label>
              <Select
                value={movimientoFormData.servicio_id}
                onValueChange={handleServicioChange}
              >
                <SelectTrigger data-testid="select-servicio-movimiento">
                  <SelectValue placeholder="Seleccionar servicio..." />
                </SelectTrigger>
                <SelectContent>
                  {(modeloSeleccionado?.servicios_ids?.length > 0
                    ? serviciosProduccion.filter(s => modeloSeleccionado.servicios_ids.includes(s.id))
                    : serviciosProduccion
                  ).map((servicio) => (
                    <SelectItem key={servicio.id} value={servicio.id}>
                      {servicio.nombre}
                    </SelectItem>
                  ))}
                  {modeloSeleccionado?.servicios_ids?.length > 0 && 
                   serviciosProduccion.filter(s => modeloSeleccionado.servicios_ids.includes(s.id)).length === 0 && (
                    <SelectItem value="none" disabled>
                      No hay servicios configurados en el modelo
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
              {modeloSeleccionado?.servicios_ids?.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Mostrando servicios configurados en el modelo
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Persona *</Label>
              <Select
                value={movimientoFormData.persona_id}
                onValueChange={handlePersonaChange}
                disabled={!movimientoFormData.servicio_id}
              >
                <SelectTrigger data-testid="select-persona-movimiento">
                  <SelectValue placeholder={movimientoFormData.servicio_id ? "Seleccionar persona..." : "Selecciona servicio primero"} />
                </SelectTrigger>
                <SelectContent>
                  {personasFiltradas.length === 0 ? (
                    <SelectItem value="none" disabled>
                      No hay personas asignadas a este servicio
                    </SelectItem>
                  ) : (
                    personasFiltradas.map((persona) => {
                      const tarifaPersona = getTarifaPersonaServicio(persona.id, movimientoFormData.servicio_id);
                      return (
                        <SelectItem key={persona.id} value={persona.id}>
                          {persona.nombre}
                          {tarifaPersona > 0 && (
                            <span className="ml-2 text-green-600">({formatCurrency(tarifaPersona)}/prenda)</span>
                          )}
                        </SelectItem>
                      );
                    })
                  )}
                </SelectContent>
              </Select>
              {movimientoFormData.servicio_id && personasFiltradas.length === 0 && (
                <p className="text-xs text-orange-500">
                  No hay personas asignadas a este servicio. Asígnalas en Maestros → Personas.
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="fecha-inicio">Fecha Inicio</Label>
                <Input
                  id="fecha-inicio"
                  type="date"
                  value={movimientoFormData.fecha_inicio}
                  onChange={(e) => setMovimientoFormData({ ...movimientoFormData, fecha_inicio: e.target.value })}
                  data-testid="input-fecha-inicio"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="fecha-fin">Fecha Fin</Label>
                <Input
                  id="fecha-fin"
                  type="date"
                  value={movimientoFormData.fecha_fin}
                  onChange={(e) => setMovimientoFormData({ ...movimientoFormData, fecha_fin: e.target.value })}
                  data-testid="input-fecha-fin"
                />
              </div>
            </div>

            {/* Cantidad enviada y recibida */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="cantidad-enviada">Cantidad Enviada</Label>
                <Input
                  id="cantidad-enviada"
                  type="number"
                  min="0"
                  value={movimientoFormData.cantidad_enviada}
                  onChange={(e) => {
                    const enviada = parseInt(e.target.value) || 0;
                    setMovimientoFormData({ 
                      ...movimientoFormData, 
                      cantidad_enviada: enviada,
                      // Por defecto, recibida = enviada
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
                <Input
                  id="cantidad-recibida"
                  type="number"
                  min="0"
                  value={movimientoFormData.cantidad_recibida}
                  onChange={(e) => setMovimientoFormData({ ...movimientoFormData, cantidad_recibida: parseInt(e.target.value) || 0 })}
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
              <Input
                id="tarifa-movimiento"
                type="number"
                min="0"
                step="0.01"
                value={movimientoFormData.tarifa_aplicada}
                onChange={(e) => setMovimientoFormData({ ...movimientoFormData, tarifa_aplicada: parseFloat(e.target.value) || 0 })}
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
              disabled={!movimientoFormData.servicio_id || !movimientoFormData.persona_id}
              data-testid="btn-guardar-movimiento"
            >
              {editingMovimiento ? 'Actualizar' : 'Registrar Movimiento'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

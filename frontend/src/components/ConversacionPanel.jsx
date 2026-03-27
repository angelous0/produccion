import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import {
  MessageSquare, Reply, Send, ChevronDown, ChevronUp, Trash2,
  Pin, PinOff, AlertTriangle, Clock, CheckCircle2, MoreHorizontal,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ESTADO_CONFIG = {
  normal:     { label: 'Normal',     border: 'border-border',       bg: '',               badge: null,        icon: null },
  importante: { label: 'Importante', border: 'border-red-400',      bg: 'bg-red-50/60',   badge: 'bg-red-100 text-red-700',    icon: AlertTriangle },
  pendiente:  { label: 'Pendiente',  border: 'border-amber-400',    bg: 'bg-amber-50/60', badge: 'bg-amber-100 text-amber-700', icon: Clock },
  resuelto:   { label: 'Resuelto',   border: 'border-green-400',    bg: 'bg-green-50/40', badge: 'bg-green-100 text-green-700', icon: CheckCircle2 },
};

function timeAgo(dateStr) {
  const d = new Date(dateStr);
  const now = new Date();
  const mins = Math.floor((now - d) / 60000);
  if (mins < 1) return 'ahora';
  if (mins < 60) return `hace ${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `hace ${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `hace ${days}d`;
  return d.toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

function formatFecha(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: '2-digit' }) +
    ' ' + d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
}

export const ConversacionPanel = ({ registroId, usuario }) => {
  const [mensajes, setMensajes] = useState([]);
  const [nuevoMensaje, setNuevoMensaje] = useState('');
  const [nuevoEstado, setNuevoEstado] = useState('normal');
  const [respondiendo, setRespondiendo] = useState(null);
  const [respuestaTexto, setRespuestaTexto] = useState('');
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const listRef = useRef(null);

  const fetchMensajes = async () => {
    try {
      const res = await axios.get(`${API}/registros/${registroId}/conversacion`);
      setMensajes(res.data);
    } catch { /* silent */ }
  };

  useEffect(() => {
    if (registroId) fetchMensajes();
  }, [registroId]);

  const enviarMensaje = async (texto, padreId = null) => {
    if (!texto.trim()) return;
    setLoading(true);
    try {
      await axios.post(`${API}/registros/${registroId}/conversacion`, {
        autor: usuario || 'Sistema',
        mensaje: texto.trim(),
        mensaje_padre_id: padreId,
        estado: padreId ? 'normal' : nuevoEstado,
      });
      await fetchMensajes();
      if (padreId) {
        setRespondiendo(null);
        setRespuestaTexto('');
      } else {
        setNuevoMensaje('');
        setNuevoEstado('normal');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al enviar mensaje');
    } finally {
      setLoading(false);
    }
  };

  const actualizarMensaje = async (msgId, data) => {
    try {
      await axios.patch(`${API}/conversacion/${msgId}`, data);
      await fetchMensajes();
    } catch {
      toast.error('Error al actualizar');
    }
  };

  const eliminarMensaje = async (msgId) => {
    try {
      await axios.delete(`${API}/conversacion/${msgId}`);
      await fetchMensajes();
      toast.success('Mensaje eliminado');
    } catch {
      toast.error('Error al eliminar');
    }
  };

  const raices = mensajes.filter(m => !m.mensaje_padre_id);
  const respuestasPor = {};
  mensajes.filter(m => m.mensaje_padre_id).forEach(m => {
    if (!respuestasPor[m.mensaje_padre_id]) respuestasPor[m.mensaje_padre_id] = [];
    respuestasPor[m.mensaje_padre_id].push(m);
  });

  const fijados = raices.filter(m => m.fijado);
  const noFijados = raices.filter(m => !m.fijado);

  const renderMensaje = (msg, esRespuesta = false) => {
    const cfg = ESTADO_CONFIG[msg.estado] || ESTADO_CONFIG.normal;
    const EstadoIcon = cfg.icon;

    return (
      <div
        key={msg.id}
        className={`group rounded-lg border ${cfg.border} ${cfg.bg} ${esRespuesta ? 'p-2.5' : 'p-3'} transition-colors ${esRespuesta ? 'border-dashed' : ''}`}
        data-testid={esRespuesta ? `reply-${msg.id}` : `msg-${msg.id}`}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              {esRespuesta && <Reply className="h-3 w-3 text-muted-foreground shrink-0" />}
              {msg.fijado && <Pin className="h-3 w-3 text-blue-500 shrink-0" />}
              <span className="text-sm font-semibold">{msg.autor}</span>
              <span className="text-xs text-muted-foreground" title={formatFecha(msg.created_at)}>
                {timeAgo(msg.created_at)}
              </span>
              {cfg.badge && (
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${cfg.badge} flex items-center gap-1`}>
                  {EstadoIcon && <EstadoIcon className="h-2.5 w-2.5" />}
                  {cfg.label}
                </span>
              )}
            </div>
            <p className={`text-sm whitespace-pre-wrap break-words ${esRespuesta ? 'ml-5' : ''}`}>{msg.mensaje}</p>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button" variant="ghost" size="icon"
                className="h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                data-testid={`msg-actions-${msg.id}`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              {!esRespuesta && (
                <DropdownMenuItem onClick={() => { setRespondiendo(respondiendo === msg.id ? null : msg.id); setRespuestaTexto(''); }}>
                  <Reply className="h-3.5 w-3.5 mr-2" /> Responder
                </DropdownMenuItem>
              )}
              {!esRespuesta && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => actualizarMensaje(msg.id, { estado: 'importante' })} disabled={msg.estado === 'importante'}>
                    <AlertTriangle className="h-3.5 w-3.5 mr-2 text-red-500" /> Importante
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => actualizarMensaje(msg.id, { estado: 'pendiente' })} disabled={msg.estado === 'pendiente'}>
                    <Clock className="h-3.5 w-3.5 mr-2 text-amber-500" /> Pendiente
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => actualizarMensaje(msg.id, { estado: 'resuelto' })} disabled={msg.estado === 'resuelto'}>
                    <CheckCircle2 className="h-3.5 w-3.5 mr-2 text-green-500" /> Resuelto
                  </DropdownMenuItem>
                  {msg.estado !== 'normal' && (
                    <DropdownMenuItem onClick={() => actualizarMensaje(msg.id, { estado: 'normal' })}>
                      <MessageSquare className="h-3.5 w-3.5 mr-2" /> Normal
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => actualizarMensaje(msg.id, { fijado: !msg.fijado })}>
                    {msg.fijado
                      ? <><PinOff className="h-3.5 w-3.5 mr-2" /> Desfijar</>
                      : <><Pin className="h-3.5 w-3.5 mr-2" /> Fijar</>
                    }
                  </DropdownMenuItem>
                </>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={() => eliminarMensaje(msg.id)}>
                <Trash2 className="h-3.5 w-3.5 mr-2" /> Eliminar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    );
  };

  const estadoBtnClass = (est) =>
    nuevoEstado === est
      ? 'ring-2 ring-offset-1 ' + (est === 'importante' ? 'ring-red-400' : est === 'pendiente' ? 'ring-amber-400' : est === 'resuelto' ? 'ring-green-400' : 'ring-border')
      : '';

  return (
    <Card data-testid="conversacion-panel" onSubmit={(e) => e.stopPropagation()}>
      <CardHeader className="pb-3 cursor-pointer" onClick={() => setCollapsed(!collapsed)}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Conversacion
            {mensajes.length > 0 && (
              <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                {mensajes.length}
              </span>
            )}
            {fijados.length > 0 && (
              <span className="text-xs font-normal text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Pin className="h-2.5 w-2.5" /> {fijados.length}
              </span>
            )}
          </CardTitle>
          {collapsed ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronUp className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>

      {!collapsed && (
        <CardContent className="space-y-3 pt-0">
          {raices.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">Sin mensajes. Inicia la conversacion.</p>
          )}

          <div className="space-y-2 max-h-[450px] overflow-y-auto pr-1" ref={listRef}>
            {/* Fijados arriba */}
            {fijados.length > 0 && (
              <div className="space-y-1.5 pb-2 mb-2 border-b border-dashed">
                {fijados.map(msg => (
                  <div key={msg.id} className="space-y-1">
                    {renderMensaje(msg)}
                    {respuestasPor[msg.id]?.map(r => (
                      <div key={r.id} className="ml-6">{renderMensaje(r, true)}</div>
                    ))}
                    {respondiendo === msg.id && renderReplyInput(msg.id)}
                  </div>
                ))}
              </div>
            )}

            {/* Resto cronologico */}
            {noFijados.map(msg => (
              <div key={msg.id} className="space-y-1">
                {renderMensaje(msg)}
                {respuestasPor[msg.id]?.map(r => (
                  <div key={r.id} className="ml-6">{renderMensaje(r, true)}</div>
                ))}
                {respondiendo === msg.id && renderReplyInput(msg.id)}
              </div>
            ))}
          </div>

          {/* Input nuevo mensaje */}
          <div className="pt-2 border-t space-y-2" data-testid="new-message-input">
            <div className="flex gap-1.5">
              {['normal', 'importante', 'pendiente', 'resuelto'].map(est => {
                const c = ESTADO_CONFIG[est];
                const Icon = c.icon;
                return (
                  <Button
                    key={est}
                    type="button"
                    variant={nuevoEstado === est ? 'default' : 'outline'}
                    size="sm"
                    className={`h-7 text-xs gap-1 ${estadoBtnClass(est)}`}
                    onClick={() => setNuevoEstado(est)}
                    data-testid={`estado-btn-${est}`}
                  >
                    {Icon && <Icon className="h-3 w-3" />}
                    {c.label}
                  </Button>
                );
              })}
            </div>
            <div className="flex gap-2">
              <Textarea
                value={nuevoMensaje}
                onChange={(e) => setNuevoMensaje(e.target.value)}
                placeholder="Escribe un mensaje..."
                rows={1}
                className="text-sm resize-none"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.stopPropagation(); enviarMensaje(nuevoMensaje); }
                }}
              />
              <Button
                type="button" size="icon" className="shrink-0 h-9 w-9"
                disabled={!nuevoMensaje.trim() || loading}
                onClick={() => enviarMensaje(nuevoMensaje)}
                data-testid="btn-send-message"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );

  function renderReplyInput(parentId) {
    return (
      <div className="ml-6 flex gap-2" data-testid={`reply-input-${parentId}`}>
        <Textarea
          value={respuestaTexto}
          onChange={(e) => setRespuestaTexto(e.target.value)}
          placeholder="Escribe tu respuesta..."
          rows={1}
          className="text-sm resize-none"
          autoFocus
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.stopPropagation(); enviarMensaje(respuestaTexto, parentId); }
            if (e.key === 'Escape') setRespondiendo(null);
          }}
        />
        <Button
          type="button" size="icon" className="shrink-0 h-9 w-9"
          disabled={!respuestaTexto.trim() || loading}
          onClick={() => enviarMensaje(respuestaTexto, parentId)}
          data-testid={`btn-send-reply-${parentId}`}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    );
  }
};

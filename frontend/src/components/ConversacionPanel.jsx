import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { MessageSquare, Reply, Send, ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function timeAgo(dateStr) {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now - d;
  const mins = Math.floor(diffMs / 60000);
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
  const [respondiendo, setRespondiendo] = useState(null);
  const [respuestaTexto, setRespuestaTexto] = useState('');
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const bottomRef = useRef(null);

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
      });
      await fetchMensajes();
      if (padreId) {
        setRespondiendo(null);
        setRespuestaTexto('');
      } else {
        setNuevoMensaje('');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al enviar mensaje');
    } finally {
      setLoading(false);
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

  // Agrupar: mensajes raiz y sus respuestas
  const raices = mensajes.filter(m => !m.mensaje_padre_id);
  const respuestasPor = {};
  mensajes.filter(m => m.mensaje_padre_id).forEach(m => {
    if (!respuestasPor[m.mensaje_padre_id]) respuestasPor[m.mensaje_padre_id] = [];
    respuestasPor[m.mensaje_padre_id].push(m);
  });

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
          </CardTitle>
          {collapsed ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronUp className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>

      {!collapsed && (
        <CardContent className="space-y-3 pt-0">
          {/* Lista de mensajes */}
          {raices.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">Sin mensajes. Inicia la conversacion.</p>
          )}

          <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
            {raices.map(msg => (
              <div key={msg.id} className="space-y-1" data-testid={`msg-${msg.id}`}>
                {/* Mensaje raiz */}
                <div className="group rounded-lg border bg-card p-3 hover:bg-muted/30 transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold">{msg.autor}</span>
                        <span className="text-xs text-muted-foreground" title={formatFecha(msg.created_at)}>
                          {timeAgo(msg.created_at)}
                        </span>
                      </div>
                      <p className="text-sm whitespace-pre-wrap break-words">{msg.mensaje}</p>
                    </div>
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <Button
                        type="button" variant="ghost" size="icon" className="h-7 w-7"
                        onClick={() => { setRespondiendo(respondiendo === msg.id ? null : msg.id); setRespuestaTexto(''); }}
                        data-testid={`btn-reply-${msg.id}`}
                      >
                        <Reply className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        type="button" variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:text-destructive"
                        onClick={() => eliminarMensaje(msg.id)}
                        data-testid={`btn-delete-msg-${msg.id}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Respuestas */}
                {respuestasPor[msg.id]?.map(resp => (
                  <div key={resp.id} className="ml-6 group rounded-lg border border-dashed bg-muted/20 p-2.5 hover:bg-muted/40 transition-colors" data-testid={`reply-${resp.id}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <Reply className="h-3 w-3 text-muted-foreground" />
                          <span className="text-sm font-semibold">{resp.autor}</span>
                          <span className="text-xs text-muted-foreground" title={formatFecha(resp.created_at)}>
                            {timeAgo(resp.created_at)}
                          </span>
                        </div>
                        <p className="text-sm whitespace-pre-wrap break-words ml-5">{resp.mensaje}</p>
                      </div>
                      <Button
                        type="button" variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive shrink-0"
                        onClick={() => eliminarMensaje(resp.id)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}

                {/* Input de respuesta inline */}
                {respondiendo === msg.id && (
                  <div className="ml-6 flex gap-2" data-testid={`reply-input-${msg.id}`}>
                    <Textarea
                      value={respuestaTexto}
                      onChange={(e) => setRespuestaTexto(e.target.value)}
                      placeholder="Escribe tu respuesta..."
                      rows={1}
                      className="text-sm resize-none"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.stopPropagation(); enviarMensaje(respuestaTexto, msg.id); }
                        if (e.key === 'Escape') setRespondiendo(null);
                      }}
                    />
                    <Button
                      type="button" size="icon" className="shrink-0 h-9 w-9"
                      disabled={!respuestaTexto.trim() || loading}
                      onClick={() => enviarMensaje(respuestaTexto, msg.id)}
                      data-testid={`btn-send-reply-${msg.id}`}
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input nuevo mensaje */}
          <div className="flex gap-2 pt-2 border-t" data-testid="new-message-input">
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
        </CardContent>
      )}
    </Card>
  );
};

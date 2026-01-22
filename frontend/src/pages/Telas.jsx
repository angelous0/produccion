import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Plus, Pencil, Trash2, Check, ChevronsUpDown } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '../components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const Telas = () => {
  const [items, setItems] = useState([]);
  const [entalles, setEntalles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({ nombre: '', entalle_ids: [] });
  const [popoverOpen, setPopoverOpen] = useState(false);

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API}/telas`);
      setItems(response.data);
    } catch (error) {
      toast.error('Error al cargar telas');
    } finally {
      setLoading(false);
    }
  };

  const fetchEntalles = async () => {
    try {
      const response = await axios.get(`${API}/entalles`);
      setEntalles(response.data);
    } catch (error) {
      console.error('Error fetching entalles:', error);
    }
  };

  useEffect(() => {
    fetchItems();
    fetchEntalles();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingItem) {
        await axios.put(`${API}/telas/${editingItem.id}`, formData);
        toast.success('Tela actualizada');
      } else {
        await axios.post(`${API}/telas`, formData);
        toast.success('Tela creada');
      }
      setDialogOpen(false);
      setEditingItem(null);
      setFormData({ nombre: '', entalle_ids: [] });
      fetchItems();
    } catch (error) {
      toast.error('Error al guardar tela');
    }
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({ nombre: item.nombre, entalle_ids: item.entalle_ids || [] });
    setDialogOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/telas/${id}`);
      toast.success('Tela eliminada');
      fetchItems();
    } catch (error) {
      toast.error('Error al eliminar tela');
    }
  };

  const handleNew = () => {
    setEditingItem(null);
    setFormData({ nombre: '', entalle_ids: [] });
    setDialogOpen(true);
  };

  const toggleEntalle = (entalleId) => {
    const current = formData.entalle_ids || [];
    if (current.includes(entalleId)) {
      setFormData({ ...formData, entalle_ids: current.filter(id => id !== entalleId) });
    } else {
      setFormData({ ...formData, entalle_ids: [...current, entalleId] });
    }
  };

  return (
    <div className="space-y-6" data-testid="telas-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Telas</h2>
          <p className="text-muted-foreground">Gestión de telas de productos</p>
        </div>
        <Button onClick={handleNew} data-testid="btn-nueva-tela">
          <Plus className="h-4 w-4 mr-2" />
          Nueva Tela
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="data-table-header">
                <TableHead>Nombre</TableHead>
                <TableHead>Entalles</TableHead>
                <TableHead className="w-[100px]">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={3} className="text-center py-8">
                    Cargando...
                  </TableCell>
                </TableRow>
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={3} className="text-center py-8 text-muted-foreground">
                    No hay telas registradas
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow key={item.id} className="data-table-row">
                    <TableCell className="font-medium">{item.nombre}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {(item.entalle_ids || []).map(entalleId => {
                          const entalle = entalles.find(e => e.id === entalleId);
                          return entalle ? (
                            <Badge key={entalleId} variant="secondary" className="text-xs">
                              {entalle.nombre}
                            </Badge>
                          ) : null;
                        })}
                        {(!item.entalle_ids || item.entalle_ids.length === 0) && (
                          <span className="text-muted-foreground text-sm">Sin entalles</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="icon" onClick={() => handleEdit(item)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(item.id)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingItem ? 'Editar Tela' : 'Nueva Tela'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Nombre de la tela"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Entalles disponibles</Label>
                <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
                  <PopoverTrigger asChild>
                    <Button variant="outline" role="combobox" className="w-full justify-between h-auto min-h-10">
                      <div className="flex flex-wrap gap-1 flex-1">
                        {formData.entalle_ids?.length === 0 ? (
                          <span className="text-muted-foreground">Seleccionar entalles...</span>
                        ) : (
                          formData.entalle_ids.map(id => {
                            const entalle = entalles.find(e => e.id === id);
                            return entalle ? (
                              <Badge key={id} variant="secondary" className="text-xs">{entalle.nombre}</Badge>
                            ) : null;
                          })
                        )}
                      </div>
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-full p-0" align="start">
                    <Command>
                      <CommandInput placeholder="Buscar entalle..." />
                      <CommandList>
                        <CommandEmpty>No se encontraron entalles.</CommandEmpty>
                        <CommandGroup>
                          {entalles.map((entalle) => (
                            <CommandItem key={entalle.id} value={entalle.nombre} onSelect={() => toggleEntalle(entalle.id)}>
                              <div className={cn(
                                "mr-2 flex h-4 w-4 items-center justify-center rounded-sm border",
                                formData.entalle_ids?.includes(entalle.id) ? "bg-primary border-primary text-primary-foreground" : "opacity-50"
                              )}>
                                {formData.entalle_ids?.includes(entalle.id) && <Check className="h-3 w-3" />}
                              </div>
                              {entalle.nombre}
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
              <Button type="submit">{editingItem ? 'Actualizar' : 'Crear'}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

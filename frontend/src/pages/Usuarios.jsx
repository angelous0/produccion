import { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '../components/ui/accordion';
import { Label } from '../components/ui/label';
import { Plus, Pencil, Trash2, Users, Shield, Key, Play, Package, Database, Settings, AlertTriangle, BarChart } from 'lucide-react';
import { toast } from 'sonner';
import { formatDate } from '../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ROLES = [
  { value: 'admin', label: 'Administrador', color: 'bg-red-500' },
  { value: 'usuario', label: 'Usuario', color: 'bg-blue-500' },
  { value: 'lectura', label: 'Solo Lectura', color: 'bg-gray-500' },
];

const CATEGORIA_ICONS = {
  'Producción': Play,
  'Inventario': Package,
  'Maestros': Database,
  'Configuración': Settings,
  'Calidad': AlertTriangle,
  'Reportes': BarChart,
};

export const Usuarios = () => {
  const { user: currentUser, isAdmin } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [estructura, setEstructura] = useState({ categorias: [] });
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [permisosDialogOpen, setPermisosDialogOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    nombre_completo: '',
    rol: 'usuario',
  });
  const [permisos, setPermisos] = useState({});
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const fetchUsuarios = async () => {
    try {
      const response = await axios.get(`${API}/usuarios`);
      setUsuarios(response.data);
    } catch (error) {
      toast.error('Error al cargar usuarios');
    } finally {
      setLoading(false);
    }
  };

  const fetchEstructura = async () => {
    try {
      const response = await axios.get(`${API}/permisos/estructura`);
      setEstructura(response.data);
    } catch (error) {
      console.error('Error fetching estructura:', error);
    }
  };

  useEffect(() => {
    fetchUsuarios();
    fetchEstructura();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingUser) {
        await axios.put(`${API}/usuarios/${editingUser.id}`, {
          email: formData.email,
          nombre_completo: formData.nombre_completo,
          rol: formData.rol,
        });
        toast.success('Usuario actualizado');
      } else {
        if (!formData.password) {
          toast.error('La contraseña es requerida');
          return;
        }
        await axios.post(`${API}/usuarios`, formData);
        toast.success('Usuario creado');
      }
      setDialogOpen(false);
      resetForm();
      fetchUsuarios();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar');
    }
  };

  const handleToggleActivo = async (user) => {
    try {
      await axios.put(`${API}/usuarios/${user.id}`, { activo: !user.activo });
      toast.success(`Usuario ${!user.activo ? 'activado' : 'desactivado'}`);
      fetchUsuarios();
    } catch (error) {
      toast.error('Error al cambiar estado');
    }
  };

  const handleResetPassword = async (user) => {
    if (!window.confirm(`¿Resetear contraseña de ${user.username}?`)) return;
    try {
      const response = await axios.put(`${API}/usuarios/${user.id}/reset-password`);
      toast.success(response.data.message);
    } catch (error) {
      toast.error('Error al resetear contraseña');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar este usuario?')) return;
    try {
      await axios.delete(`${API}/usuarios/${id}`);
      toast.success('Usuario eliminado');
      fetchUsuarios();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  const handleEditPermisos = (user) => {
    setEditingUser(user);
    setPermisos(user.permisos || {});
    setPermisosDialogOpen(true);
  };

  const handleSavePermisos = async () => {
    try {
      await axios.put(`${API}/usuarios/${editingUser.id}`, { permisos });
      toast.success('Permisos actualizados');
      setPermisosDialogOpen(false);
      fetchUsuarios();
    } catch (error) {
      toast.error('Error al guardar permisos');
    }
  };

  const togglePermiso = (tabla, accion) => {
    setPermisos(prev => ({
      ...prev,
      [tabla]: {
        ...prev[tabla],
        [accion]: !prev[tabla]?.[accion]
      }
    }));
  };

  const toggleAllPermisos = (tabla, acciones, checked) => {
    const newPermisos = { ...permisos };
    newPermisos[tabla] = {};
    acciones.forEach(acc => {
      newPermisos[tabla][acc] = checked;
    });
    setPermisos(newPermisos);
  };

  const handleNew = () => {
    setEditingUser(null);
    resetForm();
    setDialogOpen(true);
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      email: user.email || '',
      password: '',
      nombre_completo: user.nombre_completo || '',
      rol: user.rol,
    });
    setDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      username: '',
      email: '',
      password: '',
      nombre_completo: '',
      rol: 'usuario',
    });
  };

  const getRolBadge = (rol) => {
    const rolInfo = ROLES.find(r => r.value === rol) || ROLES[1];
    return (
      <Badge className={`${rolInfo.color} text-white`}>
        {rolInfo.label}
      </Badge>
    );
  };

  if (!isAdmin()) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-muted-foreground">No tienes permisos para ver esta página</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="usuarios-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Users className="h-6 w-6" />
            Gestión de Usuarios
          </h2>
          <p className="text-muted-foreground">
            Administra usuarios y sus permisos
          </p>
        </div>
        <Button onClick={handleNew} data-testid="btn-nuevo-usuario">
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Usuario
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Usuario</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Rol</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Creado</TableHead>
                <TableHead className="w-[150px]">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">Cargando...</TableCell>
                </TableRow>
              ) : usuarios.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No hay usuarios
                  </TableCell>
                </TableRow>
              ) : (
                usuarios.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.username}</TableCell>
                    <TableCell>{user.nombre_completo || '-'}</TableCell>
                    <TableCell className="text-muted-foreground">{user.email || '-'}</TableCell>
                    <TableCell>{getRolBadge(user.rol)}</TableCell>
                    <TableCell>
                      <Switch
                        checked={user.activo}
                        onCheckedChange={() => handleToggleActivo(user)}
                        disabled={user.id === currentUser?.id}
                      />
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatDate(user.created_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {user.rol === 'usuario' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEditPermisos(user)}
                            title="Editar Permisos"
                          >
                            <Shield className="h-4 w-4 text-blue-500" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleResetPassword(user)}
                          title="Resetear Contraseña"
                          disabled={user.id === currentUser?.id}
                        >
                          <Key className="h-4 w-4 text-orange-500" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(user)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(user.id)}
                          disabled={user.id === currentUser?.id}
                        >
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

      {/* Dialog Crear/Editar Usuario */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}</DialogTitle>
            <DialogDescription>
              {editingUser ? 'Modifica los datos del usuario' : 'Crea una nueva cuenta de usuario'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="username">Usuario *</Label>
                <Input
                  id="username"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  placeholder="nombre.usuario"
                  required
                  disabled={!!editingUser}
                />
              </div>
              {!editingUser && (
                <div className="space-y-2">
                  <Label htmlFor="password">Contraseña *</Label>
                  <Input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder="Contraseña inicial"
                    required={!editingUser}
                  />
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="nombre_completo">Nombre Completo</Label>
                <Input
                  id="nombre_completo"
                  value={formData.nombre_completo}
                  onChange={(e) => setFormData({ ...formData, nombre_completo: e.target.value })}
                  placeholder="Juan Pérez"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="usuario@empresa.com"
                />
              </div>
              <div className="space-y-2">
                <Label>Rol</Label>
                <Select value={formData.rol} onValueChange={(value) => setFormData({ ...formData, rol: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map((rol) => (
                      <SelectItem key={rol.value} value={rol.value}>
                        {rol.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Admin: acceso total | Usuario: permisos personalizables | Lectura: solo ver
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit">
                {editingUser ? 'Actualizar' : 'Crear'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dialog Editar Permisos */}
      <Dialog open={permisosDialogOpen} onOpenChange={setPermisosDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-500" />
              Permisos de {editingUser?.nombre_completo || editingUser?.username}
            </DialogTitle>
            <DialogDescription>
              Configura los permisos por tabla. Marca las acciones permitidas.
            </DialogDescription>
          </DialogHeader>
          
          <Accordion type="multiple" className="w-full" defaultValue={estructura.categorias?.map(c => c.nombre)}>
            {estructura.categorias?.map((categoria) => {
              const Icon = CATEGORIA_ICONS[categoria.nombre] || Database;
              return (
                <AccordionItem key={categoria.nombre} value={categoria.nombre}>
                  <AccordionTrigger className="hover:no-underline">
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      {categoria.nombre}
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-3 pl-6">
                      {categoria.tablas.map((tabla) => (
                        <div key={tabla.key} className="flex items-center justify-between py-2 border-b last:border-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm">{tabla.nombre}</span>
                          </div>
                          <div className="flex items-center gap-4">
                            {tabla.acciones.map((accion) => (
                              <label key={accion} className="flex items-center gap-1 cursor-pointer">
                                <Checkbox
                                  checked={permisos[tabla.key]?.[accion] || false}
                                  onCheckedChange={() => togglePermiso(tabla.key, accion)}
                                />
                                <span className="text-xs text-muted-foreground capitalize">{accion}</span>
                              </label>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              );
            })}
          </Accordion>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setPermisosDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSavePermisos}>
              Guardar Permisos
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

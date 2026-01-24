import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { 
  LayoutDashboard, 
  Tag, 
  Layers, 
  Shirt, 
  Palette,
  Scissors,
  Box,
  ClipboardList,
  Sun,
  Moon,
  Menu,
  X,
  Ruler,
  Droplets,
  Package,
  ArrowDownCircle,
  ArrowUpCircle,
  RefreshCw,
  FileText,
  BookOpen,
  Cog,
  Users,
  Play,
  BarChart3,
  Route,
  AlertTriangle,
  Sparkles,
  LogOut,
  User,
  Shield,
  Key,
  Loader2,
  History,
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelLeft
} from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/marcas', icon: Tag, label: 'Marcas' },
  { to: '/tipos', icon: Layers, label: 'Tipos' },
  { to: '/entalles', icon: Shirt, label: 'Entalles' },
  { to: '/telas', icon: Palette, label: 'Telas' },
  { to: '/hilos', icon: Scissors, label: 'Hilos' },
  { to: '/hilos-especificos', icon: Sparkles, label: 'Hilos Específicos' },
  { to: '/tallas-catalogo', icon: Ruler, label: 'Tallas' },
  { to: '/colores-catalogo', icon: Droplets, label: 'Colores' },
  { to: '/colores-generales', icon: Palette, label: 'Colores Generales' },
  { to: '/modelos', icon: Box, label: 'Modelos' },
  { to: '/registros', icon: ClipboardList, label: 'Registros' },
];

const inventarioItems = [
  { to: '/inventario', icon: Package, label: 'Inventario' },
  { to: '/inventario/ingresos', icon: ArrowDownCircle, label: 'Ingresos' },
  { to: '/inventario/salidas', icon: ArrowUpCircle, label: 'Salidas' },
  { to: '/inventario/ajustes', icon: RefreshCw, label: 'Ajustes' },
  { to: '/inventario/rollos', icon: Layers, label: 'Rollos' },
  { to: '/inventario/movimientos', icon: FileText, label: 'Movimientos' },
  { to: '/inventario/kardex', icon: BookOpen, label: 'Kardex' },
];

const maestrosItems = [
  { to: '/maestros/servicios', icon: Cog, label: 'Servicios' },
  { to: '/maestros/personas', icon: Users, label: 'Personas' },
  { to: '/maestros/rutas', icon: Route, label: 'Rutas' },
  { to: '/maestros/movimientos', icon: Play, label: 'Movimientos' },
  { to: '/maestros/productividad', icon: BarChart3, label: 'Productividad' },
];

const calidadItems = [
  { to: '/calidad/merma', icon: AlertTriangle, label: 'Merma' },
];

const documentosItems = [
  { to: '/guias', icon: FileText, label: 'Guías de Remisión' },
];

export const Layout = () => {
  const { theme, toggleTheme } = useTheme();
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebarCollapsed');
    return saved === 'true';
  });
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const toggleSidebarCollapsed = () => {
    const newValue = !sidebarCollapsed;
    setSidebarCollapsed(newValue);
    localStorage.setItem('sidebarCollapsed', String(newValue));
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error('Las contraseñas nuevas no coinciden');
      return;
    }
    
    if (passwordForm.new_password.length < 4) {
      toast.error('La contraseña debe tener al menos 4 caracteres');
      return;
    }

    setPasswordLoading(true);
    try {
      await axios.put(`${API}/auth/change-password`, {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      toast.success('Contraseña actualizada correctamente');
      setPasswordDialogOpen(false);
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al cambiar contraseña');
    } finally {
      setPasswordLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-background/80 border-b">
        <div className="flex h-16 items-center px-4 md:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden mr-2"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            data-testid="mobile-menu-toggle"
          >
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          
          <div className="flex items-center gap-2">
            <Scissors className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold tracking-tight">Producción Textil</h1>
          </div>
          
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              data-testid="theme-toggle"
            >
              {theme === 'light' ? (
                <Moon className="h-5 w-5" />
              ) : (
                <Sun className="h-5 w-5" />
              )}
            </Button>
            
            {/* Menú de usuario */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2" data-testid="user-menu-btn">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="h-4 w-4 text-primary" />
                  </div>
                  <span className="hidden md:inline text-sm font-medium">
                    {user?.nombre_completo || user?.username}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col">
                    <span>{user?.nombre_completo || user?.username}</span>
                    <span className="text-xs font-normal text-muted-foreground capitalize">
                      {user?.rol === 'admin' ? 'Administrador' : user?.rol === 'lectura' ? 'Solo Lectura' : 'Usuario'}
                    </span>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                {isAdmin() && (
                  <>
                    <DropdownMenuItem onClick={() => navigate('/usuarios')} data-testid="menu-usuarios">
                      <Shield className="h-4 w-4 mr-2" />
                      Gestionar Usuarios
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => navigate('/historial-actividad')} data-testid="menu-historial">
                      <History className="h-4 w-4 mr-2" />
                      Historial de Actividad
                    </DropdownMenuItem>
                  </>
                )}
                <DropdownMenuItem onClick={() => setPasswordDialogOpen(true)} data-testid="menu-change-password">
                  <Key className="h-4 w-4 mr-2" />
                  Cambiar Contraseña
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-destructive" data-testid="menu-logout">
                  <LogOut className="h-4 w-4 mr-2" />
                  Cerrar Sesión
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {/* Dialog Cambiar Contraseña */}
      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cambiar Contraseña</DialogTitle>
            <DialogDescription>
              Ingresa tu contraseña actual y la nueva contraseña
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleChangePassword}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="current_password">Contraseña Actual</Label>
                <Input
                  id="current_password"
                  type="password"
                  value={passwordForm.current_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                  placeholder="Tu contraseña actual"
                  required
                  disabled={passwordLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new_password">Nueva Contraseña</Label>
                <Input
                  id="new_password"
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                  placeholder="Tu nueva contraseña"
                  required
                  disabled={passwordLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm_password">Confirmar Nueva Contraseña</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                  placeholder="Repite la nueva contraseña"
                  required
                  disabled={passwordLoading}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setPasswordDialogOpen(false)} disabled={passwordLoading}>
                Cancelar
              </Button>
              <Button type="submit" disabled={passwordLoading}>
                {passwordLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Guardando...
                  </>
                ) : (
                  'Guardar'
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <div className="flex">
        {/* Sidebar */}
        <aside className={`
          fixed inset-y-0 left-0 z-40 w-64 transform bg-card border-r pt-16 transition-transform duration-200 ease-in-out
          md:translate-x-0 md:static md:pt-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}>
          <nav className="flex flex-col gap-1 p-4 overflow-y-auto h-full" data-testid="sidebar-nav">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `sidebar-item ${isActive ? 'active' : ''}`
                }
                data-testid={`nav-${item.label.toLowerCase()}`}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            ))}
            
            {/* Separador Inventario */}
            <div className="mt-4 mb-2">
              <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Inventario FIFO
              </p>
            </div>
            
            {inventarioItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/inventario'}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `sidebar-item ${isActive ? 'active' : ''}`
                }
                data-testid={`nav-${item.label.toLowerCase()}`}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            ))}

            {/* Separador Maestros */}
            <div className="mt-4 mb-2">
              <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Maestros
              </p>
            </div>
            
            {maestrosItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `sidebar-item ${isActive ? 'active' : ''}`
                }
                data-testid={`nav-${item.label.toLowerCase()}`}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            ))}

            {/* Separador Calidad */}
            <div className="mt-4 mb-2">
              <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Calidad
              </p>
            </div>
            {calidadItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `sidebar-item ${isActive ? 'active' : ''}`
                }
                data-testid={`nav-${item.label.toLowerCase()}`}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            ))}

            {/* Separador Documentos */}
            <div className="mt-4 mb-2">
              <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Documentos
              </p>
            </div>
            {documentosItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `sidebar-item ${isActive ? 'active' : ''}`
                }
                data-testid={`nav-${item.label.toLowerCase()}`}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        {/* Overlay for mobile */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 z-30 bg-black/50 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main content */}
        <main className="flex-1 p-6 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

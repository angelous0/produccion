import { NavLink, Outlet } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { Button } from './ui/button';
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
  AlertTriangle
} from 'lucide-react';
import { useState } from 'react';

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
  const [sidebarOpen, setSidebarOpen] = useState(false);

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
          
          <div className="ml-auto flex items-center gap-4">
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
          </div>
        </div>
      </header>

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

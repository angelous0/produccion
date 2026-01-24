import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { ThemeProvider } from "./context/ThemeContext";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Usuarios } from "./pages/Usuarios";
import { HistorialActividad } from "./pages/HistorialActividad";
import { Dashboard } from "./pages/Dashboard";
import { Marcas } from "./pages/Marcas";
import { Tipos } from "./pages/Tipos";
import { Entalles } from "./pages/Entalles";
import { Telas } from "./pages/Telas";
import { Hilos } from "./pages/Hilos";
import { TallasCatalogo } from "./pages/TallasCatalogo";
import { ColoresCatalogo } from "./pages/ColoresCatalogo";
import { ColoresGenerales } from "./pages/ColoresGenerales";
import { Modelos } from "./pages/Modelos";
import { Registros } from "./pages/Registros";
import { RegistroForm } from "./pages/RegistroForm";
import { Inventario } from "./pages/Inventario";
import { InventarioIngresos } from "./pages/InventarioIngresos";
import { InventarioSalidas } from "./pages/InventarioSalidas";
import { InventarioAjustes } from "./pages/InventarioAjustes";
import { InventarioRollos } from "./pages/InventarioRollos";
import { ReporteMovimientos } from "./pages/ReporteMovimientos";
import { Kardex } from "./pages/Kardex";
import { ServiciosProduccion } from "./pages/ServiciosProduccion";
import { PersonasProduccion } from "./pages/PersonasProduccion";
import { MovimientosProduccion } from "./pages/MovimientosProduccion";
import { ReporteProductividad } from "./pages/ReporteProductividad";
import { RutasProduccion } from "./pages/RutasProduccion";
import { CalidadMerma } from "./pages/CalidadMerma";
import { GuiasRemision } from "./pages/GuiasRemision";
import { HilosEspecificos } from "./pages/HilosEspecificos";
import { Loader2 } from "lucide-react";

// Componente de ruta protegida
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

// Componente para rutas públicas (login)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }
  
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  
  return children;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Ruta pública - Login */}
      <Route path="/login" element={
        <PublicRoute>
          <Login />
        </PublicRoute>
      } />
      
      {/* Rutas protegidas */}
      <Route path="/" element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<Dashboard />} />
        <Route path="usuarios" element={<Usuarios />} />
        <Route path="historial-actividad" element={<HistorialActividad />} />
        <Route path="marcas" element={<Marcas />} />
        <Route path="tipos" element={<Tipos />} />
        <Route path="entalles" element={<Entalles />} />
        <Route path="telas" element={<Telas />} />
        <Route path="hilos" element={<Hilos />} />
        <Route path="hilos-especificos" element={<HilosEspecificos />} />
        <Route path="tallas-catalogo" element={<TallasCatalogo />} />
        <Route path="colores-catalogo" element={<ColoresCatalogo />} />
        <Route path="colores-generales" element={<ColoresGenerales />} />
        <Route path="modelos" element={<Modelos />} />
        <Route path="registros" element={<Registros />} />
        <Route path="registros/nuevo" element={<RegistroForm />} />
        <Route path="registros/editar/:id" element={<RegistroForm />} />
        <Route path="inventario" element={<Inventario />} />
        <Route path="inventario/ingresos" element={<InventarioIngresos />} />
        <Route path="inventario/salidas" element={<InventarioSalidas />} />
        <Route path="inventario/ajustes" element={<InventarioAjustes />} />
        <Route path="inventario/rollos" element={<InventarioRollos />} />
        <Route path="inventario/movimientos" element={<ReporteMovimientos />} />
        <Route path="inventario/kardex" element={<Kardex />} />
        <Route path="maestros/servicios" element={<ServiciosProduccion />} />
        <Route path="maestros/personas" element={<PersonasProduccion />} />
        <Route path="maestros/rutas" element={<RutasProduccion />} />
        <Route path="maestros/movimientos" element={<MovimientosProduccion />} />
        <Route path="maestros/productividad" element={<ReporteProductividad />} />
        <Route path="calidad/merma" element={<CalidadMerma />} />
        <Route path="guias" element={<GuiasRemision />} />
      </Route>
      
      {/* Redirigir cualquier ruta desconocida a login */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;

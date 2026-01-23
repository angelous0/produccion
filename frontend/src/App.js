import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { ThemeProvider } from "./context/ThemeContext";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Marcas } from "./pages/Marcas";
import { Tipos } from "./pages/Tipos";
import { Entalles } from "./pages/Entalles";
import { Telas } from "./pages/Telas";
import { Hilos } from "./pages/Hilos";
import { TallasCatalogo } from "./pages/TallasCatalogo";
import { ColoresCatalogo } from "./pages/ColoresCatalogo";
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
import { RegistroHilos } from "./pages/RegistroHilos";

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="marcas" element={<Marcas />} />
            <Route path="tipos" element={<Tipos />} />
            <Route path="entalles" element={<Entalles />} />
            <Route path="telas" element={<Telas />} />
            <Route path="hilos" element={<Hilos />} />
            <Route path="tallas-catalogo" element={<TallasCatalogo />} />
            <Route path="colores-catalogo" element={<ColoresCatalogo />} />
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
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </ThemeProvider>
  );
}

export default App;

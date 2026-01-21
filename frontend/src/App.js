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
import { Modelos } from "./pages/Modelos";
import { Registros } from "./pages/Registros";

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
            <Route path="modelos" element={<Modelos />} />
            <Route path="registros" element={<Registros />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </ThemeProvider>
  );
}

export default App;

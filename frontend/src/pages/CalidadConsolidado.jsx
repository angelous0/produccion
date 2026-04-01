import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Shield, BarChart3, ListChecks } from 'lucide-react';
import { CalidadMerma } from './CalidadMerma';
import { ReporteMermas } from './ReporteMermas';
import { ReporteEstadosItem } from './ReporteEstadosItem';

export const CalidadConsolidado = () => {
  return (
    <div className="space-y-4" data-testid="calidad-consolidado">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Calidad</h2>
        <p className="text-sm text-muted-foreground">Gestión de mermas, reportes y estados</p>
      </div>

      <Tabs defaultValue="merma" className="space-y-4">
        <TabsList className="h-9">
          <TabsTrigger value="merma" className="text-xs gap-1.5" data-testid="tab-merma">
            <Shield className="h-3.5 w-3.5" /> Merma
          </TabsTrigger>
          <TabsTrigger value="reporte-mermas" className="text-xs gap-1.5" data-testid="tab-reporte-mermas">
            <BarChart3 className="h-3.5 w-3.5" /> Reporte Mermas
          </TabsTrigger>
          <TabsTrigger value="estados" className="text-xs gap-1.5" data-testid="tab-estados">
            <ListChecks className="h-3.5 w-3.5" /> Reporte Estados
          </TabsTrigger>
        </TabsList>

        <TabsContent value="merma"><CalidadMerma /></TabsContent>
        <TabsContent value="reporte-mermas"><ReporteMermas /></TabsContent>
        <TabsContent value="estados"><ReporteEstadosItem /></TabsContent>
      </Tabs>
    </div>
  );
};

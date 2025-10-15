// client/src/components/HomeAssistant/ZonesDashboard.tsx
import store from '~/store';
import type React from "react";
import { useRecoilValue } from "recoil";
import ZoneCard from "./Zones/ZoneCard";
import type { ContextType } from '~/common';
import { OpenSidebar } from '../Chat/Menus';
import useLocalize from '~/hooks/useLocalize';
import { DashboardContext } from "~/Providers";
import { useOutletContext } from 'react-router-dom';
import { HAZone } from '~/common/home-assistant-types';
import { useMemo, useContext } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useHADashboard } from "~/hooks/useHomeAssistant";
import { useMasonryColumns } from "~/hooks/useMasonryColumns"
import { Home, AlertCircle } from "lucide-react";
import { Badge, Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription, Spinner } from "~/components/ui/";

const ZonesDashboard: React.FC = () => {
  const localize = useLocalize();
  const { prevLocationPath } = useContext(DashboardContext)
  const { data, isLoading, isError, error } = useHADashboard()

  const hideSidePanel = useRecoilValue(store.hideSidePanel);
  const { navVisible, setNavVisible } = useOutletContext<ContextType>();

  // Extrae el array de zonas del objeto API y lo mapea a HAZone
  const zonesArray: HAZone[] = useMemo(() => {
    const nestedZones = data?.zones?.zones
    if (!nestedZones) return []

    // Mapeamos las entradas del objeto 'zones' a la estructura HAZone
    return Object.entries(nestedZones).map(([zoneName, zoneData]) => ({
      id: zoneName,
      name: zoneName,
      devices: zoneData.devices,
      activeCount: zoneData.activeCount,
      totalCount: zoneData.totalCount,
    }))
  }, [data])

  // Resumen global de todos los dispositivos
  const dashboardSummary = useMemo(() => {
    if (!data) return { total: 0, on: 0, off: 0 }

    const totalOn = zonesArray.reduce((sum, zone) => sum + (zone.activeCount || 0), 0)
    const totalEntities = data.zones.total_entities || 0

    return {
      total: totalEntities,
      on: totalOn,
      off: totalEntities - totalOn,
    }
  }, [data, zonesArray])

  const zoneColumns = useMasonryColumns(zonesArray, {
    mobile: 1,
    tablet: 2,
    desktop: 3,
    wide: 3,
  })

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex h-full w-full items-center justify-center p-6">
          <div className="flex flex-col items-center gap-3">
            <Spinner className="size-8" />
            <p className="text-sm text-muted-foreground">{localize('com_ha_loading_data')}</p>
          </div>
        </div>
      );
    }

    if (isError) {
      return (
        <div className="flex h-full w-full items-center justify-center p-6">
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <AlertCircle className="size-6 text-destructive" />
              </EmptyMedia>
              <EmptyTitle>{localize('com_ha_load_failed')}</EmptyTitle>
              <EmptyDescription>
                {error?.message || "An unknown error occurred while loading Home Assistant data."}
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        </div>
      );
    }

    if (!zonesArray.length) {
      return (
        <div className="flex h-full w-full items-center justify-center p-6">
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Home className="size-6" />
              </EmptyMedia>
              <EmptyTitle>{localize('com_ha_no_zones')}</EmptyTitle>
              <EmptyDescription>{localize('com_ha_no_zones_description')}</EmptyDescription>
            </EmptyHeader>
          </Empty>
        </div>
      );
    }

    return (
      <div className="flex h-full w-full flex-col overflow-y-auto">
        <div className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="flex items-center justify-between gap-4 px-4 py-3 md:px-6 md:py-4">
            {!navVisible && <OpenSidebar setNavVisible={setNavVisible} />}           
            <div className="flex items-center gap-2">
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10">
                <Home className="size-4 text-primary" />
              </div>
              <div className="flex flex-col">
                <h1 className="text-lg font-semibold text-muted-foreground leading-none">Home Assistant</h1>
                <p className="text-xs text-muted-foreground">
                  {zonesArray.length === 1
                    ? localize('com_ha_zones_active', { count: zonesArray.length })
                    : localize('com_ha_zones_active_plural', { count: zonesArray.length })}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant="outline" className="gap-1.5">
                <span className="size-2 rounded-full bg-emerald-600" />
                <span className="text-xs font-medium">{dashboardSummary.on} On</span>
              </Badge>
              <Badge variant="outline" className="gap-1.5">
                <span className="size-2 rounded-full bg-muted-foreground/40" />
                <span className="text-xs font-medium">{dashboardSummary.off} Off</span>
              </Badge>
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 md:p-6">
          <div className="flex gap-4">
            {zoneColumns.map((column, columnIndex) => (
              <div
                key={columnIndex}
                className="flex flex-1 flex-col gap-4"
                style={{ minWidth: 0 }} // Prevent flex items from overflowing
              >
                <AnimatePresence mode="popLayout">
                  {column.map((zone: HAZone) => (
                    <motion.div
                      key={zone.id}
                      layout
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{
                        layout: {
                          type: "spring",
                          stiffness: 400,
                          damping: 30,
                        },
                        opacity: { duration: 0.2 },
                        y: { duration: 0.3 },
                      }}
                    >
                      <ZoneCard
                        zoneName={zone.name}
                        devices={zone.devices}
                        activeCount={zone.activeCount}
                        totalCount={zone.totalCount}
                      />
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex  w-full flex-col">
      <main id="messages-view" className="flex-1" role="main">
        {renderContent()}
      </main>
    </div>
  );
};

export default ZonesDashboard

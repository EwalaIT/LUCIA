import cn from '~/utils/cn';
import { motion, AnimatePresence } from 'framer-motion';
import useLocalize from '~/hooks/useLocalize';
import DeviceGrid from '../Devices/DeviceGrid';
import { ChevronDown, MapPin } from "lucide-react";
import { HADevice, HAEntity } from '~/common/home-assistant-types';
import React, { useMemo, useState, useRef, useEffect } from 'react';
import { Badge, Button, Card, CardHeader, CardTitle, CardContent, CardAction } from "~/components/ui/";

interface ZoneCardProps {
  zoneName: string;
  devices: HADevice[];
  activeCount: number;
  totalCount: number;
}

const HEIGHT_ANIM_DURATION = 0.25; // segundos
const CONTENT_FADE_DURATION = 0.25; // segundos
const CONTENT_FADE_DELAY = 0; // espera tras terminar altura

const ZoneCard: React.FC<ZoneCardProps> = ({ zoneName, devices, activeCount, totalCount }) => {
  const localize = useLocalize();
  const [isExpanded, setIsExpanded] = useState(false)

  const [measuredHeight, setMeasuredHeight] = useState<number | null>(null);
  const [showInner, setShowInner] = useState(false); // si se monta/visible el DeviceGrid
  const measuringRef = useRef<HTMLDivElement | null>(null); // nodo offscreen para medir
  const contentRef = useRef<HTMLDivElement | null>(null); // referencia al content visible

  const safeDevices = devices || [];

  // Aseguramos que devices siempre tenga entities definidas
  const summary = useMemo(() => {
    let sensors = 0;
    let actuators = 0;

    // Lista de device_class/dominios que típicamente son sensores
    const sensorClasses = ['temperature', 'humidity', 'pressure', 'voltage', 'illuminance', 'gas'];
    const sensorDomains = ['sensor', 'binary_sensor'];

    safeDevices.forEach((d) => {

      const entities = d.entities || [];

      entities.forEach((e: HAEntity) => {
        const domain = e.entity_id.split('.')[0];

        if (
          e.unit ||
          (e.device_class && sensorClasses.includes(e.device_class)) ||
          sensorDomains.includes(domain)
        ) {
          sensors++;
        } else {
          actuators++;
        }
      });
    });

    return {
      total: totalCount,
      onCount: activeCount,
      offCount: totalCount - activeCount,
      sensors,
      actuators
    };
  }, [devices, activeCount, totalCount]);


  // Acción de abrir / cerrar con control de secuencia
  const toggleExpanded = async () => {
    if (!isExpanded) {
      // vamos a abrir: medir, animar altura, luego mostrar contenido
      setShowInner(false);
      setMeasuredHeight(null);

      // renderizamos el contenido en el nodo de medición (visually hidden) y medimos
      // Para ello: forzamos que measuringRef contenga el markup del DeviceGrid
      // Después de render (useEffect), medimos y lanzamos la animación (isExpanded true)
      setIsExpanded(true);
    } else {
      // cerrar: primero ocultar contenido con fade, luego colapsar altura
      // 1) esconder el contenido (fade out)
      setShowInner(false);
      // 2) tras delay espera al fade out, cerrar la altura
      setTimeout(() => {
        setIsExpanded(false);
        setMeasuredHeight(null);
      }, (CONTENT_FADE_DURATION + 0.02) * 1000);
    }
  };

  // Cuando isExpanded cambia a true necesitamos medir el contenido
  useEffect(() => {
    if (!isExpanded) return;

    // La medición se hace renderizando el contenido en measuringRef
    // Esperamos un microtick para que el DOM se pinte
    const id = window.setTimeout(() => {
      if (measuringRef.current) {
        const h = measuringRef.current.scrollHeight;
        setMeasuredHeight(h);
        // Tras animación de altura terminada, montamos el contenido visible
        const after = (HEIGHT_ANIM_DURATION + CONTENT_FADE_DELAY) * 1000;
        setTimeout(() => setShowInner(true), after);
      } else {
        // fallback: si no medimos, mostramos el contenido directamente tras animación
        setTimeout(() => setShowInner(true), (HEIGHT_ANIM_DURATION + CONTENT_FADE_DELAY) * 1000);
      }
    }, 0);

    return () => clearTimeout(id);
  }, [isExpanded]);

  // Cuando colapsa (isExpanded === false) limpiar measuredHeight para que altura vuelva a 0
  useEffect(() => {
    if (!isExpanded) {
      setMeasuredHeight(null);
      setShowInner(false);
    }
  }, [isExpanded]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
    >
      <Card className="flex flex-col transition-all hover:shadow-md">
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted">
                <MapPin className="size-5 text-muted-foreground" />
              </div>
              <div className="space-y-1">
                <CardTitle className="text-base leading-none">{zoneName}</CardTitle>
                <p className="text-xs text-muted-foreground">
                  {summary.total} {summary.total === 1 ? localize('com_ha_device') : localize('com_ha_devices')}
                </p>
              </div>
            </div>

            <CardAction>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className={cn("transition-transform", isExpanded && "rotate-180")}
                aria-label={isExpanded ? localize('com_ha_collapse_devices') : localize('com_ha_expand_devices')}
              >
                <ChevronDown className="size-4" />
              </Button>
            </CardAction>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-2">
            <Badge variant="outline" className="gap-1.5">
              <span
                className={`
                size-2 rounded-full 
                ${summary.onCount > 0
                    ? 'bg-emerald-600 dark:bg-green-500'  // Verde si hay 1 o más activos
                    : 'bg-gray-400 dark:bg-gray-500'      // Gris si no hay ninguno
                  }
              `}
              />
              <span className="text-xs font-medium">
                {summary.onCount} {localize('com_ha_active')}
              </span>
            </Badge>
            <Badge variant="secondary" className="gap-1.5 text-xs">
              <span className="text-muted-foreground">{localize('com_ha_sensors')}</span>
              <span className="font-semibold">{summary.sensors}</span>
            </Badge>

            <Badge variant="secondary" className="gap-1.5 text-xs">
              <span className="text-muted-foreground">{localize('com_ha_actuators')}</span>
              <span className="font-semibold">{summary.actuators}</span>
            </Badge>

          </div>
        </CardHeader>

        {/* --- Animated height container --- */}
        <motion.div
          className="overflow-hidden"
          animate={{ height: measuredHeight != null ? measuredHeight : 0 }}
          initial={{ height: 0 }}
          transition={{ height: { duration: HEIGHT_ANIM_DURATION, ease: [0.25, 0.1, 0.25, 1] } }}
        >
          {/* Content visible area: nosotros controlamos su montaje con showInner */}
          <div ref={contentRef}>
            <AnimatePresence>
              {showInner && (
                <motion.div
                  key="devicegrid-visible"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: CONTENT_FADE_DURATION }}
                >
                  <CardContent className="flex-1 pt-0">
                    <DeviceGrid devices={devices} />
                  </CardContent>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        {/* --- Hidden measuring node (not visible, position absolute) --- */}
        {/* Se monta únicamente cuando isExpanded=true y antes de medir (medición invisible) */}
        <div
          aria-hidden
          style={{ position: 'absolute', left: -9999, top: -9999, width: 'calc(100% - 32px)' }} // ancho similar al content real
        >
          {/* Renderizamos el DeviceGrid "offscreen" para medir su altura cuando isExpanded true */}
          {isExpanded && (
            <div ref={measuringRef} className="invisible pointer-events-none">
              <div style={{ padding: '0.0px 16px 16px 16px' }}>
                {/* Usa la misma estructura que el CardContent para medir altura real */}
                <div>
                  <DeviceGrid devices={devices} />
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>
    </motion.div>
  )
};

export default ZoneCard;

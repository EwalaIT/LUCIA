import  cn  from '~/utils/cn';
import DeviceCard from './DeviceCard';
import React, { useMemo } from 'react';
import { useHAStates } from '~/hooks/useHomeAssistant';
import { motion, AnimatePresence } from 'framer-motion';
import { HADevice, HAEntity } from '~/common/home-assistant-types';

interface DeviceGridProps {
  devices?: HADevice[];
  filterDomain?: string; // opcional, para filtrar por tipo de dispositivo
}

const DeviceGrid: React.FC<DeviceGridProps> = ({ devices: devicesProp, filterDomain }) => {
  // Hook que obtiene los dispositivos de HomeAssistant si no se pasan por props
  const { data: haEntities, isLoading: haLoading } = useHAStates();

  // Filtrado opcional por dominio
  const flattenedEntities: HAEntity[] = useMemo(() => {
    if (devicesProp) {
      // Si estamos en ZoneCard (prop devicesProp existe), aplanamos los dispositivos
      return devicesProp.flatMap((d) => d.entities || []);
    }
    // Si NO estamos en ZoneCard (prop devicesProp es null/undefined), usamos las entidades del hook
    return haEntities || [];
  }, [devicesProp, haEntities]);


  // Filtrado opcional por dominio
  const filteredEntities = useMemo(() => {
    if (!filterDomain) return flattenedEntities;

    return flattenedEntities.filter((e) => e.entity_id.split('.')[0] === filterDomain);

  }, [flattenedEntities, filterDomain]);

  const isLoading = devicesProp ? false : haLoading; 

  // Grid dinámico: adaptativo según tamaño de pantalla
  return (
    <motion.div layout className={cn("grid gap-4", "grid-cols-1 sm:grid-cols-2")}>
      <AnimatePresence mode="popLayout">
        {filteredEntities.map((entity) => (
          <motion.div
            key={entity.entity_id}
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
          >
            <DeviceCard entity={entity} />
          </motion.div>
        ))}
      </AnimatePresence>
    </motion.div>
  );
};

export default DeviceGrid;

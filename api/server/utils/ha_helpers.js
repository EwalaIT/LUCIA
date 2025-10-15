/**
 * ha_helpers.js
 * Funciones de ayuda para procesar los estados de Home Assistant.
 * Agrupa entidades por zona y dispositivo, y limpia la información redundante.
 */

/**
 * Formatea una entidad de Home Assistant en una estructura simplificada y útil.
 * @param {Object} entity
 */
function formatEntity(entity) {
  const formatted = {
    entity_id: entity.entity_id,
    name: entity.attributes?.friendly_name || entity.entity_id,
    state: entity.state,
    unit: entity.attributes?.unit_of_measurement || null,
    icon: entity.attributes?.icon || null,
    battery: entity.attributes?.battery_level || entity.attributes?.battery || null,
    device_class: entity.attributes?.device_class || null,
  };

  // Añadimos link de streaming si es cámara
  if (entity.entity_id.startsWith('camera.') && entity.attributes?.entity_picture) {
    const token = entity.attributes.access_token; // o tu long-lived token
    formatted.stream_url = `/api/camera_proxy/${entity.entity_id}?token=${token}`;
  }

  return formatted;
}

/**
 * Obtiene el nombre del dispositivo.
 * Si no existe en los atributos, intenta inferirlo del entity_id.
 */
function getDeviceName(entity) {
  return (
    entity.attributes?.device_name ||
    entity.attributes?.friendly_name?.split(' ')[0] ||
    entity.entity_id.split('.')[1].split('_')[0]
  );
}

const DEFAULT_ZONE_NAME = 'Global/Unassigned';

const IGNORE_DOMAINS = ['number', 'select', 'button', 'update', 'event', 'calendar', 'conversation', 'tts', 'todo', 'person', 'zone', 'sun'];

// Dominios de configuración a ignorar, movidos al exterior para visibilidad:
const CONFIG_DOMAINS_TO_IGNORE = ['number', 'select', 'button', 'update', 'event', 'calendar'];

/**
 * Convierte un array de estados de HA en un objeto estructurado:
 * ZONA → DISPOSITIVOS → ENTIDADES
 * @param {Array} states - Array de estados de HA (API /states)
 * @param {Array} areaRegistry - Array de registros de área de HA
 * @param {Array} deviceRegistry - Array de registros de dispositivo de HA
 * @param {Array} entityRegistry - Array de registros de entidad de HA
 * @returns {Object}
 */
function getStructuredZones(states = [], areaRegistry = [], deviceRegistry = [], entityRegistry = []) {
  const zones = {};

  // 1. Mapeo de Registros
  const deviceToAreaMap = deviceRegistry.reduce((acc, device) => {
    if (device.area_id) acc[device.id] = device.area_id;
    return acc;
  }, {});

  const areaIdToNameMap = areaRegistry.reduce((acc, area) => {
    acc[area.area_id] = area.name;
    return acc;
  }, {});

  const entityToDeviceIdMap = entityRegistry.reduce((acc, entity) => {
    if (entity.device_id) acc[entity.entity_id] = entity.device_id;
    return acc;
  }, {});

  const getReliableDeviceId = (entity) => {
    const idFromRegistry = entityToDeviceIdMap[entity.entity_id];
    if (idFromRegistry) return idFromRegistry;
    if (entity.attributes?.device_id) return entity.attributes.device_id;
    return getDeviceName(entity);
  };

  // 2. PROCESAMIENTO DE ENTIDADES y aplicación de la lógica de agrupación
  states.forEach((s) => {
    const entityId = s.entity_id;
    const [entityDomain, entityName] = entityId.split('.');

    // **[SIMPLIFICACIÓN]** Ignorar entidades de batería y dominios ignorados
    if (s.attributes?.device_class === 'battery' || IGNORE_DOMAINS.includes(entityDomain)) {
      return;
    }

    if (CONFIG_DOMAINS_TO_IGNORE.includes(entityDomain) && entityName.includes('sonoff')) {
      return;
    }

    let finalDeviceId = getReliableDeviceId(s);
    let zoneName = '';
    let deviceName = s.attributes?.device_name;

    // A. Búsqueda Principal por Device ID (Si el dispositivo tiene Area)
    if (finalDeviceId) {
      const areaId = deviceToAreaMap[finalDeviceId];
      if (areaId) {
        zoneName = areaIdToNameMap[areaId];
      }
    }

    // B. Fallback y Agrupación Lógica/Consolidada
    if (!zoneName) {
      // 1. INFERENCIA DE ZONA POR NOMBRE DE ENTIDAD
      const nameMatch = entityId.match(/^(?:sensor|switch|weather)\.([a-z0-9_&]+)_(?:temperature|humidity|switch|weather)/i);
      if (nameMatch) {
        let inferredZone = nameMatch[1].replace(/_/g, ' ');

        // Normalización
        if (inferredZone.toLowerCase().includes('office 1')) inferredZone = 'Office 1';
        else if (inferredZone.toLowerCase().includes('office 2')) inferredZone = 'Office 2';
        else if (inferredZone.toLowerCase().includes('consulting administration')) inferredZone = 'Consulting-Administration';
        else if (inferredZone.toLowerCase().includes('r d i')) inferredZone = 'R&D&I';
        else if (inferredZone.toLowerCase() === 'out') inferredZone = 'Out';

        zoneName = inferredZone;

        if (!finalDeviceId) {
          finalDeviceId = zoneName;
        }
      }

      // 2. Mover Cámaras a su Zona específica
      if (entityDomain === 'camera') {
        zoneName = 'Cameras';
        if (!finalDeviceId) finalDeviceId = getDeviceName(s);
      }
    }

    // 3. Fallback final para lo que quede
    if (!zoneName) {
      zoneName = 'Global/Unassigned';
    }

    // 4. Asegurar Device ID y Name para la estructura
    if (!finalDeviceId) {
      finalDeviceId = getDeviceName(s);
    }
    if (!deviceName) {
      const deviceData = deviceRegistry.find(d => d.id === finalDeviceId);
      deviceName = deviceData?.name_by_user || s.attributes?.friendly_name || finalDeviceId;
    }

    // 5. Filtrar zonas no deseadas
    if (zoneName === 'Global/Unassigned' && entityDomain !== 'camera') {
      return;
    }

    if (!zones[zoneName]) {
      zones[zoneName] = {
        devices: {},
        activeCount: 0,
        totalCount: 0,
      };
    }

    if (!zones[zoneName].devices[finalDeviceId]) {
      zones[zoneName].devices[finalDeviceId] = {
        device_id: finalDeviceId,
        device_name: deviceName,
        entities: [],
        // **[SIMPLIFICACIÓN]** Eliminada la propiedad 'battery'
      };
    }

    // 6. Añadir entidad procesada y contadores
    const formattedEntity = formatEntity(s);
    // **[SIMPLIFICACIÓN]** Eliminada cualquier lógica de asignación de batería a la entidad
    zones[zoneName].devices[finalDeviceId].entities.push(formattedEntity);
    zones[zoneName].totalCount++;

    // Contar activos (lógica simplificada)
    const stateLower = String(s.state).toLowerCase();
    const isActive = ['on', 'open', 'home'].includes(stateLower);
    if (isActive) {
      zones[zoneName].activeCount++;
    }
  });

  // 7. Limpieza y conversión a array
  const finalZones = {};
  let totalZonesCount = 0;
  let totalEntitiesCount = 0;

  Object.keys(zones).forEach(zoneKey => {
    if (zones[zoneKey].totalCount === 0) return;

    const zoneData = zones[zoneKey];
    zoneData.devices = Object.values(zoneData.devices);

    if (zoneKey === 'Global/Unassigned' && zoneData.totalCount < 3) return;

    finalZones[zoneKey] = zoneData;
    totalZonesCount++;
    totalEntitiesCount += zoneData.totalCount;
  });

  return {
    timestamp: new Date().toISOString(),
    total_zones: totalZonesCount,
    total_entities: totalEntitiesCount,
    zones: finalZones
  };
}

module.exports = {
  formatEntity,
  getDeviceName,
  getStructuredZones,
};

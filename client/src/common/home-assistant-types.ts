/**
 * --- Home Assistant Type Definitions (Actualizados) ---
 */

// ----------------------------------------------------
// ENTIDAD Y ESTADO
// ----------------------------------------------------

/**
 * Estado de una entidad en Home Assistant.
 * Se elimina la propiedad 'battery' de la estructura.
 */
export type HAEntity = {
  stream_url: string;
  entity_id: string;
  name: string;
  state: string;
  unit?: string;
  icon?: string;
  device_class?: string;
};

/**
 * Alias más genérico para los estados
 */
export type HAState = HAEntity;


// ----------------------------------------------------
// DISPOSITIVO
// ----------------------------------------------------

/**
 * Representa un dispositivo agrupado (abstracción a partir de entity states)
 */
export type HADevice = {
  device_id: string;
  device_name: string;
  entities: HAEntity[];
};

// ----------------------------------------------------
// DASHBOARD Y ZONAS
// ----------------------------------------------------

/**
 * Define la estructura de datos que representa una zona en el dashboard.
 * Nota: El backend agrupa los dispositivos directamente.
 */
export type HAZoneData = {
  devices: HADevice[];
  activeCount: number;
  totalCount: number;
};

/**
 * Estructura completa del dashboard devuelto por el backend.
 * El campo 'zones' es un objeto clave-valor donde la clave es el nombre de la zona.
 */
export type HADashboardData = {
  timestamp: string;
  total_zones: number;
  total_entities: number;
  zones: {
    [zoneName: string]: HAZoneData; // Clave: Nombre de la zona (ej: "Office 1") | Valor: HAZoneData
  };
};

/**
 * Representa una zona (ej: habitación o área) para el consumo en componentes frontend.
 * Es una versión aplanada que se construye a partir de HAZoneData.
 */
export type HAZone = {
  id: string; // El nombre de la zona usado como ID
  name: string;
  devices: HADevice[];
  activeCount: number;
  totalCount: number;
};


// ----------------------------------------------------
// OTROS TYPES (Sin Cambios)
// ----------------------------------------------------

export type HAService = {
  domain: string; // ej: "light"
  services: {
    [serviceName: string]: {
      description: string;
      fields: {
        [fieldName: string]: {
          description: string;
          example?: string;
          required?: boolean;
        };
      };
    };
  };
};

export type HAEvent = {
  event: string;
  listener_count: number;
};

export type HAConfig = {
  latitude: number;
  longitude: number;
  elevation: number;
  unit_system: {
    length: string;
    mass: string;
    temperature: string;
    volume: string;
  };
  time_zone: string;
  version: string;
  components: string[];
  config_dir: string;
  safe_mode?: boolean;
};

export type HAComponent = string; // ej: "light", "switch", etc.

export type HAHistoryEntry = {
  entity_id: string;
  state: string;
  last_changed: string;
  attributes: Record<string, any>;
};

export type HALogbookEntry = {
  name: string;
  entity_id: string;
  domain: string;
  message: string;
  when: string; // ISO timestamp
  [key: string]: any;
};

export type HACommand = {
  domain: string;
  service: string;
  entity_id: string;
};

export type HACommandResponse = {
  success: boolean;
  result?: any;
};

export type HAErrorLog = string;

export type HACameraStream = Blob | string;

export type HACameraUpdate = {
  entityId: string;
  image: string;        
  contentType: string; 
  timestamp: number; 
};
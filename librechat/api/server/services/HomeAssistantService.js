// services/HomeAssistant.js
const axios = require('axios');
const { logger } = require('@librechat/data-schemas');

const HA_URL = process.env.HA_URL || 'http://homeassistant.local:8123';
const HA_TOKEN = process.env.HA_TOKEN || 'YOUR_LONG_LIVED_TOKEN';

function getHAConfig() {
  const HA_URL = process.env.HA_URL;
  const HA_TOKEN = process.env.HA_TOKEN;
  if (!HA_URL || !HA_TOKEN) throw new Error('HA env missing');
  return { HA_URL, HA_TOKEN };
}

const client = axios.create({
  baseURL: `${HA_URL}/api`,
  headers: {
    Authorization: `Bearer ${HA_TOKEN}`,
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Helper para loguear errores Axios
function logAxiosError(error, context = '') {
  if (error.response) {
    // El servidor respondi� con c�digo de error
    logger.error(`[HA Axios ${context}] Response error`, {
      status: error.response.status,
      statusText: error.response.statusText,
      data: error.response.data,
    });
  } else if (error.request) {
    // La petici�n se hizo pero no hubo respuesta
    logger.error(`[HA Axios ${context}] No response received`, {
      request: {
        method: error.config.method,
        url: error.config.url,
        headers: { ...error.config.headers, Authorization: 'Bearer ****' },
        data: error.config.data,
      },
      message: error.message,
    });
  } else {
    // Otro tipo de error
    logger.error(`[HA Axios ${context}] Error setting up request`, { message: error.message });
  }
}

const HomeAssistantService = {
  /** Obtiene todos los estados de Home Assistant */
  // async getStates() {
  //   try {
  //     const { data } = await client.get('/states');
  //     return data;
  //   } catch (error) {
  //     logAxiosError(error, 'getStates');
  //     logger.info('[HA Axios getStates] URL:', `${HA_URL}/api/states`);
  //     throw new Error('Failed to fetch Home Assistant states');
  //   }
  // },

  async getStates() {
    const { HA_URL, HA_TOKEN } = getHAConfig();
    console.log('[HA Axios getStates] URL:', HA_URL ? HA_URL : '<empty>');
    try {
      const res = await axios.get(`${HA_URL}/api/states`, {
        headers: { Authorization: `Bearer ${HA_TOKEN}` },
        timeout: 8000
      });
      return res.data;
    } catch (error) {
      console.error('[HA Axios getStates] URL:', HA_URL);
      if (error.response) {
        console.error('Response error:', error.response.status, error.response.data);
      } else if (error.request) {
        console.error('No response received; request info:', error.request);
      } else {
        console.error('Axios error message:', error.message);
      }
      throw error;
    }
  },

  async getEntityState(entityId) {
    if (!entityId) throw new Error('Entity ID is required');
    try {
      const { data } = await client.get(`/states/${entityId}`);
      return data;
    } catch (error) {
      logAxiosError(error, `getEntityState ${entityId}`);
      throw new Error(`Failed to fetch state for ${entityId}`);
    }
  },

  async getServices() {
    try {
      const { data } = await client.get('/services');
      return data;
    } catch (error) {
      logAxiosError(error, 'getServices');
      throw new Error('Failed to fetch Home Assistant services');
    }
  },

  async callService(domain, service, payload = {}) {
    if (!domain || !service) throw new Error('Domain and service are required');
    try {
      const { data } = await client.post(`/services/${domain}/${service}`, payload);
      return data;
    } catch (error) {
      logAxiosError(error, `callService ${domain}.${service}`);
      throw new Error(`Failed to execute service ${domain}.${service}`);
    }
  },

  async getErrorLog() {
    try {
      const { data } = await client.get('/error_log', { responseType: 'text' });
      return data;
    } catch (error) {
      logAxiosError(error, 'getErrorLog');
      throw new Error('Failed to fetch Home Assistant error log');
    }
  },

  async getCameraStream(entityId) {
    if (!entityId) throw new Error('Entity ID is required');
    try {
      const response = await client.get(`/camera_proxy/${entityId}`, { responseType: 'stream' });
      return response;
    } catch (error) {
      logAxiosError(error, `getCameraStream ${entityId}`);
      throw new Error(`Failed to fetch camera ${entityId}`);
    }
  },

  /**
   * Obtiene la imagen de una cámara de Home Assistant como Buffer binario.
   * @param {string} entityId
   * @returns {Promise<Buffer>}
   */
  async getCameraImageBuffer(entityId) {
    if (!entityId) throw new Error('Entity ID is required');
    try {
      const response = await client.get(`/camera_proxy/${entityId}`, {
        responseType: 'arraybuffer', // ArrayBuffer => Node.js Buffer
      });
      return response.data;
    } catch (error) {
      logAxiosError(error, `getCameraImageBuffer ${entityId}`);
      const errorMessage = error.response
        ? `HA API responded with status ${error.response.status}`
        : error.message;
      throw new Error(`Failed to fetch camera image for ${entityId}: ${errorMessage}`);
    }
  },

  async getConfig() {
    try {
      const { data } = await client.get('/config');
      return data;
    } catch (error) {
      logAxiosError(error, 'getConfig');
      throw new Error('Failed to fetch Home Assistant config');
    }
  },

  async getComponents() {
    try {
      const { data } = await client.get('/components');
      return data;
    } catch (error) {
      logAxiosError(error, 'getComponents');
      throw new Error('Failed to fetch Home Assistant components');
    }
  },

  async getEvents() {
    try {
      const { data } = await client.get('/events');
      return data;
    } catch (error) {
      logAxiosError(error, 'getEvents');
      throw new Error('Failed to fetch Home Assistant events');
    }
  },

  async getHistory(period = '') {
    try {
      const { data } = await client.get(`/history/period/${period}`);
      return data;
    } catch (error) {
      logAxiosError(error, 'getHistory');
      throw new Error('Failed to fetch Home Assistant history');
    }
  },

  async getLogbook(period = '') {
    try {
      const { data } = await client.get(`/logbook/${period}`);
      return data;
    } catch (error) {
      logAxiosError(error, 'getLogbook');
      throw new Error('Failed to fetch Home Assistant logbook');
    }
  },
};

module.exports = HomeAssistantService;

const HomeAssistantService = require('~/server/services/HomeAssistantService');
const { getStructuredZones } = require('~/server/utils/ha_helpers');
const { logger } = require('@librechat/data-schemas');

const HomeAssistantController = {
  async getDashboardData(req, res) {
    try {
      const states = await HomeAssistantService.getStates();
      const structuredData = getStructuredZones(states);

      res.status(200).json({
        timestamp: new Date().toISOString(),
        total_zones: Object.keys(structuredData).length,
        total_entities: states.length,
        zones: structuredData,
      });
    } catch (error) {
      logger.error('Error fetching dashboard data', { error });
      res.status(500).json({ message: error.message || 'Internal server error' });
    }
  },


  async executeCommand(req, res) {
    const { domain, service, entity_id, data } = req.body;
    if (!domain || !service || !entity_id) {
      return res.status(400).json({ message: 'Missing domain, service, or entity_id' });
    }

    try {
      const result = await HomeAssistantService.callService(domain, service, {
        entity_id,
        ...(data || {}),
      });
      res.status(200).json({ success: true, result });
    } catch (error) {
      logger.error('Error executing HA command', { domain, service, entity_id, error });
      res.status(500).json({ message: error.message || 'Internal server error' });
    }
  },

  async getStates(req, res) {
    try {
      const states = await HomeAssistantService.getStates();
      res.status(200).json(states);
    } catch (error) {
      logger.error('Error fetching HA states', { error });
      res.status(500).json({ message: error.message || 'Internal server error' });
    }
  },

  async getEntityState(req, res) {
    const { entityId } = req.params;
    if (!entityId) return res.status(400).json({ message: 'Missing entityId parameter' });

    try {
      const state = await HomeAssistantService.getEntityState(entityId);
      if (!state) return res.status(404).json({ message: 'Entity not found' });
      res.status(200).json(state);
    } catch (error) {
      logger.error(`Error fetching state for ${entityId}`, { error });
      res.status(500).json({ message: error.message || 'Internal server error' });
    }
  },

  async getServices(req, res) {
    try {
      const services = await HomeAssistantService.getServices();
      res.status(200).json(services);
    } catch (error) {
      logger.error('Error fetching HA services', { error });
      res.status(500).json({ message: error.message || 'Internal server error' });
    }
  },

  async getErrorLog(req, res) {
    try {
      const data = await HomeAssistantService.getErrorLog();
      res.type('text').send(data);
    } catch (error) {
      logger.error('Error fetching HA error log', { error });
      res.status(500).send(error.message || 'Internal server error');
    }
  },

  async getCameraStream(req, res) {
    const { entityId } = req.params;
    if (!entityId) return res.status(400).send('Missing entityId');

    try {
      const response = await HomeAssistantService.getCameraStream(entityId);
      res.setHeader('Content-Type', response.headers['content-type']);
      response.data.pipe(res);
    } catch (error) {
      logger.error(`Error fetching camera ${entityId}`, { error });
      res.status(500).send(error.message || 'Internal server error');
    }
  },

  async getConfig(req, res) {
    try {
      const data = await HomeAssistantService.getConfig();
      res.status(200).json(data);
    } catch (error) {
      logger.error('Error fetching HA config', { error });
      res.status(500).json({ message: error.message || 'Internal server error' });
    }
  },

  async getComponents(req, res) {
    try {
      const data = await HomeAssistantService.getComponents();
      res.status(200).json(data);
    } catch (error) {
      logger.error('Error fetching HA components', { error });
      res.status(500).json({ message: error.message || 'Internal server error' });
    }
  },

  async getEvents(req, res) {
    try {
      const data = await HomeAssistantService.getEvents();
      res.status(200).json(data);
    } catch (error) {
      logger.error('Error fetching HA events', { error });
      res.status(500).json({ message: error.message || 'Internal server error' });
    }
  },

  async getHistory(req, res) {
    const { timestamp } = req.params;
    try {
      const data = await HomeAssistantService.getHistory(timestamp || '');
      res.status(200).json(data);
    } catch (error) {
      logger.error('Error fetching HA history', { error });
      res.status(500).json({ message: error.message || 'Internal server error' });
    }
  },

  async getLogbook(req, res) {
    const { timestamp } = req.params;
    try {
      const data = await HomeAssistantService.getLogbook(timestamp || '');
      res.status(200).json(data);
    } catch (error) {
      logger.error('Error fetching HA logbook', { error });
      res.status(500).json({ message: error.message || 'Internal server error' });
    }
  },
};

module.exports = HomeAssistantController;

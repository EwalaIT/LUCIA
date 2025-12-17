const express = require('express');
const HomeAssistantController = require('~/server/controllers/HomeAssistantController');

const router = express.Router();

// Dashboard y estados
router.get('/dashboard', HomeAssistantController.getDashboardData);
router.get('/states', HomeAssistantController.getStates);
router.get('/states/:entityId', HomeAssistantController.getEntityState);

// Servicios y comandos
router.get('/services', HomeAssistantController.getServices);
router.post('/command', HomeAssistantController.executeCommand);

// Config, componentes y eventos
router.get('/config', HomeAssistantController.getConfig);
router.get('/components', HomeAssistantController.getComponents);
router.get('/events', HomeAssistantController.getEvents);

// Historial y logbook
router.get('/history/period/:timestamp?', HomeAssistantController.getHistory);
router.get('/logbook/:timestamp?', HomeAssistantController.getLogbook);

// Error logs
router.get('/error_log', HomeAssistantController.getErrorLog);

// Cámara
router.get('/camera_proxy/:entityId', HomeAssistantController.getCameraStream);

module.exports = router;
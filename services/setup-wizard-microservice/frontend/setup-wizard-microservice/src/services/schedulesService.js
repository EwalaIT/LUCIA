import axios from "axios";

const API_BASE = import.meta.env.VITE_SETUP_WIZARD_API_BASE_URL || "http://setup-wizard-backend:8080/api";


/**
 * COMPANY (STEP 1)
 * -------------------------------------------------- */

/**
 * Get current company (if exists)
 * GET /setup/company
 */
export const loadCompany = async () => {
    try {
        const res = await axios.get(`${API_BASE}/setup/company`);
        return res.data; // { exists: boolean, company?: {...} }
    } catch (error) {
        console.error("Error loading company:", error);
        throw error;
    }
};

/**
 * Create or update company.
 *
 * - Si NO existe compañía -> POST /setup/company
 * - Si ya existe -> PUT /setup/company (solo actualiza campos modificados en backend)
 *
 * Devuelve siempre el objeto de respuesta del backend.
 */
export const saveCompany = async (companyData) => {
    try {
        // Primero miramos si ya existe
        const current = await loadCompany();
        if (!current.exists) {
            const res = await axios.post(`${API_BASE}/setup/company`, companyData);
            return res.data; // { created: true, company_id }
        } else {
            const res = await axios.put(`${API_BASE}/setup/company`, companyData);
            return res.data; // { updated: boolean }
        }
    } catch (error) {
        console.error("Error saving company:", error);
        throw error;
    }
};

/**
 * ENTITY SELECTION (STEP 2)
 * -------------------------------------------------- */

/**
 * Update selected entities
 * PUT /setup/entities
 * body: { selected: [entityIds] }
 */
export const updateSelectedEntities = async (selectedEntities) => {
    try {
        const res = await axios.put(`${API_BASE}/setup/entities`, {
            selected: Array.from(selectedEntities),
        });
        return res.data; // { ok: true }
    } catch (error) {
        console.error("Error updating selected entities:", error);
        throw error;
    }
};

/**
 * Get selected entities (helper, puede ser útil para otros módulos)
 * GET /entities/selected
 */
export const getSelectedEntities = async () => {
    try {
        const res = await axios.get(`${API_BASE}/entities/selected`);
        return res.data; // array de entidades seleccionadas
    } catch (error) {
        console.error("Error fetching selected entities:", error);
        throw error;
    }
};

/**
 * TEMPERATURE RULES (STEP 3)
 * -------------------------------------------------- */

export const loadSetupSchedules = async () => {
    try {
        const res = await axios.get(`${API_BASE}/setup/schedules`);
        return res.data; // array de schedules
    } catch (error) {
        console.error("Error loading setup schedules:", error);
        throw error;
    }
};


export const saveSetupSchedules = async (schedules) => {
    try {
        const res = await axios.post(`${API_BASE}/setup/schedules/bulk`, {
            schedules,
        });
        return res.data; // { saved: true, count }
    } catch (error) {
        console.error("Error saving setup schedules:", error);
        throw error;
    }
};


/**
 * Get all temperature rules
 * GET /setup/temperature-rules
 */
export const getTemperatureRules = async () => {
    try {
        const res = await axios.get(`${API_BASE}/setup/temperature-rules`);
        return res.data; // array de reglas
    } catch (error) {
        console.error("Error fetching temperature rules:", error);
        throw error;
    }
};

/**
 * Create new temperature rule
 * POST /setup/temperature-rules
 * body: { zone_id, min_temp, max_temp, days, start_time, end_time }
 */
export const createTemperatureRule = async (rule) => {
    try {
        const res = await axios.post(`${API_BASE}/setup/temperature-rules`, rule);
        return res.data; // { created: true, id }
    } catch (error) {
        console.error("Error creating temperature rule:", error);
        throw error;
    }
};

export const saveTemperatureRules = async (rules) => {
    try {
        const res = await axios.post(
            `${API_BASE}/setup/temperature-rules/bulk`,
            { rules }
        );
        return res.data; // { saved: true, count }
    } catch (error) {
        console.error("Error saving temperature rules:", error);
        throw error;
    }
};
/**
 * Update temperature rule
 * PUT /setup/temperature-rules/:id
 */
export const updateTemperatureRule = async (ruleId, updates) => {
    try {
        const res = await axios.put(
            `${API_BASE}/setup/temperature-rules/${ruleId}`,
            updates
        );
        return res.data; // { updated: true }
    } catch (error) {
        console.error("Error updating temperature rule:", error);
        throw error;
    }
};

/**
 * Delete temperature rule
 * DELETE /setup/temperature-rules/:id
 */
export const deleteTemperatureRule = async (ruleId) => {
    try {
        const res = await axios.delete(
            `${API_BASE}/setup/temperature-rules/${ruleId}`
        );
        return res.data; // { deleted: true }
    } catch (error) {
        console.error("Error deleting temperature rule:", error);
        throw error;
    }
};
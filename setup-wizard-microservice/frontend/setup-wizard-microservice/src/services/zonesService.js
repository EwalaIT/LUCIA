import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080/api";

/**
 * Zones and Entities Service
 */
export const getZones = async () => {
    try {
        const response = await axios.get(`${API_BASE}/ha/zones`);
        return response.data;
    } catch (error) {
        console.error("Error fetching zones:", error);
        return [];
    }
};

export const getEntities = async () => {
    try {
        const response = await axios.get(`${API_BASE}/ha/entities`);
        return response.data;
    } catch (error) {
        console.error("Error fetching entities:", error);
        return [];
    }
};

/**
 * Create a zone manually (optional feature)
 */
export const createZone = async (zone) => {
    try {
        const res = await axios.post(`${API_BASE}/setup/zones`, zone);
        return res.data;
    } catch (error) {
        console.error("Error creating zone:", error);
        throw error;
    }
};

/**
 * Update a zone
 */
export const updateZone = async (zoneId, updates) => {
    try {
        const res = await axios.put(`${API_BASE}/setup/zones/${zoneId}`, updates);
        return res.data;
    } catch (error) {
        console.error("Error updating zone:", error);
        throw error;
    }
};

/**
 * Delete a zone
 */
export const deleteZone = async (zoneId) => {
    try {
        const res = await axios.delete(`${API_BASE}/setup/zones/${zoneId}`);
        return res.data;
    } catch (error) {
        console.error("Error deleting zone:", error);
        throw error;
    }
};

/**
 * Get HA summary (requires setup_id in POST)
 * @param {number} setupId
 * @returns {Promise<{devices:[], zones:[], entities:[]}>}
 */
export const getHaSummary = async () => {
    try {
        const res = await axios.post(`${API_BASE}/ha/summary`, {});
        return res.data;
    } catch (error) {
        console.error("Error fetching HA summary:", error);
        throw error;
    }
};
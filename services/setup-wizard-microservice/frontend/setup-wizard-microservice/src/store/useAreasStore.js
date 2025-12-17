// store/useAreasStore.js
import { create } from "zustand";
import { getHaSummary } from "../services/zonesService";
import {
    getTemperatureRules,
    createTemperatureRule,
    updateTemperatureRule,
    deleteTemperatureRule,
} from "../services/schedulesService";

export const useAreasStore = create((set, get) => ({
    areas: [],
    devices: [],
    entities: [],
    temperatureRules: [],
    selectedAreaId: null,

    loading: false,
    error: null,

    /**
     * Load data from HA + temperature rules
     */
    loadAll: async () => {
        set({ loading: true, error: null });

        try {
            const [summary, rules] = await Promise.all([
                getHaSummary(),
                getTemperatureRules(),
            ]);

            set({
                areas: summary.areas || [],
                devices: summary.devices || [],
                entities: summary.entities || [],
                temperatureRules: rules || [],
                loading: false,
            });
        } catch (err) {
            set({
                error: err?.message || "Failed to load areas and rules",
                loading: false,
            });
        }
    },

    /**
     * Select area (used in UI)
     */
    selectArea: (areaId) => set({ selectedAreaId: areaId }),

    /**
     * Get rules filtered by the selected area
     */
    temperatureRulesForSelectedArea: () => {
        const { selectedAreaId, temperatureRules } = get();
        if (!selectedAreaId) return [];
        return temperatureRules.filter((r) => r.area_id === selectedAreaId);
    },

    /**
     * Create a temperature rule
     */
    addTemperatureRule: async (ruleData) => {
        set({ loading: true, error: null });

        try {
            const res = await createTemperatureRule(ruleData);
            const newRule = { ...ruleData, id: res.id };

            set({
                temperatureRules: [...get().temperatureRules, newRule],
                loading: false,
            });

            return newRule;
        } catch (err) {
            set({
                error: err?.message || "Failed to create temperature rule",
                loading: false,
            });
            throw err;
        }
    },

    /**
     * Update rule
     */
    editTemperatureRule: async (ruleId, updates) => {
        set({ loading: true, error: null });

        try {
            await updateTemperatureRule(ruleId, updates);

            set({
                temperatureRules: get().temperatureRules.map((r) =>
                    r.id === ruleId ? { ...r, ...updates } : r
                ),
                loading: false,
            });
        } catch (err) {
            set({
                error: err?.message || "Failed to update rule",
                loading: false,
            });
            throw err;
        }
    },

    /**
     * Delete rule
     */
    removeTemperatureRule: async (ruleId) => {
        set({ loading: true, error: null });

        try {
            await deleteTemperatureRule(ruleId);

            set({
                temperatureRules: get().temperatureRules.filter((r) => r.id !== ruleId),
                loading: false,
            });
        } catch (err) {
            set({
                error: err?.message || "Failed to delete rule",
                loading: false,
            });
            throw err;
        }
    },
}));

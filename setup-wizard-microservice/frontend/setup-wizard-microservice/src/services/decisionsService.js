import axios from "axios"

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080/api"

/**
 * Get all AI agent decisions with optional date filter
 * POST /decisions/list
 * @param {string} date - Optional date filter in YYYY-MM-DD format
 */
export const getDecisions = async (date = null, page = 1, per_page = 10, sort = "desc") => {
    try {
        const res = await axios.post(`${API_BASE}/decisions/list`, {
            date,
            page,
            per_page,
            sort
        })
        return res.data
    } catch (error) {
        console.error("Error loading decisions:", error)
        throw error
    }
}


/**
 * Update decision confidence and notes
 * POST /decisions/update
 * body: { id, confidence, notes }
 */
export const updateDecision = async (id, confidence, notes) => {
    try {
        const res = await axios.post(`${API_BASE}/decisions/update`, {
            id,
            confidence,
            notes,
        })
        return res.data
    } catch (error) {
        console.error("Error updating decision:", error)
        throw error
    }
}

/**
 * Retrieves the generated rule proposals and CoT for a given decision.
 * POST /decisions/proposals
 * body: { decision_id }
*/
export const getRuleProposals = async (decision_id) => {
    try {
        const res = await axios.post(`${API_BASE}/decisions/proposals`, {
            decision_id,
        });

        const data = res.data || {};

        // Normalizar rule_proposals_json: puede venir como string JSON o ya objeto/array
        let proposals = data.rule_proposals_json ?? null;
        if (typeof proposals === "string" && proposals.length > 0) {
            try {
                proposals = JSON.parse(proposals);
            } catch (e) {
                // Si no es JSON válido, log y dejarlo como string (se manejará en el componente)
                console.warn("getRuleProposals: rule_proposals_json is not valid JSON", e);
                proposals = null;
            }
        }

        return {
            ...data,
            rule_proposals_json: proposals,
        };
    } catch (error) {
        // Normalizar error para que el frontend lo pueda mostrar coherentemente
        const message =
            error?.response?.data?.error ||
            error?.response?.data?.message ||
            error?.message ||
            "Unknown error";

        console.error(`Error fetching rule proposals for ID ${decision_id}:`, message);

        // Lanzar para que el componente catch lo reciba
        throw new Error(message);
    }
};
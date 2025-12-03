import axios from "axios"

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080/api"

// axios instance con timeout + headers
const api = axios.create({
    baseURL: API_BASE,
    timeout: 8000,
    headers: {
        "Content-Type": "application/json",
    },
})

export const getRules = async (filters = {}) => {
    const res = await api.post("/rules/list", filters)
    return res.data
}

export const createRule = async (ruleData) => {
    const res = await api.post("/rules/create", ruleData)
    return res.data
}

export const updateRule = async (id, updates) => {
    const res = await api.post(`/rules/update`, { id, ...updates })
    return res.data
}

export const deleteRule = async (id, hardDelete = false) => {
    const res = await api.post(`/rules/delete`, {
        id,
        hard_delete: hardDelete,
    })
    return res.data
}

export const toggleRule = async (id) => {
    const res = await api.post(`/rules/toggle`, { id })
    return res.data
}

/**
 * Sends the user-approved list of rule proposals (from the draft) to the backend
 * for final execution (database write).
 * POST /decisions/apply_proposals
 * body: { decision_id, accepted_proposals: Array<RuleProposal> }
 * @param {number} decision_id - The ID of the decision being finalized.
 * @param {Array<object>} accepted_proposals - The list of rule objects to execute.
 */
export const applyRuleProposals = async (decision_id, accepted_proposals) => {
    try {
        const res = await api.post("/decisions/apply_proposals", {
            decision_id,
            accepted_proposals,
        });
        return res.data;
    } catch (error) {
        const message =
            error?.response?.data?.error ||
            error?.response?.data?.message ||
            error?.message ||
            "Failed to apply proposals";
        console.error("applyRuleProposals:", message);
        throw new Error(message);
    }
};
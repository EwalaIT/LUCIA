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

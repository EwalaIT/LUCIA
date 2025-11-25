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

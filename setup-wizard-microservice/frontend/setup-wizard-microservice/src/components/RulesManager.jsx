import React, { useState, useEffect } from "react"
import { Filter, Plus, AlertCircle, Zap, Calendar, CalendarDays } from "lucide-react"
import { getRules, createRule, updateRule, deleteRule, toggleRule } from "../services/rulesService"
import RuleCard from "./RuleCard"
import CreateRuleModal from "./CreateRuleModal"

export default function RulesManager() {
    const [rules, setRules] = useState([])
    const [filteredRules, setFilteredRules] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [isModalOpen, setIsModalOpen] = useState(false)

    // Filters
    const [priorityFilter, setPriorityFilter] = useState("")
    const [activeFilter, setActiveFilter] = useState("all")
    const [creatorFilter, setCreatorFilter] = useState("")

    const priorityGroups = [
        {
            key: "immediate",
            title: "Immediate Rules",
            subtitle: "Short-term actions executed instantly.",
            icon: "zap",
            iconColor: "text-orange-600 hover:text-orange-800 transition",
        },
        {
            key: "mid_term",
            title: "Mid-Term Rules",
            subtitle: "Daily, weekly or monthly optimization goals.",
            icon: "date",
            iconColor: "text-amber-600 hover:text-amber-800 transition",
        },
        {
            key: "long_term",
            title: "Long-Term Rules",
            subtitle: "Strategic goals and behavioral learning.",
            icon: "calendar",
            iconColor: "text-indigo-600 hover:text-indigo-800 transition",
        },
    ]

    const [openGroups, setOpenGroups] = useState({
        immediate: true,
        mid_term: true,
        long_term: true
    })

    const toggleGroup = (key) => {
        setOpenGroups(prev => ({ ...prev, [key]: !prev[key] }))
    }

    useEffect(() => {
        loadRules()
    }, [])

    useEffect(() => {
        applyFilters()
    }, [rules, priorityFilter, activeFilter, creatorFilter])

    const loadRules = async () => {
        try {
            setLoading(true)
            const data = await getRules()
            setRules(data.rules)
            setError(null)
        } catch (err) {
            setError("Failed to load rules")
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const applyFilters = () => {
        let filtered = [...rules]

        if (priorityFilter) {
            filtered = filtered.filter((r) => r.priority === priorityFilter)
        }

        if (activeFilter === "active") {
            filtered = filtered.filter((r) => r.active)
        } else if (activeFilter === "inactive") {
            filtered = filtered.filter((r) => !r.active)
        }

        if (creatorFilter) {
            filtered = filtered.filter((r) => r.created_by === creatorFilter)
        }

        setFilteredRules(filtered)
    }

    const handleCreateRule = async (ruleData) => {
        try {
            await createRule(ruleData)
            loadRules()
        } catch (err) {
            setError("Failed to create rule")
            console.error(err)
        }
    }

    const handleUpdateRule = async (id, updates) => {
        try {
            await updateRule(id, updates)
            loadRules()
        } catch (err) {
            setError("Failed to update rule")
            console.error(err)
        }
    }

    const handleDeleteRule = async (id) => {
        if (!confirm("Are you sure you want to delete this rule?")) return
        try {
            await deleteRule(id, true)
            loadRules()
        } catch (err) {
            setError("Failed to delete rule")
            console.error(err)
        }
    }

    const handleToggleRule = async (id) => {
        try {
            await toggleRule(id)
            loadRules()
        } catch (err) {
            setError("Failed to toggle rule")
            console.error(err)
        }
    }

    const clearFilters = () => {
        setPriorityFilter("")
        setActiveFilter("all")
        setCreatorFilter("")
    }

    const stats = {
        total: rules.length,
        active: rules.filter((r) => r.active).length,
        immediate: rules.filter((r) => r.priority === "immediate").length,
        mid_term: rules.filter((r) => r.priority === "mid_term").length,
        long_term: rules.filter((r) => r.priority === "long_term").length,
    }

    const groupedRules = priorityGroups.reduce((acc, group) => {
        acc[group.key] = filteredRules
            .filter(r => r.priority === group.key)
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at)) // recientes primero
        return acc
    }, {})

    const displayedGroups = priorityFilter
        ? priorityGroups.filter(g => g.key === priorityFilter)
        : priorityGroups

    return (
        <div className="max-w-6xl mx-auto py-6 px-4">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                    <div>
                        <h2 className="text-2xl font-semibold text-gray-800 dark:text-gray-100">Rules Management</h2>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            Manage energy efficiency rules from evaluator agent
                        </p>
                    </div>
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors shadow-sm"
                    >
                        <Plus size={18} /> New Rule
                    </button>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                        <div className="text-2xl font-bold text-gray-800 dark:text-gray-100">{stats.total}</div>
                        <div className="text-xs text-gray-600 dark:text-gray-400">Total Rules</div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                        <div className="text-2xl font-bold text-green-600">{stats.active}</div>
                        <div className="text-xs text-gray-600 dark:text-gray-400">Active</div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                        <div className="text-2xl font-bold text-red-600">{stats.immediate}</div>
                        <div className="text-xs text-gray-600 dark:text-gray-400">Immediate</div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                        <div className="text-2xl font-bold text-amber-600">{stats.mid_term}</div>
                        <div className="text-xs text-gray-600 dark:text-gray-400">Mid-Term</div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                        <div className="text-2xl font-bold text-blue-600">{stats.long_term}</div>
                        <div className="text-xs text-gray-600 dark:text-gray-400">Long-Term</div>
                    </div>
                </div>
            </div>

            {/* Filters */}
            <div className="mb-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-2 mb-3">
                    <Filter size={16} className="text-gray-600 dark:text-gray-400" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filters</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    <select
                        value={priorityFilter}
                        onChange={(e) => setPriorityFilter(e.target.value)}
                        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">All Priorities</option>
                        <option value="immediate">Immediate</option>
                        <option value="mid_term">Mid-Term</option>
                        <option value="long_term">Long-Term</option>
                    </select>

                    <select
                        value={activeFilter}
                        onChange={(e) => setActiveFilter(e.target.value)}
                        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="all">All Status</option>
                        <option value="active">Active Only</option>
                        <option value="inactive">Inactive Only</option>
                    </select>

                    <select
                        value={creatorFilter}
                        onChange={(e) => setCreatorFilter(e.target.value)}
                        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">All Creators</option>
                        <option value="user">User</option>
                        <option value="decisor">Decisor Agent</option>
                        <option value="evaluator">Evaluator Agent</option>
                    </select>

                    <button
                        onClick={clearFilters}
                        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 transition-colors"
                    >
                        Clear Filters
                    </button>
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                    Showing {filteredRules.length} of {stats.total} rules
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2">
                    <AlertCircle size={16} className="text-red-600" />
                    <span className="text-sm text-red-800 dark:text-red-200">{error}</span>
                </div>
            )}

            {/* Rules List */}
            <div className="space-y-4">
                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <span className="text-gray-600 dark:text-gray-400">Loading rules...</span>
                    </div>
                ) : filteredRules.length === 0 ? (
                    <div className="flex items-center justify-center py-12">
                        <span className="text-gray-600 dark:text-gray-400">
                            No rules found. Create your first rule to get started.
                        </span>
                    </div>
                ) : (
                    displayedGroups.map(group => (
                        <div key={group.key} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                            {/* Header acordeón */}
                            <button
                                onClick={() => toggleGroup(group.key)}
                                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                            >
                                <div className={`flex items-center justify-center w-8 h-8 bg-gray-300 rounded-md`}>
                                    {group.icon === "zap" && <Zap size={20} className={group.iconColor} />}
                                    {group.icon === "date" && <Calendar size={20} className={group.iconColor} />}
                                    {group.icon === "calendar" && <CalendarDays size={20} className={group.iconColor}/>}
                                </div>
                                <div className="text-left flex-1">
                                    <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100">{group.title}</h3>
                                    <p className="text-xs text-gray-500 dark:text-gray-400">{group.subtitle}</p>
                                </div>
                                <span className="text-gray-400 dark:text-gray-500">{openGroups[group.key] ? "−" : "+"}</span>
                            </button>

                            {/* Contenido acordeón */}
                            {openGroups[group.key] && (
                                <div className="p-4 space-y-3">
                                    {groupedRules[group.key].length === 0 ? (
                                        <p className="text-gray-500 dark:text-gray-400 text-sm">No rules in this category.</p>
                                    ) : (
                                        groupedRules[group.key].map(rule => (
                                            <RuleCard
                                                key={rule.id}
                                                rule={rule}
                                                onUpdate={handleUpdateRule}
                                                onDelete={handleDeleteRule}
                                                onToggle={handleToggleRule}
                                            />
                                        ))
                                    )}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
            {/* Create Modal */}
            <CreateRuleModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onCreate={handleCreateRule} />
        </div>
    );
}

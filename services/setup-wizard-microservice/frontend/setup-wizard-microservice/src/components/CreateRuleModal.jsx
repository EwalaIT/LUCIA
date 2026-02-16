import React, { useState, useEffect } from "react"
import { X, Plus } from "lucide-react"

export default function CreateRuleModal({ isOpen, onClose, onCreate }) {
    const [ruleText, setRuleText] = useState("")
    const [priority, setPriority] = useState("immediate")
    const [expiresAt, setExpiresAt] = useState("")
    const [createdBy, setCreatedBy] = useState("user")
    const [dateError, setDateError] = useState("")

    const todayStr = new Date().toISOString().split("T")[0]

    const handleSubmit = (e) => {
        e.preventDefault()
        if (!ruleText.trim()) return

        if (expiresAt && expiresAt < todayStr) {
            setDateError("Expiration date cannot be in the past")
            return
        }

        onCreate({
            rule_text: ruleText,
            priority,
            expires_at: expiresAt || null,
            created_by: createdBy,
        })

        // Reset form
        setRuleText("")
        setPriority("immediate")
        setExpiresAt("")
        setCreatedBy("user")
        onClose()
    }

   

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/50 dark:bg-black/70" onClick={onClose} />

            {/* Modal */}
            <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4 p-6">
                {/* Header */}
                <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Create New Rule</h3>
                    <button
                        onClick={onClose}
                        className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                        <X size={20} className="text-gray-600 dark:text-gray-400" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Rule Text</label>
                        <textarea
                            value={ruleText}
                            onChange={(e) => setRuleText(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            rows={4}
                            placeholder="Enter the rule description..."
                            required
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Priority</label>
                            <select
                                value={priority}
                                onChange={(e) => setPriority(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="immediate">Immediate</option>
                                <option value="mid_term">Mid-Term</option>
                                <option value="long_term">Long-Term</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Created By</label>
                            <select
                                value={createdBy}
                                onChange={(e) => setCreatedBy(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="user">User</option>
                                <option value="decisor">Decisor Agent</option>
                                <option value="evaluator">Evaluator Agent</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Expires At (Optional)
                        </label>
                        <input
                            type="date"
                            value={expiresAt}
                            onChange={(e) => {
                                setExpiresAt(e.target.value)
                                setDateError("")
                            }}
                            min={todayStr}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        {dateError && (
                            <p className="text-red-600 dark:text-red-400 text-xs mt-1 flex items-center gap-1">
                                <AlertTriangle size={14} /> {dateError}
                            </p>
                        )}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-3">
                        <button
                            type="submit"
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 transition-colors"
                        >
                            <Plus size={16} /> Create Rule
                        </button>
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 bg-gray-500 text-white rounded-md text-sm font-medium hover:bg-gray-600 transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}

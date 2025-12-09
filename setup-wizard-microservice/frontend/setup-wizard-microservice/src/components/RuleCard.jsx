import React, { useState } from "react"
import { Clock, User, Calendar, Edit2, Trash2, ToggleLeft, ToggleRight, Save, X, AlertTriangle } from "lucide-react"

export default function RuleCard({ rule, onUpdate, onDelete, onToggle }) {
    const [isEditing, setIsEditing] = useState(false)
    const [editedText, setEditedText] = useState(rule.rule_text)
    const [editedPriority, setEditedPriority] = useState(rule.priority)
    const [dateError, setDateError] = useState("")
    
    const todayStr = new Date().toISOString().split("T")[0]

    const initialExpires = rule.expires_at && rule.expires_at >= todayStr
        ? rule.expires_at
        : todayStr

    const [editedExpires, setEditedExpires] = useState(initialExpires)

    const isExpired = rule.expires_at && rule.expires_at < todayStr

    const priorityColors = {
        immediate: "border-red-500 bg-red-50 dark:bg-red-950/20",
        mid_term: "border-amber-500 bg-amber-50 dark:bg-amber-950/20",
        long_term: "border-blue-500 bg-blue-50 dark:bg-blue-950/20",
    }

    const priorityLabels = {
        immediate: "Immediate",
        mid_term: "Mid-Term",
        long_term: "Long-Term",
    }

    const creatorLabels = {
        user: "User",
        decisor: "Decisor Agent",
        evaluator: "Evaluator Agent",
        chat: "Chat Commander",
    }

    const handleSave = () => {
        if (editedExpires && editedExpires < todayStr) {
            setDateError("Expiration date cannot be in the past")
            return
        }

        onUpdate(rule.id, {
            rule_text: editedText,
            priority: editedPriority,
            expires_at: editedExpires || null,
        })
        setIsEditing(false)
    }

    const handleCancel = () => {
        setEditedText(rule.rule_text)
        setEditedPriority(rule.priority)
        setEditedExpires(rule.expires_at || "")
        setIsEditing(false)
    }

    const chipBase =
        "inline-flex items-center px-2 py-1 rounded-md text-xs font-semibold border";

    return (
        <div
            className={`relative rounded-lg border-l-4 p-4 shadow-sm transition-all ${priorityColors[rule.priority]} ${!rule.active ? "opacity-50" : ""}`}
        >

            {/* Expired Banner */}
            {isExpired && (
                <div className="absolute top-2 right-[-30px] rotate-45 bg-red-600 text-white px-6 py-1 text-xs font-bold pointer-events-none shadow-lg z-10">
                    EXPIRED
                </div>
            )}

            {/* Header */}
            <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2 flex-wrap">
                    <span
                        className={`${chipBase} bg-purple-100 border-purple-400 dark:bg-purple-900/30 dark:border-purple-700`}
                    >
                        <User size={13} className="mr-1" />
                        {creatorLabels[rule.created_by] || rule.created_by}
                    </span>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                    {!isEditing && (
                        <>
                            <button
                                onClick={() => onToggle(rule.id)}
                                className="p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                title={rule.active ? "Deactivate" : "Activate"}
                            >
                                {rule.active ? (
                                    <ToggleRight size={18} className="text-green-600" />
                                ) : (
                                    <ToggleLeft size={18} className="text-gray-400" />
                                )}
                            </button>
                            <button
                                onClick={() => setIsEditing(true)}
                                className="p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                title="Edit"
                            >
                                <Edit2 size={16} className="text-blue-600" />
                            </button>
                            <button
                                onClick={() => onDelete(rule.id)}
                                className="p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                title="Delete"
                            >
                                <Trash2 size={16} className="text-red-600" />
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Content */}
            {isEditing ? (
                <div className="space-y-3">
                    <textarea
                        value={editedText}
                        onChange={(e) => setEditedText(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={3}
                    />
                    <div className="flex gap-3">
                        <select
                            value={editedPriority}
                            onChange={(e) => setEditedPriority(e.target.value)}
                            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="immediate">Immediate</option>
                            <option value="mid_term">Mid-Term</option>
                            <option value="long_term">Long-Term</option>
                        </select>

                        <input
                            type="date"
                            value={editedExpires}
                            onChange={(e) => {
                                setEditedExpires(e.target.value)
                                setDateError("")
                            }}
                            min={todayStr}
                            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="Expires at"
                        />
                        {dateError && (
                            <p className="text-red-600 dark:text-red-400 text-xs mt-1 flex items-center gap-1">
                                <AlertTriangle size={14} /> {dateError}
                            </p>
                        )}
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={handleSave}
                            className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded-md text-sm hover:bg-green-700 transition-colors"
                        >
                            <Save size={14} /> Save
                        </button>
                        <button
                            onClick={handleCancel}
                            className="flex items-center gap-1 px-3 py-1.5 bg-gray-500 text-white rounded-md text-sm hover:bg-gray-600 transition-colors"
                        >
                            <X size={14} /> Cancel
                        </button>
                    </div>
                </div>
            ) : (
                <div className="space-y-2">
                        <p
                            className={`text-sm text-gray-800 dark:text-gray-100 leading-relaxed 
    ${!rule.active ? "line-through" : ""}`}
                        >
                            {rule.rule_text}
                        </p>

                    {/* Metadata */}
                    <div className="flex flex-wrap gap-3 text-xs text-gray-600 dark:text-gray-400">
                            <span
                                className={`${chipBase} bg-blue-100 border-blue-400 dark:bg-blue-900/30 dark:border-blue-700`}
                            >
                                <Calendar size={13} className="mr-1" />
                                Created: {new Date(rule.created_at).toLocaleDateString()}
                            </span>

                            {/* Expires */}
                            {rule.expires_at && (
                                <span
                                    className={`${chipBase} bg-red-100 border-red-400 dark:bg-red-900/30 dark:border-red-700`}
                                >
                                    <Clock size={13} className="mr-1" />
                                    Expires: {new Date(rule.expires_at).toLocaleDateString()}
                                </span>
                            )}

                            {/* Modified */}
                            {rule.last_modified && (
                                <span
                                    className={`${chipBase} bg-amber-100 border-amber-400 dark:bg-amber-900/30 dark:border-amber-700`}
                                >
                                    <Clock size={13} className="mr-1" />
                                    Modified: {new Date(rule.last_modified).toLocaleDateString()}
                                </span>
                            )}
                    </div>
                </div>
            )}
        </div>
    )
}

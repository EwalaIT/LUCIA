import { useState } from "react";

export default function DecisionFeedback({
    type,
    onSave,
    onCancel,
    initialConfidence,
    initialNotes
}) {
    const [confidence, setConfidence] = useState(initialConfidence);
    const [notes, setNotes] = useState(initialNotes);

    const handleSave = () => {
        const conf = type === "incorrect" ? 0 : confidence;
        onSave(conf, notes);
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-4 border border-gray-300 dark:border-gray-600">
            {/* Nivel de confianza */}
            <div className="mb-4">
                <label className="text-xs text-gray-600 dark:text-gray-300 font-medium">
                    {type === "correct"
                        ? "Confidence Level (0.0 - 1.0)"
                        : "Confidence: 0.0 (incorrect)"}
                </label>

                {type === "correct" ? (
                    <>
                        <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.1"
                            value={confidence}
                            onChange={(e) => setConfidence(parseFloat(e.target.value))}
                            className="w-full mt-1"
                        />
                        <div className="text-center text-base font-semibold mt-1">
                            {confidence.toFixed(1)}
                        </div>
                    </>
                ) : (
                    <div className="text-center text-base font-bold text-red-600 mt-1">
                        0.0
                    </div>
                )}
            </div>

            {/* Notas */}
            <div className="mb-3">
                <label className="text-xs text-gray-600 dark:text-gray-300 font-medium">
                    {type === "correct" ? "Notes (optional)" : "Explanation"}
                </label>

                <textarea
                    className="w-full mt-1 p-2 text-sm border rounded-lg dark:bg-gray-900 dark:border-gray-700"
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder={type === "correct" ? "Add notes..." : "Explain why it's incorrect"}
                />
            </div>

            {/* Botones */}
            <div className="flex justify-end gap-2">
                <button
                    onClick={onCancel}
                    className="px-3 py-1.5 text-xs border rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                    Cancel
                </button>

                <button
                    onClick={handleSave}
                    className={`px-3 py-1.5 text-xs text-white rounded-md ${type === "correct"
                            ? "bg-green-500 hover:bg-green-600"
                            : "bg-red-500 hover:bg-red-600"
                        }`}
                >
                    Save
                </button>
            </div>
        </div>
    );
}

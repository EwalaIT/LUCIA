import { useState, useRef, useEffect } from "react";
import { Check, X, FileEdit } from "lucide-react";
import DecisionFeedback from "./DecisionFeedback";

export default function DecisionBubble({ decision, onUpdate }) {
    const [showFeedback, setShowFeedback] = useState(null);
    const [position, setPosition] = useState({ top: 0, left: 0 });
    const correctBtnRef = useRef(null);
    const incorrectBtnRef = useRef(null);
    const bubbleRef = useRef(null);
    const feedbackRef = useRef(null);

    /* --- Reposicionamiento inteligente del tooltip --- */
    const openFeedback = (type, btnRef) => {
        const btnRect = btnRef.current.getBoundingClientRect();
        const bubbleRect = bubbleRef.current.getBoundingClientRect();

        const TOP_OFFSET = 10;

        let left = btnRect.left - bubbleRect.left + btnRect.width / 2;
        let top = btnRect.bottom - bubbleRect.top + TOP_OFFSET;

        const FEEDBACK_WIDTH = 300;
        const PADDING = 20;

        if (left + FEEDBACK_WIDTH > bubbleRect.width - PADDING) {
            left = bubbleRect.width - FEEDBACK_WIDTH - PADDING;
        }
        if (left < PADDING) left = PADDING;

        setPosition({ top, left });
        setShowFeedback(type);
    };

    const handleCorrect = () => openFeedback("correct", correctBtnRef);
    const handleIncorrect = () => openFeedback("incorrect", incorrectBtnRef);

    const handleSaveFeedback = async (confidence, notes) => {
        await onUpdate(decision.id, confidence, notes);
        setShowFeedback(null);
    };

    const statusColors = {
        FAILED: "bg-red-500 text-white",
        EXECUTED: "bg-green-500 text-white",
        PENDING: "bg-yellow-300 text-gray-900",
        REJECTED: "bg-gray-500 text-white",
        RULES_READY: "bg-blue-500 text-white",
        IN_PROGRESS: "bg-orange-400 text-gray-900"
    };

    useEffect(() => {
        if (!showFeedback) return;

        const handleClickOutside = (e) => {
            if (
                feedbackRef.current &&
                !feedbackRef.current.contains(e.target) &&
                !correctBtnRef.current.contains(e.target) &&
                !incorrectBtnRef.current.contains(e.target)
            ) {
                setShowFeedback(null); // mismo efecto que cancelar
            }
        };

        document.addEventListener("mousedown", handleClickOutside);

        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [showFeedback]);

    return (
        <div className="flex justify-start w-full relative">
            <div
                ref={bubbleRef}
                className="relative bg-white dark:bg-gray-800 p-4 rounded-2xl shadow-md w-full max-w-2xl border border-gray-200 dark:border-gray-700"
            >
                {/* Fecha + Estado */}
                <div className="flex justify-between items-center mb-2">
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                        {decision.created_at ? new Date(decision.created_at).toLocaleString() : ""}
                    </span>

                    <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${statusColors[decision.status]}`}
                    >
                        {decision.status}
                    </span>
                </div>

                {/* Información del mensaje */}
                <div className="space-y-1 text-sm text-gray-700 dark:text-gray-200">
                    <div><strong>Goal:</strong> {decision.goal || "N/A"}</div>
                    <div><strong>Reasoning:</strong> {decision.reasoning || "N/A"}</div>
                    <div><strong>Executed Action:</strong> {decision.executed_action || "N/A"}</div>
                    <div><strong>Action Result:</strong> {decision.action_result ? JSON.stringify(decision.action_result) : "N/A"}</div>
                    <div><strong>Target Entity:</strong> {decision.target_entity || "N/A"}</div>
                </div>

                {/* Botones feedback */}
                <div className="flex justify-end gap-2 mt-3">
                    {decision.rule_status === "RULES_READY" || decision.rule_status === "IN_PROGRESS" ? (
                        <button
                            onClick={() => onReviewRules(decision.id)}
                            className="px-3 py-1 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-700 text-white shadow flex items-center gap-1"
                        >
                            <FileEdit size={16} />
                            {decision.rule_status === "IN_PROGRESS" ? "Rules Generating..." : "Review Rules"}
                        </button>
                    ) : (
                        // Botones de Feedback normal (solo si no se ha enviado feedback o si no hay reglas listas)
                        <>
                            <button
                                ref={correctBtnRef}
                                onClick={handleCorrect}
                                disabled={decision.notes !== null} // Deshabilitar si ya se dio feedback
                                className="w-8 h-8 flex items-center justify-center rounded-md bg-green-500 hover:bg-green-600 text-white shadow disabled:bg-gray-400"
                            >
                                <Check size={18} />
                            </button>

                            <button
                                ref={incorrectBtnRef}
                                onClick={handleIncorrect}
                                disabled={decision.notes !== null} // Deshabilitar si ya se dio feedback
                                className="w-8 h-8 flex items-center justify-center rounded-md bg-red-500 hover:bg-red-600 text-white shadow disabled:bg-gray-400"
                            >
                                <X size={18} />
                            </button>
                        </>
                    )}
                </div>

                {/* Tooltip Feedback */}
                {showFeedback && (
                    <div
                        ref={feedbackRef}
                        className="absolute z-50"
                        style={{
                            top: position.top,
                            left: position.left,
                            width: 300
                        }}
                    >
                        <DecisionFeedback
                            type={showFeedback}
                            onSave={handleSaveFeedback}
                            onCancel={() => setShowFeedback(null)}
                            initialConfidence={decision.confidence ?? 0.5}
                            initialNotes={decision.notes ?? ""}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}

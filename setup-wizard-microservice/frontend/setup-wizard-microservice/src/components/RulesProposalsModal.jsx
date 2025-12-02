import { useState, useEffect, useCallback } from "react"
import { getRuleProposals } from "../services/decisionsService";
import { applyRuleProposals } from "../services/rulesService"
import { CheckCircle2, XCircle, Loader2, AlertTriangle, FileText, Zap, Clock } from "lucide-react"

const POLLING_INTERVAL = 5000 // 5 seconds
const MAX_POLLING_ATTEMPTS = 60 // 5 minutes max


export default function RulesProposalsModal({ decisionId, onClose }) {
    const [status, setStatus] = useState("LOADING")
    const [chainOfThought, setChainOfThought] = useState("")
    const [proposals, setProposals] = useState([])
    const [acceptedProposals, setAcceptedProposals] = useState([])
    const [errorMessage, setErrorMessage] = useState("")
    const [pollingAttempts, setPollingAttempts] = useState(0)

    // Polling logic
    const pollProposals = useCallback(async () => {
        try {
            const response = await getRuleProposals(decisionId)

            if (response.is_ready) {
                const parsedProposals = response.rule_proposals_json || []
                setProposals(parsedProposals)
                setAcceptedProposals(parsedProposals) // All initially accepted
                setChainOfThought(response.rule_cot || "")
                setStatus("RULES_READY")
                return true // Stop polling
            }

            setPollingAttempts((prev) => prev + 1)
            return false // Continue polling
        } catch (error) {
            console.error("Error polling proposals:", error)
            setErrorMessage("Failed to fetch rule proposals")
            setStatus("ERROR")
            return true // Stop polling on error
        }
    }, [decisionId])

    // Initial polling setup
    useEffect(() => {
        let intervalId = null
        let mounted = true

        const startPolling = async () => {
            const shouldStop = await pollProposals()
            if (shouldStop || !mounted) return

            intervalId = setInterval(async () => {
                if (pollingAttempts >= MAX_POLLING_ATTEMPTS) {
                    setErrorMessage("Timeout: Rule proposals took too long to generate")
                    setStatus("ERROR")
                    if (intervalId) clearInterval(intervalId)
                    return
                }

                const shouldStop = await pollProposals()
                if (shouldStop && intervalId) {
                    clearInterval(intervalId)
                }
            }, POLLING_INTERVAL)
        }

        startPolling()

        return () => {
            mounted = false
            if (intervalId) clearInterval(intervalId)
        }
    }, [])

    // Toggle proposal acceptance
    const toggleProposal = (index) => {
        const proposal = proposals[index];

        const exists = acceptedProposals.some(p => p.id === proposal.id);

        if (exists) {
            setAcceptedProposals(acceptedProposals.filter(p => p.id !== proposal.id));
        } else {
            setAcceptedProposals([...acceptedProposals, proposal]);
        }
    };

    // Check if proposal is accepted
    const isProposalAccepted = (index) => {
        const proposal = proposals[index];
        return acceptedProposals.includes(proposal);
    }

    // Apply rules
    const handleApplyRules = async () => {
        if (acceptedProposals.length === 0) return

        setStatus("APPLYING")
        try {
            await applyRuleProposals(decisionId, acceptedProposals)
            setStatus("APPLIED")
        } catch (error) {
            console.error("Error applying rules:", error)
            setErrorMessage("Failed to apply rules")
            setStatus("ERROR")
        }
    }

    // Reject all
    const handleRejectAll = () => {
        setStatus("REJECTED")
        onClose()
    }

    // Get action color and icon
    const getActionStyle = (action) => {
        switch (action) {
            case "CREATE":
                return {
                    color: "text-green-600 dark:text-green-400",
                    bg: "bg-green-100 dark:bg-green-900/30",
                    icon: <CheckCircle2 size={16} />,
                }
            case "MODIFY":
                return {
                    color: "text-blue-600 dark:text-blue-400",
                    bg: "bg-blue-100 dark:bg-blue-900/30",
                    icon: <FileText size={16} />,
                }
            case "DELETE":
                return {
                    color: "text-red-600 dark:text-red-400",
                    bg: "bg-red-100 dark:bg-red-900/30",
                    icon: <XCircle size={16} />,
                }
            default:
                return {
                    color: "text-gray-600 dark:text-gray-400",
                    bg: "bg-gray-100 dark:bg-gray-700/30",
                    icon: <FileText size={16} />,
                }
        }
    }

    // Get priority style
    const getPriorityStyle = (priority) => {
        switch (priority) {
            case "IMMEDIATE":
                return {
                    color: "text-red-700 dark:text-red-300",
                    bg: "bg-red-100 dark:bg-red-900/30",
                    icon: <Zap size={14} />,
                }
            case "MID_TERM":
                return {
                    color: "text-yellow-700 dark:text-yellow-300",
                    bg: "bg-yellow-100 dark:bg-yellow-900/30",
                    icon: <Calendar size={14} />,
                }
            case "LONG_TERM":
                return {
                    color: "text-gray-700 dark:text-gray-300",
                    bg: "bg-gray-100 dark:bg-gray-700/30",
                    icon: <CalendarDays size={14} />,
                }
            default:
                return {
                    color: "text-gray-700 dark:text-gray-300",
                    bg: "bg-gray-100 dark:bg-gray-700/30",
                    icon: <Clock size={14} />,
                }
        }
    }

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 font-sans antialiased">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-7xl max-h-[90vh] overflow-hidden flex flex-col transform transition-all duration-300 ease-out">

                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Rule Review & Approval</h2>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Decision ID: <span className="font-mono bg-gray-100 dark:bg-gray-700 px-1 rounded">{decisionId}</span></p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-full text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        aria-label="Close modal"
                    >
                        <XCircle size={24} />
                    </button>
                </div>

                {/* Loading State */}
                {status === "LOADING" && (
                    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-gray-50 dark:bg-gray-900">
                        <Loader2 className="animate-spin text-blue-500 mb-4" size={48} />
                        <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">Waiting for AI Rule Draft...</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                            Polling attempt {pollingAttempts + 1} of {MAX_POLLING_ATTEMPTS}
                        </p>
                    </div>
                )}

                {/* Error State */}
                {status === "ERROR" && (
                    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-red-50 dark:bg-red-900/20">
                        <AlertTriangle className="text-red-500 mb-4" size={48} />
                        <p className="text-lg font-medium text-red-600 dark:text-red-400">{errorMessage}</p>
                        <button
                            onClick={onClose}
                            className="mt-6 px-6 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 font-medium transition-colors"
                        >
                            Close
                        </button>
                    </div>
                )}

                {/* Applying State */}
                {status === "APPLYING" && (
                    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-green-50 dark:bg-green-900/20">
                        <Loader2 className="animate-spin text-green-500 mb-4" size={48} />
                        <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">Applying Rules... Please Wait.</p>
                    </div>
                )}

                {/* Applied State */}
                {status === "APPLIED" && (
                    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-green-50 dark:bg-green-900/20">
                        <CheckCircle2 className="text-green-500 mb-4" size={48} />
                        <p className="text-xl font-semibold text-green-600 dark:text-green-400">
                            Rules successfully applied and system is improved.
                        </p>
                        <button onClick={onClose} className="mt-6 px-8 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 shadow-md transition-colors">
                            Finish Review
                        </button>
                    </div>
                )}

                {/* Main Content - Rules Ready */}
                {status === "RULES_READY" && (
                    <>
                        <div className="flex-1 overflow-hidden flex">
                            {/* Left Panel - Rule Proposals */}
                            <div className="w-1/2 border-r border-gray-200 dark:border-gray-700 overflow-y-auto p-6">
                                <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4 sticky top-0 bg-white dark:bg-gray-800 pb-2 z-10">Rule Proposals (Draft)</h3>

                                <div className="space-y-4">
                                    {proposals.map((proposal, index) => {
                                        const actionStyle = getActionStyle(proposal.action)
                                        const priorityStyle = getPriorityStyle(proposal.priority)
                                        const isAccepted = isProposalAccepted(index)

                                        return (
                                            <div
                                                key={index}
                                                className={`border rounded-xl p-4 transition-all duration-200 cursor-pointer ${isAccepted
                                                        ? "border-blue-500 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/30 shadow-md"
                                                        : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/50 hover:border-blue-400"
                                                    }`}
                                                onClick={() => toggleProposal(index)}
                                            >
                                                <div className="flex items-start gap-3">
                                                    {/* Checkbox */}
                                                    <input
                                                        type="checkbox"
                                                        checked={isAccepted}
                                                        readOnly // Controlled by the div click
                                                        className="mt-1 w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                                    />

                                                    <div className="flex-1">
                                                        {/* Header - Action Type & Priority */}
                                                        <div className="flex items-center gap-2 mb-2">
                                                            <span
                                                                className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${actionStyle.bg} ${actionStyle.color}`}
                                                            >
                                                                {actionStyle.icon}
                                                                {proposal.action}
                                                            </span>

                                                            <span
                                                                className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${priorityStyle.bg} ${priorityStyle.color}`}
                                                            >
                                                                {priorityStyle.icon}
                                                                {proposal.priority.replace('_', ' ')}
                                                            </span>

                                                            {proposal.rule_id && (
                                                                <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
                                                                    ID: {proposal.rule_id}
                                                                </span>
                                                            )}
                                                        </div>

                                                        {/* Rule Text */}
                                                        <p className="text-base text-gray-800 dark:text-gray-200 font-medium leading-snug">{proposal.rule_text}</p>

                                                        {/* Additional Details */}
                                                        {(proposal.target_entity || proposal.rule_type) && (
                                                            <div className="mt-3 text-xs text-gray-600 dark:text-gray-400 space-x-3 border-t pt-2 border-gray-200 dark:border-gray-700/50">
                                                                {proposal.target_entity && (
                                                                    <span className="inline-block">
                                                                        <span className="font-semibold">Target:</span> {proposal.target_entity}
                                                                    </span>
                                                                )}
                                                                {proposal.rule_type && (
                                                                    <span className="inline-block">
                                                                        <span className="font-semibold">Type:</span> {proposal.rule_type}
                                                                    </span>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>

                                {proposals.length === 0 && (
                                    <p className="text-center text-gray-500 dark:text-gray-400 py-8">No rule proposals available</p>
                                )}
                            </div>

                            {/* Right Panel - Analysis & Actions */}
                            <div className="w-1/2 overflow-y-auto p-6 flex flex-col">
                                {/* AI Diagnosis */}
                                <div className="flex-1 mb-6">
                                    <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                                        AI Evaluator Diagnosis & Rationale
                                    </h3>

                                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-inner h-full max-h-96 overflow-y-auto">
                                        <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
                                            {chainOfThought || "No analysis available"}
                                        </p>
                                    </div>
                                </div>

                                {/* Action Buttons */}
                                <div className="pt-6 border-t border-gray-200 dark:border-gray-700 sticky bottom-0 bg-white dark:bg-gray-800">
                                    <div className="flex items-center justify-between text-base text-gray-700 dark:text-gray-300 mb-4 font-semibold">
                                        <span>
                                            Selected Rules:
                                        </span>
                                        <span className="text-blue-600 dark:text-blue-400">
                                            {acceptedProposals.length} of {proposals.length}
                                        </span>
                                    </div>

                                    <button
                                        onClick={handleApplyRules}
                                        disabled={acceptedProposals.length === 0}
                                        className="w-full py-4 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:hover:bg-gray-400 disabled:cursor-not-allowed text-white text-lg font-bold rounded-xl shadow-lg transition-all duration-300 ease-in-out transform hover:scale-[1.01] flex items-center justify-center gap-3 mb-3"
                                    >
                                        <CheckCircle2 size={24} />
                                        Apply {acceptedProposals.length} Accepted Rule{acceptedProposals.length !== 1 ? "s" : ""}
                                    </button>

                                    <button
                                        onClick={handleRejectAll}
                                        className="w-full py-3 px-4 bg-white dark:bg-gray-700 border-2 border-red-500 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 font-semibold rounded-xl transition-colors flex items-center justify-center gap-3"
                                    >
                                        <XCircle size={20} />
                                        Reject All Proposals
                                    </button>
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}
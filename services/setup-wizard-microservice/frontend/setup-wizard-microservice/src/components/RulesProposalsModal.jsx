import { useState, useEffect, useCallback, useRef } from "react"
import { getRuleProposals } from "../services/decisionsService";
import { applyRuleProposals } from "../services/rulesService"
import { CheckCircle2, XCircle, Loader2, AlertTriangle, FileText, Zap, Clock, Calendar, CalendarDays } from "lucide-react"

const MAX_TIMEOUT_MS = 70000; // 5 seconds
const POLLING_INTERVAL_MS = 6000;
const MAX_POLLING_ATTEMPTS = 60 // 5 minutes max


export default function RulesProposalsModal({ decisionId, onClose }) {
    const [status, setStatus] = useState("LOADING")
    const [chainOfThought, setChainOfThought] = useState("")
    const [proposals, setProposals] = useState([])
    const [acceptedProposals, setAcceptedProposals] = useState([])
    const [errorMessage, setErrorMessage] = useState("")
    const [pollingAttempts, setPollingAttempts] = useState(0)
    const mountedRef = useRef(false);
    const attemptsRef = useRef(0);

    const proposalId = (p, idx) => {
        if (!p) return `idx_${idx}`;
        if (p.id) return String(p.id);
        if (p.rule_id) return `rule_${p.rule_id}`;
        // fallback: hash-ish using index + rule_text
        return `idx_${idx}_${(p.rule_text || "").slice(0, 50).replace(/\s+/g, "_")}`;
    };

    // Polling logic
    const pollProposals = useCallback(async () => {
        try {
            const response = await getRuleProposals(decisionId);

            // If backend indicates explicit failure
            const ruleStatus = response.rule_status ?? response.status ?? null;
            if (ruleStatus === "RULES_FAILED") {
                setErrorMessage("AI failed to generate proposals. Please try again.");
                setStatus("ERROR");
                return true; // stop polling
            }

            if (response.is_ready || (ruleStatus === "RULES_READY")) {
                // response.rule_proposals_json is already parsed by service (or null)
                const parsedProposals = Array.isArray(response.rule_proposals_json)
                    ? response.rule_proposals_json
                    : [];

                // Defensive: ensure proposals are objects
                const normalized = parsedProposals.map((p, i) => {
                    // Some backends may use action vs action_type or uppercase/lowercase priority
                    return {
                        id: p.id ?? p.rule_id ?? `p_${i}`,
                        action_type: p.action_type ?? p.action ?? p.actionType ?? "CREATE",
                        rule_text: p.rule_text ?? p.text ?? p.rule ?? "",
                        priority: (p.priority || p.priority_level || "mid_term").toUpperCase(),
                        expires_at: p.expires_at ?? null,
                        rule_id: p.rule_id ?? null,
                        ...p,
                    };
                });

                // Mark all accepted by default
                setProposals(normalized);
                setAcceptedProposals(normalized.map((p) => proposalId(p)));
                setChainOfThought(response.rule_cot || "");
                setStatus("RULES_READY");
                return true; // stop polling
            }

            // Not ready: increment attempt counter
            attemptsRef.current = attemptsRef.current + 1;
            if (attemptsRef.current >= MAX_POLLING_ATTEMPTS) {
                setErrorMessage("Timeout: Rule proposals took too long to generate");
                setStatus("ERROR");
                return true; // stop polling
            }

            // Continue polling
            return false;
        } catch (err) {
            console.error("Polling error:", err);
            setErrorMessage(err.message || "Failed to fetch rule proposals");
            setStatus("ERROR");
            return true; // stop polling on network/server error
        }
    }, [decisionId]);


    useEffect(() => {
        mountedRef.current = true;
        attemptsRef.current = 0;
        setStatus("LOADING");
        setErrorMessage("");

        let cancelled = false;
        const startTime = Date.now();

        const tick = async () => {
            if (cancelled) return;

            const done = await pollProposals(); // usamos la función ya existente
            if (done) return; // stop polling

            // si no se completó, revisamos timeout
            if (Date.now() - startTime >= MAX_TIMEOUT_MS) {
                setStatus("ERROR");
                setErrorMessage("Timeout: Rule proposals took too long to generate");
                return;
            }

            setTimeout(tick, POLLING_INTERVAL_MS);
        };

        tick();

        return () => {
            cancelled = true;
            mountedRef.current = false;
        };
    }, [decisionId, pollProposals]);

    // Toggle proposal acceptance
    const toggleProposal = (index) => {
        const p = proposals[index];
        const id = proposalId(p, index);
        setAcceptedProposals((prev) => {
            if (prev.includes(id)) return prev.filter((x) => x !== id);
            return [...prev, id];
        });
    };

    // Check if proposal is accepted
    const isProposalAccepted = (index) => {
        const p = proposals[index];
        const id = proposalId(p, index);
        return acceptedProposals.includes(id);
    };

    // Apply rules
    const handleApplyRules = async () => {
        // build accepted objects in original shape
        const accepted = proposals.filter((_, i) => isProposalAccepted(i));

        if (accepted.length === 0) return;

        setStatus("APPLYING");
        setErrorMessage("");

        // map back to payload the backend expects (action_type + fields)
        const payloadProposals = accepted.map((p) => ({
            action_type: p.action_type,
            rule_text: p.rule_text,
            priority: p.priority,
            expires_at: p.expires_at ?? null,
            rule_id: p.rule_id ?? null,
            target_entity: p.target_entity ?? null,
            rule_type: p.rule_type ?? null,
        }));

        try {
            const res = await applyRuleProposals(decisionId, payloadProposals);

            // applyRuleProposals returns the backend result; check for applied flag
            if (res && (res.applied === true || res.status === "success" || res.details)) {
                setStatus("APPLIED");
                // small delay so user sees success
                setTimeout(() => {
                    onClose();
                }, 900);
            } else {
                // If backend returned an error shape
                const msg =
                    res?.error ||
                    res?.message ||
                    "Failed to apply proposals (unknown backend response)";
                setErrorMessage(msg);
                setStatus("ERROR");
            }
        } catch (err) {
            console.error("Error applying proposals:", err);
            setErrorMessage(err.message || "Failed to apply rules");
            setStatus("ERROR");
        }
    };

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
        const p = (priority || "").toUpperCase();
        switch (p) {
            case "IMMEDIATE":
                return { color: "text-red-700 dark:text-red-300", bg: "bg-red-100 dark:bg-red-900/30", icon: <Zap size={14} /> };
            case "MID_TERM":
            case "MID-TERM":
            case "MIDTERM":
                return { color: "text-yellow-700 dark:text-yellow-300", bg: "bg-yellow-100 dark:bg-yellow-900/30", icon: <Calendar size={14} /> };
            case "LONG_TERM":
                return { color: "text-gray-700 dark:text-gray-300", bg: "bg-gray-100 dark:bg-gray-700/30", icon: <CalendarDays size={14} /> };
            default:
                return { color: "text-gray-700 dark:text-gray-300", bg: "bg-gray-100 dark:bg-gray-700/30", icon: <Clock size={14} /> };
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 font-sans antialiased">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-7xl max-h-[90vh] overflow-hidden flex flex-col transform transition-all duration-300 ease-out">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Rule Review & Approval</h2>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Decision ID: <span className="font-mono bg-gray-100 dark:bg-gray-700 px-1 rounded">{decisionId}</span></p>
                    </div>
                    <button onClick={onClose} className="p-2 rounded-full text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" aria-label="Close modal">
                        <XCircle size={24} />
                    </button>
                </div>

                {/* Loading */}
                {status === "LOADING" && (
                    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-gray-50 dark:bg-gray-900">
                        <Loader2 className="animate-spin text-blue-500 mb-4" size={48} />
                        <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">Waiting for AI Rule Draft...</p>
                    </div>
                )}

                {/* Error */}
                {status === "ERROR" && (
                    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-red-50 dark:bg-red-900/20">
                        <AlertTriangle className="text-red-500 mb-4" size={48} />
                        <p className="text-lg font-medium text-red-600 dark:text-red-400">{errorMessage || "An error occurred"}</p>
                        <div className="mt-6 flex gap-3">
                            <button onClick={() => { attemptsRef.current = 0; setStatus("LOADING"); setErrorMessage(""); }} className="px-6 py-2 bg-blue-600 text-white rounded-lg">Retry</button>
                            <button onClick={onClose} className="px-6 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg">Close</button>
                        </div>
                    </div>
                )}

                {/* Applying */}
                {status === "APPLYING" && (
                    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-green-50 dark:bg-green-900/20">
                        <Loader2 className="animate-spin text-green-500 mb-4" size={48} />
                        <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">Applying Rules... Please Wait.</p>
                    </div>
                )}

                {/* Applied */}
                {status === "APPLIED" && (
                    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-green-50 dark:bg-green-900/20">
                        <CheckCircle2 className="text-green-500 mb-4" size={48} />
                        <p className="text-xl text-green-600 dark:text-green-400">Rules successfully applied and system is improved.</p>
                        <button onClick={onClose} className="mt-6 px-8 py-3 bg-green-600 text-white font-semibold rounded-lg">Finish Review</button>
                    </div>
                )}

                {/* RULES_READY */}
                {status === "RULES_READY" && (
                    <>
                        <div className="flex-1 overflow-hidden flex">
                            {/* Left Panel - proposals */}
                            <div className="w-1/2 border-r border-gray-200 dark:border-gray-700 overflow-y-auto p-6">
                                <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4 sticky top-0 bg-white dark:bg-gray-800 pb-2 z-10">Rule Proposals (Draft)</h3>

                                <div className="space-y-4">
                                    {proposals.length === 0 && <p className="text-center text-gray-500 dark:text-gray-400 py-8">No rule proposals available</p>}

                                    {proposals.map((proposal, index) => {
                                        const actionStyle = getActionStyle(proposal.action_type);
                                        const priorityStyle = getPriorityStyle(proposal.priority);
                                        const accepted = isProposalAccepted(index);

                                        return (
                                            <div key={proposalId(proposal, index)} className={`border rounded-xl p-4 transition-all duration-200 cursor-pointer ${accepted ? "border-blue-500 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/30 shadow-md" : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/50 hover:border-blue-400"}`} onClick={() => toggleProposal(index)}>
                                                <div className="flex items-start gap-3">
                                                    <input type="checkbox" checked={accepted} readOnly className="mt-1 w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer" />
                                                    <div className="flex-1">
                                                        <div className="flex items-center gap-2 mb-2">
                                                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${actionStyle.bg} ${actionStyle.color}`}>{actionStyle.icon}{proposal.action_type}</span>
                                                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${priorityStyle.bg} ${priorityStyle.color}`}>{priorityStyle.icon}{(proposal.priority || "").replace("_", " ")}</span>
                                                            {proposal.rule_id && <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">ID: {proposal.rule_id}</span>}
                                                        </div>
                                                        <p className="text-base text-gray-800 dark:text-gray-200 font-medium leading-snug">{proposal.rule_text}</p>
                                                        {(proposal.target_entity || proposal.rule_type) && <div className="mt-3 text-xs text-gray-600 dark:text-gray-400 space-x-3 border-t pt-2 border-gray-200 dark:border-gray-700/50">
                                                            {proposal.target_entity && <span className="inline-block"><span className="font-semibold">Target:</span> {proposal.target_entity}</span>}
                                                            {proposal.rule_type && <span className="inline-block"><span className="font-semibold">Type:</span> {proposal.rule_type}</span>}
                                                        </div>}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Right Panel */}
                            <div className="w-1/2 overflow-y-auto p-6 flex flex-col">
                                <div className="flex-1 mb-6">
                                    <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4">AI Evaluator Diagnosis & Rationale</h3>
                                    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-inner h-full max-h-96 overflow-y-auto">
                                        <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">{chainOfThought || "No analysis available"}</p>
                                    </div>
                                </div>

                                <div className="pt-6 border-t border-gray-200 dark:border-gray-700 sticky bottom-0 bg-white dark:bg-gray-800">
                                    <div className="flex items-center justify-between text-base text-gray-700 dark:text-gray-300 mb-4 font-semibold">
                                        <span>Selected Rules:</span>
                                        <span className="text-blue-600 dark:text-blue-400">{acceptedProposals.length} of {proposals.length}</span>
                                    </div>

                                    <button onClick={handleApplyRules} disabled={acceptedProposals.length === 0} className="w-full py-4 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:hover:bg-gray-400 disabled:cursor-not-allowed text-white text-lg font-bold rounded-xl shadow-lg transition-all duration-300 ease-in-out transform hover:scale-[1.01] flex items-center justify-center gap-3 mb-3">
                                        <CheckCircle2 size={24} /> Apply {acceptedProposals.length} Accepted Rule{acceptedProposals.length !== 1 ? "s" : ""}
                                    </button>

                                    <button onClick={handleRejectAll} className="w-full py-3 px-4 bg-white dark:bg-gray-700 border-2 border-red-500 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 font-semibold rounded-xl transition-colors flex items-center justify-center gap-3">
                                        <XCircle size={20} /> Reject All Proposals
                                    </button>
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
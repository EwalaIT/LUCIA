import { useState, useEffect, useRef } from "react";
import { Calendar, ChevronLeft, ChevronRight, ArrowUpDown } from "lucide-react";
import { getDecisions, updateDecision } from "../services/decisionsService";
import DecisionBubble from "./DecisionBubble";

export default function DecisionsManager() {
    const [decisions, setDecisions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedDate, setSelectedDate] = useState("");
    const [page, setPage] = useState(1);
    const [perPage] = useState(5);
    const [sort, setSort] = useState("desc");
    const [total, setTotal] = useState(0);
    const chatEndRef = useRef(null);

    useEffect(() => { loadDecisions() }, [selectedDate, page, sort]);

    const loadDecisions = async () => {
        try {
            setLoading(true);
            const data = await getDecisions(selectedDate, page, perPage, sort);
            setDecisions(data.decisions);
            setTotal(data.total);
            setError(null);
            setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
        } catch (err) {
            setError("Failed to load decisions");
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateDecision = async (id, confidence, notes) => {
        await updateDecision(id, confidence, notes);
        loadDecisions();
    };

    const handleClearDate = () => { setSelectedDate(""); setPage(1); };
    const toggleSort = () => setSort(sort === "desc" ? "asc" : "desc");
    const totalPages = Math.ceil(total / perPage);

    return (
        <div className="max-w-4xl mx-auto py-6 px-4 flex flex-col h-[90vh]">
            <div className="mb-4 flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-semibold text-gray-800 dark:text-gray-100">AI Agent Decisions</h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        Review and provide feedback on energy efficiency decisions
                    </p>
                </div>
                <button
                    onClick={toggleSort}
                    className="flex items-center gap-1 px-3 py-1 border rounded-md text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                    <ArrowUpDown size={16} /> {sort === "desc" ? "Recent First" : "Oldest First"}
                </button>
            </div>

            <div className="mb-4 flex items-center gap-3">
                <div className="relative flex-1 max-w-xs">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                    <input
                        type="date"
                        value={selectedDate}
                        onChange={(e) => { setSelectedDate(e.target.value); setPage(1); }}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                {selectedDate && (
                    <button
                        onClick={handleClearDate}
                        className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200"
                    >
                        Clear
                    </button>
                )}
                <div className="text-sm text-gray-500 dark:text-gray-400">{total} decision{total !== 1 ? "s" : ""}</div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 bg-gray-50 dark:bg-gray-900 rounded-lg space-y-3 max-h-[75vh]">
                {loading ? (
                    <div className="flex items-center justify-center h-full">
                        <span className="text-gray-600 dark:text-gray-400">Loading decisions...</span>
                    </div>
                ) : error ? (
                    <div className="flex items-center justify-center h-full">
                        <span className="text-red-600 dark:text-red-400">{error}</span>
                    </div>
                ) : decisions.length === 0 ? (
                    <div className="flex items-center justify-center h-full">
                        <span className="text-gray-600 dark:text-gray-400">
                            {selectedDate ? "No decisions found for this date" : "No decisions found"}
                        </span>
                    </div>
                ) : (
                    decisions.map((decision) => (
                        <DecisionBubble
                            key={decision.id}
                            decision={decision}
                            onUpdate={handleUpdateDecision}
                        />
                    ))
                )}
                <div ref={chatEndRef}></div>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex justify-center items-center gap-2 mt-4">
                    <button
                        disabled={page === 1}
                        onClick={() => setPage(page - 1)}
                        className="p-2 rounded-md border disabled:opacity-50"
                    >
                        <ChevronLeft size={16} />
                    </button>
                    <span className="text-sm text-gray-600 dark:text-gray-400">{page} / {totalPages}</span>
                    <button
                        disabled={page === totalPages}
                        onClick={() => setPage(page + 1)}
                        className="p-2 rounded-md border disabled:opacity-50"
                    >
                        <ChevronRight size={16} />
                    </button>
                </div>
            )}
        </div>
    );
}

import { ArrowLeft } from "lucide-react"
import { useNavigate } from "react-router-dom"

export default function BackButton({ label = "Back" }) {
    const navigate = useNavigate();

    return (
        <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-3 py-2 mb-4 
                       bg-gray-200 dark:bg-gray-700 
                       text-gray-800 dark:text-gray-200 
                       rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 
                       transition shadow-sm"
        >
            <ArrowLeft size={18} />
            <span className="text-sm font-medium">{label}</span>
        </button>
    );
}

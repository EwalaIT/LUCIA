import React from "react";

/**
 * Button con variantes principales y soporte dark mode
 * Props:
 * - variant: "primary" | "secondary" | "danger"
 * - className: clases Tailwind adicionales
 */
export function Button({ children, variant = "primary", className = "", ...props }) {
    const baseClasses =
        "px-4 py-2 rounded-lg font-medium shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1";

    const variants = {
        primary: "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",
        secondary: "bg-gray-100 text-gray-800 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-100 dark:hover:bg-gray-600 focus:ring-gray-400",
        danger: "bg-red-500 text-white hover:bg-red-600 focus:ring-red-400",
    };

    return (
        <button className={`${baseClasses} ${variants[variant]} ${className}`} {...props}>
            {children}
        </button>
    );
}

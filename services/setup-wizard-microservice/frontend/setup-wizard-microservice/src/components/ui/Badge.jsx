import React from "react";

/**
 * Badge pequeño para count/status
 * Props:
 * - color: "green" | "blue" | "gray" | "red"
 * - className: clases Tailwind adicionales
 */
export function Badge({ children, color = "gray", className = "" }) {
    const colors = {
        green: "bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100",
        blue: "bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100",
        gray: "bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-100",
        red: "bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100",
    };

    return (
        <span
            className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${colors[color]} ${className}`}
        >
            {children}
        </span>
    );
}

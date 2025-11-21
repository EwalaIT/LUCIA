import React from "react";

/**
 * Card container
 * Props:
 * - className: clases Tailwind adicionales
 * - children: contenido del card
 */
export function Card({ children, className }) {
    return (
        <div
            className={`bg-white dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-xl shadow-sm p-5 ${className}`}
        >
            {children}
        </div>
    );
}

/**
 * CardHeader: título o cabecera
 */
export function CardHeader({ children, className }) {
    return (
        <div className={`text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3 ${className}`}>
            {children}
        </div>
    );
}

/**
 * CardContent: contenido interno
 */
export function CardContent({ children, className }) {
    return <div className={`text-gray-700 dark:text-gray-300 ${className}`}>{children}</div>;
}

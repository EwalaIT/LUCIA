import React, { useEffect, useRef } from "react";

export function CheckboxBase({
    checked,
    indeterminate = false,
    onChange,
    disabled = false,
    size = "md", // sm, md, lg
    className = "",
}) {
    const ref = useRef(null);

    useEffect(() => {
        if (ref.current) ref.current.indeterminate = indeterminate;
    }, [indeterminate]);

    const sizeClasses = {
        sm: "h-4 w-4",
        md: "h-5 w-5",
        lg: "h-6 w-6"
    };

    const iconSize = {
        sm: "w-2.5 h-2.5",
        md: "w-3.5 h-3.5",
        lg: "w-4 h-4"
    };

    return (
        <div
            className={`
        relative flex items-center justify-center 
        rounded-md border transition-all duration-200
        ${sizeClasses[size]}
        ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
        ${indeterminate
                    ? "bg-blue-500 border-blue-500"
                    : checked
                        ? "bg-blue-600 border-blue-600"
                        : "bg-white dark:bg-gray-900 border-gray-400 dark:border-gray-600"
                }
        group-hover:border-blue-500
        dark:group-hover:border-blue-400
        focus-within:ring-2 focus-within:ring-blue-500 dark:focus-within:ring-blue-400
        ${className}
      `}
        >
            <input
                ref={ref}
                type="checkbox"
                checked={checked}
                onChange={onChange}
                disabled={disabled}
                className="absolute inset-0 appearance-none opacity-0 cursor-pointer"
            />

            {/* CHECK ICON */}
            {checked && !indeterminate && (
                <svg
                    className={`${iconSize[size]} text-white transition-opacity duration-200`}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    viewBox="0 0 24 24"
                >
                    <path d="M5 13l4 4L19 7" />
                </svg>
            )}

            {/* INDETERMINATE ICON */}
            {indeterminate && (
                <svg
                    className={`${iconSize[size]} text-white transition-opacity duration-200`}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    viewBox="0 0 24 24"
                >
                    <path d="M5 12h14" />
                </svg>
            )}
        </div>
    );
}

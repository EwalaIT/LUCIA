import React, { useEffect, useRef } from "react";

export function Checkbox({
    checked,
    indeterminate = false,
    onChange,
    label,
    disabled = false,
    className = "",
}) {
    const ref = useRef(null);

    // Permite el estado tri-estado visual
    useEffect(() => {
        if (ref.current) {
            ref.current.indeterminate = indeterminate;
        }
    }, [indeterminate]);

    return (
        <label
            className={`
        group flex items-center gap-3 cursor-pointer select-none
        ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
        ${className}
      `}
        >
            <div
                className={`
          relative flex items-center justify-center
          h-5 w-5 rounded-md border
          transition-all duration-200

          ${disabled ? "border-gray-300 bg-gray-200" : ""}

          ${indeterminate
                        ? "border-blue-500 bg-blue-500"
                        : checked
                            ? "border-blue-600 bg-blue-600"
                            : "border-gray-400 bg-white dark:bg-gray-900 dark:border-gray-600"
                    }

          group-hover:border-blue-500
          dark:group-hover:border-blue-400

          focus-within:ring-2 focus-within:ring-blue-500 dark:focus-within:ring-blue-400
        `}
            >
                <input
                    ref={ref}
                    type="checkbox"
                    checked={checked}
                    onChange={onChange}
                    disabled={disabled}
                    className="
            absolute inset-0 appearance-none opacity-0 cursor-pointer
          "
                />

                {/* Checkmark icon */}
                {checked && !indeterminate && (
                    <svg
                        className="w-3.5 h-3.5 text-white transition-opacity duration-200"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        viewBox="0 0 24 24"
                    >
                        <path d="M5 13l4 4L19 7" />
                    </svg>
                )}

                {/* Indeterminate icon */}
                {indeterminate && (
                    <svg
                        className="w-3.5 h-3.5 text-white transition-opacity duration-200"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        viewBox="0 0 24 24"
                    >
                        <path d="M5 12h14" />
                    </svg>
                )}
            </div>

            {label && (
                <span
                    className="
            text-gray-900 dark:text-gray-100 
            font-medium leading-none
            transition-colors duration-200
          "
                >
                    {label}
                </span>
            )}
        </label>
    );
}

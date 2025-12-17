import React from "react";

export function Dialog({ children, isOpen, onClose, closeOnOutside = true }) {
    if (!isOpen) return null;

    return (
        <div
            className="
        fixed inset-0 z-[999]
        flex items-center justify-center
        bg-black/50 dark:bg-black/70
        backdrop-blur-sm
        animate-fadeIn
      "
            onClick={closeOnOutside ? onClose : undefined}
        >
            <div
                className="
          bg-white dark:bg-gray-800
          rounded-lg shadow-xl 
          w-full max-w-lg p-6
          animate-slideUp
        "
                onClick={(e) => e.stopPropagation()}
            >
                {children}
            </div>
        </div>
    );
}

export function DialogContent({ children, className = "" }) {
    return <div className={`space-y-4 ${className}`}>{children}</div>;
}

export function DialogHeader({ children, className = "" }) {
    return <div className={`mb-2 border-b border-gray-200 dark:border-gray-700 pb-3 ${className}`}>{children}</div>;
}

export function DialogTitle({ children, className = "" }) {
    return (
        <h3 className={`text-xl font-semibold text-gray-900 dark:text-gray-100 ${className}`}>
            {children}
        </h3>
    );
}

export function DialogDescription({ children, className = "" }) {
    return (
        <p className={`text-gray-600 dark:text-gray-300 mt-1 ${className}`}>
            {children}
        </p>
    );
}

export function DialogFooter({ children, className = "" }) {
    return <div className={`mt-6 flex justify-end gap-3 ${className}`}>{children}</div>;
}

// client/src/components/ui/Dialog.tsx
import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import  cn  from '~/utils/cn';

/* ============================= */
/* Componente raíz: Dialog       */
/* ============================= */
interface DialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    children: React.ReactNode;
}

export const Dialog: React.FC<DialogProps> = ({ open, onOpenChange, children }) => {
    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => onOpenChange(false)}
                >
                    <div
                        className="relative max-w-lg w-full mx-4"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {children}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};

/* ============================= */
/* Contenido del Modal           */
/* ============================= */
interface DialogContentProps {
    children: React.ReactNode;
    className?: string;
}

export const DialogContent: React.FC<DialogContentProps> = ({ children, className }) => {
    return (
        <motion.div
            className={cn(
                "bg-background dark:bg-background-dark rounded-xl shadow-lg p-6",
                className
            )}
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
        >
            {children}
        </motion.div>
    );
};

/* ============================= */
/* Header del Modal              */
/* ============================= */
interface DialogHeaderProps {
    children: React.ReactNode;
    className?: string;
}

export const DialogHeader: React.FC<DialogHeaderProps> = ({ children, className }) => {
    return (
        <div className={cn("flex items-center justify-between mb-4", className)}>
            {children}
        </div>
    );
};

/* ============================= */
/* Título del Modal              */
/* ============================= */
interface DialogTitleProps {
    children: React.ReactNode;
    className?: string;
}

export const DialogTitle: React.FC<DialogTitleProps> = ({ children, className }) => {
    return (
        <h3 className={cn("text-lg font-semibold text-foreground", className)}>
            {children}
        </h3>
    );
};

/* ============================= */
/* Botón de cerrar               */
/* ============================= */
interface DialogCloseProps {
    onClick?: () => void;
    className?: string;
}

export const DialogClose: React.FC<DialogCloseProps> = ({ onClick, className }) => {
    return (
        <button
            onClick={onClick}
            className={cn(
                "p-1 rounded hover:bg-muted transition-colors text-foreground",
                className
            )}
            aria-label="Close"
        >
            <X className="w-5 h-5" />
        </button>
    );
};

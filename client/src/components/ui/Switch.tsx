import  cn  from '~/utils/cn';
import * as React from "react";
import { motion } from "framer-motion";

interface SwitchProps {
    checked: boolean;
    onChange: (checked: boolean) => void;
    disabled?: boolean;
    label?: string;
    className?: string;
}

export const Switch: React.FC<SwitchProps> = ({
    checked,
    onChange,
    disabled = false,
    label,
    className,
}) => {
    return (
        <label
            className={cn(
                "flex items-center gap-2 select-none",
                disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
                className
            )}
        >
            {label && (
                <span className="text-sm font-medium text-muted-foreground">{label}</span>
            )}

            <motion.div
                className={cn(
                    "relative w-12 h-7 flex items-center rounded-full p-[2px] transition-colors duration-300",
                    checked
                        ? "bg-primary/80 dark:bg-primary/60 shadow-sm"
                        : "bg-muted dark:bg-muted/70"
                )}
                whileTap={{ scale: 0.97 }}
                onClick={() => !disabled && onChange(!checked)}
            >
                {/* Track interno con degradado sutil */}
                <div
                    className={cn(
                        "absolute inset-0 rounded-full transition-colors duration-300",
                        checked ? "bg-primary/60" : "bg-muted/50"
                    )}
                />
                {/* Toggle */}
                <motion.div
                    className="absolute left-[2px] w-6 h-6 bg-background rounded-full shadow-md"
                    layout
                    animate={{ x: checked ? 20 : 0 }}
                    transition={{ type: "spring", stiffness: 500, damping: 25 }}
                />
            </motion.div>
        </label>
    );
};

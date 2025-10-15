import * as React from "react";
import  cn  from '~/utils/cn';
import { motion } from "framer-motion";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "outline" | "ghost";
    size?: "sm" | "md" | "lg";
    isLoading?: boolean;
    icon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    (
        {
            children,
            className,
            variant = "primary",
            size = "md",
            isLoading = false,
            icon,
            disabled,
            ...props
        },
        ref
    ) => {
        const baseStyles =
            "relative inline-flex items-center justify-center rounded-xl font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-accent/50 disabled:opacity-60 disabled:cursor-not-allowed shadow-sm";

        const variants = {
            primary:
                "bg-accent text-white hover:bg-accent-hover active:bg-accent-active",
            secondary:
                "bg-surface-secondary text-text-primary hover:bg-surface-tertiary border border-border",
            outline:
                "border border-border text-text-primary bg-transparent hover:bg-surface-secondary",
            ghost: "bg-transparent text-text-secondary hover:bg-surface-secondary/50",
        };

        const sizes = {
            sm: "px-3 py-1.5 text-sm",
            md: "px-4 py-2 text-base",
            lg: "px-5 py-2.5 text-lg",
        };

        return (
            <motion.button
                ref={ref}
                whileTap={{ scale: 0.98 }}
                className={cn(baseStyles, variants[variant], sizes[size], className)}
                disabled={disabled || isLoading}
                {...props}
            >
                {isLoading && (
                    <span className="absolute left-3 inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                )}
                {icon && !isLoading && (
                    <span className={cn("mr-2 flex items-center", isLoading && "opacity-0")}>
                        {icon}
                    </span>
                )}
                <span className={cn(isLoading && "opacity-50")}>{children}</span>
            </motion.button>
        );
    }
);

Button.displayName = "Button";

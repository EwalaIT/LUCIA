import type * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import cn from "~/utils/cn"

const spinnerVariants = cva("animate-spin rounded-full border-2 border-current border-t-transparent", {
    variants: {
        size: {
            sm: "h-4 w-4",
            md: "h-6 w-6",
            lg: "h-8 w-8",
            xl: "h-12 w-12",
        },
        variant: {
            default: "text-primary",
            secondary: "text-muted-foreground",
            destructive: "text-destructive",
            success: "text-green-500",
        },
    },
    defaultVariants: {
        size: "md",
        variant: "default",
    },
})

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof spinnerVariants> {
    label?: string
}

function Spinner({ className, size, variant, label, ...props }: SpinnerProps) {
    return (
        <div
            role="status"
            aria-label={label || "Loading"}
            data-slot="spinner"
            className={cn("inline-block", className)}
            {...props}
        >
            <div className={cn(spinnerVariants({ size, variant }))} />
            <span className="sr-only">{label || "Loading..."}</span>
        </div>
    )
}

function SpinnerContainer({ className, ...props }: React.ComponentProps<"div">) {
    return (
        <div data-slot="spinner-container" className={cn("flex items-center justify-center p-8", className)} {...props} />
    )
}

export { Spinner, SpinnerContainer, spinnerVariants }

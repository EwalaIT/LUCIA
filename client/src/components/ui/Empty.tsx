import type * as React from "react"
import cn from "~/utils/cn"

function Empty({ className, ...props }: React.ComponentProps<"div">) {
    return (
        <div
            data-slot="empty"
            className={cn(
                "flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-border bg-muted/30 p-8 text-center",
                className,
            )}
            {...props}
        />
    )
}

function EmptyHeader({ className, ...props }: React.ComponentProps<"div">) {
    return <div data-slot="empty-header" className={cn("flex flex-col items-center gap-2", className)} {...props} />
}

function EmptyMedia({ className, ...props }: React.ComponentProps<"div">) {
    return (
        <div
            data-slot="empty-media"
            className={cn(
                "flex h-16 w-16 items-center justify-center rounded-full bg-muted text-muted-foreground",
                className,
            )}
            {...props}
        />
    )
}

function EmptyTitle({ className, ...props }: React.ComponentProps<"h3">) {
    return <h3 data-slot="empty-title" className={cn("text-lg font-semibold text-foreground", className)} {...props} />
}

function EmptyDescription({ className, ...props }: React.ComponentProps<"p">) {
    return (
        <p data-slot="empty-description" className={cn("text-sm text-muted-foreground max-w-sm", className)} {...props} />
    )
}

function EmptyActions({ className, ...props }: React.ComponentProps<"div">) {
    return <div data-slot="empty-actions" className={cn("flex items-center gap-2 mt-2", className)} {...props} />
}

export { Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription, EmptyActions }

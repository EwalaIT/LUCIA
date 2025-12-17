"use client"

import { useState, useEffect, useMemo } from "react"

/**
 * Hook to distribute items into masonry columns based on viewport width
 * Returns an array of column arrays for rendering
 */
export function useMasonryColumns<T>(
    items: T[],
    options: {
        mobile?: number
        tablet?: number
        desktop?: number
        wide?: number
    } = {},
): T[][] {
    const { mobile = 1, tablet = 2, desktop = 3, wide = 4 } = options

    const [columnCount, setColumnCount] = useState(() => {
        if (typeof window === "undefined") return mobile
        const width = window.innerWidth
        if (width >= 1536) return wide
        if (width >= 1024) return desktop
        if (width >= 640) return tablet
        return mobile
    })

    useEffect(() => {
        const handleResize = () => {
            const width = window.innerWidth
            let newCount = mobile

            if (width >= 1536) {
                newCount = wide
            } else if (width >= 1024) {
                newCount = desktop
            } else if (width >= 640) {
                newCount = tablet
            }

            if (newCount !== columnCount) {
                setColumnCount(newCount)
            }
        }

        window.addEventListener("resize", handleResize)
        return () => window.removeEventListener("resize", handleResize)
    }, [columnCount, mobile, tablet, desktop, wide])

    // Distribute items into columns in a round-robin fashion
    // This ensures stable positioning - each item always goes to the same column
    const columns = useMemo(() => {
        const cols: T[][] = Array.from({ length: columnCount }, () => [])

        items.forEach((item, index) => {
            const columnIndex = index % columnCount
            cols[columnIndex].push(item)
        })

        return cols
    }, [items, columnCount])

    return columns
}

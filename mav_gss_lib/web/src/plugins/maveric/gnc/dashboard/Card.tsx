import type { ReactNode } from 'react'
import { colors } from '@/lib/colors'

interface CardProps {
  title: string
  /** Optional right-aligned status chip (e.g., current mode). */
  status?: ReactNode
  /** Extra classes on the outer card element (e.g., "h-full"). */
  className?: string
  children: ReactNode
}

export function Card({ title, status, className, children }: CardProps) {
  return (
    <div
      className={`flex flex-col rounded-sm border ${className ?? ''}`}
      style={{ backgroundColor: colors.bgPanel, borderColor: colors.borderSubtle }}
    >
      <div
        className="flex items-center justify-between px-3 py-2 border-b"
        style={{ borderColor: colors.borderSubtle }}
      >
        <h3
          className="font-sans text-[12px] uppercase tracking-wider"
          style={{ color: colors.textPrimary }}
        >
          {title}
        </h3>
        {status}
      </div>
      <div className="flex-1">
        {children}
      </div>
    </div>
  )
}

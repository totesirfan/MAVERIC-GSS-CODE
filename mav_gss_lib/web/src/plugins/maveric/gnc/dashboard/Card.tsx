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
      className={`flex flex-col border overflow-hidden ${className ?? ''}`}
      style={{
        backgroundColor: colors.bgPanel,
        borderColor: colors.borderSubtle,
        borderRadius: 6,
        boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
      }}
    >
      <div
        className="flex items-center justify-between border-b"
        style={{
          borderColor: colors.borderSubtle,
          padding: '6px 12px',
          minHeight: 34,
        }}
      >
        <h3
          className="font-sans uppercase"
          style={{
            color: colors.textPrimary,
            fontSize: 14,
            fontWeight: 700,
            letterSpacing: '0.02em',
            whiteSpace: 'nowrap',
          }}
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

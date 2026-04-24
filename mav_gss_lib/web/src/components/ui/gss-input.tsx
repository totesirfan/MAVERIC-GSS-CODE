import { useState, type InputHTMLAttributes, type Ref } from 'react'
import { cn } from '@/lib/utils'
import { colors } from '@/lib/colors'

export function GssInput({ className, style, onFocus, onBlur, ref, ...props }: InputHTMLAttributes<HTMLInputElement> & { ref?: Ref<HTMLInputElement> }) {
  const [focused, setFocused] = useState(false)
  return (
    <input
      {...props}
      ref={ref}
      onFocus={(e) => { setFocused(true); onFocus?.(e) }}
      onBlur={(e) => { setFocused(false); onBlur?.(e) }}
      className={cn('px-2 py-1 rounded text-xs outline-none border', className)}
      style={{
        backgroundColor: colors.bgBase,
        color: colors.value,
        borderColor: focused ? `${colors.active}80` : colors.borderSubtle,
        ...style,
      } as React.CSSProperties}
    />
  )
}

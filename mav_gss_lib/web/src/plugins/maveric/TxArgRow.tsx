import { forwardRef } from 'react'
import { GssInput } from '@/components/ui/gss-input'
import { colors } from '@/lib/colors'
import type { TxArgSchema } from '@/lib/types'

// Per Task 8b/9, the arg shape lives in lib/types.ts (mirrored from
// the Python TxArgSchema TypedDict). Importing it here means drift is
// impossible: when the contract changes, both ends update together.

type Props = {
  arg: TxArgSchema
  value: string
  onChange: (next: string) => void
  onEnter: () => void
  disabled: boolean
}

const TxArgRow = forwardRef<HTMLInputElement, Props>(
  ({ arg, value, onChange, onEnter, disabled }, ref) => {
    const range = arg.valid_range
    const rangeChip = range ? `${range[0]}–${range[1]}` : null
    return (
      <div className="space-y-1" style={{ opacity: disabled ? 0.35 : 1 }}>
        <div className="flex items-baseline gap-1">
          <span className="text-[11px] font-medium" style={{ color: colors.dim }}>{arg.name}</span>
          {rangeChip && (
            <span
              className="text-[10px] px-1 rounded"
              style={{ color: colors.sep, border: `1px solid ${colors.sep}` }}
            >
              {rangeChip}
            </span>
          )}
          {arg.optional && (
            <span className="text-[10px]" style={{ color: colors.sep }}>optional</span>
          )}
        </div>
        <GssInput
          ref={ref}
          className="w-full"
          style={arg.optional ? { borderStyle: 'dashed' } : undefined}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') onEnter() }}
          placeholder={arg.type}
        />
        {arg.description && (
          <span className="block text-[10px]" style={{ color: colors.sep }}>
            {arg.description}
          </span>
        )}
      </div>
    )
  },
)
TxArgRow.displayName = 'TxArgRow'
export default TxArgRow

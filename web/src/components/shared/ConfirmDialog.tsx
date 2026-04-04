import { colors } from '@/lib/colors'

interface ConfirmDialogProps {
  open: boolean
  title: string
  detail?: string
  content?: React.ReactNode
  variant?: 'normal' | 'caution' | 'destructive'
  onConfirm: () => void
  onCancel: () => void
}

const borderColors: Record<string, string> = {
  normal: colors.label,
  caution: colors.warning,
  destructive: colors.error,
}

const confirmColors: Record<string, string> = {
  normal: colors.label,
  caution: colors.warning,
  destructive: colors.error,
}

export function ConfirmDialog({
  open, title, detail, content, variant = 'normal',
  onConfirm, onCancel,
}: ConfirmDialogProps) {
  if (!open) return null

  const borderColor = borderColors[variant]
  const btnColor = confirmColors[variant]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={onCancel}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Modal */}
      <div
        className="relative z-10 rounded-lg p-4 min-w-[300px] max-w-[400px] border"
        style={{ backgroundColor: colors.bgPanel, borderColor }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="text-sm font-bold mb-2" style={{ color: colors.value }}>{title}</div>
        {detail && (
          <div className="text-xs mb-3" style={{ color: colors.dim }}>{detail}</div>
        )}
        {content && <div className="mb-3">{content}</div>}

        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-3 py-1 rounded text-xs border"
            style={{ color: colors.dim, borderColor: '#333' }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-3 py-1 rounded text-xs font-medium"
            style={{ color: colors.bgBase, backgroundColor: btnColor }}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}

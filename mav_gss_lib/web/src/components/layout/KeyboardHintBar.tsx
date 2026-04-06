import { useEffect, useState } from 'react'
import { Kbd } from '@/components/ui/kbd'
import { colors } from '@/lib/colors'

type HintContext = 'default' | 'rx-packet' | 'tx-queue' | 'input'

function getContext(): HintContext {
  const el = document.activeElement
  if (!el) return 'default'
  const tag = el.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA') return 'input'
  return 'default'
}

const hints: Record<HintContext, { key: string; desc: string }[]> = {
  default: [
    { key: 'Ctrl+K', desc: 'Search' },
    { key: 'Ctrl+S', desc: 'Send' },
    { key: 'Ctrl+X', desc: 'Clear' },
    { key: 'Ctrl+Z', desc: 'Undo' },
    { key: '?', desc: 'Help' },
  ],
  'rx-packet': [
    { key: '↑↓', desc: 'Navigate' },
    { key: 'Space', desc: 'Expand' },
    { key: 'Esc', desc: 'Deselect' },
    { key: 'Right-click', desc: 'Copy' },
  ],
  'tx-queue': [
    { key: '↑↓', desc: 'Navigate' },
    { key: 'G', desc: 'Guard' },
    { key: 'Del', desc: 'Remove' },
    { key: 'Drag', desc: 'Reorder' },
  ],
  input: [
    { key: 'Enter', desc: 'Queue' },
    { key: '↑↓', desc: 'History' },
    { key: 'Esc', desc: 'Cancel' },
  ],
}

export function KeyboardHintBar() {
  const [ctx, setCtx] = useState<HintContext>('default')

  useEffect(() => {
    function update() { setCtx(getContext()) }
    // Listen on focus changes
    document.addEventListener('focusin', update)
    document.addEventListener('focusout', () => setTimeout(update, 50))
    return () => {
      document.removeEventListener('focusin', update)
      document.removeEventListener('focusout', () => {})
    }
  }, [])

  const items = hints[ctx]

  return (
    <div className="flex items-center justify-center gap-4 h-6 px-4 shrink-0 border-t" style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgApp }}>
      {items.map((h) => (
        <span key={h.key} className="flex items-center gap-1.5 text-[11px]">
          <Kbd className="!h-4 !min-w-4 !text-[11px] !px-1">{h.key}</Kbd>
          <span style={{ color: colors.dim }}>{h.desc}</span>
        </span>
      ))}
    </div>
  )
}

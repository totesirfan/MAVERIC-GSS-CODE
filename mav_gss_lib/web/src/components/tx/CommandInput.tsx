import { useState, useRef, useCallback, forwardRef } from 'react'
import { CornerDownLeft } from 'lucide-react'
import { Kbd } from '@/components/ui/kbd'
import { colors } from '@/lib/colors'

interface CommandInputProps {
  onSubmit: (line: string) => void
  history: string[]
  onHistoryPush: (cmd: string) => void
}

export const CommandInput = forwardRef<HTMLTextAreaElement, CommandInputProps>(
  function CommandInput({ onSubmit, history, onHistoryPush }, ref) {
  const [value, setValue] = useState('')
  const [histIdx, setHistIdx] = useState(-1)
  const [focused, setFocused] = useState(false)
  const internalRef = useRef<HTMLTextAreaElement>(null)
  const inputRef = (ref as React.RefObject<HTMLTextAreaElement | null>) ?? internalRef

  const submit = useCallback(() => {
    if (!value.trim()) return
    onSubmit(value.trim())
    onHistoryPush(value.trim())
    setValue('')
    setHistIdx(-1)
  }, [value, onSubmit, onHistoryPush])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && value.trim()) {
      e.preventDefault()
      submit()
    } else if (e.key === 'ArrowUp' && !value.includes('\n')) {
      e.preventDefault()
      const nextIdx = Math.min(histIdx + 1, history.length - 1)
      setHistIdx(nextIdx)
      if (history[nextIdx]) setValue(history[nextIdx])
    } else if (e.key === 'ArrowDown' && !value.includes('\n')) {
      e.preventDefault()
      const nextIdx = histIdx - 1
      if (nextIdx < 0) { setHistIdx(-1); setValue('') }
      else { setHistIdx(nextIdx); setValue(history[nextIdx]) }
    }
  }, [value, history, histIdx, submit])

  const hasText = value.trim().length > 0
  const showCursor = focused && !hasText

  return (
    <div className="flex flex-col h-full">
      {/* Input row */}
      <div className="flex-1 flex items-center gap-2 px-3 min-h-0">
        <span
          className="font-mono text-[13px] leading-none select-none"
          style={{ color: colors.active }}
          aria-hidden="true"
        >❯</span>
        {showCursor && (
          <div
            className="w-0.5 h-[18px] rounded-sm shrink-0 animate-[blink_1.2s_ease-in-out_infinite]"
            style={{ backgroundColor: colors.active }}
          />
        )}
        <textarea
          ref={inputRef}
          className="flex-1 bg-transparent text-xs font-mono outline-none resize-none leading-5"
          style={{ color: colors.value }}
          placeholder="Type a command..."
          value={value}
          rows={1}
          onChange={(e) => { setValue(e.target.value); setHistIdx(-1) }}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          spellCheck={false}
          autoComplete="off"
        />
      </div>
      {/* Kbd hints */}
      <div className="flex items-center gap-1.5 px-3 pb-1.5">
        <Kbd>↑</Kbd><Kbd>↓</Kbd>
        <span className="text-[10px]" style={{ color: colors.sep }}>history</span>
        <span className="text-[10px] ml-auto flex items-center gap-1" style={{ color: colors.sep }}>
          <Kbd><CornerDownLeft className="size-2.5" /></Kbd>
          queue
        </span>
      </div>
    </div>
  )
})

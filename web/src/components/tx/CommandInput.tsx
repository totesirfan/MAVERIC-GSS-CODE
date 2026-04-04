import { useState, useRef, useCallback } from 'react'
import { colors } from '@/lib/colors'

interface CommandInputProps {
  onSubmit: (line: string) => void
  onBuilderToggle: () => void
  error: string | null
}

export function CommandInput({ onSubmit, onBuilderToggle, error }: CommandInputProps) {
  const [value, setValue] = useState('')
  const [history, setHistory] = useState<string[]>([])
  const [histIdx, setHistIdx] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && value.trim()) {
      onSubmit(value.trim())
      setHistory((prev) => [value.trim(), ...prev])
      setValue('')
      setHistIdx(-1)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const nextIdx = Math.min(histIdx + 1, history.length - 1)
      setHistIdx(nextIdx)
      if (history[nextIdx]) setValue(history[nextIdx])
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      const nextIdx = histIdx - 1
      if (nextIdx < 0) {
        setHistIdx(-1)
        setValue('')
      } else {
        setHistIdx(nextIdx)
        setValue(history[nextIdx])
      }
    }
  }, [value, history, histIdx, onSubmit])

  return (
    <div className="shrink-0">
      <div className="flex items-center gap-2 px-2 py-1.5 border-t" style={{ borderColor: '#333' }}>
        <span className="text-xs font-bold" style={{ color: colors.success }}>$</span>
        <input
          ref={inputRef}
          type="text"
          className="flex-1 bg-transparent text-xs outline-none"
          style={{ color: colors.value }}
          placeholder="CMD [ARGS] or SRC DEST ECHO TYPE CMD [ARGS]"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          spellCheck={false}
          autoComplete="off"
        />
        <button
          onClick={onBuilderToggle}
          className="px-1.5 py-0.5 rounded text-xs"
          style={{ color: colors.dim, border: `1px solid #333` }}
          title="Command Builder"
        >
          &#x2699;
        </button>
      </div>
      {error && (
        <div className="px-2 py-0.5 text-xs" style={{ color: colors.error }}>
          {error}
        </div>
      )}
      <div className="px-2 py-0.5 text-[10px]" style={{ color: colors.dim }}>
        Enter to queue | Up/Down for history
      </div>
    </div>
  )
}

import { useState, useEffect, useRef } from 'react'

/**
 * Returns { mounted, phase } for enter/exit animations.
 * - mounted: whether to render the DOM
 * - phase: 'entering' | 'visible' | 'exiting'
 * Use phase as a CSS class to drive transitions.
 */
export function useAnimatedOpen(open: boolean, duration = 200) {
  const [mounted, setMounted] = useState(open)
  const [phase, setPhase] = useState<'entering' | 'visible' | 'exiting'>(open ? 'visible' : 'entering')
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (open) {
      setMounted(true)
      setPhase('entering')
      // Small delay so browser renders 'entering' state before transitioning
      timer.current = setTimeout(() => setPhase('visible'), 20)
    } else if (mounted) {
      setPhase('exiting')
      timer.current = setTimeout(() => {
        setMounted(false)
        setPhase('entering')
      }, duration)
    }
    return () => { if (timer.current) clearTimeout(timer.current) }
  }, [open, duration, mounted])

  return { mounted, phase }
}

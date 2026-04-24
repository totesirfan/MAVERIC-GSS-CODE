import { useEffect, useRef, useState, useCallback, type RefObject } from 'react'

interface UseFollowScrollArgs {
  containerRef: RefObject<HTMLElement | null>
  // Selector value for the row we want centered. The container is queried
  // for `[data-follow-id="<target>"]` on every change of `target`.
  target: string | null
  // Reset-to-attached on this key's rising edge. Use 'idle' | 'active' so
  // the reset fires on every null→active transition, regardless of total.
  resetKey: 'idle' | 'active'
}

interface UseFollowScrollResult {
  detached: boolean
  jumpToCurrent: () => void
}

/**
 * Center-on-change with detach-on-manual-scroll.
 *
 * - `target` change → smooth-scroll the matching row into vertical center.
 * - Manual user scroll (wheel or touchmove) during a programmatic scroll
 *   is suppressed via a RAF flag; genuine user scrolls set `detached=true`.
 * - `jumpToCurrent()` re-centers and clears the detach.
 * - `resetKey` changing edge-wise re-attaches automatically (null→active).
 */
export function useFollowScroll({
  containerRef, target, resetKey,
}: UseFollowScrollArgs): UseFollowScrollResult {
  const [detached, setDetached] = useState(false)
  const suppressRef = useRef(false)

  const center = useCallback(() => {
    const c = containerRef.current
    if (!c || !target) return
    const el = c.querySelector<HTMLElement>(`[data-follow-id="${target}"]`)
    if (!el) return
    suppressRef.current = true
    el.scrollIntoView({ block: 'center', behavior: 'smooth' })
    requestAnimationFrame(() => {
      requestAnimationFrame(() => { suppressRef.current = false })
    })
  }, [containerRef, target])

  // Auto-center on target change (when attached).
  useEffect(() => {
    if (detached) return
    center()
  }, [target, detached, center])

  // Edge-triggered re-attach on idle → active.
  useEffect(() => {
    if (resetKey === 'active') {
      setDetached(false)
      center()
    }
  }, [resetKey, center])

  // Detach on real user scroll.
  useEffect(() => {
    const c = containerRef.current
    if (!c) return
    const onUserScroll = () => {
      if (suppressRef.current) return
      setDetached(true)
    }
    c.addEventListener('wheel', onUserScroll, { passive: true })
    c.addEventListener('touchmove', onUserScroll, { passive: true })
    return () => {
      c.removeEventListener('wheel', onUserScroll)
      c.removeEventListener('touchmove', onUserScroll)
    }
  }, [containerRef])

  const jumpToCurrent = useCallback(() => {
    setDetached(false)
    center()
  }, [center])

  return { detached, jumpToCurrent }
}

import { useEffect, useState } from 'react'
import { RadioTower } from 'lucide-react'
import { colors } from '@/lib/colors'

interface BlackoutPillProps {
  /** performance.now()-relative deadline, or null when idle. */
  until: number | null
  /** Configured blackout window in ms; pill hides entirely when <= 0. */
  configuredMs: number
}

export function BlackoutPill({ until, configuredMs }: BlackoutPillProps) {
  const [now, setNow] = useState(() => performance.now())

  const active = configuredMs > 0 && until !== null && until > now

  useEffect(() => {
    if (!active) return
    const id = setInterval(() => setNow(performance.now()), 50)
    return () => clearInterval(id)
  }, [active])

  if (!active || until === null) return null

  const remaining = Math.max(0, Math.round(until - now))

  return (
    <span
      className="text-[11px] font-bold tabular-nums flex items-center gap-1 px-1.5 py-0.5 rounded border"
      style={{
        color: colors.warning,
        borderColor: `${colors.warning}55`,
        backgroundColor: `${colors.warning}12`,
      }}
      role="status"
      aria-label={`TX blackout ${remaining} milliseconds remaining`}
    >
      <RadioTower className="size-3" style={{ color: colors.warning }} />
      BLACKOUT {remaining}ms
    </span>
  )
}

import { memo, useEffect, useState } from 'react'
import {
  ageMs, formatAge, staleLevel, STALE_OPACITY, NO_DATA_OPACITY,
} from '../../shared/staleness'

interface Props {
  pktNum: number | null
  /** Most recently updated EPS field across all sources. */
  newestT: number | null
  /** Oldest updated EPS field across all sources — drives the "fields
   *  going stale" indicator. Diverges from newestT as soon as one
   *  source runs faster than another (e.g. beacon every ~90s vs
   *  eps_hk on-demand). */
  oldestT: number | null
}

function formatUtc(ms: number): string {
  const d = new Date(ms)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} `
    + `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}Z`
}

function FooterMetaInner({ pktNum, newestT, oldestT }: Props) {
  const [nowMs, setNowMs] = useState<number>(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNowMs(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [])

  const newestAge = ageMs(newestT, nowMs)
  const oldestAge = ageMs(oldestT, nowMs)
  const hasNewest = newestT !== null && Number.isFinite(newestT)
  const hasOldest = oldestT !== null && Number.isFinite(oldestT)

  const newestLevel = hasNewest ? staleLevel(newestAge) : 'critical'
  const oldestLevel = hasOldest ? staleLevel(oldestAge) : 'critical'
  const newestOpacity = hasNewest ? STALE_OPACITY[newestLevel] : NO_DATA_OPACITY
  const oldestOpacity = hasOldest ? STALE_OPACITY[oldestLevel] : NO_DATA_OPACITY

  const pktText = pktNum !== null && Number.isFinite(pktNum) ? `eps · #${pktNum}` : 'eps'
  const snapText = hasNewest ? formatUtc(newestT!) : '—'

  return (
    <div className="footer-row" data-component="FooterMeta" aria-live="polite">
      <span><span className="k">pkt</span><span className="v">{pktText}</span></span>
      <span className="sep">|</span>
      <span style={{ opacity: newestOpacity }}>
        <span className="k">newest</span>
        <span className="v" data-age="newest">{hasNewest ? formatAge(newestAge) : '—'}</span>
      </span>
      <span className="sep">|</span>
      <span style={{ opacity: oldestOpacity }}>
        <span className="k">oldest</span>
        <span className="v" data-age="oldest">{hasOldest ? formatAge(oldestAge) : '—'}</span>
      </span>
      <span className="right">
        <span className="k">newest @</span><span className="v">{snapText}</span>
      </span>
    </div>
  )
}

export const FooterMeta = memo(FooterMetaInner)

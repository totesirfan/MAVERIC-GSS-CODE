import { memo, useEffect, useState } from 'react'

interface Props {
  pktNum: number | null
  receivedAtMs: number | null
}

function formatAge(nowMs: number, pastMs: number): string {
  const delta = Math.max(0, Math.floor((nowMs - pastMs) / 1000))
  if (delta < 60) return `00:00:${String(delta).padStart(2, '0')} ago`
  const m = Math.floor(delta / 60)
  const s = delta % 60
  if (m < 60) return `00:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')} ago`
  const h = Math.floor(m / 60)
  return `${String(h).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}:${String(s).padStart(2, '0')} ago`
}

function formatUtc(ms: number): string {
  const d = new Date(ms)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} `
    + `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}Z`
}

function FooterMetaInner({ pktNum, receivedAtMs }: Props) {
  const [nowMs, setNowMs] = useState<number>(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNowMs(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [])

  const hasSnap = receivedAtMs !== null && Number.isFinite(receivedAtMs)
  const ageText = hasSnap ? formatAge(nowMs, receivedAtMs!) : '—'
  const snapText = hasSnap ? formatUtc(receivedAtMs!) : '—'
  const pktText = pktNum !== null && Number.isFinite(pktNum) ? `eps_hk · #${pktNum}` : 'eps_hk'
  return (
    <div className="footer-row" data-component="FooterMeta" aria-live="polite">
      <span><span className="k">pkt</span><span className="v">{pktText}</span></span>
      <span className="sep">|</span>
      <span><span className="k">last</span><span className="v" data-age="lastRxAt">{ageText}</span></span>
      <span className="right">
        <span className="k">snapshot</span><span className="v">{snapText}</span>
      </span>
    </div>
  )
}

export const FooterMeta = memo(FooterMetaInner)

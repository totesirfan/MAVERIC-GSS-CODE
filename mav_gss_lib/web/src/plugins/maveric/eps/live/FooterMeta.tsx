import { memo } from 'react'

interface Props {
  pktNum: number | null
  receivedAtMs: number | null
  onClearSnapshot: () => Promise<void>
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

function FooterMetaInner({ pktNum, receivedAtMs, onClearSnapshot }: Props) {
  const now = Date.now()
  const hasSnap = receivedAtMs !== null && Number.isFinite(receivedAtMs)
  const ageText = hasSnap ? formatAge(now, receivedAtMs!) : '—'
  const snapText = hasSnap ? formatUtc(receivedAtMs!) : '—'
  const pktText = pktNum !== null && Number.isFinite(pktNum) ? `eps_hk · 48 F · #${pktNum}` : 'eps_hk · 48 F'
  return (
    <div className="footer-row" data-component="FooterMeta" aria-live="polite">
      <span><span className="k">pkt</span><span className="v">{pktText}</span></span>
      <span className="sep">|</span>
      <span><span className="k">payload</span><span className="v">96 B</span></span>
      <span className="sep">|</span>
      <span><span className="k">last</span><span className="v" data-age="lastRxAt">{ageText}</span></span>
      <span className="right">
        <span className="k">snapshot</span><span className="v">{snapText}</span>
        <button
          type="button"
          onClick={() => { void onClearSnapshot() }}
          aria-label="Clear EPS snapshot"
          style={{
            marginLeft: 10, fontSize: 10, padding: '2px 8px',
            background: 'transparent', color: 'var(--text-muted)',
            border: '1px solid var(--border-strong)', borderRadius: 3, cursor: 'pointer',
          }}
        >
          CLEAR
        </button>
      </span>
    </div>
  )
}

export const FooterMeta = memo(FooterMetaInner)

import styles from './ModeStrip.module.css'

interface ModeStripProps {
  labels: string[]
  activeIndex: number | undefined
  columns?: number
}

export function ModeStrip({ labels, activeIndex, columns }: ModeStripProps) {
  const cols = columns ?? labels.length
  return (
    <div
      className={styles.modeStrip}
      style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
    >
      {labels.map((label, idx) => (
        <div
          key={idx}
          className={`${styles.modeCell} ${activeIndex === idx ? styles.modeCellActive : ''}`}
        >
          <span className={styles.modeCellIdx}>{idx}</span>
          <span className={styles.modeCellLabel}>{label}</span>
        </div>
      ))}
    </div>
  )
}

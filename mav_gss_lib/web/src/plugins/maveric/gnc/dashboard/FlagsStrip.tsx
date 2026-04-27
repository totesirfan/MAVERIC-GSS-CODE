import type { ReactNode } from 'react'
import { Card } from './Card'
import { FlagDot } from '../shared/FlagDot'
import { ageMs, formatAge, staleLevel } from '../../staleness'
import type { GncState, StatBitfield, ActErrBitfield, SenErrBitfield } from '../types'
import styles from './FlagsStrip.module.css'

type Tone = 'fresh' | 'warn' | 'danger' | 'neutral'

/** Roll up a section's tone from its data + faults + age.
 *  - no data yet → neutral (gray)
 *  - has data + faults → fault polarity (danger for actuators, warn for sensors)
 *  - has data + nominal + very stale (> 12 h) → neutral (gray), since
 *    a green accent over 12-hour-old data would be misleading
 *  - otherwise → fresh (green)
 *  The 30-min staleness tier is left alone — it's within normal GNC pass
 *  cadence, so promoting to warn there would cry wolf. */
function sectionTone(
  hasData: boolean,
  faults: number,
  receivedAt: number | null,
  nowMs: number,
  faultPolarity: 'warn' | 'danger',
): Tone {
  if (!hasData) return 'neutral'
  if (faults > 0) return faultPolarity
  return staleLevel(ageMs(receivedAt, nowMs)) === 'critical' ? 'neutral' : 'fresh'
}

interface FlagsStripProps {
  state: GncState
  nowMs: number
}

export function FlagsStrip({ state, nowMs }: FlagsStripProps) {
  // STAT is the STAT register (module 0, reg 128). Both the RES path
  // (mtq_get_1 / mtq_get_active / mtq_get_hk / mtq_get_param) and
  // tlm_beacon populate it; the platform router LWW-merges them, so
  // this consumer sees the newest value regardless of source. Errors
  // and status flags both live in STAT, so they share one cluster
  // header + one timer.
  const stat = state.STAT
  const actErr = state.ACT_ERR
  const senErr = state.SEN_ERR

  const statV = stat?.value as StatBitfield | undefined
  const actV  = actErr?.value as ActErrBitfield | undefined
  const senV  = senErr?.value as SenErrBitfield | undefined

  const statT = stat?.t ?? null
  const actT  = actErr?.t ?? null
  const senT  = senErr?.t ?? null

  // Fault tallies drive the per-section tone + optional pill.
  const statFaults = countTrue([
    statV?.HERR, statV?.SERR, statV?.WDT,
    statV?.UV, statV?.OC, statV?.OT,
  ])
  const actFaults = countTrue([actV?.MTQ0, actV?.MTQ1, actV?.MTQ2])
  const senFaults = countTrue([senV?.IMU0, senV?.IMU1, senV?.MAG5, senV?.FSS5])

  const statTone = sectionTone(statV != null, statFaults, statT, nowMs, 'danger')
  const actTone  = sectionTone(actV  != null, actFaults,  actT,  nowMs, 'danger')
  const senTone  = sectionTone(senV  != null, senFaults,  senT,  nowMs, 'warn')

  return (
    <Card title="ADCS · MTQ Flags">
      <FlagSection
        tag="STAT · System Flags"
        tone={statTone}
        receivedAt={statT}
        nowMs={nowMs}
      >
        <div className={`${styles.grid} ${styles.c7}`}>
          <FlagDot label="Hard Error"  value={statV?.HERR}            receivedAtMs={statT} nowMs={nowMs} compact />
          <FlagDot label="Soft Error"  value={statV?.SERR}            receivedAtMs={statT} nowMs={nowMs} compact />
          <FlagDot label="Watchdog"    value={statV?.WDT}             receivedAtMs={statT} nowMs={nowMs} compact />
          <FlagDot label="Undervolt"   value={statV?.UV}              receivedAtMs={statT} nowMs={nowMs} compact />
          <FlagDot label="Overcurrent" value={statV?.OC}              receivedAtMs={statT} nowMs={nowMs} compact />
          <FlagDot label="Temp Prot"   value={statV?.OT}              receivedAtMs={statT} nowMs={nowMs} compact />
          <FlagDot label="GNSS"        value={statV?.GNSS_UP_TO_DATE} receivedAtMs={statT} nowMs={nowMs} polarity="status" compact />
        </div>
        <div className={`${styles.grid} ${styles.c8}`}>
          <FlagDot label="TLE"         value={statV?.TLE}   receivedAtMs={statT} nowMs={nowMs} polarity="status" compact />
          <FlagDot label="De-Sat"      value={statV?.DES}   receivedAtMs={statT} nowMs={nowMs} polarity="status" compact />
          <FlagDot label="Sun"         value={statV?.SUN}   receivedAtMs={statT} nowMs={nowMs} polarity="status" compact />
          <FlagDot label="Target Lost" value={statV?.TGL}   receivedAtMs={statT} nowMs={nowMs} compact />
          <FlagDot label="Tumble"      value={statV?.TUMB}  receivedAtMs={statT} nowMs={nowMs} compact />
          <FlagDot label="Ang Mom"     value={statV?.AME}   receivedAtMs={statT} nowMs={nowMs} compact />
          <FlagDot label="Custom SV"   value={statV?.CUSSV} receivedAtMs={statT} nowMs={nowMs} polarity="status" compact />
          <FlagDot label="EKF"         value={statV?.EKF}   receivedAtMs={statT} nowMs={nowMs} polarity="status" compact />
        </div>
      </FlagSection>

      <div className={styles.rowSplit}>
        <FlagSection
          tag="Actuator Errors"
          tone={actTone}
          receivedAt={actT}
          nowMs={nowMs}
          pill={actFaults > 0 ? pluralizeFaults(actFaults) : undefined}
        >
          <div className={`${styles.grid} ${styles.c3}`}>
            <FlagDot label="MTQ2" value={actV?.MTQ2} receivedAtMs={actT} nowMs={nowMs} compact />
            <FlagDot label="MTQ1" value={actV?.MTQ1} receivedAtMs={actT} nowMs={nowMs} compact />
            <FlagDot label="MTQ0" value={actV?.MTQ0} receivedAtMs={actT} nowMs={nowMs} compact />
          </div>
        </FlagSection>
        <FlagSection
          tag="Sensor Errors"
          tone={senTone}
          receivedAt={senT}
          nowMs={nowMs}
          pill={senFaults > 0 ? pluralizeFaults(senFaults) : undefined}
        >
          <div className={`${styles.grid} ${styles.c4}`}>
            <FlagDot label="IMU1" value={senV?.IMU1} receivedAtMs={senT} nowMs={nowMs} compact />
            <FlagDot label="IMU0" value={senV?.IMU0} receivedAtMs={senT} nowMs={nowMs} compact />
            <FlagDot label="MAG5" value={senV?.MAG5} receivedAtMs={senT} nowMs={nowMs} compact />
            <FlagDot label="FSS5" value={senV?.FSS5} receivedAtMs={senT} nowMs={nowMs} compact />
          </div>
        </FlagSection>
      </div>
    </Card>
  )
}

interface FlagSectionProps {
  tag: string
  tone: Tone
  receivedAt: number | null
  nowMs: number
  pill?: string
  children: ReactNode
}

function FlagSection({ tag, tone, receivedAt, nowMs, pill, children }: FlagSectionProps) {
  const age = ageMs(receivedAt, nowMs)
  const timerText = receivedAt != null ? formatAge(age) : '—'
  return (
    <div className={`${styles.section} ${styles[tone]}`}>
      <div className={styles.sidebar}>
        <span className={styles.tag}>{tag}</span>
        <div className={styles.meta}>
          <span className={styles.timer}>{timerText}</span>
          {pill && <span className={styles.pill}>{pill}</span>}
        </div>
      </div>
      <div className={styles.body}>{children}</div>
    </div>
  )
}

function countTrue(flags: Array<boolean | undefined>): number {
  let n = 0
  for (const f of flags) if (f === true) n += 1
  return n
}

function pluralizeFaults(n: number): string {
  return n === 1 ? '1 Fault' : `${n} Faults`
}

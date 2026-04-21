import { describe, expect, it } from 'vitest'
import {
  activeSource, alarmState, chargeDirection, clamp, efficiency,
  fmt, socFromVbat, thermalEta,
} from './derive'
import alarmsFixture from '../../../../../../docs/eps-port/fixtures/alarms.json'
import decodedFixture from '../../../../../../docs/eps-port/fixtures/decoded.json'
import type { EpsFields, SourceId } from './types'

interface AlarmCase {
  name: string
  fields: Record<string, unknown>
  expect: Record<string, string>
}

interface AlarmFixture {
  cases: AlarmCase[]
}

interface DecodedFixture {
  fields: EpsFields
  derived_values: {
    P_BUS: number
    P_IN: number
    P_OUT: number
    EFFICIENCY: number
    SOC_from_VBAT: number
    active_source: SourceId
    charge_direction_single_sample: string
  }
}

const fixture = decodedFixture as unknown as DecodedFixture

describe('fmt', () => {
  it('returns — for non-finite', () => {
    expect(fmt(NaN, 2)).toBe('—')
    expect(fmt(Infinity, 2)).toBe('—')
    expect(fmt(null, 2)).toBe('—')
    expect(fmt(undefined, 3)).toBe('—')
  })
  it('formats with fixed digits', () => {
    expect(fmt(3.14159, 2)).toBe('3.14')
    expect(fmt(3, 3)).toBe('3.000')
  })
})

describe('clamp', () => {
  it('clamps to range', () => {
    expect(clamp(5, 0, 10)).toBe(5)
    expect(clamp(-1, 0, 10)).toBe(0)
    expect(clamp(11, 0, 10)).toBe(10)
  })
})

describe('socFromVbat', () => {
  it('maps 6.0 V → 0%', () => { expect(socFromVbat(6.0)).toBe(0) })
  it('maps 8.4 V → 100%', () => { expect(socFromVbat(8.4)).toBe(100) })
  it('is linear in between', () => {
    expect(socFromVbat(7.2)).toBeCloseTo(50, 1)
  })
  it('clamps to [0,100]', () => {
    expect(socFromVbat(5.0)).toBe(0)
    expect(socFromVbat(9.0)).toBe(100)
  })
  it('returns null for non-finite', () => {
    expect(socFromVbat(NaN)).toBeNull()
    expect(socFromVbat(undefined)).toBeNull()
  })
  it('matches fixture at V_BAT=7.4', () => {
    const got = socFromVbat(fixture.fields.V_BAT)
    expect(got).not.toBeNull()
    expect(got as number).toBeCloseTo(fixture.derived_values.SOC_from_VBAT, 1)
  })
})

describe('activeSource', () => {
  it('priority V_AC2 > V_AC1 > VSIN1 > VSIN2 > VSIN3 > BAT', () => {
    expect(activeSource({ V_AC2: 9, V_AC1: 8, VSIN1: 5 } as Partial<EpsFields>)).toBe('V_AC2')
    expect(activeSource({ V_AC2: 0, V_AC1: 8, VSIN1: 5 } as Partial<EpsFields>)).toBe('V_AC1')
    expect(activeSource({ V_AC2: 0, V_AC1: 0, VSIN1: 5, VSIN2: 4 } as Partial<EpsFields>)).toBe('VSIN1')
  })
  it('qualifies source when V > 1.0', () => {
    expect(activeSource({ VSIN1: 0.9 } as Partial<EpsFields>)).toBeNull()
    expect(activeSource({ VSIN1: 1.1 } as Partial<EpsFields>)).toBe('VSIN1')
  })
  it('BAT qualifies when I_BAT < -0.010', () => {
    expect(activeSource({ I_BAT: -0.02 } as Partial<EpsFields>)).toBe('BAT')
    expect(activeSource({ I_BAT: -0.005 } as Partial<EpsFields>)).toBeNull()
  })
  it('returns fixture-expected source', () => {
    expect(activeSource(fixture.fields)).toBe(fixture.derived_values.active_source)
  })
})

describe('chargeDirection', () => {
  it('returns idle for non-finite', () => {
    expect(chargeDirection(NaN, [])).toBe('idle')
  })
  it('uses current sign when |current| > 0.05', () => {
    expect(chargeDirection(0.1, [])).toBe('charge')
    expect(chargeDirection(-0.1, [])).toBe('discharge')
  })
  it('returns idle in deadband without 3 confirming samples', () => {
    expect(chargeDirection(0.02, [])).toBe('idle')
    expect(chargeDirection(0.02, [0.015])).toBe('idle')
  })
  it('returns direction when 3 same-sign samples > hysteresis', () => {
    expect(chargeDirection(0.02, [0.03, 0.015])).toBe('charge')
    expect(chargeDirection(-0.02, [-0.03, -0.015])).toBe('discharge')
  })
  it('returns idle if samples are mixed sign', () => {
    expect(chargeDirection(0.02, [-0.015, 0.015])).toBe('idle')
  })
  it('matches fixture single-sample case (I_BAT=-0.3)', () => {
    const dir = chargeDirection(fixture.fields.I_BAT, [])
    expect(dir).toBe(fixture.derived_values.charge_direction_single_sample)
  })
})

describe('thermalEta', () => {
  it('null when dtMs < 1000', () => {
    expect(thermalEta(30, 29, 500, 60)).toBeNull()
  })
  it('null when |rate| < 0.02 °C/s', () => {
    expect(thermalEta(30.01, 30.0, 1000, 60)).toBeNull()
  })
  it('null for non-finite inputs', () => {
    expect(thermalEta(NaN, 30, 1000, 60)).toBeNull()
    expect(thermalEta(30, NaN, 1000, 60)).toBeNull()
  })
  it('seconds to limit for rising T', () => {
    // T=30, prevT=28 over 1000 ms → rate 2 °C/s → (60-30)/2 = 15s
    expect(thermalEta(30, 28, 1000, 60)).toBeCloseTo(15, 3)
  })
})

describe('efficiency', () => {
  it('null when source is AC', () => {
    expect(efficiency(fixture.fields, 'V_AC1')).toBeNull()
    expect(efficiency(fixture.fields, 'V_AC2')).toBeNull()
  })
  it('matches fixture value (VSIN1 active)', () => {
    const got = efficiency(fixture.fields, fixture.derived_values.active_source)
    expect(got).not.toBeNull()
    expect(got as number).toBeCloseTo(fixture.derived_values.EFFICIENCY, 3)
  })
  it('null when P_in < 0.1', () => {
    const fields = { ...fixture.fields, PSIN1: 0, PSIN2: 0, PSIN3: 0, I_BAT: 0 } as EpsFields
    expect(efficiency(fields, 'VSIN1')).toBeNull()
  })
})

describe('alarmState — fixture-driven', () => {
  const alarms = alarmsFixture as AlarmFixture
  for (const c of alarms.cases) {
    it(`case: ${c.name}`, () => {
      // Coerce JSON "NaN"/"Infinity" strings to actual non-finite numbers
      // so the decoder-side behaviour is testable (production inputs are
      // always numbers, but the fixture exercises the non-finite branch).
      const fields: Record<string, unknown> = {}
      for (const [k, v] of Object.entries(c.fields)) {
        if (v === 'NaN') fields[k] = NaN
        else if (v === 'Infinity') fields[k] = Infinity
        else fields[k] = v
      }
      const got = alarmState(fields)
      for (const [field, want] of Object.entries(c.expect)) {
        expect(got[field]).toBe(want)
      }
    })
  }
})

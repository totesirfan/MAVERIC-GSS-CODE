import { describe, expect, it } from 'vitest'
import { fuzzyScore } from './fuzzyScore'

describe('fuzzyScore', () => {
  it('returns 1 for empty needle', () => {
    expect(fuzzyScore('eps_get_temp', '')).toBe(1)
  })

  it('returns 1 for exact match', () => {
    expect(fuzzyScore('eps_get_temp', 'eps_get_temp')).toBe(1)
  })

  it('scores prefix highest below exact', () => {
    expect(fuzzyScore('eps_get_temp', 'eps')).toBe(0.95)
  })

  it('scores word-boundary anchor above plain substring', () => {
    expect(fuzzyScore('gnc_get_mode', 'get')).toBe(0.85)
    expect(fuzzyScore('gnc_get_mode', 'et_')).toBe(0.7)
  })

  it('scores fuzzy subsequence below substring', () => {
    const fuzzy = fuzzyScore('eps_get_temp', 'egtm')
    expect(fuzzy).toBeGreaterThan(0)
    expect(fuzzy).toBeLessThan(0.7)
  })

  it('returns 0 when characters are missing', () => {
    expect(fuzzyScore('eps_get_temp', 'xyz')).toBe(0)
  })

  it('ranks tighter clusters above scattered subsequences', () => {
    const tight = fuzzyScore('eps_get_temp', 'egt')
    const scattered = fuzzyScore('toggle_hex_display', 'eps')
    expect(tight).toBeGreaterThan(scattered)
  })

  it('rejects scattered subsequence noise that the old strict scorer missed', () => {
    // "Toggle Hex Display" famously matched "eps" via scattered subsequence
    // under cmdk's default scorer. We allow it a small fuzzy score here
    // (well below 0.70) but a real prefix match must dominate.
    const noise = fuzzyScore('toggle_hex_display', 'eps')
    const real = fuzzyScore('eps_get_temp', 'eps')
    expect(real).toBeGreaterThan(noise)
  })
})

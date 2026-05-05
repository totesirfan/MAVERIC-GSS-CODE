// Fuzzy scorer for the MAVERIC TX command picker. Returns 0..1.
//
// Tiers:
//   exact equality                         → 1.00
//   haystack starts with needle            → 0.95
//   needle anchored at a word boundary     → 0.85
//   plain substring                        → 0.70
//   subsequence inside one word, anchored  → 0.55
//   fuzzy subsequence with bonuses         → 0..0.65
//   no subsequence                         → 0
//
// Word boundaries are `_`, `-`, whitespace, or position 0 — matching
// how cmdk and the MAVERIC command names (`gnc_get_mode`, ...) split.

const WORD_BOUNDARY_RE = /[_\-\s]/

export function fuzzyScore(haystack: string, needle: string): number {
  const n = needle.toLowerCase().trim()
  if (!n) return 1
  const h = haystack.toLowerCase()

  if (h === n) return 1
  if (h.startsWith(n)) return 0.95
  if (anchoredAtWord(h, n)) return 0.85
  if (h.includes(n)) return 0.7

  for (const word of h.split(WORD_BOUNDARY_RE)) {
    if (word && word[0] === n[0] && isSubsequence(word, n)) return 0.55
  }

  return fuzzySubsequence(h, n)
}

function anchoredAtWord(hay: string, needle: string): boolean {
  let from = 0
  while (from <= hay.length - needle.length) {
    const idx = hay.indexOf(needle, from)
    if (idx < 0) return false
    if (idx === 0 || WORD_BOUNDARY_RE.test(hay[idx - 1])) return true
    from = idx + 1
  }
  return false
}

function isSubsequence(hay: string, needle: string): boolean {
  let i = 0
  for (let j = 0; j < hay.length && i < needle.length; j++) {
    if (hay[j] === needle[i]) i++
  }
  return i === needle.length
}

// Fuzzy subsequence with positional bonuses. Capped at 0.65 so a fuzzy
// hit can never beat a real substring (0.70+).
function fuzzySubsequence(hay: string, needle: string): number {
  let i = 0
  let consecutive = 0
  let score = 0
  let firstMatch = -1
  let lastMatch = -1

  for (let j = 0; j < hay.length && i < needle.length; j++) {
    if (hay[j] !== needle[i]) {
      consecutive = 0
      continue
    }
    if (firstMatch < 0) firstMatch = j
    lastMatch = j

    let charScore = 1
    if (j === 0 || WORD_BOUNDARY_RE.test(hay[j - 1])) charScore += 2
    charScore += consecutive

    score += charScore
    consecutive += 1
    i++
  }

  if (i < needle.length) return 0

  const span = lastMatch - firstMatch + 1
  const density = needle.length / span
  const ideal = needle.length * 4
  const normalized = (score / ideal) * density
  return Math.min(0.65, Math.max(0.05, normalized * 0.65))
}

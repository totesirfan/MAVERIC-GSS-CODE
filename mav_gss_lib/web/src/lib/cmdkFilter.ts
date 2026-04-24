// Custom command-palette scorer. cmdk's default is a subsequence matcher — it
// gives "Toggle Hex Display" a non-zero score for "eps" because the letters
// appear scattered across the string. That noise pushes real hits down, since
// cmdk renders groups in JSX order. This scorer only rewards matches a human
// would recognise as intentional:
//
//   exact                         → 1.00
//   haystack starts with needle   → 0.95
//   needle starts a word          → 0.85
//   plain substring               → 0.70
//   acronym / word initials       → 0.60
//   subsequence inside one word,
//   anchored at the word's start  → 0.50
//
// Keywords are pooled alongside the value, so nav items can declare extra
// search terms without diluting the score.

const ESCAPE_RE = /[.*+?^${}()|[\]\\]/g
const INITIALS_RE = /\b\w/g
const WORDS_RE = /\s+/

export function strictFilter(value: string, search: string, keywords?: string[]): number {
  const needle = search.toLowerCase().trim()
  if (!needle) return 1

  let best = 0
  for (const raw of [value, ...(keywords ?? [])]) {
    if (!raw) continue
    const s = scoreOne(raw.toLowerCase(), needle)
    if (s > best) best = s
    if (best === 1) break
  }
  return best
}

function scoreOne(hay: string, needle: string): number {
  if (hay === needle) return 1
  if (hay.startsWith(needle)) return 0.95

  const escaped = needle.replace(ESCAPE_RE, '\\$&')
  if (new RegExp(`\\b${escaped}`).test(hay)) return 0.85
  if (hay.includes(needle)) return 0.7

  const initials = hay.match(INITIALS_RE)?.join('') ?? ''
  if (initials.includes(needle)) return 0.6

  for (const word of hay.split(WORDS_RE)) {
    if (word[0] === needle[0] && isSubsequence(word, needle)) return 0.5
  }
  return 0
}

function isSubsequence(hay: string, needle: string): boolean {
  let i = 0
  for (let j = 0; j < hay.length && i < needle.length; j++) {
    if (hay[j] === needle[i]) i++
  }
  return i === needle.length
}

export const colors = {
  label: '#00bfff', value: '#ffffff', success: '#00ff87',
  warning: '#ffd700', error: '#ff4444', dim: '#888888',
  sep: '#707070', bgBase: '#12121e', bgPanel: '#1a1a2e',
  bgCard: 'rgba(255,255,255,0.03)',
  frameAx25: '#6699cc', frameGolay: '#55bbaa',
  ptypeCmd: '#00bfff', ptypeRes: '#00ff87', ptypeAck: '#55bbaa',
  ptypeTlm: '#6699cc', ptypeFile: '#ff69b4',
} as const

export function ptypeColor(ptype: string): string {
  const map: Record<string, string> = {
    CMD: colors.ptypeCmd, RES: colors.ptypeRes, ACK: colors.ptypeAck,
    TLM: colors.ptypeTlm, FILE: colors.ptypeFile,
  }
  return map[ptype] || colors.dim
}

export function frameColor(frame: string): string {
  if (frame.includes('AX.25')) return colors.frameAx25
  if (frame.includes('GOLAY')) return colors.frameGolay
  return colors.error
}

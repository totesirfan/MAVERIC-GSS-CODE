import type { RenderCell, RenderingData, RenderingFlag } from '@/lib/types'

export function cellValue(cell: RenderCell | undefined): unknown {
  return cell?.value ?? ''
}

export function cellText(cell: RenderCell | undefined): string {
  return String(cellValue(cell))
}

export function renderingValue(rendering: RenderingData | undefined, id: string): unknown {
  return cellValue(rendering?.row?.[id])
}

export function renderingText(rendering: RenderingData | undefined, id: string): string {
  return String(renderingValue(rendering, id))
}

export function renderingFlags(rendering: RenderingData | undefined, id = 'flags'): RenderingFlag[] {
  const value = renderingValue(rendering, id)
  return Array.isArray(value) ? value as RenderingFlag[] : []
}

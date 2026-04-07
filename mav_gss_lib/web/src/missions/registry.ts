/**
 * Mission TX Builder Registry
 *
 * Maps mission IDs to lazy-loaded builder components. A mission builder
 * receives the queueMissionCmd callback and renders its own command-building UI.
 *
 * To register a mission builder, add one entry:
 *   '<mission_id>': () => import('./<mission_id>/TxBuilder'),
 *
 * The component must satisfy MissionBuilderProps from '@/lib/types'.
 */
import { lazy, type ComponentType } from 'react'
import type { MissionBuilderProps } from '@/lib/types'

const builders: Record<string, () => Promise<{ default: ComponentType<MissionBuilderProps> }>> = {
  // 'maveric': () => import('./maveric/TxBuilder'),  // Phase 4
}

export function getMissionBuilder(missionId: string): ComponentType<MissionBuilderProps> | null {
  const loader = builders[missionId.toLowerCase()]
  if (!loader) return null
  return lazy(loader)
}

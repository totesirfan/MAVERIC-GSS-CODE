/**
 * Mission TX Builder Registry — Convention-Based Discovery
 *
 * Auto-discovers mission builder components by convention:
 *   missions/<mission_id>/TxBuilder.tsx
 *
 * Each component must satisfy MissionBuilderProps from '@/lib/types'.
 * No manual registration needed — just create the file.
 */
import { lazy, type ComponentType } from 'react'
import type { MissionBuilderProps } from '@/lib/types'

const modules = import.meta.glob<{ default: ComponentType<MissionBuilderProps> }>(
  './**/TxBuilder.tsx',
)

const builders: Record<string, () => Promise<{ default: ComponentType<MissionBuilderProps> }>> = {}
for (const path of Object.keys(modules)) {
  const match = path.match(/^\.\/([^/]+)\/TxBuilder\.tsx$/)
  if (match) {
    builders[match[1].toLowerCase()] = modules[path]
  }
}

const cache = new Map<string, ComponentType<MissionBuilderProps>>()

export function getMissionBuilder(missionId: string): ComponentType<MissionBuilderProps> | null {
  const key = missionId.toLowerCase()
  const loader = builders[key]
  if (!loader) return null
  let component = cache.get(key)
  if (!component) {
    component = lazy(loader)
    cache.set(key, component)
  }
  return component
}

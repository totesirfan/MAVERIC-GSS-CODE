import { Gauge, Radio } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { PluginPageDef } from '@/plugins/registry'

export type NavigationTabDef =
  | {
      kind: 'dashboard'
      id: '__dashboard__'
      name: string
      description: string
      icon: LucideIcon
      category: 'mission'
      order: number
    }
  | {
      kind: 'radio'
      id: '__radio__'
      name: string
      description: string
      icon: LucideIcon
      category: 'platform'
      order: number
    }
  | {
      kind: 'plugin'
      id: string
      name: string
      description: string
      icon: LucideIcon
      category: 'mission' | 'platform'
      order?: number
      plugin: PluginPageDef
    }

export const DASHBOARD_TAB: NavigationTabDef = {
  kind: 'dashboard',
  id: '__dashboard__',
  name: 'Dashboard',
  description: 'RX / TX mission console',
  icon: Gauge,
  category: 'mission',
  order: -Infinity,
}

export const RADIO_TAB: NavigationTabDef = {
  kind: 'radio',
  id: '__radio__',
  name: 'Radio',
  description: 'GNU Radio process supervisor',
  icon: Radio,
  category: 'platform',
  order: -1000,
}

/** Sort: Dashboard first, then explicit order, then category, then alphabetical. */
export function navTabCompare(a: NavigationTabDef, b: NavigationTabDef): number {
  if (a.id === '__dashboard__') return -1
  if (b.id === '__dashboard__') return 1
  const orderA = a.order ?? Infinity
  const orderB = b.order ?? Infinity
  if (orderA !== orderB) return orderA - orderB
  const catOrder = (t: NavigationTabDef) => t.category === 'mission' ? 0 : 1
  const catDiff = catOrder(a) - catOrder(b)
  if (catDiff !== 0) return catDiff
  return a.name.localeCompare(b.name)
}

/** Build NavigationTabDef[] from a PluginPageDef[] array. */
export function buildNavigationTabs(plugins: PluginPageDef[]): NavigationTabDef[] {
  const pluginNavs: NavigationTabDef[] = plugins.map(p => ({
    kind: 'plugin' as const,
    id: p.id,
    name: p.name,
    description: p.description,
    icon: p.icon,
    category: p.category,
    order: p.order,
    plugin: p,
  }))
  return [DASHBOARD_TAB, RADIO_TAB, ...pluginNavs].sort(navTabCompare)
}

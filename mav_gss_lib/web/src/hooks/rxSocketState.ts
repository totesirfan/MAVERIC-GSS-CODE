import { packetFlags } from '@/lib/rxPacket'
import type { ParamUpdate, RxPacket } from '@/lib/types'

export interface RxPacketStats {
  total: number
  crcFailures: number
  dupCount: number
  hasEcho: boolean
}

export interface WireParamUpdate {
  name: string
  v: unknown
  t: number
  unit?: string
  display_only?: boolean
}

export interface RxPacketEvent {
  type: 'rx_packet'
  packet: RxPacket
  parameters?: WireParamUpdate[]
  replay?: boolean
}

export interface RxBatchEvent {
  type: 'rx_batch'
  events?: RxPacketEvent[]
}

const EMPTY_STATS: RxPacketStats = {
  total: 0,
  crcFailures: 0,
  dupCount: 0,
  hasEcho: false,
}

export function createEmptyStats(): RxPacketStats {
  return { ...EMPTY_STATS }
}

function packetHasEcho(packet: RxPacket): boolean {
  return packet.is_echo
}

function packetHasCrcFail(packet: RxPacket): boolean {
  return packetFlags(packet).some(f => f.tag === 'CRC')
}

function toParamUpdate(update: WireParamUpdate): ParamUpdate {
  return {
    name: update.name,
    value: update.v,
    ts_ms: update.t,
    unit: update.unit,
    display_only: update.display_only,
  }
}

export class RxPacketBuffer {
  private packets: RxPacket[] = []
  private parametersById: Record<string, ParamUpdate[]> = {}
  private stats: RxPacketStats = createEmptyStats()
  private readonly maxPackets: number

  constructor(maxPackets: number) {
    this.maxPackets = maxPackets
  }

  add(event: RxPacketEvent): void {
    const pkt = event.packet
    this.packets.push(pkt)
    if (pkt.event_id) {
      this.parametersById[pkt.event_id] = (event.parameters ?? []).map(toParamUpdate)
    }
    this.stats.total += 1
    if (packetHasCrcFail(pkt)) this.stats.crcFailures += 1
    if (pkt.is_dup) this.stats.dupCount += 1
    if (!this.stats.hasEcho && packetHasEcho(pkt)) this.stats.hasEcho = true

    if (this.packets.length > this.maxPackets) {
      const removed = this.packets.shift()
      if (!removed) return
      if (removed.event_id) delete this.parametersById[removed.event_id]
      this.stats.total -= 1
      if (packetHasCrcFail(removed)) this.stats.crcFailures -= 1
      if (removed.is_dup) this.stats.dupCount -= 1
      if (this.stats.hasEcho && packetHasEcho(removed) && !this.packets.some(packetHasEcho)) {
        this.stats.hasEcho = false
      }
    }
  }

  clear(): void {
    this.packets = []
    this.parametersById = {}
    this.stats = createEmptyStats()
  }

  snapshot(): {
    packets: RxPacket[]
    parametersById: Record<string, ParamUpdate[]>
    stats: RxPacketStats
  } {
    return {
      packets: [...this.packets],
      parametersById: { ...this.parametersById },
      stats: { ...this.stats },
    }
  }
}

// ---- RX ----

export interface RxPacket {
  num: number
  time: string
  time_utc: string
  frame: string
  src: string
  dest: string
  echo: string
  ptype: string
  cmd: string
  args_named: { name: string; value: string; important?: boolean }[]
  args_extra: string[]
  size: number
  crc16_ok: boolean | null
  crc32_ok: boolean | null
  is_echo: boolean
  is_dup: boolean
  is_unknown: boolean
  raw_hex: string
  warnings: string[]
  csp_header: Record<string, number> | null
  ax25_header: string | null
  sat_time_utc?: string | null
  sat_time_local?: string | null
  sat_time_ms?: number | null
}

export interface RxStatus {
  zmq: string
  pkt_rate: number
  silence_s: number
}

// ---- TX ----

export interface TxQueueCmd {
  type: 'cmd'
  num: number
  src: string
  dest: string
  echo: string
  ptype: string
  cmd: string
  args: string
  args_named?: { name: string; value: string }[]
  args_extra?: string[]
  guard: boolean
  size: number
}

export interface TxQueueDelay {
  type: 'delay'
  delay_ms: number
}

export type TxQueueItem = TxQueueCmd | TxQueueDelay

export interface TxQueueSummary {
  cmds: number
  guards: number
  est_time_s: number
}

export interface TxHistoryItem {
  n: number
  ts: string
  src: string
  dest: string
  echo: string
  ptype: string
  cmd: string
  args: string
  size: number
}

export interface SendProgress {
  sent: number
  total: number
  current: string
  waiting?: boolean
}

export interface GuardConfirm {
  index: number
  cmd: string
  args: string
  dest: string
}

// ---- Commands ----

export interface CommandArg {
  name: string
  type: string
  important?: boolean
}

export interface CommandDef {
  dest?: string
  echo?: string
  ptype?: string
  nodes?: string[]
  tx_args?: CommandArg[]
  rx_args?: CommandArg[]
  rx_only?: boolean
  variadic?: boolean
}

export type CommandSchema = Record<string, CommandDef>

// ---- Config ----

export interface GssConfig {
  nodes: Record<number, string>
  ptypes: Record<number, string>
  node_descriptions?: Record<string, string>
  ax25: {
    src_call: string
    src_ssid: number
    dest_call: string
    dest_ssid: number
  }
  csp: {
    priority: number
    source: number
    destination: number
    dest_port: number
    src_port: number
    flags: number
    csp_crc: boolean
  }
  tx: {
    zmq_addr: string
    frequency: string
    delay_ms: number
    uplink_mode: string
  }
  rx: {
    zmq_addr: string
    zmq_port: number
  }
  general: {
    mission_name?: string
    version: string
    log_dir: string
    gs_node: number
  }
}

// ---- Logs ----

export interface LogSession {
  id: string
  filename: string
  packets: number
  path: string
}

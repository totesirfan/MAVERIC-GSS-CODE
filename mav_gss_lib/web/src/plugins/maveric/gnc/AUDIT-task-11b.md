# Task 11b — GNC UI dropped-metadata audit

**Purpose.** v2 drops `decode_error`, `raw_tokens`, `decode_ok`,
`pkt_num`, `source_cmd_id`, and `gs_ts` from canonical telemetry
state. `received_at_ms` is replaced by the platform entry's `t: number`
field. This file enumerates every consumer under
`mav_gss_lib/web/src/plugins/maveric/gnc/**` and records the decision
Task 15 will apply per hit.

**Outcome verdict codes:**
- `drop` — field was only surfaced for debug, remove it from the UI.
- `rename-to-t` — staleness derived from `received_at_ms` → read `.t` instead.
- `catalog` — metadata that belongs on the shared catalog (`useTelemetryCatalog<CatalogEntry[]>('gnc')`), already keyed by register name.
- `log-link` — per-packet provenance; pivot to a "view source packet" link
  opening the log viewer filtered by `pkt_num` — but that's out of scope
  here, so drop the field for now and add the hook later.
- `obsolete` — file itself is being deleted in Task 16; no migration needed.

Task 15 acceptance checks this file exists, walks it top-to-bottom,
applies every decision, then `git rm`s it in its own commit.

---

## types.ts

| Line | Code | Verdict | Why |
|---|---|---|---|
| 96  | `raw_tokens: string[]` (CatalogEntry) | drop | Catalog metadata doesn't need raw_tokens — that's live-data transport detail. |
| 124 | `raw_tokens: string[]` (RegisterSnapshot) | drop | Transport detail; not canonical state. |
| 125 | `decode_ok: boolean` | drop | Extractor filters decode_ok=False; live values are always ok. |
| 126 | `decode_error: string \| null` | drop | Paired with decode_ok; errors live in the log, not state. |
| 129–130 | `received_at_ms: number` | rename-to-t | Replace with platform entry `t: number`. |
| 132 | `gs_ts: string` | log-link (drop) | Not in platform state; re-surface via log-viewer link later. |
| 134 | `pkt_num: number` | log-link (drop) | Same as gs_ts. |

Whole `RegisterSnapshot` type is redesigned in Task 15 to a lean
`{ value: unknown; t: number }` — the platform's `TelemetryEntry`.
Static metadata (`name`, `module`, `register`, `type`, `unit`, `notes`)
moves to a sibling `CatalogEntry` consumed through
`useTelemetryCatalog('gnc')`.

## registers/exportTable.ts

| Line | Code | Verdict | Why |
|---|---|---|---|
| 37  | docstring mentions Raw Tokens / gs_ts / Decode OK columns | drop | Update docstring to match the new column list. |
| 51  | `snap?.received_at_ms != null ? nowMs - snap.received_at_ms` | rename-to-t | Read `.t` instead. |
| 59  | `snap?.raw_tokens ? snap.raw_tokens.join(' ') : ''` | drop column | Dropped from state. |
| 61  | `snap?.gs_ts ?? ''` | drop column | Log-link (not wired in this PR). |
| 62  | `snap?.decode_ok == null ? '' : snap.decode_ok ? 'yes' : 'no'` | drop column | Always yes post-filter. |
| 85  | `age_ms: snap?.received_at_ms != null ? nowMs - snap.received_at_ms : null` | rename-to-t | Same as line 51. |

Net effect: the CSV export loses Raw Tokens, Last Seen (gs_ts), and
Decode OK columns; Age column keeps its semantics but is computed from
`.t`. Column-count consumers downstream of this file (if any) get
verified by the tests Task 15 touches.

## registers/formatValue.ts

| Line | Code | Verdict | Why |
|---|---|---|---|
| 7 | `if (!snap \|\| !snap.decode_ok) return '—'` | drop decode_ok guard | Live entries are always decoded-ok by extractor filter; retain only the nullish guard (`!snap`). |

## registers/RegistersTable.tsx

| Line | Code | Verdict | Why |
|---|---|---|---|
| 93 | `const age = ageMs(snap?.received_at_ms ?? null, nowMs)` | rename-to-t | Use `.t`. |
| 94 | `const hasData = snap?.received_at_ms != null` | rename-to-t | Use `.t`. |

All `e.name` / `e.module` / `e.register` / `e.type` / `e.notes` /
`e.unit` reads (lines 25–29, 104–119) stay as-is — they read from the
catalog entry, which keeps those fields.

## dashboard/AdcsMtqCard.tsx

| Line | Code | Verdict | Why |
|---|---|---|---|
| 112 | `receivedAt={q?.received_at_ms}` | rename-to-t | Read `.t`. |
| 135 | `receivedAt={rate?.received_at_ms}` | rename-to-t |  |
| 148 | `receivedAt={time?.received_at_ms}` | rename-to-t |  |
| 154 | `receivedAt={date?.received_at_ms}` | rename-to-t |  |
| 206 | `receivedAt={tmp?.received_at_ms}` | rename-to-t |  |

## dashboard/FlagsStrip.tsx

| Line | Code | Verdict | Why |
|---|---|---|---|
| 19 | `const statAt = stat?.received_at_ms ?? null` | rename-to-t | Use `.t`. |
| 20 | `const actAt  = actErr?.received_at_ms ?? null` | rename-to-t |  |
| 21 | `const senAt  = senErr?.received_at_ms ?? null` | rename-to-t |  |

## dashboard/GncPlannerCard.tsx

| Line | Code | Verdict | Why |
|---|---|---|---|
| 45 | `receivedAt={counters?.received_at_ms}` | rename-to-t | Use `.t`. |
| 51 | `receivedAt={counters?.received_at_ms}` | rename-to-t |  |
| 57 | `receivedAt={counters?.received_at_ms}` | rename-to-t |  |

## dashboard/NaviGuiderCard.tsx

| Line | Code | Verdict | Why |
|---|---|---|---|
| 121 | `receivedAt={mag?.received_at_ms}` | rename-to-t | Use `.t`. |
| 138 | `receivedAt={temp?.received_at_ms}` | rename-to-t |  |

## useGncRegisters.ts / registers/useRegisterCatalog.ts

| File | Verdict | Why |
|---|---|---|
| useGncRegisters.ts | obsolete | Replaced by `useTelemetry('gnc')` — Task 15 rewires call sites; Task 16 `git rm`s this file. |
| registers/useRegisterCatalog.ts | obsolete | Replaced by `useTelemetryCatalog<CatalogEntry[]>('gnc')` — Task 15 rewires call sites; Task 16 `git rm`s this file. |

---

## Summary

Total hits: **21** across 8 files. Verdicts:
- `rename-to-t`: 14 (all `received_at_ms` → `.t`)
- `drop`: 5 (raw_tokens, decode_ok, decode_error, gs_ts, pkt_num + docstring reference)
- `obsolete`: 2 file deletions in Task 16

No hit requires extending the GNC extractor's emitted shape — every
dropped field was debug provenance or a rename.

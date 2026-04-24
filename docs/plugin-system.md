# Plugin System

The plugin system lets missions provide standalone tool pages beyond the core
RX/TX dashboard. Plugins are mission-scoped, convention-discovered, and
lazy-loaded. Backend hooks are wired through the platform v2 `MissionSpec`
contract — missions expose capabilities, the platform invokes them.

## What Plugins Are

A plugin is a full-page tool that lives alongside the main dashboard. The
operator navigates to it via the header nav and back again. Each plugin page
mounts lazily; its state lives in a root-mounted mission provider so incoming
WebSocket data accumulates whether or not the page is visible.

Plugins are distinct from the core mission boundary:

- **`PacketOps` / `CommandOps` / `UiOps`** — required `MissionSpec`
  capabilities, called per-packet / per-command, run on every mission.
- **TX Builder** — optional inline React component, mounts inside the TX
  panel. Discovered at `plugins/<mission_id>/TxBuilder.tsx`.
- **Mission providers** — optional root-level React providers discovered from
  `plugins/<mission_id>/providers.ts`. Used for shared plugin state that must
  stay warm (telemetry, imaging progress, etc.).
- **Plugin pages** — optional standalone pages, navigated to separately.
  Discovered from `plugins/<mission_id>/plugins.ts`.

## Architecture

```
App.tsx (route owner)
  ├─ ?panel=tx|rx  → PopOutTx / PopOutRx (no header, takes precedence over ?page=)
  └─ AppShell (default)
       ├─ GlobalHeader
       ├─ TabViewport
       │    ├─ activeTabId = '__dashboard__' → <MainDashboard />
       │    └─ activeTabId = '<plugin-id>'   → plugin page component
       └─ modals, toaster
```

### URL Parameter Precedence

Two URL parameters control the top-level view mode:

1. **`?panel=tx|rx`** — pop-out panel mode. Takes absolute precedence. If
   `?panel=` is present, all other routing is ignored. Pop-out windows
   render a single panel with no header or navigation.
2. **`?page=<id>`** — plugin page mode. Only evaluated when `?panel=` is
   absent. Renders the named plugin page with the GlobalHeader and back
   navigation.
3. **Neither** — normal split-pane dashboard.

Plugin pages cannot be popped out. If both `?panel=` and `?page=` are present,
`?panel=` wins and `?page=` is ignored.

### Component Ownership

`App.tsx` owns route state and renders the active page component. The
`MainDashboard` component owns the core `useRxSocket()` / `useTxSocket()`
hooks — they connect only when the main dashboard is mounted and disconnect
when the operator navigates to a plugin page.

Mission providers (`providers.ts`) mount at the app root inside `RxProvider`,
so provider-held state (telemetry snapshots, imaging progress) accumulates
across page navigation and is present before any plugin page mounts.

Route state is driven by `useState` initialized from `?page=`, updated via
`history.pushState`, and synced with `popstate` events.

## Frontend Structure

```
mav_gss_lib/web/src/plugins/
  registry.ts                    ← lazy discovery of builders + page plugins
  missionRuntime.tsx             ← eager discovery of mission providers
  maveric/
    TxBuilder.tsx                ← inline TX builder
    plugins.ts                   ← page plugin manifest
    providers.ts                 ← root-mounted mission providers
    ImagingPage.tsx              ← imaging plugin page
    imaging/                     ← imaging panel subcomponents
    eps/                         ← EPS telemetry plugin
    gnc/                         ← GNC telemetry plugin
```

### Plugin Registry (`registry.ts`)

The registry serves two roles, both lazy:

1. **TX Builder discovery** — `getMissionBuilder(missionId)` uses
   `import.meta.glob('./**/TxBuilder.tsx')`.
2. **Page plugin discovery** — `getPluginPages(missionId)` loads page
   manifests from `import.meta.glob('./**/plugins.ts')`.

### Mission Provider Discovery (`missionRuntime.tsx`)

Mission packages may also export `providers.ts` in their frontend plugin
directory. `missionRuntime.tsx` discovers them **eagerly** (bundle-time) and
composes them into a `<MissionProviders>` wrapper that `App.tsx` mounts inside
`RxProvider`.

Eager discovery is required: providers must exist before `RxProvider`'s
WebSocket starts delivering messages, including the mission
`EventOps.on_client_connect` replay. A lazy provider would miss that replay.

### Plugin Discovery and Config Loading

`import.meta.glob` runs at build time — all plugin manifests from all missions
are bundled. `getPluginPages(missionId)` filters at runtime.

- **Before config loads:** the plugins list is empty, so `TabViewport` cannot
  resolve `?page=<id>` to a component and shows "Plugin not found". Typically
  <200ms since config is fetched on mount.
- **After config loads:** `getPluginPages(missionId)` resolves the page ID
  and the plugin page mounts through `Suspense` with a `Skeleton` fallback.
- **Mismatched mission/page:** if `?page=imaging` is in the URL but the
  active mission has no imaging plugin, the page renders "plugin not found"
  after config loads.

### Plugin Manifest (`plugins.ts`)

Each mission directory may contain a `plugins.ts` that exports an array of
`PluginPageDef`:

```typescript
import { lazy } from 'react'
import { Camera } from 'lucide-react'
import type { PluginPageDef } from '@/plugins/registry'

const plugins: PluginPageDef[] = [
  {
    id: 'imaging',
    name: 'Imaging',
    description: 'Image downlink viewer',
    icon: Camera,
    category: 'mission',
    order: 10,
    component: lazy(() => import('./ImagingPage')),
  },
]

export default plugins
```

### PluginPageDef Interface

```typescript
interface PluginPageDef {
  id: string                                      // URL slug: ?page=<id>
  name: string                                    // Display name in nav
  description: string                             // Card description
  icon: LucideIcon                                // lucide-react icon
  component: LazyExoticComponent<ComponentType>   // React.lazy() result
  category: 'mission' | 'platform'                // nav grouping
  keepAlive?: boolean                             // keep mounted when inactive
  order?: number                                  // nav sort order
}
```

### Adding a Plugin (Frontend Only)

1. Create a component file in `plugins/<mission>/` (e.g. `MyToolPage.tsx`).
2. Add an entry to `plugins/<mission>/plugins.ts`.
3. If the page needs state continuity across navigation, add a provider to
   `plugins/<mission>/providers.ts`.
4. Run `npm run build` and commit `dist/`.

## Backend Support

Frontend-only plugins need no backend changes. Plugins that need backend
state use three mission-owned `MissionSpec` capabilities, all wired by
`mission.py::build(ctx)`:

- **`HttpOps`** — FastAPI routers for REST endpoints.
- **`EventOps`** — per-packet side effects and replay-on-connect messages.
- **`TelemetryOps`** — declarative telemetry domains + extractors driving the
  platform `TelemetryRouter`.

No mission code is imported from `mav_gss_lib/web_runtime/`; the platform
reads the capabilities off the live `MissionSpec`.

### HTTP Router Mounting (`HttpOps`)

Missions declare plugin REST endpoints as FastAPI routers and hang them off
`MissionSpec.http`:

```python
# mav_gss_lib/missions/maveric/mission.py
from mav_gss_lib.missions.maveric.imaging import ImageAssembler, get_imaging_router
from mav_gss_lib.platform.mission_api import HttpOps

def build(ctx: MissionContext) -> MissionSpec:
    image_assembler = ImageAssembler(image_dir(ctx.mission_config))
    routers = [
        get_imaging_router(
            image_assembler,
            config_accessor=lambda: ctx.mission_config,
        ),
    ]
    return MissionSpec(
        ...,
        http=HttpOps(routers=routers),
    )
```

`ctx.mission_config` is a **live reference** to `runtime.mission_cfg` — the
lambda lets routers read live config values (e.g. `imaging.thumb_prefix`)
without a MissionSpec rebuild when `/api/config` edits land.

**Platform side** — `create_app()` iterates the spec's routers once at
startup:

```python
# mav_gss_lib/web_runtime/app.py
if runtime.mission.http is not None:
    for router in runtime.mission.http.routers:
        app.include_router(router)
```

Each router should set its own prefix (e.g. `/api/plugins/imaging`).

### Packet Events (`EventOps`)

Plugins that need to observe RX packets (imaging progress, chunk assemblers,
etc.) implement the `PacketEventSource` protocol:

```python
from typing import Iterable, Any
from mav_gss_lib.platform import PacketEnvelope

class MyPluginEvents:
    def on_packet(self, packet: PacketEnvelope) -> Iterable[dict[str, Any]]:
        """Inspect an RX packet. Return WS messages to broadcast (or empty)."""

    def on_client_connect(self) -> Iterable[dict[str, Any]]:
        """Return replay messages when a new /ws/rx client connects."""
```

Register the source on `MissionSpec.events`:

```python
from mav_gss_lib.platform import EventOps

return MissionSpec(
    ...,
    events=EventOps(sources=[MyPluginEvents(...)]),
)
```

**Platform side** — `RxService.broadcast_loop` calls
`collect_packet_events(runtime.mission, pkt)` after packet parse/log/render
and fans the returned dicts out on `/ws/rx`. `rx.ws_rx()` calls
`collect_connect_events(runtime.mission)` after the packet backlog replay.
Each event source is wrapped in try/except inside the platform helpers, so a
broken source degrades gracefully without taking down RX.

### Telemetry (`TelemetryOps`)

Subsystem dashboards (EPS, GNC, spacecraft time) use the declarative
telemetry pipeline rather than per-plugin REST + WS plumbing. The mission
declares domains and extractors; the platform owns merge, persistence, and
delivery.

```python
# mav_gss_lib/missions/maveric/telemetry/ops.py (sketch)
from mav_gss_lib.platform import TelemetryOps
from mav_gss_lib.platform.telemetry import TelemetryDomainSpec

def build_telemetry_ops(nodes) -> TelemetryOps:
    return TelemetryOps(
        domains={
            "eps": TelemetryDomainSpec(catalog=eps_catalog),
            "gnc": TelemetryDomainSpec(catalog=gnc_catalog),
            "spacecraft": TelemetryDomainSpec(catalog=spacecraft_catalog),
        },
        extractors=[MavericTelemetryExtractor(nodes=nodes)],
    )
```

Each extractor implements `extract(packet) -> Iterable[TelemetryFragment]`.
The platform `TelemetryRouter` merges fragments into per-domain state,
persists snapshots under `<log_dir>/.telemetry/<domain>.json`, and broadcasts
unified `{type: "telemetry", domain, changes, replay?}` messages on `/ws/rx`.
Catalog callables back `GET /api/telemetry/{domain}/catalog`.

See `docs/telemetry-known-smells.md` for the invariants kept by this
pipeline.

## REST Endpoints

Plugin endpoints live under `/api/plugins/<plugin_id>/`:

```python
# mav_gss_lib/missions/maveric/imaging/router.py
from fastapi import APIRouter

def get_imaging_router(assembler: "ImageAssembler", config_accessor=None):
    router = APIRouter(prefix="/api/plugins/imaging")

    @router.get("/status")
    async def status(request: Request):
        # Uses assembler directly; config_accessor() for live config lookups
        ...

    return router
```

The imaging router exposes `paired_status()` which groups image pairs
(full + thumb) by filename prefix — the prefix is read live from
`imaging.thumb_prefix` via `config_accessor()` so operators can retune it at
runtime without restarting. `ImageAssembler.feed_chunk(filename, chunk_num,
data, chunk_size=None)` returns `(received, total, complete)`; the optional
`chunk_size` records the declared per-chunk byte length so the pair view can
display it.

## WebSocket Integration

Plugins reuse the existing `/ws/rx` and `/ws/tx` WebSocket endpoints. A
plugin page connects to the same sockets and filters for relevant message
types. Backend-side:

- **Custom per-packet messages** — emitted by `EventOps` sources
  (e.g. `imaging_progress`).
- **Telemetry messages** — emitted by the platform `TelemetryRouter`
  (unified `{type: "telemetry", domain, changes}` envelope).
- **Replay on connect** — `EventOps.on_client_connect()` and the telemetry
  router's per-domain replay both run after the packet backlog is replayed.

**Tradeoff:** every `/ws/rx` connection currently receives column metadata,
the in-memory packet backlog (capped at 500 packets), telemetry replay, and
any plugin connect-events; every `/ws/tx` connection receives the
queue/history snapshot. A plugin page that only needs one domain still pays
this startup cost. This is acceptable for v1 because the backlog and
snapshots are bounded. If narrower consumers appear later, subscription
scoping can be added to the existing endpoints without a protocol change.

## Navigation

The GlobalHeader renders a `TabStrip` (`components/layout/TabStrip.tsx`)
built from `buildNavigationTabs(plugins)` in
`components/layout/navigation.ts`. The dashboard is always the first tab
(id `__dashboard__`); each discovered plugin becomes an additional tab,
sorted by category (mission first, then platform) and `order`.

Clicking a tab calls `navigateTo(id)` in `App.tsx`, which updates the URL via
`history.pushState` and swaps the rendered page in `TabViewport`. Browser
back/forward is handled via `popstate`. The Command Palette (Ctrl+K) exposes
the same navigation targets.

## Imaging Plugin

The MAVERIC image downlink viewer is the reference plugin that exercises
every backend extension point:

- **`HttpOps` router** — `mav_gss_lib/missions/maveric/imaging/router.py`
  exposes `/api/plugins/imaging/*` endpoints.
- **`EventOps` source** — `MavericImagingEvents` in
  `mav_gss_lib/missions/maveric/imaging/events.py` watches
  `img_cnt_chunks` / `img_get_chunks` / `cam_capture` packets, drives the
  `ImageAssembler`, and emits `imaging_progress` messages. Replays current
  per-file progress on `/ws/rx` connect.
- **Image assembly** — `ImageAssembler` in
  `mav_gss_lib/missions/maveric/imaging/assembler.py` reassembles chunks to
  disk with per-chunk persistence and restart recovery.

### Backend Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/plugins/imaging/status` | GET | Active files with progress, grouped into full/thumb pairs |
| `/api/plugins/imaging/files` | GET | List image files on disk |
| `/api/plugins/imaging/chunks/{filename}` | GET | Received chunk indices for one file |
| `/api/plugins/imaging/preview/{filename}` | GET | Serve partial/complete image (no-cache, ETag) |
| `/api/plugins/imaging/file/{filename}` | DELETE | Remove image, meta sidecar, chunk dir, and in-memory state |

### WebSocket Messages

```json
{
  "type": "imaging_progress",
  "filename": "photo_01.jpg",
  "received": 42,
  "total": 100,
  "complete": false
}
```

### Image Assembly

`ImageAssembler` handles chunk reassembly:

- `set_total(filename, count)` — register expected chunk count (from
  `img_cnt_chunks`).
- `feed_chunk(filename, chunk_num, data, chunk_size=None)` — store chunk +
  auto-save partial image.
- Writes contiguous chunks from index 0, skipping gaps.
- Appends JPEG EOI marker so viewers can open partial files.
- Auto-saves to `images/` on every chunk.
- `delete_file(filename)` — remove image, meta sidecar, chunk directory, and
  in-memory state (backs the DELETE endpoint).

## Telemetry Plugins

MAVERIC ships EPS and GNC telemetry plugin pages backed by the platform
telemetry router, not mission-specific REST routers:

- **Backend state** — `mav_gss_lib/web_runtime/telemetry/router.py` registers
  mission-declared domains from `MissionSpec.telemetry`. Current MAVERIC
  domains are `eps`, `gnc`, and `spacecraft`; snapshots persist under
  `<log_dir>/.telemetry/<domain>.json`.
- **Backend API** — `GET /api/telemetry/{domain}/catalog` serves mission-owned
  catalog metadata, `DELETE /api/telemetry/{domain}/snapshot` clears a
  domain and broadcasts `{type: "telemetry", domain, cleared: true}` on
  `/ws/rx`.
- **WebSocket data** — telemetry extractors emit `TelemetryFragment` objects;
  the router broadcasts `{type: "telemetry", domain, changes, replay?}`.
- **Frontend pages** — MAVERIC registers `gnc` and `eps` in
  `plugins/maveric/plugins.ts`. `providers.ts` mounts `GncProvider` and
  `EpsProvider` at the app root so each page reads stable provider state
  instead of owning its own WebSocket.

The imaging plugin remains a mission-specific REST plugin because it owns
file assembly and preview endpoints. EPS and GNC use the shared telemetry
API because their backend needs are latest-value state, catalogs, clear, and
replay.

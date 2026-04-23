# Plugin System

The plugin system lets missions provide standalone tool pages beyond the core RX/TX dashboard. Plugins are mission-scoped, convention-discovered, and lazy-loaded.

## What Plugins Are

A plugin is a full-page tool that lives alongside the main dashboard. The operator navigates to it via the header nav and back again. Each plugin gets its own WebSocket connections and manages its own state.

Plugins are distinct from the core adapter contract:

- **Adapter methods** (parse, render, build_tx) — required, called per-packet, run on every mission
- **TX Builder** — optional inline component, mounts inside the TX panel
- **Mission providers** — optional root-level React providers discovered from `providers.ts`, used for shared plugin state such as telemetry domains
- **Plugins** — optional standalone pages, navigated to separately

## Architecture

```
App.tsx (route owner)
  ├─ ?panel=tx|rx  → PopOutTx / PopOutRx (no header, takes precedence over ?page=)
  └─ AppShell (default)
       ├─ GlobalHeader
       ├─ TabViewport
       │    ├─ activeTabId = '__dashboard__' → <MainDashboard /> (owns useRxSocket + useTxSocket)
       │    └─ activeTabId = '<plugin-id>'   → plugin page component (owns its own sockets)
       └─ modals, toaster
```

### URL Parameter Precedence

Two URL parameters control the top-level view mode:

1. **`?panel=tx|rx`** — pop-out panel mode (pre-existing). Takes absolute precedence. If `?panel=` is present, all other routing is ignored. Pop-out windows render a single panel with no header or navigation.
2. **`?page=<id>`** — plugin page mode. Only evaluated when `?panel=` is absent. Renders the named plugin page with the GlobalHeader and back navigation.
3. **Neither** — normal split-pane dashboard.

Plugin pages cannot be popped out. The `?panel=` parameter is reserved for the core TX/RX panels. If both `?panel=` and `?page=` are present in the URL, `?panel=` wins and `?page=` is ignored.

### Component Ownership

`App.tsx` owns route state and renders the active page component. Each page component is a separate React subtree that mounts/unmounts its own WebSocket hooks:

```
App.tsx
  ├─ ?panel=tx  → <PopOutTx />            ← standalone window, no header
  ├─ ?panel=rx  → <PopOutRx />            ← standalone window, no header
  └─ AppShell (default)
       ├─ GlobalHeader
       ├─ TabViewport (renders by activeTabId)
       │    ├─ '__dashboard__' → <MainDashboard />  ← mounts useRxSocket, useTxSocket
       │    └─ '<plugin-id>'   → plugin page        ← mounts its own sockets
       └─ modals, toaster, etc.
```

The main dashboard's `useRxSocket()` / `useTxSocket()` live inside the `MainDashboard` component — not at the App level — so they connect only when the main dashboard is mounted and disconnect when the operator navigates to a plugin page.

Route state is driven by `useState` initialized from `?page=`, updated via `history.pushState`, and synced with `popstate` events for browser back/forward.

## Frontend Structure

```
mav_gss_lib/web/src/plugins/
  registry.ts                    ← platform: discovers builders + page plugins
  missionRuntime.tsx             ← platform: discovers mission providers
  maveric/
    TxBuilder.tsx                ← inline TX builder (unchanged behavior)
    plugins.ts                   ← page plugin manifest for MAVERIC
    providers.ts                 ← root-level mission providers
    ImagingPage.tsx              ← imaging plugin page component
    eps/EpsPage.tsx              ← EPS telemetry plugin page
    gnc/GNCPage.tsx              ← GNC telemetry plugin page
```

### Plugin Registry (`registry.ts`)

The registry serves two roles:

1. **TX Builder discovery** — same `getMissionBuilder(missionId)` API as before, using `import.meta.glob('./**/TxBuilder.tsx')` for convention-based discovery
2. **Page plugin discovery** — `getPluginPages(missionId)` loads page manifests from `import.meta.glob('./**/plugins.ts')`

### Mission Provider Discovery (`missionRuntime.tsx`)

Mission packages may also export `providers.ts` in their frontend plugin
directory. The platform composes these providers once at the app root inside
`TelemetryProvider`, so plugin state can stay warm even when a plugin page is
not visible. MAVERIC uses this for `EpsProvider` and `GncProvider`.

### Plugin Discovery and Config Loading

The `import.meta.glob` calls run at build time — all plugin manifests from all missions are bundled. `getPluginPages(missionId)` filters by mission ID at runtime.

Plugin IDs are mission-scoped, not globally unique. Two missions may both define `id: "imaging"`. This means `?page=imaging` cannot be resolved until the active mission is known from `/api/config`.

Loading strategy:

- **Before config loads:** The plugins list is empty, so `TabViewport` cannot resolve `?page=<id>` to a component and falls back to its "Plugin not found" view. This is typically <200ms since config is fetched on mount.
- **After config loads:** `getPluginPages(missionId)` resolves the page ID to the correct mission's component. The plugin page mounts (through `Suspense` with a `Skeleton` fallback while the lazy chunk loads) and connects its own sockets.
- **Nav tabs wait for config.** The plugin tabs are appended to the tab strip only after config loads and `missionId` is known (see the `getPluginPages` effect in `AppShell`). Before config loads, only the dashboard tab is present.
- **Mismatched mission/page.** If `?page=imaging` is in the URL but the active mission has no imaging plugin, the page renders a "plugin not found" fallback after config loads.

### Plugin Manifest (`plugins.ts`)

Each mission directory may contain a `plugins.ts` that exports an array of page plugin definitions:

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
import type { LazyExoticComponent, ComponentType } from 'react'
import type { LucideIcon } from 'lucide-react'

interface PluginPageDef {
  id: string                                      // URL slug: ?page=<id>
  name: string                                    // Display name in nav
  description: string                             // Card description
  icon: LucideIcon                                // lucide-react icon component
  component: LazyExoticComponent<ComponentType>   // React.lazy() result
  category: 'mission' | 'platform'                // nav grouping
  keepAlive?: boolean                             // keep mounted when inactive
  order?: number                                  // nav sort order
}
```

### Adding a Plugin (Frontend Only)

1. Create a component file in `plugins/<mission>/` (e.g., `MyToolPage.tsx`)
2. Add an entry to `plugins/<mission>/plugins.ts`
3. The registry discovers it automatically — no platform code changes
4. Run `npm run build` and commit `dist/`

## Backend Support

Frontend-only plugins need no backend changes. Plugins that need backend state (like imaging) use two extension points, both mission-owned:

### Plugin Router Discovery

Mission packages can declare backend routers for their plugins. The platform discovers and mounts them automatically at startup — no manual `app.include_router()` edits needed.

**Mission side** — the mission `__init__.py` exposes an optional `get_plugin_routers(adapter, config_accessor)` function:

```python
# mav_gss_lib/missions/maveric/__init__.py
def get_plugin_routers(adapter=None, config_accessor=None):
    """Return FastAPI routers for mission plugins. Called once at app startup.

    Args:
        adapter: the live mission adapter instance — plugins typically need
                 state owned by the adapter (e.g., ImageAssembler).
        config_accessor: zero-arg callable returning the live merged config
                 dict. Plugin routers that read runtime config (e.g., the
                 imaging router reads ``imaging.thumb_prefix`` for pair
                 grouping) should use this rather than snapshotting config.
    """
    assembler = getattr(adapter, "image_assembler", None) if adapter else None
    if assembler is None:
        return []
    from .imaging import get_imaging_router
    return [get_imaging_router(assembler, config_accessor=config_accessor)]
```

Each router should set its own prefix (e.g., `/api/plugins/imaging`).

**Platform side** — `app.py` calls `get_plugin_routers()` on the active mission package and mounts whatever comes back, passing the live adapter and a config accessor:

```python
# mav_gss_lib/web_runtime/app.py (in create_app)
mission_pkg = importlib.import_module(f"mav_gss_lib.missions.{mission_id}")
get_routers = getattr(mission_pkg, "get_plugin_routers", None)
if get_routers:
    for router in get_routers(runtime.adapter, config_accessor=lambda: runtime.cfg):
        app.include_router(router)
```

This keeps `app.py` stable as plugins are added or removed. The mission package owns the list, and the adapter owns plugin state (assemblers, aggregators, etc.).

### Packet Hooks

Plugins that need to observe RX packets (imaging, telemetry aggregators, etc.) hook in through the mission adapter, not by editing `RxService`.

The adapter can expose optional hooks:

- `attach_fragments(pkt)` runs after parsing and before log/render serialization. Use it when downstream sinks must see derived per-packet data.
- `on_packet_received(pkt)` runs after the normal packet broadcast. Use it to emit extra WebSocket messages.
- `on_client_connect()` runs when a new `/ws/rx` client connects, after packet backlog replay. Use it to replay current plugin state.

```python
def attach_fragments(self, pkt) -> list:
    """Attach mission-derived telemetry fragments before logs/rendering."""

def on_packet_received(self, pkt) -> list[dict] | None:
    """Called for every parsed RX packet. Return optional extra WS messages.

    The platform calls this in the broadcast loop after parsing, logging,
    and rendering. The adapter dispatches internally to whatever plugin
    state it owns (ImageAssembler, aggregators, etc.).

    Returns None or a list of dicts to broadcast as additional WS messages.
    Each dict must have a 'type' key (e.g., 'imaging_progress').
    """

def on_client_connect(self) -> list[dict]:
    """Return synthetic replay messages for a fresh RX WebSocket client."""
```

**Platform side** — generic hook calls in `broadcast_loop()` and `/ws/rx`, never tied to a specific plugin:

```python
# In RxService.broadcast_loop(), before log/render serialization:
attach = getattr(self.runtime.adapter, "attach_fragments", None)
if attach:
    attach(pkt)

# In RxService.broadcast_loop(), after normal packet broadcast:
if hasattr(self.runtime.adapter, 'on_packet_received'):
    extra_msgs = self.runtime.adapter.on_packet_received(pkt)
    if extra_msgs:
        for msg in extra_msgs:
            await self._broadcast_json(msg)

# In ws_rx(), after packet backlog replay:
connect_hook = getattr(runtime.adapter, "on_client_connect", None)
if connect_hook:
    for msg in connect_hook() or []:
        await websocket.send_text(json.dumps(msg))
```

**Mission side** — the MAVERIC adapter owns `ImageAssembler` and dispatches.
Telemetry state is platform-owned by `TelemetryRouter`; the adapter receives
`telemetry_manifest` and `telemetry_extractors` from `init_mission(cfg)`, then
`WebRuntime` registers the domains and attaches the router to the adapter.

```python
# In MavericMissionAdapter (illustrative — see adapter.py for the full version)
@dataclass
class MavericMissionAdapter:
    cmd_defs: dict
    nodes: NodeTable
    image_assembler: object = None   # built by init_mission()
    telemetry: object = None         # attached by WebRuntime
    extractors: tuple = ()           # attached by WebRuntime

    def on_packet_received(self, pkt):
        md = getattr(pkt, 'mission_data', {}) or {}
        cmd = md.get('cmd')
        if not cmd or not self.image_assembler:
            return None
        cmd_id = cmd.get('cmd_id', '')
        if cmd_id == 'img_cnt_chunks':
            # extract filename, count from typed_args
            ...
            self.image_assembler.set_total(filename, count)
        elif cmd_id == 'img_get_chunk':
            # extract filename, chunk_num, data, chunk_size from typed_args
            ...
            self.image_assembler.feed_chunk(filename, chunk_num, data, chunk_size=chunk_size)
        else:
            return None
        received, total = self.image_assembler.progress(filename)
        return [{"type": "imaging_progress", "filename": filename,
                 "received": received, "total": total,
                 "complete": self.image_assembler.is_complete(filename)}]
```

`init_mission(cfg)` resolves `general.image_dir`, constructs the
`ImageAssembler`, and returns `TELEMETRY_MANIFEST` plus extractor callables.
The shared loader injects mission constructor resources such as `cmd_defs`,
`nodes`, and `image_assembler`; `WebRuntime` then registers telemetry domains
and attaches `telemetry` / `extractors` to the adapter. Plugins therefore do
not instantiate backend state themselves.

This keeps `RxService` clean — it calls one hook, never knows about imaging. Future plugins (telemetry dashboards, file transfer trackers) hook in the same way via `on_packet_received` without any platform code changes.

### REST Endpoints

Plugin endpoints live under `/api/plugins/<plugin_id>/`:

```python
# mav_gss_lib/missions/maveric/imaging.py
from fastapi import APIRouter

def get_imaging_router(assembler: "ImageAssembler", config_accessor=None):
    router = APIRouter(prefix="/api/plugins/imaging")

    @router.get("/status")
    async def status(request: Request):
        # Uses assembler directly; config_accessor() for live config lookups
        ...

    return router
```

The imaging router exposes `paired_status()` which groups image pairs (full + thumb) by filename prefix — the prefix is read live from `imaging.thumb_prefix` in config via `config_accessor()` so operators can retune it at runtime without restarting. `ImageAssembler.feed_chunk(filename, chunk_num, data, chunk_size=None)` returns `(received, total, complete)`; the optional `chunk_size` kwarg lets the adapter record the declared per-chunk byte length (used by the OBC to strip its C-string terminator) so the pair view can display it.

### WebSocket Integration

Plugins reuse the existing `/ws/rx` and `/ws/tx` WebSocket endpoints. A plugin
page connects to the same sockets and filters for relevant messages. The
adapter's `attach_fragments(pkt)` hook runs before logging/rendering so
telemetry fragments are present for every sink, and `on_packet_received(pkt)`
injects plugin-specific message types (for example `telemetry` and
`imaging_progress`) into the existing RX broadcast — no separate WebSocket
endpoint needed. On a fresh `/ws/rx` connection, `on_client_connect()` replays
the current telemetry snapshots as synthetic `telemetry` messages.

**Tradeoff:** Every `/ws/rx` connection currently receives column metadata, the
in-memory packet backlog (capped at 500 packets), and telemetry replay frames;
every `/ws/tx` connection receives the queue/history snapshot. A plugin page
that only needs one domain still pays this startup cost. This is acceptable for
v1 because the backlog and snapshots are bounded. If narrower consumers are
added later, subscription scoping can be added to the existing WebSocket
endpoints without a protocol change.

## Navigation

The GlobalHeader renders a `TabStrip` (`components/layout/TabStrip.tsx`) built from `buildNavigationTabs(plugins)` in `components/layout/navigation.ts`. The dashboard is always the first tab (id `__dashboard__`); each discovered plugin becomes an additional tab, sorted by category (mission first, then platform) and `order`.

Clicking a tab calls `navigateTo(id)` in `App.tsx`, which updates the URL via `history.pushState` and swaps the rendered page in `TabViewport`. Browser back/forward is handled via `popstate`. The Command Palette (Ctrl+K) also exposes the same navigation targets.

## Imaging Plugin

The first plugin is the MAVERIC image downlink viewer. See the imaging page implementation for a complete example of:

- Filtered RX log (only image-related packets)
- Purpose-built TX controls (not the generic CLI)
- Real-time image preview with chunk progress
- Backend integration via `ImageAssembler` + adapter packet hook + REST endpoints

### Backend Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/plugins/imaging/status` | GET | Active files with progress (received/total/complete), grouped into full/thumb pairs |
| `/api/plugins/imaging/files` | GET | List image files on disk |
| `/api/plugins/imaging/chunks/{filename}` | GET | Received chunk indices for one file |
| `/api/plugins/imaging/preview/{filename}` | GET | Serve partial/complete image (no-cache, ETag) |
| `/api/plugins/imaging/file/{filename}` | DELETE | Remove image, meta sidecar, chunk dir, and in-memory state |

### WebSocket Messages

The RX broadcast includes `imaging_progress` messages (injected by the adapter's `on_packet_received` hook) when image chunks arrive:

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

`ImageAssembler` in `mav_gss_lib/missions/maveric/imaging.py` handles chunk reassembly:

- `set_total(filename, count)` — register expected chunk count (from `img_cnt_chunks`)
- `feed_chunk(filename, chunk_num, data, chunk_size=None)` — store chunk + auto-save partial image; optional `chunk_size` records the declared per-chunk byte length
- Writes contiguous chunks from index 0, skipping gaps
- Appends JPEG EOI marker so viewers can open partial files
- Auto-saves to `images/` on every chunk
- `delete_file(filename)` — remove image, meta sidecar, chunk directory, and in-memory state (backs the DELETE endpoint)

The assembler is owned by the MAVERIC adapter and fed via `on_packet_received` when `img_cnt_chunks` or `img_get_chunk` responses are parsed.

## Telemetry Plugins

MAVERIC ships EPS and GNC telemetry plugin pages backed by the platform
telemetry router rather than mission-specific REST routers:

- **Backend state** — `mav_gss_lib/web_runtime/telemetry/router.py` registers
  mission-declared domains from `TELEMETRY_MANIFEST`. Current MAVERIC domains
  are `eps`, `gnc`, and `spacecraft`; snapshots persist under
  `<log_dir>/.telemetry/<domain>.json`.
- **Backend API** — `GET /api/telemetry/{domain}/catalog` serves mission-owned
  catalog metadata, and `DELETE /api/telemetry/{domain}/snapshot` clears a
  domain and broadcasts `{type: "telemetry", domain, cleared: true}` on
  `/ws/rx`.
- **WebSocket data** — telemetry extractors emit `TelemetryFragment` objects;
  the router broadcasts `{type: "telemetry", domain, changes, replay?}`.
- **Frontend pages** — MAVERIC registers `gnc` and `eps` in
  `mav_gss_lib/web/src/plugins/maveric/plugins.ts`. `providers.ts` mounts
  `GncProvider` and `EpsProvider` at the app root so each page reads stable
  provider state instead of owning its own WebSocket.

The imaging plugin remains a mission-specific REST plugin because it owns file
assembly and preview endpoints. EPS/GNC use the shared telemetry API because
their backend needs are latest-value state, catalogs, clear, and replay.

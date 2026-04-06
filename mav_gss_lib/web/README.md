# MAVERIC GSS Web Console

This directory contains the React/Vite operator console for MAVERIC GSS.

It is not a standalone app. It is the frontend for the FastAPI runtime under `mav_gss_lib/web_runtime/`.

## What Lives Here

- RX monitoring views
- TX queue and command-builder views
- config sidebar
- log browser and replay controls
- shared layout, keyboard shortcuts, and operator feedback components

## Build

```bash
npm --prefix mav_gss_lib/web install
npm --prefix mav_gss_lib/web run build
```

The built assets are emitted into `mav_gss_lib/web/dist` and served by the backend runtime.

## Runtime Contract

The web app should consume normalized runtime data, not mission-specific packet internals.

In practice that means:

- packet parsing and protocol truth belong in `mav_gss_lib/mission_adapter.py`
- backend packet shaping belongs in `mav_gss_lib/web_runtime/services.py`
- React components should render the normalized packet/queue/config models they receive

If adapting this repository for a future SERC mission requires widespread React changes just to support a different packet format, the backend mission boundary is probably leaking.

## Development Guidance

- Keep mission naming and operator-facing labels config-driven where practical.
- Treat protocol-detail sections as optional UI blocks, not universal assumptions.
- Prefer extending the normalized packet shape over teaching React components new mission parsing rules.

## Entry Points

- `src/App.tsx`
  Main shell and split-pane layout.
- `src/components/rx/`
  RX monitor views.
- `src/components/tx/`
  TX queue and command controls.
- `src/components/logs/`
  Session log browsing and replay UI.
- `src/components/config/`
  Runtime config editor.

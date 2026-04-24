"""FastAPI server backing the MAVERIC GSS dashboard.

    app.py       — create_app + lifespan (RX thread, TX send loop,
                   preflight + updater scheduling)
    state.py     — WebRuntime container (split-state config, services)
    shutdown.py  — delayed SIGINT once all clients disconnect
    security.py  — CORS + CSP + session-token middleware

    ws/          — WebSocket handlers: rx, tx, session, preflight, update
    rx/          — RX service thread (ZMQ SUB → WebSocket fan-out)
    tx/          — TX service + queue + actions
    api/         — REST endpoints (config, identity, logs, queue_io,
                   schema, session)
    telemetry/   — REST catalog endpoint + one-shot legacy-snapshot reset

Author: Irfan Annuar — USC ISI SERC
"""

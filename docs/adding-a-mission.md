# Adding a New Mission

> **This document has been retired.** The pre-v2 `MissionAdapter` boundary no
> longer exists. Missions are added as platform v2 `MissionSpec` packages.
> Until a full rewrite of this guide lands, use the following sources directly:
>
> - **Mission boundary contract** — `mav_gss_lib/platform/mission_api.py`
>   (`MissionSpec`, `MissionContext`, `MissionConfigSpec`, `UiOps`, `HttpOps`).
> - **Capability protocols** — `mav_gss_lib/platform/packets.py` (`PacketOps`),
>   `mav_gss_lib/platform/commands.py` (`CommandOps`),
>   `mav_gss_lib/platform/telemetry.py` (`TelemetryOps`),
>   `mav_gss_lib/platform/events.py` (`EventOps`).
> - **Reference implementations** — `mav_gss_lib/missions/maveric/` (full
>   production mission), `mav_gss_lib/missions/echo_v2/mission.py` (minimal
>   stub), `mav_gss_lib/missions/balloon_v2/mission.py` (telemetry-only stub).
>
> A mission package lives under `mav_gss_lib/missions/<id>/` and exports
> `build(ctx: MissionContext) -> MissionSpec` from a top-level `mission.py`.
> The platform loader (`mav_gss_lib/platform/loader.py::load_mission_spec_from_split`)
> imports the module by convention and calls `build()`.

"""
mav_gss_lib.missions -- Mission Implementation Packages

Each subdirectory is a mission package providing a platform v2 MissionSpec:

  - mission.py: exports `build(ctx: MissionContext) -> MissionSpec`.
  - commands.yml (optional): command schema for missions that use one.

Mission identity constants and default mission-config values live inside the
mission package (e.g. `defaults.py`) and are seeded into `mission_cfg` by the
mission's own `build(ctx)`. The platform owns no mission metadata.
"""

"""
mav_gss_lib.missions.maveric -- MAVERIC CubeSat Mission Implementation

Mission package contract:
  - ADAPTER_API_VERSION: int — adapter contract version
  - ADAPTER_CLASS: type — adapter class (MavericMissionAdapter)
  - mission.yml: mission metadata (nodes, ptypes, callsigns, schema path, UI labels)
  - adapter.py: MissionAdapter implementation
  - wire_format.py: command wire format, schema, node tables
  - imaging.py: image chunk reassembly
"""

ADAPTER_API_VERSION = 1

from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter as ADAPTER_CLASS  # noqa: F401

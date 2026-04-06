"""
mav_gss_lib.missions.maveric -- MAVERIC CubeSat Mission Implementation

Wire format, command schema, adapter, and imaging for the MAVERIC mission.
"""

ADAPTER_API_VERSION = 1

from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter as ADAPTER_CLASS  # noqa: F401

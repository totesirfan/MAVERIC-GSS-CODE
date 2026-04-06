"""
mav_gss_lib.imaging -- Compatibility facade

STATUS: Phase 11 removal candidate. Canonical location is
mav_gss_lib.missions.maveric.imaging. Re-exports ImageAssembler for
backward compatibility with MAV_IMG.py and backup_control/.
"""

from mav_gss_lib.missions.maveric.imaging import ImageAssembler  # noqa: F401

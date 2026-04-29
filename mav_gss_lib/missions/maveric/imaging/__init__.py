"""MAVERIC imaging plugin.

End-to-end handling of on-orbit camera downlink: chunk accumulation,
JPEG reassembly to disk, REST API for the operator UI, and the packet
event source that drives assembler state from inbound imaging commands.

Modules
-------
- `assembler.py` — `ImageAssembler`. Collects `img_get_chunks` payloads,
  persists each chunk under `<image_dir>/.chunks/<source>/<filename>/`,
  and rewrites the reconstructed JPEG under
  `<image_dir>/<source>/<filename>` on every new chunk. A `.meta.json`
  sidecar tracks progress so non-contiguous transfers survive server
  restarts without filename collisions between HoloNav and Astroboard.
- `router.py`    — FastAPI router mounted under `/api/plugins/imaging`
  by `mission.py`. Serves paired-file status, chunk-progress lookups,
  JPEG previews, and file deletion. Reads `imaging.thumb_prefix` from
  mission config via a live accessor so `/api/config` edits apply
  without a MissionSpec rebuild.
- `events.py`    — `MavericImagingEvents`, the `EventOps` source that
  watches inbound `img_cnt_chunks`, `img_get_chunks`, and
  `cam_capture` packets, advances the `ImageAssembler`, and emits
  `imaging_progress` messages for the platform to broadcast to
  connected websocket clients.
"""

from mav_gss_lib.missions.maveric.imaging.assembler import (
    ImageFileRef,
    ImageAssembler,
    derive_full_filename,
    derive_thumb_filename,
    image_file_id,
)
from mav_gss_lib.missions.maveric.imaging.events import MavericImagingEvents
from mav_gss_lib.missions.maveric.imaging.router import get_imaging_router

__all__ = [
    "ImageAssembler",
    "ImageFileRef",
    "MavericImagingEvents",
    "derive_full_filename",
    "derive_thumb_filename",
    "image_file_id",
    "get_imaging_router",
]

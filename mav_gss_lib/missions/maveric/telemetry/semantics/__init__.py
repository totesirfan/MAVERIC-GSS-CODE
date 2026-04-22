"""Mission-owned semantic decoders.

These modules define the canonical shape of each domain's values
(bitfield layouts, enum tables, engineering-unit scalings). They
are called by rx_ops.parse_packet at ingest time and by the adapter
helpers inside extractors/tlm_beacon.py when the beacon extractor
needs to produce a canonical shape. Content is not re-authored as
part of v2 — it was relocated via git mv from its pre-v2 locations
(gnc_registers/ and telemetry/eps.py).
"""

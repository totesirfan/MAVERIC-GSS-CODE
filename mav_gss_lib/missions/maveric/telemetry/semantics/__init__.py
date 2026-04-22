"""Mission-owned semantic decoders.

These modules define the canonical shape of each domain's values
(bitfield layouts, enum tables, engineering-unit scalings). They are
called by rx_ops.parse_packet at ingest time and by the helpers inside
extractors/tlm_beacon.py when the beacon extractor produces a
canonical shape from the packed binary beacon struct.
"""

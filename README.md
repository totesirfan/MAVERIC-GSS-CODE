# MAVERIC Ground Station Software

Packet monitor for the MAVERIC CubeSat mission. Receives decoded satellite frames from a GNU Radio / gr-satellites flowgraph over ZMQ and displays packet contents for live debugging.

## What It Does

`MAVERIC_GSS.py` subscribes to a ZMQ PUB socket where GNU Radio publishes decoded PDUs, then for each packet displays:

- Packet count, ground station timestamp, and inter-packet timing
- Frame type (AX.25 or AX100), inferred from gr-satellites metadata
- Inner payload after stripping transport framing
- CSP v1 header candidate (first 4 bytes, may not be valid)
- Satellite timestamp candidate (searches for 13-digit epoch-ms values)
- Numeric scanner showing leading bytes interpreted as various types in both byte orders
- Full raw hex dump (ground truth)
- Printable ASCII extraction

Raw hex is ground truth. All other outputs are diagnostic and should not be treated as confirmed telemetry.

## Logging

Each session writes two log files to `logs/`:

- `.jsonl` — machine-readable, one JSON object per packet
- `.txt` — human-readable plain text

## Usage

Start your GNU Radio flowgraph first, then:

```bash
python3 MAVERIC_GSS.py
```

Press `Ctrl+C` to stop.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZMQ_PORT` | `"52001"` | Port to subscribe to |
| `ZMQ_RECV_TIMEOUT_MS` | `200` | Receive timeout in ms |
| `LOG_DIR` | `"logs"` | Log output directory |

## Dependencies

- Python 3.8+
- PyZMQ
- pmt (included with GNU Radio)
- GNU Radio 3.10+ with gr-satellites

## Status

Early development. Telemetry decoding is not yet implemented — the monitor shows raw packet data and diagnostic heuristics only.
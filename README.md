# MAVERIC Ground Station Software

Ground station tools for the MAVERIC CubeSat mission. Receives and displays decoded satellite frames, and provides a command terminal for uplink operations.

## Components

### MAVERIC_GSS.py — Packet Monitor

Subscribes to a ZMQ PUB socket where GNU Radio publishes decoded PDUs and displays packet contents for live debugging. Designed to run continuously — the flowgraph can be started and stopped independently.

For each packet, the monitor shows:

- Packet count, ground station timestamp, and inter-packet timing
- Frame type (AX.25 or AX100), inferred from gr-satellites metadata
- Inner payload after stripping transport framing
- CSP v1 header candidate parse
- Satellite timestamp candidate (epoch-ms detection)
- Parsed command structure with node routing and arguments
- SHA-256 fingerprint for duplicate detection

With `--loud`, hex dump, ASCII, and CRC are also shown in the terminal. These are always written to the log files regardless.

Raw hex is ground truth. All parsed fields are diagnostic until the telemetry map is finalized.

### MAVERIC_CMD.py — Command Terminal

Interactive terminal for sending commands to the satellite via gr-satellites AX100 ASM+Golay framing. Sends payloads as PMT PDUs over ZMQ to a GNU Radio flowgraph that handles modulation and transmission.

### AX100_Loopback_Test.py — Encoder Verification

End-to-end loopback test that encodes a payload using our AX100 encoder (ASM, CCSDS scrambling, Golay, Reed-Solomon) and decodes it with gr-satellites blocks to verify round-trip correctness.

## Usage

All scripts require the radioconda GNU Radio environment. Start your GNU Radio flowgraph first, then:

```bash
conda activate gnuradio

# Packet monitor (normal display)
python3 MAVERIC_GSS.py

# Packet monitor (verbose — includes hex, ASCII, CRC, SHA256 in terminal)
python3 MAVERIC_GSS.py --loud

# Packet monitor (display only, no log files)
python3 MAVERIC_GSS.py --nolog

# Command terminal
python3 MAVERIC_CMD.py

# AX100 encoder loopback test
python3 AX100_Loopback_Test.py
```

Press `Ctrl+C` to stop the monitor or command terminal.

## Logging

Each session writes two log files to `logs/`:

- `.jsonl` — machine-readable, one JSON object per packet (includes all parse candidates)
- `.txt` — human-readable plain text

The command terminal logs uplink commands to a separate `.jsonl` file.

Logging can be disabled with `--nolog` on the monitor.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZMQ_PORT` (GSS) | `52001` | Downlink — port to subscribe to |
| `ZMQ_ADDR` (CMD) | `tcp://127.0.0.1:52002` | Uplink — port to publish on |
| `ZMQ_RECV_TIMEOUT_MS` | `200` | Receive timeout in ms |
| `LOG_DIR` | `logs` | Log output directory |

## Dependencies

- [radioconda](https://github.com/ryanvolz/radioconda) (provides GNU Radio 3.10+, gr-satellites, PyZMQ, and pmt)
- `crc` Python package (for command terminal and loopback test)

## Decoder

`MAVERIC_DECODER.yml` is the gr-satellites satellite definition file. It configures three transmitter modes on 437.250 MHz:

- 19k2 FSK AX.25 G3RUH
- 4k8 FSK AX.25 G3RUH
- 4k8 FSK AX100 ASM+Golay

## Status

Early development. Telemetry structure is not yet finalized — the monitor shows raw packet data and diagnostic heuristics. Command definitions are maintained separately.
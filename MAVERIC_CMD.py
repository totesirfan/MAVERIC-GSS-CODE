"""
MAVERIC Command Terminal
Irfan Annuar — USC ISI SERC

Type commands, they get transmitted via gr-satellites AX100 ASM+Golay.

  You type:         EPS PING
  This script:      Builds command payload → sends as PMT PDU over ZMQ
  gr-satellites:    Wraps in ASM+Golay frame → FSK modulates → SDR transmits

GNU Radio flowgraph needs:
  ZMQ SUB Message Source (tcp://127.0.0.1:52002)
    → AX100 ASM+Golay Framer
    → FSK Modulator (4800 baud)
    → SDR Sink (437.250 MHz)
"""

import zmq
import pmt
import sys
import os
import json
import time
from datetime import datetime
from crc import Calculator, Crc16

# ── Config ──────────────────────────────────────────────────────────────────

ZMQ_ADDR = "tcp://127.0.0.1:52002"
LOG_DIR  = "logs"

NODES = {
    'NONE': 0, 'LPPM': 1, 'EPS': 2, 'UPPM': 3,
    'HOLONAV': 4, 'ASTROBOARD': 5, 'GS': 6, 'FTDI': 7,
}
NODES_REV = {v: k for k, v in NODES.items()}

PTYPES = {'NONE': 0, 'REQ': 1, 'RES': 2, 'ACK': 3}

ORIGIN = NODES['GS']   # we are the ground station

# ── Colors ──────────────────────────────────────────────────────────────────

R  = "\033[91m"    # red
G  = "\033[92m"    # green
Y  = "\033[93m"    # yellow
C  = "\033[96m"    # cyan
D  = "\033[2m"     # dim
B  = "\033[1m"     # bold
E  = "\033[0m"     # reset

# ── Payload Builder ─────────────────────────────────────────────────────────

crc_calc = Calculator(Crc16.XMODEM)

def build_payload(dest, cmd, args="", echo=0, ptype=1):
    """
    Build MAVERIC command payload — same wire format as Commands.py:
      [orgn][dest][echo][ptype][id_len][args_len][id][0x00][args][0x00][crc16-LE]
    """
    p = bytearray()
    p.append(ORIGIN)
    p.append(dest)
    p.append(echo)
    p.append(ptype)
    p.append(len(cmd))
    p.append(len(args))
    p.extend(cmd.encode('ascii'))
    p.append(0x00)
    p.extend(args.encode('ascii'))
    p.append(0x00)
    crc = crc_calc.checksum(p)
    p.extend(crc.to_bytes(2, byteorder='little'))
    return p

# ── ZMQ ─────────────────────────────────────────────────────────────────────

def zmq_connect(addr):
    """Open ZMQ PUB socket. gr-satellites SUB Message Source connects to this."""
    ctx  = zmq.Context()
    sock = ctx.socket(zmq.PUB)
    sock.bind(addr)
    time.sleep(0.3)   # let subscriber attach
    return ctx, sock

def zmq_send(sock, payload):
    """Send payload as PMT PDU — gr-satellites adds the AX100 framing."""
    meta = pmt.make_dict()
    vec  = pmt.init_u8vector(len(payload), list(payload))
    sock.send(pmt.serialize_str(pmt.cons(meta, vec)))

# ── Logging ─────────────────────────────────────────────────────────────────

def open_log():
    os.makedirs(LOG_DIR, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LOG_DIR, f"uplink_{ts}.jsonl")
    return open(path, "a"), path

def log_cmd(f, n, dest, cmd, args, payload):
    rec = {
        "n": n,
        "ts": datetime.now().astimezone().isoformat(),
        "dest": dest, "dest_lbl": NODES_REV.get(dest, "?"),
        "cmd": cmd, "args": args,
        "hex": payload.hex(),
        "len": len(payload),
    }
    f.write(json.dumps(rec) + "\n")
    f.flush()

# ── Display ─────────────────────────────────────────────────────────────────

def show_tx(n, dest, cmd, args, payload):
    ts   = datetime.now().strftime("%H:%M:%S")
    dlbl = NODES_REV.get(dest, "?")
    print(f"\n  {D}───────────────────────────────────────────────{E}")
    print(f"  {B}{G}TX #{n}{E}  {ts}  {B}GS → {dlbl}{E}  {C}{cmd}{E}  {args or ''}")
    print(f"  {D}{len(payload)}B{E}  {payload.hex(' ')}")
    print(f"  {D}───────────────────────────────────────────────{E}")

# ── Node Resolution ─────────────────────────────────────────────────────────

def resolve_dest(s):
    """Accept node name or number. Returns int or None."""
    if s.upper() in NODES:
        return NODES[s.upper()]
    if s.isdigit() and int(s) in NODES_REV:
        return int(s)
    return None

# ── Main Loop ───────────────────────────────────────────────────────────────

def main():
    print(f"""
{B}  MAVERIC Command Terminal{E}  {D}v1.0{E}
  {D}gr-satellites AX100 ASM+Golay uplink{E}
  {D}ZMQ: {ZMQ_ADDR}{E}
""")

    ctx, sock = zmq_connect(ZMQ_ADDR)
    logf, logpath = open_log()
    print(f"  {D}Log: {logpath}{E}")
    print(f"  {D}Type a command or 'help'{E}\n")

    n    = 0
    last = None

    try:
        while True:
            try:
                line = input(f"  {C}>{E} ").strip()
            except EOFError:
                break

            if not line:
                continue

            low = line.lower()

            # ── built-in commands ──
            if low in ('q', 'quit', 'exit'):
                break

            if low == 'help':
                print(f"""
  {B}Usage:{E}   <dest> <command> [args]

  {B}Examples:{E}
    EPS PING
    EPS GET_VOLTAGE
    HOLONAV SET_MODE fast
    2 RESET
    5 CALIBRATE x=1,y=2

  {B}Shortcuts:{E}
    !!           repeat last command
    nodes        list node IDs
    raw <hex>    send raw hex bytes
    q            quit
""")
                continue

            if low == 'nodes':
                for nid in sorted(NODES_REV):
                    lbl = NODES_REV[nid]
                    tag = f" {G}← you{E}" if nid == ORIGIN else ""
                    print(f"    {nid} = {B}{lbl}{E}{tag}")
                print()
                continue

            if low == '!!' or low == 'last':
                if last is None:
                    print(f"  {D}nothing to repeat{E}")
                    continue
                dest, cmd, args = last
            elif low.startswith('raw '):
                # send arbitrary hex bytes as a PDU
                hexstr = line[4:].replace(' ', '')
                try:
                    raw = bytes.fromhex(hexstr)
                except ValueError:
                    print(f"  {R}bad hex{E}")
                    continue
                n += 1
                zmq_send(sock, raw)
                print(f"\n  {B}{G}TX #{n}{E}  raw {len(raw)}B  {raw.hex(' ')}\n")
                continue
            else:
                parts = line.split(None, 2)
                if len(parts) < 2:
                    print(f"  {R}need: <dest> <command> [args]{E}")
                    continue

                dest = resolve_dest(parts[0])
                if dest is None:
                    print(f"  {R}unknown node '{parts[0]}' — type 'nodes'{E}")
                    continue

                cmd  = parts[1]
                args = parts[2] if len(parts) > 2 else ""
                last = (dest, cmd, args)

            # ── build + send ──
            payload = build_payload(dest, cmd, args)
            n += 1
            zmq_send(sock, payload)
            show_tx(n, dest, cmd, args, payload)
            log_cmd(logf, n, dest, cmd, args, payload)

    except KeyboardInterrupt:
        pass

    print(f"\n  {D}Sent {n} commands. Log: {logpath}{E}\n")
    logf.close()
    sock.close()
    ctx.term()


if __name__ == "__main__":
    main()
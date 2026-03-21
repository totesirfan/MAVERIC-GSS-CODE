"""
MAVERIC Command Terminal v2.1
Irfan Annuar -- USC ISI SERC

Type commands, they get KISS-wrapped with a CSP v1 header and
transmitted via AX100 ASM+Golay.

Single command:
  > EPS PING

Batch multiple commands (sent in one AX100 frame):
  > + EPS SET_MODE auto
  > + EPS SET_VOLTAGE 3.3
  > send

CSP header config:
  > csp                    show current CSP settings
  > csp off                disable CSP header
  > csp on                 enable CSP header
  > csp dest 8             set CSP destination
  > csp dport 24           set CSP destination port

GNU Radio flowgraph needs:
  ZMQ SUB Message Source (tcp://127.0.0.1:52002)
    -> AX100 ASM+Golay Encoder
    -> GFSK Modulator (4800 baud)
    -> SDR Sink (437.250 MHz)
"""

import zmq
import pmt
import sys
import os
import json
import time
from datetime import datetime
from crc import Calculator, Crc16

# -- Config -------------------------------------------------------------------

ZMQ_ADDR = "tcp://127.0.0.1:52002"
LOG_DIR  = "logs"
MAX_RS_PAYLOAD = 223

NODES = {
    'NONE': 0, 'LPPM': 1, 'EPS': 2, 'UPPM': 3,
    'HOLONAV': 4, 'ASTROBOARD': 5, 'GS': 6, 'FTDI': 7,
}
NODES_REV = {v: k for k, v in NODES.items()}

PTYPES = {'NONE': 0, 'REQ': 1, 'RES': 2, 'ACK': 3}

ORIGIN = NODES['GS']

# KISS constants
FEND  = 0xC0
FESC  = 0xDB
TFEND = 0xDC
TFESC = 0xDD

# -- Colors -------------------------------------------------------------------

R  = "\033[91m"
G  = "\033[92m"
Y  = "\033[93m"
C  = "\033[96m"
D  = "\033[2m"
B  = "\033[1m"
E  = "\033[0m"

# -- CSP v1 Header ------------------------------------------------------------
#
# Derived from MAVERIC downlink: Prio:2 Src:8 Dest:0 DPort:24 SPort:0
# Uplink reverses Src/Dest: GS(0) -> Sat(8), same port.
#
# CSP v1 header (32-bit big-endian):
#   [31:30] priority   2 bits
#   [29:25] source     5 bits
#   [24:20] destination 5 bits
#   [19:14] dest_port  6 bits
#   [13:8]  src_port   6 bits
#   [7:0]   flags      8 bits
#
# These are PLACEHOLDERS based on observed downlink traffic.
# Adjust once the AX100 CSP config is confirmed.

class CSPConfig:
    def __init__(self):
        self.enabled = True
        self.prio    = 2     # same as downlink
        self.src     = 0     # GS CSP address (was Dest:0 in downlink)
        self.dest    = 8     # satellite CSP address (was Src:8 in downlink)
        self.dport   = 24    # service port (same as downlink DPort)
        self.sport   = 0     # source port
        self.flags   = 0x00  # no HMAC/XTEA/RDP/CRC flags

    def build_header(self):
        """Build 4-byte CSP v1 header."""
        h = ((self.prio  & 0x03) << 30 |
             (self.src   & 0x1F) << 25 |
             (self.dest  & 0x1F) << 20 |
             (self.dport & 0x3F) << 14 |
             (self.sport & 0x3F) << 8  |
             (self.flags & 0xFF))
        return h.to_bytes(4, 'big')

    def overhead(self):
        """Bytes added by CSP wrapping."""
        return 4 if self.enabled else 0

    def show(self):
        hdr = self.build_header()
        print(f"  {B}CSP v1 Header{E}  {'enabled' if self.enabled else D + 'disabled' + E}")
        print(f"    Prio:  {self.prio}")
        print(f"    Src:   {self.src}  (GS)")
        print(f"    Dest:  {self.dest}  (satellite)")
        print(f"    DPort: {self.dport}")
        print(f"    SPort: {self.sport}")
        print(f"    Flags: 0x{self.flags:02X}")
        print(f"    Bytes: {hdr.hex(' ')}")
        print(f"    {D}Placeholder -- adjust once CSP config confirmed{E}")

    def handle_cmd(self, args):
        """Handle 'csp ...' commands. Returns True if handled."""
        if not args:
            self.show()
            return True
        parts = args.split()
        cmd = parts[0].lower()

        if cmd == 'on':
            self.enabled = True
            print(f"  {G}CSP header enabled{E}")
        elif cmd == 'off':
            self.enabled = False
            print(f"  {Y}CSP header disabled{E}")
        elif cmd == 'prio' and len(parts) > 1:
            self.prio = int(parts[1]) & 0x03
            print(f"  CSP prio = {self.prio}")
        elif cmd == 'src' and len(parts) > 1:
            self.src = int(parts[1]) & 0x1F
            print(f"  CSP src = {self.src}")
        elif cmd == 'dest' and len(parts) > 1:
            self.dest = int(parts[1]) & 0x1F
            print(f"  CSP dest = {self.dest}")
        elif cmd == 'dport' and len(parts) > 1:
            self.dport = int(parts[1]) & 0x3F
            print(f"  CSP dport = {self.dport}")
        elif cmd == 'sport' and len(parts) > 1:
            self.sport = int(parts[1]) & 0x3F
            print(f"  CSP sport = {self.sport}")
        elif cmd == 'flags' and len(parts) > 1:
            self.flags = int(parts[1], 0) & 0xFF
            print(f"  CSP flags = 0x{self.flags:02X}")
        else:
            print(f"  {R}csp [on|off|prio N|src N|dest N|dport N|sport N|flags N]{E}")
        return True

# -- Command Builder ----------------------------------------------------------

crc_calc = Calculator(Crc16.XMODEM)

def build_cmd_raw(dest, cmd, args="", echo=0, ptype=1):
    """Build raw MAVERIC command with CRC-16 (before KISS wrapping)."""
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

def kiss_wrap(raw_cmd):
    """KISS-wrap a raw command -- identical to Commands.py create_cmd()."""
    escaped = bytearray()
    for b in raw_cmd:
        if b == FEND:
            escaped.extend(bytes([FESC, TFEND]))
        elif b == FESC:
            escaped.extend(bytes([FESC, TFESC]))
        else:
            escaped.append(b)
    frame = bytearray([FEND, 0x00])
    frame.extend(escaped)
    frame.append(FEND)
    return bytes(frame)

def build_kiss_cmd(dest, cmd, args="", echo=0, ptype=1):
    """Build a complete KISS-wrapped command."""
    raw = build_cmd_raw(dest, cmd, args, echo, ptype)
    return kiss_wrap(raw), raw

def wrap_with_csp(csp, kiss_payload):
    """Prepend CSP header to payload if enabled."""
    if csp.enabled:
        return csp.build_header() + kiss_payload
    return kiss_payload

# -- ZMQ ---------------------------------------------------------------------

def zmq_connect(addr):
    ctx  = zmq.Context()
    sock = ctx.socket(zmq.PUB)
    sock.bind(addr)
    time.sleep(0.3)
    return ctx, sock

def zmq_send(sock, payload):
    meta = pmt.make_dict()
    vec  = pmt.init_u8vector(len(payload), list(payload))
    sock.send(pmt.serialize_str(pmt.cons(meta, vec)))

# -- Logging ------------------------------------------------------------------

def open_log():
    os.makedirs(LOG_DIR, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LOG_DIR, f"uplink_{ts}.jsonl")
    return open(path, "a"), path

def log_tx(f, n, cmds, payload, csp_enabled):
    rec = {
        "n": n,
        "ts": datetime.now().astimezone().isoformat(),
        "cmds": cmds,
        "hex": payload.hex(),
        "len": len(payload),
        "num_cmds": len(cmds),
        "csp": csp_enabled,
    }
    f.write(json.dumps(rec) + "\n")
    f.flush()

# -- Display ------------------------------------------------------------------

def show_single(n, dest, cmd, args, payload, csp):
    ts   = datetime.now().strftime("%H:%M:%S")
    dlbl = NODES_REV.get(dest, "?")
    csp_tag = f" {D}[CSP]{E}" if csp.enabled else ""
    print(f"\n  {D}-----------------------------------------------{E}")
    print(f"  {B}{G}TX #{n}{E}  {ts}  {B}GS -> {dlbl}{E}  {C}{cmd}{E}  {args or ''}{csp_tag}")
    print(f"  {D}{len(payload)}B{E}  {payload.hex(' ')}")
    print(f"  {D}-----------------------------------------------{E}")

def show_batch(n, batch_info, payload, csp):
    ts = datetime.now().strftime("%H:%M:%S")
    csp_tag = f" {D}[CSP]{E}" if csp.enabled else ""
    print(f"\n  {D}==============================================={E}")
    print(f"  {B}{G}TX #{n}{E}  {ts}  {Y}BATCH ({len(batch_info)} cmds){E}  {D}{len(payload)}B{E}{csp_tag}")
    for i, (dest, cmd, args, kiss_len) in enumerate(batch_info):
        dlbl = NODES_REV.get(dest, "?")
        print(f"    {D}{i+1}.{E} {B}GS -> {dlbl}{E}  {C}{cmd}{E}  {args or ''}  {D}({kiss_len}B){E}")
    print(f"  {D}payload: {payload.hex(' ')}{E}")
    print(f"  {D}==============================================={E}")

# -- Node Resolution ----------------------------------------------------------

def resolve_dest(s):
    if s.upper() in NODES:
        return NODES[s.upper()]
    if s.isdigit() and int(s) in NODES_REV:
        return int(s)
    return None

def parse_cmd_line(line):
    parts = line.split(None, 2)
    if len(parts) < 2:
        return None
    dest = resolve_dest(parts[0])
    if dest is None:
        return None
    cmd  = parts[1]
    args = parts[2] if len(parts) > 2 else ""
    return (dest, cmd, args)

# -- Main Loop ----------------------------------------------------------------

def main():
    csp = CSPConfig()

    print(f"""
{B}  MAVERIC Command Terminal{E}  {D}v2.1{E}
  {D}gr-satellites AX100 ASM+Golay uplink{E}
  {D}KISS-wrapped + CSP v1 header{E}
  {D}ZMQ: {ZMQ_ADDR}{E}
""")

    ctx, sock = zmq_connect(ZMQ_ADDR)
    logf, logpath = open_log()
    print(f"  {D}Log: {logpath}{E}")
    csp.show()
    print(f"\n  {D}Type a command or 'help'{E}\n")

    n      = 0
    last   = None
    batch  = []

    def max_payload():
        return MAX_RS_PAYLOAD - csp.overhead()

    try:
        while True:
            if batch:
                prompt = f"  {Y}+({len(batch)}){E}{C}>{E} "
            else:
                prompt = f"  {C}>{E} "

            try:
                line = input(prompt).strip()
            except EOFError:
                break

            if not line:
                continue

            low = line.lower()

            if low in ('q', 'quit', 'exit'):
                if batch:
                    print(f"  {Y}Discarding {len(batch)} queued commands{E}")
                break

            if low == 'help':
                print(f"""
  {B}Single command:{E}
    {C}<dest> <cmd> [args]{E}     send immediately

  {B}Batch commands:{E}
    {C}+ <dest> <cmd> [args]{E}   queue a command
    {C}send{E}                    transmit all queued
    {C}batch{E}                   show queue
    {C}clear{E}                   discard queue

  {B}CSP config:{E}
    {C}csp{E}                     show CSP settings
    {C}csp on/off{E}              enable/disable CSP header
    {C}csp dest N{E}              set CSP destination node
    {C}csp dport N{E}             set CSP destination port
    {C}csp src/sport/prio/flags N{E}

  {B}Other:{E}
    {C}!!{E}                      repeat last command
    {C}nodes{E}                   list node IDs
    {C}raw <hex>{E}               send raw hex bytes
    {C}q{E}                       quit

  {B}Examples:{E}
    EPS PING
    + EPS SET_MODE auto
    + EPS SET_VOLTAGE 3.3
    send
    csp dest 8
""")
                continue

            if low == 'nodes':
                for nid in sorted(NODES_REV):
                    lbl = NODES_REV[nid]
                    tag = f" {G}<- you{E}" if nid == ORIGIN else ""
                    print(f"    {nid} = {B}{lbl}{E}{tag}")
                print()
                continue

            # -- CSP config --
            if low == 'csp' or low.startswith('csp '):
                csp_args = line[3:].strip() if len(line) > 3 else ""
                csp.handle_cmd(csp_args)
                continue

            # -- batch commands --
            if low == 'batch':
                if not batch:
                    print(f"  {D}batch is empty{E}")
                else:
                    total = sum(len(k) for _, _, _, k in batch)
                    print(f"  {Y}Queued ({len(batch)} commands, {total}B + {csp.overhead()}B CSP = {total + csp.overhead()}B):{E}")
                    for i, (dest, cmd, args, kiss) in enumerate(batch):
                        dlbl = NODES_REV.get(dest, "?")
                        print(f"    {i+1}. {B}{dlbl}{E} {C}{cmd}{E} {args}  {D}({len(kiss)}B){E}")
                    remaining = max_payload() - total
                    print(f"  {D}{remaining}B remaining in frame{E}")
                continue

            if low == 'clear':
                if batch:
                    print(f"  {D}cleared {len(batch)} commands{E}")
                    batch.clear()
                else:
                    print(f"  {D}nothing to clear{E}")
                continue

            if low == 'send':
                if not batch:
                    print(f"  {R}nothing queued -- use + to add commands{E}")
                    continue

                kiss_stream = bytearray()
                batch_info = []
                for dest, cmd, args, kiss in batch:
                    kiss_stream.extend(kiss)
                    batch_info.append((dest, cmd, args, len(kiss)))

                if len(kiss_stream) > max_payload():
                    print(f"  {R}batch too large: {len(kiss_stream)}B > {max_payload()}B max{E}")
                    continue

                payload = wrap_with_csp(csp, bytes(kiss_stream))

                n += 1
                zmq_send(sock, payload)
                show_batch(n, batch_info, payload, csp)
                log_tx(logf, n,
                       [{"dest": d, "dest_lbl": NODES_REV.get(d,"?"),
                         "cmd": c, "args": a} for d, c, a, _ in batch],
                       payload, csp.enabled)
                batch.clear()
                continue

            # -- queue with + --
            if line.startswith('+'):
                cmd_text = line[1:].strip()
                if not cmd_text:
                    print(f"  {R}need: + <dest> <cmd> [args]{E}")
                    continue
                parsed = parse_cmd_line(cmd_text)
                if parsed is None:
                    print(f"  {R}bad command -- format: + <dest> <cmd> [args]{E}")
                    continue
                dest, cmd, args = parsed
                kiss, raw = build_kiss_cmd(dest, cmd, args)

                current_total = sum(len(k) for _, _, _, k in batch)
                if current_total + len(kiss) > max_payload():
                    print(f"  {R}won't fit: {current_total + len(kiss)}B > {max_payload()}B{E}")
                    continue

                batch.append((dest, cmd, args, kiss))
                dlbl = NODES_REV.get(dest, "?")
                remaining = max_payload() - (current_total + len(kiss))
                print(f"  {D}queued #{len(batch)}: {dlbl} {cmd} {args} ({len(kiss)}B, {remaining}B remaining){E}")
                continue

            # -- repeat last --
            if low == '!!' or low == 'last':
                if last is None:
                    print(f"  {D}nothing to repeat{E}")
                    continue
                dest, cmd, args = last

            # -- raw hex --
            elif low.startswith('raw '):
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

            # -- single command --
            else:
                parsed = parse_cmd_line(line)
                if parsed is None:
                    print(f"  {R}need: <dest> <cmd> [args]{E}")
                    continue
                dest, cmd, args = parsed
                last = (dest, cmd, args)

            # Build, wrap with CSP, send
            kiss, raw = build_kiss_cmd(dest, cmd, args)

            if len(kiss) + csp.overhead() > MAX_RS_PAYLOAD:
                print(f"  {R}command too large: {len(kiss) + csp.overhead()}B > {MAX_RS_PAYLOAD}B{E}")
                continue

            payload = wrap_with_csp(csp, kiss)

            n += 1
            zmq_send(sock, payload)
            show_single(n, dest, cmd, args, payload, csp)
            log_tx(logf, n,
                   [{"dest": dest, "dest_lbl": NODES_REV.get(dest,"?"),
                     "cmd": cmd, "args": args}],
                   payload, csp.enabled)

    except KeyboardInterrupt:
        if batch:
            print(f"\n  {Y}Discarding {len(batch)} queued commands{E}")

    print(f"\n  {D}Sent {n} transmissions. Log: {logpath}{E}\n")
    logf.close()
    sock.close()
    ctx.term()


if __name__ == "__main__":
    main()
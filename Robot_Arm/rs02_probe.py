#!/usr/bin/env python3
"""
RS02 broad diagnostic — port scan, protocol probe, raw listen.
Run: python3 rs02_probe.py
"""
import struct, time, subprocess, serial

BAUD_RATES = [115200, 230400, 460800, 921600, 1000000, 500000]
PORTS = ['/dev/ttyUSB0', '/dev/ttyACM0']
MOTOR_ID = 0x7F
MASTER_ID = 0x00FD

HEADER = bytes([0x41, 0x54])
TAIL   = bytes([0x0D, 0x0A])

def build_frame(comm_type, motor_id, master_id, data=b'\x00'*8, with_dlc=True):
    arb_id = (comm_type << 24) | (master_id << 8) | motor_id
    id_bytes = struct.pack('<I', arb_id)
    if with_dlc:
        return HEADER + id_bytes + b'\x08' + data + TAIL
    else:
        return HEADER + id_bytes + data + TAIL

def check_socketcan():
    """Check if there are any socketcan interfaces."""
    try:
        result = subprocess.run(['ip', 'link', 'show', 'type', 'can'],
                                capture_output=True, text=True)
        if result.stdout.strip():
            print(f"SocketCAN interfaces found:\n{result.stdout}")
        else:
            print("No socketcan interfaces found (ip link show type can → empty)")
    except Exception as e:
        print(f"Could not check socketcan: {e}")

def raw_listen(port, baud, duration=2.0):
    """Just open port and listen — catches unsolicited bytes / echo."""
    try:
        s = serial.Serial(port, baud, timeout=0.1)
    except Exception as e:
        return None
    s.reset_input_buffer()
    deadline = time.time() + duration
    buf = b''
    while time.time() < deadline:
        chunk = s.read(128)
        if chunk:
            buf += chunk
    s.close()
    return buf

def probe_port(port, baud):
    try:
        s = serial.Serial(port, baud, timeout=0.4)
    except Exception as e:
        return False
    time.sleep(0.1)
    s.reset_input_buffer()

    frames_to_try = [
        ("Type-0 detect 17B",  build_frame(0, MOTOR_ID, MASTER_ID, with_dlc=True)),
        ("Type-0 detect 16B",  build_frame(0, MOTOR_ID, MASTER_ID, with_dlc=False)),
        # broadcast motor ID = 0
        ("Type-0 bcast  17B",  build_frame(0, 0x00, MASTER_ID, with_dlc=True)),
        ("Type-0 bcast  16B",  build_frame(0, 0x00, MASTER_ID, with_dlc=False)),
        # Type-0 with big-endian CAN ID
        ("Type-0 BE ID 17B",
         HEADER + struct.pack('>I', (0 << 24)|(MASTER_ID << 8)|MOTOR_ID) + b'\x08' + b'\x00'*8 + TAIL),
        # SLCAN format (text-based): T{8-hex-id}{dlc}{16-hex-data}\r
        ("SLCAN extended",
         b'T' + f'{(0 << 24)|(MASTER_ID << 8)|MOTOR_ID:08X}8' .encode() + b'00'*8 + b'\r'),
        # Simple ping: just header+tail
        ("Raw 41 54 0D 0A", HEADER + TAIL),
    ]

    found = False
    for label, frame in frames_to_try:
        s.reset_input_buffer()
        s.write(frame)
        time.sleep(0.4)
        raw = s.read(128)
        if raw:
            print(f"  *** RESPONSE at {port} {baud} baud [{label}] ***")
            print(f"      TX ({len(frame)}B): {frame.hex()}")
            print(f"      RX ({len(raw)}B):  {raw.hex()}")
            try:
                print(f"      RX ascii: {raw.decode('latin1')!r}")
            except Exception:
                pass
            found = True
            break
    s.close()
    return found


# ── main ──────────────────────────────────────────────────────────────────────

print("=" * 60)
print("Step 1: Check for SocketCAN interfaces")
print("=" * 60)
check_socketcan()
print()

print("=" * 60)
print("Step 2: Listen on all ports at 921600 for 2s (no TX)")
print("=" * 60)
for port in PORTS:
    buf = raw_listen(port, 921600)
    if buf is None:
        print(f"  {port}: could not open")
    elif buf:
        print(f"  {port}: got {len(buf)} bytes unprompted: {buf.hex()}")
    else:
        print(f"  {port}: silent")
print()

print("=" * 60)
print("Step 3: TX probe — all ports × baud rates × frame formats")
print("=" * 60)
found = False
for port in PORTS:
    for baud in BAUD_RATES:
        if probe_port(port, baud):
            found = True
            break
    if found:
        break

if not found:
    print()
    print("Still no response. Most likely causes:")
    print("  1. Opto-isolator limiting baud rate — try direct USB connection")
    print("  2. Adapter uses a different protocol (GKcan, ZLG, PEAK, CANalyst)")
    print("  3. Motor CAN ID was changed from 127 during earlier troubleshooting")
    print("  4. CAN termination: new RS02 (FW ≥0.2.3.9) has no internal resistor.")
    print("     With DIP-2 ON, you have 120Ω on the adapter side only.")
    print("     A proper CAN bus needs 120Ω at BOTH ends — add a 120Ω resistor")
    print("     across CANH–CANL at the motor connector.")
    print()
    print("  What adapter model do you have? (look for model number on PCB or box)")

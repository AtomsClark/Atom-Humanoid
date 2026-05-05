#!/usr/bin/env python3
"""
RS02 CAN diagnostic — confirms adapter TX works, checks bus health, tries all comm types.

Run:
    python3 rs02_diag.py

What this checks:
  1. CAN interface stats (TX/RX counts, error counters)
  2. Loopback test — do we see our own TX frames? Confirms adapter is functioning.
  3. Passive listen — any unsolicited frames from motor?
  4. Brute-force: send all comm types 0-31 to motor ID 127, log everything received.
"""

import can
import struct
import subprocess
import time

INTERFACE = 'can0'
MASTER_ID = 0x00FD
MOTOR_ID  = 127


def can_stats():
    """Print current CAN interface statistics."""
    try:
        result = subprocess.run(
            ['ip', '-s', '-d', 'link', 'show', INTERFACE],
            capture_output=True, text=True)
        print(result.stdout)
    except Exception as e:
        print(f"  (could not read stats: {e})")


def loopback_test(bus):
    """
    Enable CAN loopback mode, send a test frame, confirm we receive it back.
    This verifies the adapter is actually transmitting — NOT motor comms.
    Runs only if the kernel module supports loopback.
    """
    print("--- Loopback test (software loopback on can0) ---")
    # Enable loopback via socket option
    import socket
    raw = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    try:
        raw.bind((INTERFACE,))
        # CAN_RAW_LOOPBACK = 3, enable = 1
        raw.setsockopt(socket.SOL_CAN_RAW, 3, struct.pack('i', 1))
        raw.setsockopt(socket.SOL_CAN_RAW, 4, struct.pack('i', 1))  # RECV_OWN_MSGS
        raw.settimeout(0.2)

        # Build a minimal CAN frame: ID=0x12345678 (extended), DLC=1, data=0xAB
        # struct: <IB3x8s (canid, dlc, pad, data[8])
        test_id = 0x12345678 | 0x80000000  # EFF flag
        frame = struct.pack('=IB3x8s', test_id, 1, bytes([0xAB] + [0]*7))
        raw.send(frame)

        try:
            reply = raw.recv(16)
            got_id = struct.unpack_from('=I', reply)[0] & 0x1FFFFFFF
            got_data = reply[8]
            if got_id == 0x12345678 and got_data == 0xAB:
                print("  PASS — loopback frame received. Adapter is transmitting.\n")
            else:
                print(f"  UNEXPECTED: got id=0x{got_id:08X} data=0x{got_data:02X}\n")
        except socket.timeout:
            print("  FAIL — no loopback. Adapter may not be transmitting, OR kernel\n"
                  "         CAN socket does not support SO_RXQ_OVFL loopback.\n"
                  "         Try: sudo ip link set can0 type can bitrate 1000000 loopback on\n")
    finally:
        raw.close()


def passive_listen(bus, seconds=2.0):
    print(f"--- Passive listen for {seconds}s ---")
    bus.set_filters([])
    deadline = time.time() + seconds
    count = 0
    while time.time() < deadline:
        msg = bus.recv(timeout=deadline - time.time())
        if msg:
            arb = msg.arbitration_id
            comm = (arb >> 24) & 0x1F
            data_area = (arb >> 8) & 0xFFFF
            motor_id = arb & 0xFF
            print(f"  Frame: arb=0x{arb:08X}  comm={comm}  data_area=0x{data_area:04X}"
                  f"  motor={motor_id}  data={bytes(msg.data).hex()}")
            count += 1
    if count == 0:
        print("  (none)")
    print()


def brute_force_all_types(bus):
    """Send all 32 comm types to motor 127 and capture anything received."""
    print("--- Brute-force: all comm types 0-31 → motor ID 127 ---")
    print("    (also tries motor IDs 0, 1, 253, 254, 255)")
    found = []

    motor_ids = [127, 0, 1, 253, 254, 255]
    comm_types = list(range(32))

    for motor_id in motor_ids:
        for comm_type in comm_types:
            arb = (comm_type << 24) | (MASTER_ID << 8) | motor_id
            data = b'\x00' * 8
            bus.send(can.Message(arbitration_id=arb, data=data, is_extended_id=True))

            deadline = time.time() + 0.02
            while time.time() < deadline:
                msg = bus.recv(timeout=deadline - time.time())
                if msg and msg.is_extended_id:
                    a = msg.arbitration_id
                    found.append({
                        'sent_motor': motor_id, 'sent_comm': comm_type,
                        'recv_arb': a, 'recv_data': bytes(msg.data).hex()
                    })
                    print(f"  RESPONSE! sent motor={motor_id} comm_type=0x{comm_type:02X}"
                          f" → recv arb=0x{a:08X} data={bytes(msg.data).hex()}")

    if not found:
        print("  No responses to any command.")
        print()
        print("  Most likely cause: missing 120Ω termination resistor at motor end.")
        print("  RS02 firmware ≥ 0.2.3.9 removed the internal resistor.")
        print("  Fix: solder/clip a 120Ω resistor across CANH and CANL at motor connector.")
        print()
        print("  To verify: check 'ip -s link show can0' TX error count.")
        print("  If TXerr keeps climbing, bus is not properly terminated.")
    print()
    return found


def check_error_state():
    """Check whether the CAN controller is in BUS-OFF state."""
    print("--- CAN interface details ---")
    try:
        result = subprocess.run(
            ['ip', '-details', 'link', 'show', INTERFACE],
            capture_output=True, text=True)
        output = result.stdout
        print(output)
        if 'BUS-OFF' in output:
            print("  WARNING: Interface is in BUS-OFF state!")
            print("  Fix: sudo ip link set can0 down && sudo ip link set can0 up")
        elif 'ERROR-PASSIVE' in output:
            print("  WARNING: Interface is ERROR-PASSIVE (too many errors).")
        elif 'ERROR-ACTIVE' in output:
            print("  Interface is ERROR-ACTIVE (healthy).")
    except Exception as e:
        print(f"  (could not check: {e})")
    print()


def tx_count_before_after(bus):
    """Send 10 frames and check if TX count increases."""
    def get_tx_count():
        r = subprocess.run(['ip', '-s', 'link', 'show', INTERFACE],
                           capture_output=True, text=True)
        lines = r.stdout.split('\n')
        for i, line in enumerate(lines):
            if 'TX:' in line and 'bytes' in line:
                # Next line has the values: bytes packets errors dropped carrier collsns
                if i + 1 < len(lines):
                    parts = lines[i + 1].strip().split()
                    if len(parts) >= 2:
                        return int(parts[1])  # packets
        return -1

    before = get_tx_count()
    for _ in range(10):
        arb = (0x00 << 24) | (MASTER_ID << 8) | 127
        bus.send(can.Message(arbitration_id=arb, data=b'\x00'*8, is_extended_id=True))
    time.sleep(0.1)
    after = get_tx_count()

    print(f"--- TX packet count: before={before}  after={after}  delta={after - before} ---")
    if after - before >= 10:
        print("  TX is working — adapter is putting frames on the bus.")
    elif after == before == -1:
        print("  (could not read TX count)")
    else:
        print("  WARNING: TX count did not increase by 10. Adapter may not be transmitting.")
    print()


def main():
    print("=" * 60)
    print("RS02 CAN Diagnostic")
    print("=" * 60)
    print()

    check_error_state()

    bus = can.interface.Bus(channel=INTERFACE, interface='socketcan')

    try:
        loopback_test(bus)
        tx_count_before_after(bus)
        passive_listen(bus, seconds=2.0)
        brute_force_all_types(bus)
        print("--- Final stats ---")
        can_stats()
    finally:
        bus.shutdown()


if __name__ == '__main__':
    main()

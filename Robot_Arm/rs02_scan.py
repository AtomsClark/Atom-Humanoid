#!/usr/bin/env python3
"""
Scan all motor CAN IDs (0-127) and capture ALL raw CAN frames.
Run: python3 rs02_scan.py
"""
import can, struct, time

BUS = can.interface.Bus(channel='can0', interface='socketcan')
MASTER_ID = 0x00FD

def send(comm_type, motor_id, data=b'\x00'*8, data_area=MASTER_ID):
    arb = (comm_type << 24) | (data_area << 8) | motor_id
    BUS.send(can.Message(arbitration_id=arb, data=data, is_extended_id=True))

def recv_all(timeout=0.05):
    frames = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = BUS.recv(timeout=deadline - time.time())
        if msg:
            frames.append(msg)
    return frames

print("Listening for any unsolicited frames for 2s...")
BUS.set_filters([])  # accept everything
passive = recv_all(timeout=2.0)
if passive:
    for m in passive:
        print(f"  UNSOLICITED arb=0x{m.arbitration_id:08X} ext={m.is_extended_id} data={m.data.hex()}")
else:
    print("  (none)")

print()
print("Scanning motor IDs 0-127 with Type-0 query (250ms each)...")
print("Any response — regardless of source — will be shown.")

found = []
for motor_id in range(128):
    send(0x00, motor_id)
    frames = recv_all(timeout=0.05)
    for m in frames:
        arb = m.arbitration_id
        print(f"\n  *** RESPONSE to motor_id={motor_id} ***")
        print(f"      arb_id=0x{arb:08X}  ext={m.is_extended_id}")
        print(f"      comm_type={(arb>>24)&0x1F}  field_23_8={(arb>>8)&0xFFFF:#06x}  field_7_0={arb&0xFF:#04x}")
        print(f"      data: {bytes(m.data).hex()}")
        found.append(motor_id)

print()
if found:
    print(f"Motors found at CAN IDs: {found}")
else:
    print("No response to any motor ID query.")
    print()
    print("Trying Type-3 enable broadcast to IDs 0, 127, 0xFE, 0xFF...")
    for mid in [0, 1, 127, 0xFE, 0xFF]:
        send(0x03, mid & 0xFF)
        frames = recv_all(timeout=0.1)
        for m in frames:
            print(f"  *** Response to enable motor_id={mid}: arb=0x{m.arbitration_id:08X} data={bytes(m.data).hex()}")

    print()
    print("Final candump — any frames seen in 3s:")
    frames = recv_all(timeout=3.0)
    if frames:
        for m in frames:
            print(f"  arb=0x{m.arbitration_id:08X} ext={m.is_extended_id} data={bytes(m.data).hex()}")
    else:
        print("  (none) — motor may need power cycle or termination resistor at motor end")

BUS.shutdown()

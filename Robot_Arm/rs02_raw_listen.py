#!/usr/bin/env python3
"""
Listen for ALL CAN frames (standard + extended + error frames) while
repeatedly sending Type-0 detect to motor 127. No filtering whatsoever.

Run:  python3 rs02_raw_listen.py
"""
import can, time

INTERFACE = 'can0'
MASTER_ID = 0x00FD
MOTOR_ID  = 127

bus = can.interface.Bus(channel=INTERFACE, interface='socketcan')

print("Sending Type-0 detect every 100ms while listening for ANYTHING (10s)...")
print("This includes standard (11-bit) frames, extended (29-bit), and error frames.\n")

deadline = time.time() + 10.0
next_send = time.time()
sent = 0
received = 0

while time.time() < deadline:
    now = time.time()
    if now >= next_send:
        arb = (0x00 << 24) | (MASTER_ID << 8) | MOTOR_ID
        bus.send(can.Message(arbitration_id=arb, data=b'\x00'*8, is_extended_id=True))
        sent += 1
        next_send = now + 0.1

    msg = bus.recv(timeout=0.01)
    if msg is None:
        continue

    received += 1
    if msg.is_error_frame:
        print(f"  ERROR FRAME: {msg}")
    elif msg.is_remote_frame:
        print(f"  RTR frame: arb=0x{msg.arbitration_id:X} ext={msg.is_extended_id}")
    elif msg.is_extended_id:
        a = msg.arbitration_id
        comm = (a >> 24) & 0x1F
        data_area = (a >> 8) & 0xFFFF
        motor = a & 0xFF
        print(f"  EXT frame: arb=0x{a:08X} comm={comm} data_area=0x{data_area:04X} "
              f"motor={motor} data={bytes(msg.data).hex()}")
    else:
        print(f"  STD frame: arb=0x{msg.arbitration_id:03X} "
              f"data={bytes(msg.data).hex()}")

print(f"\nDone: sent={sent} received={received}")
bus.shutdown()

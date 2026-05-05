#!/usr/bin/env python3
"""
RS02 advanced scan — tries all 256 motor IDs, MIT control command,
CANopen NMT, and protocol-switch commands.

Key insight: motor is ACKing our frames (0 TX errors) but sending nothing back.
This means it's electrically present but either:
  - In wrong protocol mode (CANopen/MIT instead of RobStride private)
  - Motor ID is in range 128-255 (rs02_scan.py only tried 0-127)
  - Needs Type-1 MIT command to elicit a Type-2 feedback response
"""
import can, struct, time

INTERFACE = 'can0'
MASTER_ID = 0x00FD

bus = can.interface.Bus(channel=INTERFACE, interface='socketcan')
bus.set_filters([])


def send(comm_type, motor_id, data=b'\x00'*8, data_area=MASTER_ID):
    arb = (comm_type << 24) | ((data_area & 0xFFFF) << 8) | (motor_id & 0xFF)
    bus.send(can.Message(arbitration_id=arb, data=data, is_extended_id=True))


def recv_all(timeout=0.05):
    frames = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=deadline - time.time())
        if msg and msg.is_extended_id:
            frames.append(msg)
    return frames


def report(frames, context):
    for m in frames:
        a = m.arbitration_id
        print(f"  *** RESPONSE [{context}] arb=0x{a:08X} "
              f"comm={(a>>24)&0x1F}  motor={(a>>8)&0xFF}  "
              f"data={bytes(m.data).hex()}")


# ── 1. Full ID sweep with Type-0 (128-255 — range not covered by rs02_scan.py)
print("=== Full ID sweep: Type-0 to motor IDs 128-255 ===")
found = []
for mid in range(128, 256):
    send(0x00, mid)
    frames = recv_all(0.03)
    if frames:
        found.append(mid)
        report(frames, f"Type-0 motor={mid}")
print(f"  Found: {found}" if found else "  No response in range 128-255")
print()

# ── 2. Broadcast with motor_id=0xFF (all-nodes query)
print("=== Broadcast Type-0/3/4 with motor_id=0xFF ===")
for ct, name in [(0x00, 'detect'), (0x03, 'enable'), (0x04, 'stop')]:
    send(ct, 0xFF)
    frames = recv_all(0.1)
    if frames:
        report(frames, f"{name} broadcast")
    else:
        print(f"  No response to {name} broadcast (motor_id=0xFF)")
print()

# ── 3. Type-1 MIT control command to motor 127
# Motor in operation mode should respond with Type-2 feedback when it receives a Type-1
print("=== Type-1 MIT control to motor 127 (kp=0, kd=0 — zero torque) ===")
# pos=0, vel=0, kp=0, kd=0, torque_ff=0  (all mid-scale = 0x8000)
# with all zeros: pos=P_MIN, vel=V_MIN — use 0x8000 for zero
mid16 = 0x8000
zero_torque = 0x8000
data = struct.pack('>HHHH', mid16, mid16, 0, 0)  # pos, vel, kp=0, kd=0
arb = (0x01 << 24) | (zero_torque << 8) | 127
bus.send(can.Message(arbitration_id=arb, data=data, is_extended_id=True))
frames = recv_all(0.2)
if frames:
    report(frames, "Type-1 MIT motor=127")
else:
    print("  No response to Type-1 MIT command (motor 127)")
print()

# ── 4. Try Type-1 with Kp/Kd for soft hold (sometimes needed to unlock feedback)
print("=== Type-1 MIT soft-hold to motor 127 (Kp=5, Kd=0.5) ===")
P_MIN, P_MAX = -12.57, 12.57
V_MIN, V_MAX = -44.0, 44.0
KP_MIN, KP_MAX = 0.0, 500.0
KD_MIN, KD_MAX = 0.0, 5.0
T_MIN, T_MAX = -17.0, 17.0

def f2u(x, xmin, xmax, bits=16):
    return int((max(xmin, min(xmax, x)) - xmin) / (xmax - xmin) * ((1<<bits)-1))

pos_i = f2u(0.0, P_MIN, P_MAX)
vel_i = f2u(0.0, V_MIN, V_MAX)
kp_i  = f2u(5.0, KP_MIN, KP_MAX)
kd_i  = f2u(0.5, KD_MIN, KD_MAX)
trq_i = f2u(0.0, T_MIN, T_MAX)
data = struct.pack('>HHHH', pos_i, vel_i, kp_i, kd_i)
arb = (0x01 << 24) | (trq_i << 8) | 127
for _ in range(5):
    bus.send(can.Message(arbitration_id=arb, data=data, is_extended_id=True))
    time.sleep(0.02)
frames = recv_all(0.2)
if frames:
    report(frames, "Type-1 soft-hold motor=127")
else:
    print("  No response to Type-1 soft-hold (motor 127)")
print()

# ── 5. CANopen NMT start (in case motor booted in CANopen mode)
# NMT start-node broadcast: CAN ID=0x000, data=[0x01, 0x00]
# Then NMT for specific node IDs
print("=== CANopen NMT start broadcast (in case motor is in CANopen mode) ===")
nmt_start = can.Message(arbitration_id=0x000, data=bytes([0x01, 0x00]),
                        is_extended_id=False)
bus.send(nmt_start)
frames = recv_all(0.2)
if frames:
    report(frames, "CANopen NMT start broadcast")
else:
    print("  No response to CANopen NMT start broadcast")

# NMT reset for node 127
nmt_reset = can.Message(arbitration_id=0x000, data=bytes([0x82, 127]),
                        is_extended_id=False)
bus.send(nmt_reset)
frames = recv_all(0.2)
if frames:
    report(frames, "CANopen NMT reset node=127")
else:
    print("  No response to CANopen NMT reset (node 127)")
print()

# ── 6. Protocol switch command (Type 0x19 = 25): switch to private protocol
# If motor is in CANopen/MIT mode, this tells it to switch back to private
print("=== Protocol-switch (Type 0x19) → private mode to all IDs ===")
found = []
for mid in [127, 0xFF, 0, 1]:
    data = struct.pack('<B', 0) + b'\x00'*7  # mode=0 (private)
    send(0x19, mid, data)
    frames = recv_all(0.1)
    if frames:
        found.append(mid)
        report(frames, f"proto-switch motor={mid}")
if not found:
    print("  No response to protocol-switch commands")
print()

# ── 7. After all that: listen for 3 seconds for anything
print("=== Final passive listen — 3 seconds ===")
all_frames = recv_all(3.0)
if all_frames:
    for m in all_frames:
        a = m.arbitration_id
        print(f"  arb=0x{a:08X} comm={(a>>24)&0x1F} data={bytes(m.data).hex()}")
else:
    print("  Still nothing.")
    print()
    print("  Recommendation: power-cycle the motor (disconnect 24V, wait 5s, reconnect).")
    print("  If still silent after power cycle, try adding 120Ω resistor at motor connector")
    print("  even though TX errors are 0 — the motor may be receiving but its TX output")
    print("  is too weak without proper termination to be detected by the adapter.")

bus.shutdown()

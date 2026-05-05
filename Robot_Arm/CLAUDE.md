# CLAUDE.md — Robot_Arm/

This file provides guidance to Claude Code when working in this subdirectory.

## Hardware

- **Motor**: RS02 (RobStride) — 17 Nm peak, 6 Nm rated, 7.75:1 reduction, FOC, 24–60 VDC
- **CAN adapter**: Native SocketCAN device → `can0` (NOT `/dev/ttyUSB0`)
- **USB opto-isolator** in use. CAN-side GND **must** be connected to motor V- / power supply GND.
- **Termination**: DIP switch 2 ON = 120Ω at adapter end. Motor FW ≥ 0.2.3.9 has no internal resistor — add external 120Ω at motor connector.
- **Motor connector**: 4-pin daisy-chain. Thick red/black = V+/V-. Thin red = CANH, thin black = CANL.

## CAN interface setup (once per boot)

```bash
sudo ip link set can0 down
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up
```

## Scripts

| Script | Purpose |
|--------|---------|
| `rs02_motor.py` | Main driver — detect, velocity, position, current, demo, stop |
| `rs02_diag.py` | Bus health check — loopback test, TX counter, brute-force scan |
| `rs02_scan.py` | Scan motor IDs 0-127 with Type-0 |
| `rs02_scan2.py` | Extended scan — IDs 128-255, MIT control, CANopen NMT, proto-switch |
| `rs02_raw_listen.py` | Listen for ALL frames (standard + extended + error) while sending |

```bash
python3 rs02_motor.py detect
python3 rs02_motor.py velocity 2.0     # rad/s, Enter to stop
python3 rs02_motor.py position 1.5708  # rad
python3 rs02_motor.py demo             # MIT hold-zero (Kp=20, Kd=1)
python3 rs02_motor.py stop
```

## CAN protocol (private RobStride)

`arbitration_id = (comm_type << 24) | (data_area << 8) | motor_id`

| Type | Dir | Purpose |
|------|-----|---------|
| 0 | TX | Get device ID |
| 1 | TX | MIT control — pos/vel/Kp/Kd in data, torque_ff in ID bits 23~8 |
| 2 | RX | Feedback — angle/vel/torque/temp; motor_id in ID bits 15~8 |
| 3 | TX | Enable |
| 4 | TX | Stop (data[0]=1 clears fault) |
| 6 | TX | Set mechanical zero |
| 17 | TX | Read parameter |
| 18 | TX | Write parameter |

**Type 1 ranges**: pos ±4π rad, vel ±44 rad/s, Kp 0–500, Kd 0–5, torque ±17 Nm (all 16-bit unsigned)

**Key parameter indices**: `0x7005` run_mode, `0x700A` spd_ref, `0x7016` loc_ref, `0x7006` iq_ref, `0x700B` limit_torque

**Mode switch sequence**: `set_mode()` → `enable()` → commands → `stop()`. Never switch mode while running.

**Motor defaults**: CAN ID = 127. Factory protocol = private. Default state = operation control (MIT PD+FF).

## LED indicators (power-on)

- Solid red + slow blink = motor alive, **no CAN bus detected**
- Fault bit 7 in Type-2 feedback = encoder uncalibrated (normal for new motor)

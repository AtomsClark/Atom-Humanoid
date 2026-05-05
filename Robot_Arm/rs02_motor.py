#!/usr/bin/env python3
"""
RS02 CAN motor controller via SocketCAN (python-can).

Setup (one-time per boot, or add to /etc/network/interfaces):
    sudo ip link set can0 down
    sudo ip link set can0 type can bitrate 1000000
    sudo ip link set can0 up

CAN arbitration ID (29-bit extended frame):
    bits 28~24 : communication type
    bits 23~8  : data area (master_id for most commands; torque for Type 1)
    bits  7~0  : target motor CAN ID

Default motor CAN ID : 127 (0x7F)
Default host CAN ID  : 253 (0xFD)

Usage:
  python3 rs02_motor.py detect
  python3 rs02_motor.py enable
  python3 rs02_motor.py stop
  python3 rs02_motor.py velocity 2.0        # rad/s
  python3 rs02_motor.py position 1.5708     # rad (~90°)
  python3 rs02_motor.py current 1.0         # amps
  python3 rs02_motor.py zero                # set mechanical zero (careful!)
  python3 rs02_motor.py demo                # MIT impedance hold-zero demo

Options:
  --interface can0   SocketCAN interface (default: can0)
  --motor-id 127     CAN ID of target motor (default: 127)
"""

import argparse
import struct
import time
from typing import Optional

import can

INTERFACE    = 'can0'
MASTER_ID    = 0x00FD   # host CAN ID used in data-area field
DEFAULT_MOTOR_ID = 127  # factory default

# RS02 physical ranges for Type-1 (operation control) encoding
P_MIN, P_MAX = -12.57, 12.57    # rad  (±4π)
V_MIN, V_MAX = -44.0,  44.0     # rad/s
T_MIN, T_MAX = -17.0,  17.0     # Nm
KP_MIN, KP_MAX = 0.0,  500.0
KD_MIN, KD_MAX = 0.0,  5.0

# Parameter register indices for Type-17 read / Type-18 write
IDX_RUN_MODE  = 0x7005
IDX_IQ_REF    = 0x7006
IDX_SPD_REF   = 0x700A
IDX_LIMIT_TRQ = 0x700B
IDX_LOC_REF   = 0x7016
IDX_LIMIT_SPD = 0x7017
IDX_LIMIT_CUR = 0x7018

# run_mode values (index 0x7005)
MODE_OPERATION    = 0   # MIT-style PD+FF (power-on default)
MODE_POSITION_PP  = 1   # Profile Position
MODE_VELOCITY     = 2   # Velocity
MODE_CURRENT      = 3   # Current (iq)
MODE_POSITION_CSP = 5   # Cyclic Synchronous Position


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

def _float_to_uint(x: float, x_min: float, x_max: float, bits: int) -> int:
    x = max(x_min, min(x_max, x))
    return int((x - x_min) / (x_max - x_min) * ((1 << bits) - 1))


def _uint_to_float(x: int, x_min: float, x_max: float, bits: int) -> float:
    return x * (x_max - x_min) / ((1 << bits) - 1) + x_min


def _arb_id(comm_type: int, motor_id: int, data_area: int = MASTER_ID) -> int:
    return (comm_type << 24) | ((data_area & 0xFFFF) << 8) | (motor_id & 0xFF)


def _make_msg(comm_type: int, motor_id: int, data: bytes,
              data_area: int = MASTER_ID) -> can.Message:
    payload = (data + b'\x00' * 8)[:8]
    return can.Message(
        arbitration_id=_arb_id(comm_type, motor_id, data_area),
        data=payload,
        is_extended_id=True,
    )


# ---------------------------------------------------------------------------
# Feedback frame parser
# ---------------------------------------------------------------------------

def _parse_feedback(msg: can.Message) -> dict:
    """
    Parse a Type-2 motor feedback CAN frame.
    Returns dict: motor_id, comm_type, mode_status, fault,
                  angle (rad), velocity (rad/s), torque (Nm), temperature (°C).
    """
    arb     = msg.arbitration_id
    comm_type   = (arb >> 24) & 0x1F
    mode_status = (arb >> 22) & 0x03   # 0=reset, 1=calibration, 2=running
    fault       = (arb >> 16) & 0x3F   # 6 fault bits (0 = healthy)
    motor_id    = (arb >>  8) & 0xFF
    d = bytes(msg.data)

    angle_raw  = (d[0] << 8) | d[1]
    vel_raw    = (d[2] << 8) | d[3]
    torque_raw = (d[4] << 8) | d[5]
    temp_raw   = (d[6] << 8) | d[7]   # big-endian, units 0.1 °C

    return {
        'motor_id':    motor_id,
        'comm_type':   comm_type,
        'mode_status': mode_status,
        'fault':       fault,
        'angle':       _uint_to_float(angle_raw,  P_MIN, P_MAX, 16),
        'velocity':    _uint_to_float(vel_raw,    V_MIN, V_MAX, 16),
        'torque':      _uint_to_float(torque_raw, T_MIN, T_MAX, 16),
        'temperature': temp_raw / 10.0,
    }


# ---------------------------------------------------------------------------
# Motor class
# ---------------------------------------------------------------------------

class RS02Motor:
    """
    Driver for a single RS02 motor over SocketCAN.

    Typical velocity-control startup:
        m = RS02Motor('can0')
        m.detect()
        m.set_mode(MODE_VELOCITY)
        m.enable()
        m.set_velocity(2.0)   # rad/s
        ...
        m.stop()
        m.close()

    Mode changes MUST happen before enable(). Do not switch modes while running.
    """

    def __init__(self, interface: str = INTERFACE,
                 motor_id: int = DEFAULT_MOTOR_ID):
        self.motor_id = motor_id
        self.bus = can.interface.Bus(channel=interface, interface='socketcan')

    def close(self):
        try:
            self.stop()
        except Exception:
            pass
        self.bus.shutdown()

    # ------------------------------------------------------------------
    # Low-level send / receive
    # ------------------------------------------------------------------

    def _send(self, comm_type: int, data: bytes = b'',
              data_area: int = MASTER_ID) -> None:
        self.bus.send(_make_msg(comm_type, self.motor_id, data, data_area))

    def _recv(self, timeout: float = 0.1) -> Optional[dict]:
        """Wait for a CAN frame from this motor, return parsed feedback or None."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = deadline - time.time()
            msg = self.bus.recv(timeout=remaining)
            if msg is None:
                break
            if not msg.is_extended_id:
                continue
            src_motor = (msg.arbitration_id >> 8) & 0xFF
            if src_motor == self.motor_id:
                return _parse_feedback(msg)
        return None

    # ------------------------------------------------------------------
    # Command API
    # ------------------------------------------------------------------

    def detect(self) -> Optional[dict]:
        """Type 0: broadcast query — returns device ID."""
        self._send(0x00)
        return self._recv(timeout=0.2)

    def enable(self) -> Optional[dict]:
        """Type 3: enable motor (enter run state)."""
        self._send(0x03)
        return self._recv()

    def stop(self) -> Optional[dict]:
        """Type 4: stop motor (disable torque output)."""
        self._send(0x04)
        return self._recv()

    def clear_fault(self) -> Optional[dict]:
        """Type 4 with Byte[0]=1: clear active fault then stop."""
        self._send(0x04, bytes([1, 0, 0, 0, 0, 0, 0, 0]))
        return self._recv()

    def set_zero(self) -> Optional[dict]:
        """Type 6: set current shaft position as mechanical zero (saved to flash)."""
        self._send(0x06, bytes([1, 0, 0, 0, 0, 0, 0, 0]))
        return self._recv()

    def set_mode(self, mode: int) -> None:
        """
        Write run_mode (index 0x7005) via Type 18.
        Must be called while motor is stopped.

        mode: MODE_OPERATION=0, MODE_POSITION_PP=1, MODE_VELOCITY=2,
              MODE_CURRENT=3, MODE_POSITION_CSP=5
        """
        self._write_param(IDX_RUN_MODE, struct.pack('<B', mode))

    def operation_control(self, position: float, velocity: float,
                          torque_ff: float, kp: float, kd: float) -> Optional[dict]:
        """
        Type 1: MIT-style impedance control.
        t_ref = Kd*(v_set - v_actual) + Kp*(p_set - p_actual) + t_ff

        Units: position [rad], velocity [rad/s], torque [Nm],
               Kp [Nm/rad] (0–500), Kd [Nm·s/rad] (0–5).

        Hold position:  kp=20~50, kd=1~2, velocity=0, torque_ff=0
        Free spin:      kp=0, kd=1~2, v_set=target_speed, torque_ff=0
        Pure damping:   kp=0, kd=1~5, position=0, velocity=0, torque_ff=0
        """
        pos_int = _float_to_uint(position,  P_MIN,  P_MAX,  16)
        vel_int = _float_to_uint(velocity,  V_MIN,  V_MAX,  16)
        kp_int  = _float_to_uint(kp,        KP_MIN, KP_MAX, 16)
        kd_int  = _float_to_uint(kd,        KD_MIN, KD_MAX, 16)
        trq_int = _float_to_uint(torque_ff, T_MIN,  T_MAX,  16)

        data = bytes([
            pos_int >> 8, pos_int & 0xFF,
            vel_int >> 8, vel_int & 0xFF,
            kp_int  >> 8, kp_int  & 0xFF,
            kd_int  >> 8, kd_int  & 0xFF,
        ])
        # torque feedforward goes in CAN ID data-area field (bits 23~8)
        arb = (0x01 << 24) | (trq_int << 8) | self.motor_id
        msg = can.Message(arbitration_id=arb, data=data, is_extended_id=True)
        self.bus.send(msg)
        return self._recv()

    def set_velocity(self, vel_rad_s: float) -> None:
        """Write spd_ref. Requires set_mode(MODE_VELOCITY) + enable() first."""
        self._write_param(IDX_SPD_REF, struct.pack('<f', vel_rad_s))

    def set_position(self, pos_rad: float) -> None:
        """Write loc_ref. Requires set_mode(MODE_POSITION_CSP) + enable() first."""
        self._write_param(IDX_LOC_REF, struct.pack('<f', pos_rad))

    def set_current(self, iq_amps: float) -> None:
        """Write iq_ref. Requires set_mode(MODE_CURRENT) + enable() first."""
        self._write_param(IDX_IQ_REF, struct.pack('<f', iq_amps))

    def set_torque_limit(self, limit_nm: float) -> None:
        """Write limit_torque (0–14 Nm)."""
        self._write_param(IDX_LIMIT_TRQ, struct.pack('<f', limit_nm))

    def enable_active_reporting(self, enable: bool = True) -> None:
        """
        Type 24: toggle 10ms active status reporting.
        When enabled the motor pushes Type-2 feedback without being polled.
        """
        cmd = 0x01 if enable else 0x00
        self._send(0x18, bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, cmd, 0x00]))

    def read_feedback(self, timeout: float = 0.05) -> Optional[dict]:
        """Read one feedback frame (use after enable_active_reporting)."""
        return self._recv(timeout=timeout)

    def read_param_raw(self, index: int) -> Optional[bytes]:
        """
        Type 17: read a single parameter. Returns 4 raw value bytes or None.
        Example: struct.unpack('<f', motor.read_param_raw(IDX_SPD_REF))[0]
        """
        data = struct.pack('<H', index) + b'\x00' * 6
        self._send(0x11, data)
        # Response is also a CAN frame; just grab the next one
        deadline = time.time() + 0.1
        while time.time() < deadline:
            msg = self.bus.recv(timeout=0.1)
            if msg and msg.is_extended_id:
                src = (msg.arbitration_id >> 8) & 0xFF
                if src == self.motor_id:
                    return bytes(msg.data)[4:8]
        return None

    def _write_param(self, index: int, value_bytes: bytes) -> None:
        """
        Type 18: write parameter at index.
        Data layout: [index uint16 LE] [0x00 0x00] [value, up to 4 bytes LE]
        """
        idx_bytes = struct.pack('<H', index)
        padded = (value_bytes + b'\x00' * 4)[:4]
        self._send(0x12, idx_bytes + b'\x00\x00' + padded)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description='RS02 motor controller (SocketCAN)')
    ap.add_argument('--interface', default=INTERFACE)
    ap.add_argument('--motor-id',  type=int, default=DEFAULT_MOTOR_ID)
    ap.add_argument('command',
                    choices=['detect', 'enable', 'stop', 'zero',
                             'velocity', 'position', 'current', 'demo'])
    ap.add_argument('value', type=float, nargs='?', default=0.0)
    args = ap.parse_args()

    motor = RS02Motor(args.interface, args.motor_id)
    print(f"Opened {args.interface}  motor_id={args.motor_id}")

    try:
        if args.command == 'detect':
            print("Querying motor...")
            fb = motor.detect()
            if fb:
                fault_str = f"FAULT=0x{fb['fault']:02X}" if fb['fault'] else "healthy"
                print(f"  Motor {fb['motor_id']}: "
                      f"angle={fb['angle']:.3f} rad  "
                      f"temp={fb['temperature']:.1f}°C  {fault_str}")
            else:
                print("  No response. Check:")
                print("  - can0 bitrate set to 1Mbps?  (sudo ip link set can0 type can bitrate 1000000)")
                print("  - Motor powered (24V)?")
                print("  - CANH/CANL connected and not swapped?")
                print("  - DIP switch 1 OFF, switch 2 ON (120Ω termination)")
                print("  - New RS02 (FW ≥0.2.3.9) has no internal resistor —")
                print("    add 120Ω across CANH–CANL at the motor end")

        elif args.command == 'enable':
            fb = motor.enable()
            print(f"Enable response: {fb}")

        elif args.command == 'stop':
            fb = motor.stop()
            print(f"Stop response: {fb}")

        elif args.command == 'zero':
            confirm = input("Set mechanical zero at current position? Saves to flash. [y/N] ")
            if confirm.strip().lower() == 'y':
                fb = motor.set_zero()
                print(f"Zero set: {fb}")
            else:
                print("Aborted.")

        elif args.command == 'velocity':
            print(f"Velocity mode: {args.value:.3f} rad/s  (Enter to stop)")
            motor.set_mode(MODE_VELOCITY)
            time.sleep(0.05)
            motor.enable()
            time.sleep(0.05)
            motor.set_velocity(args.value)
            input()
            motor.stop()

        elif args.command == 'position':
            print(f"CSP position: target {args.value:.4f} rad")
            motor.set_mode(MODE_POSITION_CSP)
            time.sleep(0.05)
            motor.enable()
            time.sleep(0.05)
            motor.set_position(args.value)
            time.sleep(2.0)
            fb = motor._recv()
            if fb:
                print(f"  Final: angle={fb['angle']:.4f} rad")
            motor.stop()

        elif args.command == 'current':
            print(f"Current mode: {args.value:.3f} A  (Enter to stop)")
            motor.set_mode(MODE_CURRENT)
            time.sleep(0.05)
            motor.enable()
            time.sleep(0.05)
            motor.set_current(args.value)
            input()
            motor.stop()

        elif args.command == 'demo':
            print("MIT hold-zero demo: Kp=20, Kd=1  (Ctrl+C to stop)")
            motor.enable()
            time.sleep(0.05)
            try:
                while True:
                    fb = motor.operation_control(
                        position=0.0, velocity=0.0, torque_ff=0.0,
                        kp=20.0, kd=1.0)
                    if fb:
                        fault_str = f"FAULT=0x{fb['fault']:02X}" if fb['fault'] else "ok"
                        print(f"\r  pos={fb['angle']:+7.3f} rad  "
                              f"vel={fb['velocity']:+7.3f} rad/s  "
                              f"trq={fb['torque']:+6.2f} Nm  "
                              f"T={fb['temperature']:5.1f}°C  {fault_str}    ",
                              end='', flush=True)
                    time.sleep(0.01)
            except KeyboardInterrupt:
                print()
            motor.stop()

    finally:
        motor.close()


if __name__ == '__main__':
    main()

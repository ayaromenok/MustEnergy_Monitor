#!/usr/bin/env python3
"""
MustEnergyMonitor.py — RS485 / Modbus-RTU serial port functionality for the PowerMonitor
inverter + solar-charger units.

Protocol:
  * RS485, 19200 baud, 8N1, RTS enabled
  * Modbus RTU: function 03 (read holding registers), 16 (write multiple)
  * CRC16-Modbus, low byte first (verified against the probe frame
    "04 03 4E 21 00 05 C2 BE")

Register map (charger and inverter share the same slave address on the bus):
  charger id    03 27 11 00 0A   10 regs  identity / versions / raw hex values
  charger id    03 27 75 00 0C   12 regs  charger settings
  charger id    03 3B 61 00 15   21 regs  charger status
  inverter id   03 4E 21 00 10   16 regs  inverter identity / versions
  inverter id   03 4E 85 00 2B   43 regs  inverter settings
  inverter id   03 62 71 00 4A   74 regs  inverter real-time data

Usage:
  .venv/bin/python MustEnergyMonitor.py list
  .venv/bin/python MustEnergyMonitor.py scan [-p /dev/ttyUSB0]
  .venv/bin/python MustEnergyMonitor.py read    -p /dev/ttyUSB0
  .venv/bin/python MustEnergyMonitor.py monitor -p /dev/ttyUSB0 --interval 3
  .venv/bin/python MustEnergyMonitor.py write   -p /dev/ttyUSB0 "04 10 4E F6 00 01 02 00 01"
  .venv/bin/python MustEnergyMonitor.py write   -p /dev/ttyUSB0 --reset-params --inverter-id 4
  .venv/bin/python MustEnergyMonitor.py write   -p /dev/ttyUSB0 --remove-data  --inverter-id 4

  add -v to any command for debug logging (raw TX/RX hex frames).
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from dataclasses import dataclass, field, fields
from typing import Optional

try:
    import serial
    import serial.tools.list_ports
except ImportError:  # pragma: no cover
    sys.exit("pyserial is required:  .venv/bin/pip install pyserial")

log = logging.getLogger("rs485")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SP_BAUD_RATE = 19200          # serial baud rate
FAIL_TIMES = 2                # consecutive failed polls before a rescan
PORT_SCAN_STR = "04 03 4E 21 00 05"   # scan probe (without CRC)
SCAN_PROBE_ADDR = 0x04
SCAN_PROBE_REG = 0x4E21
SCAN_PROBE_COUNT = 5
MAX_LOOP = 20                 # 100 ms polling steps for a receive timeout

# Register blocks: (start register, count)
BLOCK_CHARGER_ID    = (0x2711, 10)   # identity / versions
BLOCK_CHARGER_SET   = (0x2775, 12)   # charger settings
BLOCK_CHARGER_STAT  = (0x3B61, 21)   # charger status
BLOCK_INVERTER_ID   = (0x4E21, 16)   # inverter identity / versions
BLOCK_INVERTER_SET  = (0x4E85, 43)   # inverter settings
BLOCK_INVERTER_STAT = (0x6271, 74)   # inverter real-time data

MACHINE_TYPES = (1000, 1600, 1800, 3000, 3500)

# ---------------------------------------------------------------------------
# State / fault name tables
# ---------------------------------------------------------------------------

CHARGER_WORK_ENABLE = ["OFF", "ON"]
BATTERY_TYPE = ["", "Use defined battery", "Lithium battery",
                "SEALED_LEAD battery", "AGM battery", "GEL battery", "FLOODED battery"]
CHARGER_WORKSTATE = ["Initialization mode", "Selftest Mode", "Work Mode", "Stop Mode"]
MPPT_STATE = ["Stop", "MPPT", "Current limiting"]
CHARGING_STATE = ["Stop", "Absorb charge", "Float charge"]
CONNECT_STATES = ["Disconnect", "Connect"]
ENERGY_USE_MODE = ["", "SBU", "SUB", "UTI", "SOL"]
GRID_PROTECT_STANDARD = ["VDE4105", "UPS", "Home", "GEN"]
SOLAR_USE_AIM = ["LBU", "BLU"]
SYSTEM_SETTING_BIT = ["OverLoadRestartForbid", "OverTempRestartForbid",
                      "OverLoadBypassForbid", "AutoTurnPageFlagForbid",
                      "GridBuzzEnable(only use by PV1800)", "BuzzForbide(only use by PV1800)",
                      "LcdLightEnable", "RecordFaultForbid"] + [""] * 8
CHARGER_SOURCE_PRIORITY = ["Soalr first", "", "Solar and Utility(default)", "Only Solar"]
WORK_STATE = ["PowerOn", "SelfTest", "OffGrid", "Grid-Tie", "ByPass", "Stop", "Grid charging"]
INVERTER_ERROR1 = [
    "Fan is locked when inverter is off", "Inverter transformer over temperature",
    "battery voltage is too high", "battery voltage is too low", "Output short circuited",
    "Inverter output voltage is high", "Overload time out",
    "Inverter bus voltage is too high", "Bus soft start failed", "Main relay failed",
    "Inverter output voltage sensor error", "Inverter grid voltage sensor error",
    "Inverter output current sensor error", "Inverter grid current sensor error",
    "Inverter load current sensor error", "Inverter grid over current error"]
INVERTER_ERROR2 = [
    "Inverter radiator over temperature", "Solar charger battery voltage class error",
    "Solar charger current sensor error", "Solar charger current is uncontrollable",
    "Inverter grid voltage is low", "Inverter grid voltage is high",
    "Inverter grid under frequency", "Inverter grid over frequency",
    "Inverter over current protection error", "Inverter bus voltage is too low",
    "Inverter soft start failed", "Over DC voltage in AC output",
    "Battery connection is open", "Inverter control current sensor error",
    "Inverter output voltage is too low", ""]
INVERTER_WARNING = [
    "Fan is locked when inverter is on.", "Fan2 is locked when inverter is on.",
    "Battery is over-charged.", "Low battery", "Overload", "Output power derating",
    "Solar charger stops due to low battery.", "Solar charger stops due to high PV voltage.",
    "Solar charger stops due to over load.", "Solar charger over temperature",
    "PV charger communication error", "", "", "", "", "", ""]
CHARGER_ERROR = ["Hardware protection", "Over current", "Current sensor error",
                 "Over temperature", "PV voltage is too high", "",
                 "Battery voltage is too high", "Battery voltage is too Low",
                 "Current is uncontrollable", "Parameter error", "", "", "", "", "", ""]
CHARGER_WARNING = ["Fan Error"] + [""] * 15


# ---------------------------------------------------------------------------
# Modbus helpers
# ---------------------------------------------------------------------------

def modbus_crc16(data: bytes) -> int:
    """Standard Modbus CRC16 (poly 0xA001, init 0xFFFF)."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def hex_to_bytes(hexstr: str) -> bytes:
    """Convert a space-separated hex string to bytes: '04 03 4E 21' -> b'\\x04\\x03...'"""
    data = bytes.fromhex(re.sub(r"\s+", "", hexstr))
    return data


def add_crc(hexstr: str) -> str:
    """Append Modbus CRC (lo, hi) to a hex string."""
    data = hex_to_bytes(hexstr)
    crc = modbus_crc16(data)
    return f"{hexstr.rstrip().upper()} {crc & 0xFF:02X} {crc >> 8:02X}"


def build_read_frame(addr: int, start_reg: int, count: int) -> bytes:
    """Modbus function 03 request with CRC, e.g. b'04 03 27 11 00 0A 9F 29'."""
    data = bytes([addr, 0x03, start_reg >> 8, start_reg & 0xFF,
                  count >> 8, count & 0xFF])
    crc = modbus_crc16(data)
    return data + bytes([crc & 0xFF, crc >> 8])


def parse_response(frame: bytes, addr: int, count: int) -> Optional[list[int]]:
    """
    Parse a Modbus-03 response into `count` 16-bit big-endian registers.
    Returns None on any protocol error (logged).
    """
    expected = 5 + 2 * count
    if len(frame) < expected:
        log.warning("response too short: got %d bytes, expected %d (%s)",
                    len(frame), expected, " ".join(f"{b:02X}" for b in frame))
        return None
    if frame[0] != addr:
        log.warning("response slave id mismatch: got 0x%02X, expected 0x%02X", frame[0], addr)
        return None
    if frame[1] & 0x80:
        code = frame[3] if len(frame) > 3 else -1
        log.error("Modbus exception from slave 0x%02X: func=0x%02X code=%d",
                  frame[0], frame[1], code)
        return None
    if frame[1] != 0x03:
        log.warning("unexpected function code 0x%02X", frame[1])
        return None
    if frame[2] != 2 * count:
        log.warning("byte count mismatch: got %d, expected %d", frame[2], 2 * count)
        return None
    if modbus_crc16(frame[:-2]) != (frame[-2] | (frame[-1] << 8)):
        log.warning("response CRC mismatch (%s)",
                    " ".join(f"{b:02X}" for b in frame))
        return None
    return [int.from_bytes(frame[3 + 2 * i:5 + 2 * i], "big") for i in range(count)]


def s16(v: int) -> int:
    """Convert an unsigned 16-bit register value to signed."""
    return v - 65536 if v > 0x7FFF else v


def get_value(v: int, table: list[str]) -> str:
    """Table lookup with an out-of-range message."""
    if 0 <= v < len(table):
        return table[v]
    return f"Results are out of range[0-{len(table) - 1}].{v}"


def analyze_bit_message(reg: int, names: list[str]) -> str:
    """Expand a 16-bit fault bitmask to a list of active fault names."""
    active = [names[i] for i in range(16) if names[i] and (reg >> i) & 1]
    return "; ".join(active)


def format_version(reg: int) -> str:
    """Format a version register: 12345 -> '1.23.45', 0 -> '1.00.00'."""
    if reg == 0:
        return "1.00.00"
    s = str(reg)
    s = s[:3] + "." + s[3:]      # Insert(3, ".")
    s = s[:1] + "." + s[1:]      # Insert(1, ".")
    return s


def num_from_string(text: str) -> Optional[float]:
    """Extract the first number from a formatted value like '14.2 V' / '-3 W'."""
    m = re.search(r"-?\d+(?:\.\d+)?", text or "")
    return float(m.group()) if m else None


def machine_type_name(mt: int, charger_sw_version: int) -> str:
    """Map a machine-type register to a model name (1800 uses charger SW version)."""
    if mt == 1600:
        return "PC1600"
    if mt == 1800:
        return "PV1800" if charger_sw_version > 20000 else "PH1800"
    if mt == 3000:
        return "PH3000"
    if mt == 3500:
        return "PV3500"
    return ""


# ---------------------------------------------------------------------------
# Device data model
# ---------------------------------------------------------------------------

@dataclass
class DeviceData:
    charger_id: int = 0
    inverter_id: int = 0
    # charger identity (0x2711)
    machine_type: str = ""
    serial_number: str = ""
    hardware_version: str = ""
    software_version: str = ""
    pv_voltage_c: str = ""          # raw hex register value
    battery_voltage_c: str = ""
    charger_current_c: str = ""
    # charger settings (0x2775)
    charger_work_enable: str = ""
    absorb_voltage: str = ""
    float_voltage: str = ""
    absorption_voltage: str = ""
    battery_low_voltage: str = ""
    battery_high_voltage: str = ""
    max_charger_current: str = ""
    absorb_charger_current: str = ""
    battery_type: str = ""
    battery_ah: str = ""
    remove_the_accumulated_data: str = ""
    # charger status (0x3B61)
    charger_workstate: str = ""
    mppt_state: str = ""
    charging_state: str = ""
    pv_voltage: str = ""
    battery_voltage: str = ""
    charger_current: str = ""
    charger_power: str = ""
    radiator_temperature: str = ""
    external_temperature: str = ""
    battery_relay: str = ""
    pv_relay: str = ""
    error_message: str = ""
    warning_message: str = ""
    batt_vol_grade: str = ""
    rated_current: str = ""
    accumulated_power: str = ""
    accumulated_time: str = ""
    # inverter identity (0x4E21)
    inverter_machine_type: str = ""
    inverter_serial_number: str = ""
    inverter_hardware_version: str = ""
    inverter_software_version: str = ""
    inverter_battery_voltage_c: str = ""
    inverter_voltage_c: str = ""
    grid_voltage_c: str = ""
    bus_voltage_c: str = ""
    control_current_c: str = ""
    inverter_current_c: str = ""
    grid_current_c: str = ""
    load_current_c: str = ""
    # inverter settings (0x4E85)
    inverter_offgrid_work_enable: str = ""
    inverter_output_voltage_set: str = ""
    inverter_output_frequency_set: str = ""
    inverter_search_mode_enable: str = ""
    inverter_discharger_to_grid_enable: str = ""
    energy_use_mode: str = ""
    grid_protect_standard: str = ""
    solar_use_aim: str = ""
    inverter_max_discharger_current: str = ""
    normal_voltage_point: str = ""
    start_sell_voltage_point: str = ""
    grid_max_charger_current_set: str = ""
    inverter_battery_low_voltage: str = ""
    inverter_battery_high_voltage: str = ""
    max_combine_charger_current: str = ""
    system_setting: str = ""
    charger_source_priority: str = ""
    # inverter real-time (0x6271)
    work_state: str = ""
    ac_voltage_grade: str = ""
    rated_power: str = ""
    inverter_battery_voltage: str = ""
    inverter_voltage: str = ""
    grid_voltage: str = ""
    bus_voltage: str = ""
    control_current: str = ""
    inverter_current: str = ""
    grid_current: str = ""
    load_current: str = ""
    p_inverter: str = ""
    p_grid: str = ""
    p_load: str = ""
    load_percent: str = ""
    s_inverter: str = ""
    s_grid: str = ""
    s_load: str = ""
    q_inverter: str = ""
    q_grid: str = ""
    q_load: str = ""
    inverter_frequency: str = ""
    grid_frequency: str = ""
    inverter_max_number: str = ""
    combine_type: str = ""
    inverter_number: str = ""
    ac_radiator_temperature: str = ""
    transformer_temperature: str = ""
    dc_radiator_temperature: str = ""
    inverter_relay_state: str = ""
    grid_relay_state: str = ""
    load_relay_state: str = ""
    n_line_relay_state: str = ""
    dc_relay_state: str = ""
    earth_relay_state: str = ""
    accumulated_charger_power: str = ""
    accumulated_discharger_power: str = ""
    accumulated_buy_power: str = ""
    accumulated_sell_power: str = ""
    accumulated_load_power: str = ""
    accumulated_self_use_power: str = ""
    accumulated_pv_sell_power: str = ""
    accumulated_grid_charger_power: str = ""
    inverter_error_message: str = ""
    inverter_warning_message: str = ""
    batt_power: str = ""
    batt_current: str = ""

    def summary(self) -> str:
        """One-line summary for the terminal log."""
        return (
            f"{self.inverter_machine_type or self.machine_type or '?'} "
            f"SN={self.inverter_serial_number or self.serial_number} | "
            f"WorkState={self.work_state} | "
            f"Charger={self.charger_workstate}/{self.charging_state} | "
            f"PV={self.pv_voltage} Batt={self.battery_voltage} "
            f"I_chg={self.charger_current} P_grid={self.p_grid} "
            f"V_inv={self.inverter_voltage} I_batt={self.batt_current} "
            f"P_batt={self.batt_power}"
        )


# ---------------------------------------------------------------------------
# Serial port server
# ---------------------------------------------------------------------------

class Rs485ComServer:
    """
    Wraps one serial port:
      * 19200 baud, 8N1, 1 s read/write timeouts, RTS enabled
      * transact(): write frame, poll for 2*count+5 reply bytes (100 ms steps), read
    """

    def __init__(self, port_name: str, baud_rate: int = SP_BAUD_RATE):
        self.port_name = port_name
        self.baud_rate = baud_rate
        self._ser: Optional[serial.Serial] = None

    # -- lifecycle ----------------------------------------------------------

    def open(self) -> "Rs485ComServer":
        self._ser = serial.Serial(self.port_name, self.baud_rate,
                                  timeout=1.0, write_timeout=1.0)
        try:
            self._ser.rts = True          # RS485 direction control
        except Exception as e:            # pragma: no cover
            log.debug("cannot set RTS on %s: %s", self.port_name, e)
        log.info("opened %s @ %d baud (8N1, RTS)", self.port_name, self.baud_rate)
        return self

    def close(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()
            log.info("closed %s", self.port_name)
        self._ser = None

    def __enter__(self) -> "Rs485ComServer":
        return self.open()

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def ser(self) -> serial.Serial:
        if self._ser is None or not self._ser.is_open:
            raise RuntimeError(f"serial port {self.port_name} is not open")
        return self._ser

    # -- low level ----------------------------------------------------------

    def _read_expected(self, expected: int, max_loop: int = MAX_LOOP) -> Optional[bytes]:
        """
        Receive loop: poll every 100 ms until `expected` bytes are available
        (uses >= instead of == so a late extra byte cannot wedge the reader).
        """
        ser = self.ser
        deadline_steps = max_loop
        for _ in range(deadline_steps):
            n = ser.in_waiting
            if n >= expected:
                data = ser.read(expected)
                extra = n - expected
                if extra > 0:
                    drained = ser.read(extra)
                    log.debug("drained %d extra byte(s): %s",
                              len(drained or b""),
                              (drained or b"").hex(" ").upper())
                return data
            time.sleep(0.1)
        n = ser.in_waiting
        if n:
            partial = ser.read(n)
            log.warning("timeout: only %d of %d expected bytes arrived (%s)",
                        n, expected, partial.hex(" ").upper())
            return partial
        return None

    def transact(self, frame: bytes, expected_len: int,
                 max_loop: int = MAX_LOOP) -> Optional[bytes]:
        """Write a full Modbus frame and wait for the expected reply length."""
        ser = self.ser
        stale = ser.in_waiting
        if stale:
            drained = ser.read(stale)
            log.debug("drained %d stale byte(s) before TX: %s",
                      stale, drained.hex(" ").upper())
        log.debug("TX: %s", frame.hex(" ").upper())
        ser.write(frame)
        data = self._read_expected(expected_len, max_loop)
        if data is not None:
            log.debug("RX: %s", data.hex(" ").upper())
        else:
            log.warning("no response (timeout after %.1f s)", 0.1 * max_loop)
        return data

    # -- Modbus read --------------------------------------------------------

    def read_registers(self, addr: int, start_reg: int, count: int,
                       max_loop: int = MAX_LOOP) -> Optional[list[int]]:
        frame = build_read_frame(addr, start_reg, count)
        data = self.transact(frame, expected_len=5 + 2 * count, max_loop=max_loop)
        if data is None:
            return None
        regs = parse_response(data, addr, count)
        if regs is not None:
            log.debug("slave 0x%02X read 0x%04X x%d OK", addr, start_reg, count)
        return regs

    # -- scan ---------------------------------------------------------------

    def scan_probe(self, addr: int = SCAN_PROBE_ADDR):
        """
        Send the scan probe and return (machine_type, reg4) or None.
        Reads 5 registers @0x4E21: reg0 = machine type, reg4 = unit-count register.
        """
        frame = hex_to_bytes(add_crc(f"{addr:02X} 03 4E 21 00 05"))
        data = self.transact(frame, expected_len=5 + 2 * SCAN_PROBE_COUNT)
        if data is None:
            return None
        regs = parse_response(data, addr, SCAN_PROBE_COUNT)
        if regs is None or regs[0] not in MACHINE_TYPES:
            return None
        return regs[0], regs[4]

    # -- full data fetch ----------------------------------------------------

    def get_part_data(self, charger_id: int, inverter_id: int) -> DeviceData:
        """
        Read the 6 register blocks (3 charger + 3 inverter) and decode every
        field. Returns a (possibly empty) DeviceData.
        """
        d = DeviceData(charger_id=charger_id, inverter_id=inverter_id)

        # 1) charger identity: {id} 03 27 11 00 0A  (10 regs)
        r1 = self.read_registers(charger_id, *BLOCK_CHARGER_ID)
        if r1 is None or len(r1) != 10:
            log.warning("charger 0x%02X: identity block unreadable, skipping unit", charger_id)
            return d
        d.machine_type = str(r1[0])
        d.serial_number = f"{r1[1]:04X}{r1[2]:04X}"
        d.hardware_version = "" if r1[3] == 0 else format_version(r1[3])
        d.software_version = "" if r1[4] == 0 else format_version(r1[4])
        d.pv_voltage_c = f"{r1[5]:04X}"
        d.battery_voltage_c = f"{r1[6]:04X}"
        d.charger_current_c = f"{r1[7]:04X}"

        time.sleep(0.1)  # inter-block delay
        # 2) charger settings: {id} 03 27 75 00 0C  (12 regs)
        r2 = self.read_registers(charger_id, *BLOCK_CHARGER_SET)
        if r2 is not None and len(r2) == 12:
            d.charger_work_enable = get_value(s16(r2[0]), CHARGER_WORK_ENABLE)
            d.absorb_voltage = f"{s16(r2[1]) * 0.1:g}"
            d.float_voltage = f"{s16(r2[2]) * 0.1:g}"
            d.absorption_voltage = f"{s16(r2[3]) * 0.1:g}"
            d.battery_low_voltage = f"{s16(r2[4]) * 0.1:g}"
            d.battery_high_voltage = f"{s16(r2[6]) * 0.1:g}"
            d.max_charger_current = f"{s16(r2[7]) * 0.1:g}"
            d.absorb_charger_current = f"{s16(r2[8]) * 0.1:g}"
            d.battery_type = str(s16(r2[9]))
            d.battery_ah = str(s16(r2[10]))
            d.remove_the_accumulated_data = str(s16(r2[11]))

        time.sleep(0.1)
        # 3) charger status: {id} 03 3B 61 00 15  (21 regs)
        r3 = self.read_registers(charger_id, *BLOCK_CHARGER_STAT)
        if r3 is not None and len(r3) == 21:
            d.charger_workstate = get_value(s16(r3[0]), CHARGER_WORKSTATE)
            d.mppt_state = get_value(s16(r3[1]), MPPT_STATE)
            d.charging_state = get_value(s16(r3[2]), CHARGING_STATE)
            d.pv_voltage = f"{s16(r3[4]) * 0.1:g} V"
            d.battery_voltage = f"{s16(r3[5]) * 0.1:g} V"
            d.charger_current = f"{s16(r3[6]) * 0.1:g} A"
            d.charger_power = f"{s16(r3[7])} W"
            d.radiator_temperature = f"{s16(r3[8])} \u2103"
            d.external_temperature = f"{s16(r3[9])} \u2103"
            d.battery_relay = get_value(s16(r3[10]), CONNECT_STATES)
            d.pv_relay = get_value(s16(r3[11]), CONNECT_STATES)
            d.error_message = analyze_bit_message(r3[12], CHARGER_ERROR)
            d.warning_message = analyze_bit_message(r3[13], CHARGER_WARNING)
            d.batt_vol_grade = f"{s16(r3[14])} V"
            d.rated_current = f"{s16(r3[15]) * 0.1:g} A"
            d.accumulated_power = (f"{s16(r3[16]) * 1000 + s16(r3[17]) * 0.1:g} KWH")
            d.accumulated_time = (f"{s16(r3[18]):02d}:{s16(r3[19]):02d}:{s16(r3[20]):02d}")

        time.sleep(0.1)
        # 4) inverter identity: {id} 03 4E 21 00 10  (16 regs)
        r4 = self.read_registers(inverter_id, *BLOCK_INVERTER_ID, max_loop=MAX_LOOP)
        if r4 is not None and len(r4) == 16:
            d.inverter_machine_type = machine_type_name(r4[0], r1[4])
            d.inverter_serial_number = f"{r4[1]:04X}{r4[2]:04X}"
            d.inverter_hardware_version = "" if r4[3] == 0 else format_version(r4[3])
            d.inverter_software_version = "" if r4[4] == 0 else format_version(r4[4])
            d.inverter_battery_voltage_c = f"{r4[8]:04X}"
            d.inverter_voltage_c = f"{r4[9]:04X}"
            d.grid_voltage_c = f"{r4[10]:04X}"
            d.bus_voltage_c = f"{r4[11]:04X}"
            d.control_current_c = f"{r4[12]:04X}"
            d.inverter_current_c = f"{r4[13]:04X}"
            d.grid_current_c = f"{r4[14]:04X}"
            d.load_current_c = f"{r4[15]:04X}"

        time.sleep(0.1)
        # 5) inverter settings: {id} 03 4E 85 00 2B  (43 regs)
        r5 = self.read_registers(inverter_id, *BLOCK_INVERTER_SET)
        if r5 is not None and len(r5) == 43:
            d.inverter_offgrid_work_enable = str(s16(r5[0]))
            d.inverter_output_voltage_set = f"{s16(r5[1]) * 0.1:g}"
            d.inverter_output_frequency_set = str(s16(r5[2]))
            d.inverter_search_mode_enable = str(s16(r5[3]))
            d.inverter_discharger_to_grid_enable = str(s16(r5[7]))
            d.energy_use_mode = get_value(s16(r5[8]), ENERGY_USE_MODE)
            d.grid_protect_standard = get_value(s16(r5[10]), GRID_PROTECT_STANDARD)
            d.solar_use_aim = get_value(s16(r5[11]), SOLAR_USE_AIM)
            d.inverter_max_discharger_current = f"{s16(r5[12]) * 0.1:g}"
            d.normal_voltage_point = f"{s16(r5[17]) * 0.1:g}"
            d.start_sell_voltage_point = f"{s16(r5[18]) * 0.1:g}"
            d.grid_max_charger_current_set = f"{s16(r5[24]) * 0.1:g}"
            d.inverter_battery_low_voltage = f"{s16(r5[26]) * 0.1:g}"
            d.inverter_battery_high_voltage = f"{s16(r5[27]) * 0.1:g}"
            d.max_combine_charger_current = f"{s16(r5[31]) * 0.1:g}"
            d.system_setting = analyze_bit_message(r5[41], SYSTEM_SETTING_BIT)
            d.charger_source_priority = get_value(s16(r5[42]), CHARGER_SOURCE_PRIORITY)

        time.sleep(0.1)
        # 6) inverter real-time: {id} 03 62 71 00 4A  (74 regs, longer timeout)
        r6 = self.read_registers(inverter_id, *BLOCK_INVERTER_STAT, max_loop=40)
        if r6 is not None and len(r6) == 74:
            d.work_state = get_value(s16(r6[0]), WORK_STATE)
            d.ac_voltage_grade = f"{s16(r6[1])} V"
            rated = s16(r6[2])
            unit = "VA" if d.inverter_machine_type in ("PV1800", "PH1800") else \
                   ("W" if d.inverter_machine_type == "PH3000" else "W")
            d.rated_power = f"{rated} {unit}"
            d.inverter_battery_voltage = f"{s16(r6[4]) * 0.1:g} V"
            d.inverter_voltage = f"{s16(r6[5]) * 0.1:g} V"
            d.grid_voltage = f"{s16(r6[6]) * 0.1:g} V"
            d.bus_voltage = f"{s16(r6[7]) * 0.1:g} V"
            d.control_current = f"{s16(r6[8]) * 0.1:g} A"
            d.inverter_current = f"{s16(r6[9]) * 0.1:g} A"
            d.grid_current = f"{s16(r6[10]) * 0.1:g} A"
            d.load_current = f"{s16(r6[11]) * 0.1:g} A"
            d.p_inverter = f"{s16(r6[12])} W"
            d.p_grid = f"{s16(r6[13])} W"
            d.p_load = f"{s16(r6[14])} W"
            d.load_percent = f"{s16(r6[15])} %"
            d.s_inverter = f"{s16(r6[16])} VA"
            d.s_grid = f"{s16(r6[17])} VA"
            d.s_load = f"{s16(r6[18])} VA"
            d.q_inverter = f"{s16(r6[20])} var"
            d.q_grid = f"{s16(r6[21])} var"
            d.q_load = f"{s16(r6[22])} var"
            d.inverter_frequency = f"{s16(r6[24]) * 0.01:g} Hz"
            d.grid_frequency = f"{s16(r6[25]) * 0.01:g} Hz"
            d.inverter_max_number = r6[28]
            d.combine_type = r6[29]
            d.inverter_number = r6[30]
            d.ac_radiator_temperature = f"{s16(r6[32])} \u2103"
            d.transformer_temperature = f"{s16(r6[33])} \u2103"
            d.dc_radiator_temperature = f"{s16(r6[34])} \u2103"
            d.inverter_relay_state = get_value(s16(r6[36]), CONNECT_STATES)
            d.grid_relay_state = get_value(s16(r6[37]), CONNECT_STATES)
            d.load_relay_state = get_value(s16(r6[38]), CONNECT_STATES)
            d.n_line_relay_state = get_value(s16(r6[39]), CONNECT_STATES)
            d.dc_relay_state = get_value(s16(r6[40]), CONNECT_STATES)
            d.earth_relay_state = get_value(s16(r6[41]), CONNECT_STATES)
            d.accumulated_charger_power = (f"{s16(r6[44]) * 1000 + s16(r6[45]) * 0.1:g} KWH")
            d.accumulated_discharger_power = (f"{s16(r6[46]) * 1000 + s16(r6[47]) * 0.1:g} KWH")
            d.accumulated_buy_power = (f"{s16(r6[48]) * 1000 + s16(r6[49]) * 0.1:g} KWH")
            d.accumulated_sell_power = (f"{s16(r6[50]) * 1000 + s16(r6[51]) * 0.1:g} KWH")
            d.accumulated_load_power = (f"{s16(r6[52]) * 1000 + s16(r6[53]) * 0.1:g} KWH")
            d.accumulated_self_use_power = (f"{s16(r6[54]) * 1000 + s16(r6[55]) * 0.1:g} KWH")
            d.accumulated_pv_sell_power = (f"{s16(r6[56]) * 1000 + s16(r6[57]) * 0.1:g} KWH")
            d.accumulated_grid_charger_power = (f"{s16(r6[58]) * 1000 + s16(r6[59]) * 0.1:g} KWH")
            d.inverter_error_message = (
                analyze_bit_message(r6[60], INVERTER_ERROR1)
                + analyze_bit_message(r6[61], INVERTER_ERROR2)
            )
            d.inverter_warning_message = analyze_bit_message(r6[64], INVERTER_WARNING)
            d.batt_power = f"{s16(r6[72])} W"
            d.batt_current = f"{s16(r6[73])} A"
        return d

    def get_device_data(self, unit_pairs: list[tuple[int, int]]) -> list[DeviceData]:
        """Read all units (charger_id, inverter_id) pairs on one port."""
        results = []
        for charger_id, inverter_id in unit_pairs:
            log.info("reading unit: charger=0x%02X inverter=0x%02X", charger_id, inverter_id)
            results.append(self.get_part_data(charger_id, inverter_id))
        return results

    # -- command write ------------------------------------------------------

    def write_command(self, hexcmd: str, auto_crc: bool = True) -> str:
        """
        Send a hex command, wait for a reply (200 ms + up to 8x100 ms polling)
        and report it.
        """
        if not hexcmd or not hexcmd.strip():
            return ""
        frame_hex = add_crc(hexcmd) if auto_crc else hexcmd.strip().upper()
        frame = hex_to_bytes(frame_hex)
        log.debug("TX (command): %s", frame.hex(" ").upper())
        self.ser.write(frame)
        time.sleep(0.2)
        for _ in range(8):
            if self.ser.in_waiting:
                break
            time.sleep(0.1)
        n = self.ser.in_waiting
        if n:
            reply = self.ser.read(n)
            log.debug("RX (command reply): %s", reply.hex(" ").upper())
            return f"command:[{frame_hex}] has been written,returns:{reply.hex(' ').upper()}"
        log.warning("command:[%s] fail (no response)", frame_hex)
        return f"command:[{frame_hex}] fail"


# ---------------------------------------------------------------------------
# Port scanning + unit-group discovery
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    port: str
    machine_type: int
    unit_info_reg: int      # register 0x4E25 raw value (unit count encoded)
    unit_pairs: list[tuple[int, int]] = field(default_factory=list)


def determine_unit_pairs(machine_type: int, unit_info_reg: int) -> list[tuple[int, int]]:
    """
    Derive the (charger_id, inverter_id) pairs for a machine type:
      type 1800/3000/1000 -> 3rd char of decimal unit-info reg = unit count
          units >= 3 : linkable      -> (4,4) (5,5) (6,6)
          units <  3 : linkable part -> (1,4) (2,5) (3,6)
      type 3500        -> single unit -> (4,4)
    """
    if machine_type in (1800, 3000, 1000):
        s = str(unit_info_reg)
        units = int(s[2]) if len(s) >= 3 else 0
        if units >= 3:
            return [(4, 4), (5, 5), (6, 6)]          # 3 linked units
        return [(1, 4), (2, 5), (3, 6)]              # 3 partially linked units
    if machine_type == 3500:
        return [(4, 4)]                              # single unit
    return []


def list_ports() -> list[str]:
    return [p.device for p in serial.tools.list_ports.comports()]


def scan_ports(ports: list[str] | None = None,
               device_ids: tuple[int, ...] = (4, 5, 6)) -> list[ScanResult]:
    """
    For each device id, for each port, send the probe and return the first
    (id, port) that answers.
    """
    if ports is None:
        ports = list_ports()
    results: list[ScanResult] = []
    for device_id in device_ids:
        probe_hex = add_crc(f"{device_id:02X} 03 4E 21 00 05")
        log.info("scanning for device id 0x%02X on %d port(s) [probe %s]",
                 device_id, len(ports), probe_hex)
        for port_name in ports:
            try:
                with Rs485ComServer(port_name) as srv:
                    srv.open()
                    time.sleep(0.2)  # settle delay after write
                    frame = hex_to_bytes(probe_hex)
                    srv.ser.write(frame)
                    # poll for data for up to 20 x 100 ms
                    for _ in range(MAX_LOOP):
                        if srv.ser.in_waiting:
                            break
                        time.sleep(0.1)
                    n = srv.ser.in_waiting
                    if not n:
                        continue
                    data = srv.ser.read(n)
                    regs = parse_response(data, device_id, SCAN_PROBE_COUNT)
                    if regs is None or regs[0] not in MACHINE_TYPES:
                        continue
                    mt, info = regs[0], regs[4]
                    pairs = determine_unit_pairs(mt, info)
                    res = ScanResult(port_name, mt, info, pairs)
                    results.append(res)
                    log.info("scan: device 0x%02X found on %s | machine type %d | "
                             "unit-info reg %d -> units %s",
                             device_id, port_name, mt, info, pairs)
                    break  # stop at first responding port
            except serial.SerialException as e:
                log.warning("scan: cannot open %s: %s", port_name, e)
    if not results:
        log.warning("scan: no responding device found")
    return results


# ---------------------------------------------------------------------------
# Power-flow analysis
# ---------------------------------------------------------------------------

def analyze_device_states(d: DeviceData) -> dict:
    """
    Derive current-flow directions:
      [0] WLtoR  solar -> battery (charger working)
      [1] NBtoT / NTtoB  grid <-> battery
      [2] ELtoR  load fed from ... (work state OffGrid/Grid-Tie/ByPass/Grid charging)
      [3] SBtoT / STtoB  battery <-> load
    """
    flows: list[Optional[str]] = [None, None, None, None]
    ws_index = WORK_STATE.index(d.work_state) if d.work_state in WORK_STATE else -1

    if ws_index in (2, 3, 4, 6):
        flows[2] = "ELtoR"

    p_grid = num_from_string(d.p_grid)
    if p_grid is not None:
        rated = num_from_string(d.rated_power)
        sw = num_from_string((d.inverter_software_version or "").replace(".", ""))
        if (rated is not None and sw is not None and sw > 20000
                and rated in (20000, 3000) and ws_index in (3, 4, 6)):
            flows[1] = "NTtoB"
        elif ws_index == 6:
            flows[1] = "NTtoB"
        else:
            if p_grid > 0:
                flows[1] = "NBtoT"
            if p_grid < 0:
                flows[1] = "NTtoB"

    batt = num_from_string(d.batt_current)
    if batt is not None:
        if ws_index == 6:
            flows[3] = "SBtoT"
        else:
            if batt > 0:
                flows[3] = "SBtoT"
            if batt < 0:
                flows[3] = "STtoB"
            if p_grid == 0 and abs(batt) < 0.1:
                flows[3] = "SBtoT"

    if d.charger_workstate == CHARGER_WORKSTATE[2]:  # "Work Mode"
        flows[0] = "WLtoR"

    return {"soc": 100.0, "flows": flows}


# ---------------------------------------------------------------------------
# Settings / maintenance command builders
# ---------------------------------------------------------------------------

def cmd_reset_params(inverter_id: int) -> str:
    """Factory-reset inverter parameters: {id} 10 4E F6 00 01 02 00 01"""
    return f"{inverter_id:02X} 10 4E F6 00 01 02 00 01"


def cmd_remove_data(inverter_id: int) -> str:
    """Clear accumulated energy data: {id} 10 4E F5 00 01 02 00 01"""
    return f"{inverter_id:02X} 10 4E F5 00 01 02 00 01"


def build_charger_settings_command(
    charger_id: int, work_enable: int, absorb_v: float, float_v: float,
    absorption_v: float, batt_low_v: float, batt_high_v: float,
    max_chg_a: float, absorb_chg_a: float, batt_type: int, batt_ah: int,
) -> str:
    """
    Multi-register write of the charger settings block:
      {id} 10 27 75 00 0B 16 {work} {absorb} {float} {absorb} {batlow} FFFF
      {bathigh} {maxchg} {absorbchg} {batttype} {ah}
    (voltages/currents are stored x10; batt_type 0 -> FFFF)
    """
    bt = "FFFF" if batt_type == 0 else f"{batt_type:04X}"
    return (f"{charger_id:02X} 10 27 75 00 0B 16 "
            f"{work_enable:04X} {round(absorb_v * 10):04X} {round(float_v * 10):04X} "
            f"{round(absorption_v * 10):04X} {round(batt_low_v * 10):04X} FFFF "
            f"{round(batt_high_v * 10):04X} {round(max_chg_a * 10):04X} "
            f"{round(absorb_chg_a * 10):04X} {bt} {int(batt_ah):04X}")


def build_inverter_settings_command(
    inverter_id: int, offgrid_enable: int, output_v: float,
    output_freq: int, search_enable: int, dischg2grid_enable: int,
    energy_mode: int, grid_std: int, solar_aim: int,
    max_dischg_a: float, normal_v_point: float, sell_v_point: float,
    grid_max_chg_a: float, batt_low_v: float, batt_high_v: float,
    max_combine_chg_a: float, system_setting_bits: int, src_priority: int,
) -> str:
    """
    Multi-register write of the inverter settings block:
      {id} 10 4E 85 00 2B 56 ... 43 registers, untouched ones FFFF ...
    """
    freq = "0000" if output_freq not in (5000, 6000) else f"{output_freq:04X}"
    em = "FFFF" if energy_mode == 0 else f"{energy_mode:04X}"
    sp = "FFFF" if src_priority == 1 else f"{src_priority:04X}"
    return (f"{inverter_id:02X} 10 4E 85 00 2B 56 "
            f"{offgrid_enable:04X} {round(output_v * 10):04X} {freq} {search_enable:04X} "
            f"FFFF FFFF FFFF "
            f"{dischg2grid_enable:04X} {em} FFFF "
            f"{grid_std:04X} {solar_aim:04X} {round(max_dischg_a * 10):04X} "
            f"FFFF FFFF FFFF FFFF "
            f"{round(normal_v_point * 10):04X} {round(sell_v_point * 10):04X} "
            f"FFFF FFFF FFFF FFFF FFFF "
            f"{round(grid_max_chg_a * 10):04X} FFFF "
            f"{round(batt_low_v * 10):04X} {round(batt_high_v * 10):04X} "
            f"FFFF FFFF FFFF "
            f"{round(max_combine_chg_a * 10):04X} "
            f"FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF "
            f"{system_setting_bits:04X} {sp}")


# ---------------------------------------------------------------------------
# Terminal reporting
# ---------------------------------------------------------------------------

def print_device(d: DeviceData) -> None:
    """Full readable dump of one unit (all decoded fields)."""
    print(f"\n=== Unit: charger=0x{d.charger_id:02X} inverter=0x{d.inverter_id:02X} ===")
    groups = {
        "Charger identity (0x2711)": [
            "machine_type", "serial_number", "hardware_version", "software_version",
            "pv_voltage_c", "battery_voltage_c", "charger_current_c"],
        "Charger settings (0x2775)": [
            "charger_work_enable", "absorb_voltage", "float_voltage",
            "absorption_voltage", "battery_low_voltage", "battery_high_voltage",
            "max_charger_current", "absorb_charger_current", "battery_type",
            "battery_ah", "remove_the_accumulated_data"],
        "Charger status (0x3B61)": [
            "charger_workstate", "mppt_state", "charging_state", "pv_voltage",
            "battery_voltage", "charger_current", "charger_power",
            "radiator_temperature", "external_temperature", "battery_relay",
            "pv_relay", "error_message", "warning_message", "batt_vol_grade",
            "rated_current", "accumulated_power", "accumulated_time"],
        "Inverter identity (0x4E21)": [
            "inverter_machine_type", "inverter_serial_number",
            "inverter_hardware_version", "inverter_software_version",
            "inverter_battery_voltage_c", "inverter_voltage_c", "grid_voltage_c",
            "bus_voltage_c", "control_current_c", "inverter_current_c",
            "grid_current_c", "load_current_c"],
        "Inverter settings (0x4E85)": [
            "inverter_offgrid_work_enable", "inverter_output_voltage_set",
            "inverter_output_frequency_set", "inverter_search_mode_enable",
            "inverter_discharger_to_grid_enable", "energy_use_mode",
            "grid_protect_standard", "solar_use_aim",
            "inverter_max_discharger_current", "normal_voltage_point",
            "start_sell_voltage_point", "grid_max_charger_current_set",
            "inverter_battery_low_voltage", "inverter_battery_high_voltage",
            "max_combine_charger_current", "system_setting",
            "charger_source_priority"],
        "Inverter real-time (0x6271)": [
            "work_state", "ac_voltage_grade", "rated_power",
            "inverter_battery_voltage", "inverter_voltage", "grid_voltage",
            "bus_voltage", "control_current", "inverter_current", "load_current",
            "p_inverter", "p_grid", "p_load", "load_percent", "s_inverter",
            "s_grid", "s_load", "q_inverter", "q_grid", "q_load",
            "inverter_frequency", "grid_frequency", "inverter_max_number",
            "combine_type", "inverter_number", "ac_radiator_temperature",
            "transformer_temperature", "dc_radiator_temperature",
            "inverter_relay_state", "grid_relay_state", "load_relay_state",
            "n_line_relay_state", "dc_relay_state", "earth_relay_state",
            "accumulated_charger_power", "accumulated_discharger_power",
            "accumulated_buy_power", "accumulated_sell_power",
            "accumulated_load_power", "accumulated_self_use_power",
            "accumulated_pv_sell_power", "accumulated_grid_charger_power",
            "inverter_error_message", "inverter_warning_message",
            "batt_power", "batt_current"],
    }
    for title, keys in groups.items():
        print(f"  -- {title} --")
        for k in keys:
            v = getattr(d, k, "")
            if v not in ("", None):
                print(f"     {k:32s} = {v}")
    st = analyze_device_states(d)
    flows = [f for f in st["flows"] if f]
    if flows:
        print(f"  -- Power flow --")
        print(f"     flows                          = {', '.join(flows)}")


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def discover_units(port: str | None, device_ids: tuple[int, ...]):
    """Find the device group. Returns (port, unit_pairs) or (None, None)."""
    if port:
        results = scan_ports([port], device_ids)
    else:
        results = scan_ports(None, device_ids)
    for r in results:
        if r.unit_pairs:
            return r.port, r.unit_pairs
    # Fallback: assume the default Linkable group on the requested port
    if port:
        log.warning("no scan response; falling back to default unit group (4,4) (5,5) (6,6)")
        return port, [(4, 4), (5, 5), (6, 6)]
    return None, None


def cmd_list(_args) -> int:
    ports = list_ports()
    if not ports:
        print("no serial ports found")
        return 1
    for p in ports:
        print(p)
    return 0


def cmd_scan(args) -> int:
    ports = [args.port] if args.port else None
    results = scan_ports(ports, tuple(args.ids))
    if not results:
        return 1
    print(f"\n{len(results)} device(s) found:")
    for r in results:
        print(f"  port={r.port}  machine_type={r.machine_type}  "
              f"unit_info={r.unit_info_reg}  units={r.unit_pairs}")
    return 0


def cmd_read(args) -> int:
    port, pairs = discover_units(args.port, tuple(args.ids))
    if port is None:
        log.error("no device found on any port")
        return 1
    try:
        with Rs485ComServer(port) as srv:
            devices = srv.get_device_data(pairs)
    except serial.SerialException as e:
        log.error("cannot open %s: %s", port, e)
        return 1
    ok = 0
    for d in devices:
        if d.machine_type or d.inverter_machine_type:
            ok += 1
            print_device(d)
            log.info("unit 0x%02X/0x%02X: %s", d.charger_id, d.inverter_id, d.summary())
        else:
            log.warning("unit 0x%02X/0x%02X: no data", d.charger_id, d.inverter_id)
    if ok:
        log.info("read OK: %d/%d unit(s) on %s", ok, len(devices), port)
    else:
        log.error("read failed: no unit responded on %s", port)
        return 1
    return 0


def cmd_monitor(args) -> int:
    port, pairs = discover_units(args.port, tuple(args.ids))
    if port is None:
        log.error("no device found on any port")
        return 1
    log.info("monitoring %s every %.1f s (Ctrl+C to stop)", port, args.interval)
    fail_streak = 0
    try:
        while True:
            t0 = time.time()
            try:
                with Rs485ComServer(port) as srv:
                    devices = srv.get_device_data(pairs)
                ok = [d for d in devices
                      if d.machine_type or d.inverter_machine_type]
                if ok:
                    fail_streak = 0
                    for d in ok:
                        log.info("unit 0x%02X/0x%02X: %s",
                                 d.charger_id, d.inverter_id, d.summary())
                        if args.verbose_dump:
                            print_device(d)
                else:
                    fail_streak += 1
                    log.warning("poll: no unit responded (streak=%d/%d)",
                                fail_streak, FAIL_TIMES)
                    if fail_streak >= FAIL_TIMES:
                        log.error("device lost after %d failed polls; rescanning",
                                  fail_streak)
                        fail_streak = 0
                        port, pairs = discover_units(port, tuple(args.ids))
                        if port is None:
                            return 1
            except Exception as e:
                fail_streak += 1
                log.error("poll error: %s (streak=%d)", e, fail_streak)
            elapsed = time.time() - t0
            time.sleep(max(0.0, args.interval - elapsed))
    except KeyboardInterrupt:
        log.info("monitoring stopped")
        return 0


def cmd_write(args) -> int:
    if args.reset_params:
        hexcmd = cmd_reset_params(args.inverter_id)
    elif args.remove_data:
        hexcmd = cmd_remove_data(args.inverter_id)
    elif args.command:
        hexcmd = args.command
    else:
        print("nothing to write: give a hex command or --reset-params/--remove-data")
        return 2
    try:
        with Rs485ComServer(args.port) as srv:
            result = srv.write_command(hexcmd, auto_crc=not args.no_crc)
    except serial.SerialException as e:
        log.error("cannot open %s: %s", args.port, e)
        return 1
    print(result)
    return 0 if "fail" not in result else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s.%(msecs)03d  %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    logging.getLogger("serial").setLevel(logging.WARNING)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="RS485 Modbus-RTU monitor for PowerMonitor inverter/charger units",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:")[1] if __doc__ else None,
    )
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="debug logging (raw TX/RX hex frames)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list available serial ports")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("scan", help="scan for connected devices")
    p.add_argument("-p", "--port", help="only scan this port (default: all)")
    p.add_argument("--ids", type=lambda s: [int(x, 0) for x in s.split(",")],
                   default=[4, 5, 6], help="device ids to probe (default 4,5,6)")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("read", help="one-shot full read of all units")
    p.add_argument("-p", "--port", help="serial port (default: scan all ports)")
    p.add_argument("--ids", type=lambda s: [int(x, 0) for x in s.split(",")],
                   default=[4, 5, 6], help="scan probe ids (default 4,5,6)")
    p.set_defaults(func=cmd_read)

    p = sub.add_parser("monitor", help="continuously poll and log to the terminal")
    p.add_argument("-p", "--port", help="serial port (default: scan all ports)")
    p.add_argument("--ids", type=lambda s: [int(x, 0) for x in s.split(",")],
                   default=[4, 5, 6], help="scan probe ids (default 4,5,6)")
    p.add_argument("--interval", type=float, default=3.0,
                   help="poll interval seconds (default 3)")
    p.add_argument("--dump", dest="verbose_dump", action="store_true",
                   help="print the full field table every cycle (not just the summary)")
    p.set_defaults(func=cmd_monitor)

    p = sub.add_parser("write", help="write a raw hex command (CRC appended unless --no-crc)")
    p.add_argument("-p", "--port", required=True)
    p.add_argument("command", nargs="?",
                   help='hex command, e.g. "04 10 4E F6 00 01 02 00 01"')
    p.add_argument("--no-crc", action="store_true",
                   help="send the command as-is (it already contains the CRC)")
    p.add_argument("--reset-params", action="store_true",
                   help="factory-reset inverter parameters (0x4EF6)")
    p.add_argument("--remove-data", action="store_true",
                   help="clear accumulated energy data (0x4EF5)")
    p.add_argument("--inverter-id", type=lambda s: int(s, 0), default=4,
                   help="inverter id for --reset-params/--remove-data (default 4)")
    p.set_defaults(func=cmd_write)

    args = ap.parse_args(argv)
    setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

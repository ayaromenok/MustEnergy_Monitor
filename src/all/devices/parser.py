"""Parse raw register values using device definitions."""

from __future__ import annotations

import logging
from typing import Any

from .definitions import (
    DeviceDefinition,
    Register,
    RegisterPair,
    COMMON_FAULT_BITS,
    COMMON_WARNING_BITS,
    ERROR_TABLE_32,
    PH1000_WARNING_BITS,
)

log = logging.getLogger(__name__)


def decode_signed(raw: int) -> int:
    """Convert unsigned 16-bit to signed two's complement."""
    if raw >= 0x8000:
        return raw - 0x10000
    return raw


def format_version_eighteen(version_raw: int) -> str:
    """Format protocol edition like 10414 → '1.04.14'."""
    s = str(version_raw)
    if len(s) >= 5:
        return f"{s[0]}.{s[1:3]}.{s[3:]}"
    if len(s) >= 3:
        return f"{s[0]}.{s[1:]}"
    return s


def format_hex_version(version_hex: int) -> str:
    """Format hex version like 0x1234 → '12.34'."""
    s = f"{version_hex:04X}"
    return f"{s[:2]}.{s[2:]}"


def int_to_ascii(value: int, length: int = 2) -> str:
    """Convert integer to ASCII string (big-endian)."""
    chars = []
    for i in range(length - 1, -1, -1):
        char_code = (value >> (i * 8)) & 0xFF
        if 32 <= char_code <= 126:
            chars.append(chr(char_code))
        else:
            chars.append("?")
    return "".join(chars)


def serial_number(h: int, l: int) -> str:
    """Format serial number from H/L words."""
    return f"{h:05d}{l:05d}"


def serial_number_3part(h: int, m: int, l: int) -> str:
    """Format 3-part serial number."""
    return f"{h:05d}{m:05d}{l:05d}"


def energy_kwh(high: int, low: int, coeff: float = 0.1, no_decimal: bool = False) -> float:
    """Calculate energy from H/L register pair."""
    if no_decimal:
        return high * 1000 + low
    return (high * 1000 + low) * coeff


def energy_32bit(high: int, low: int, coeff: float = 0.1) -> float:
    """Calculate energy from 32-bit value (H*65536 + L)."""
    return (high * 65536 + low) * coeff


def bitmask_to_labels(value: int, bit_map: dict[int, str]) -> list[str]:
    """Convert a bitmask to a list of active labels."""
    return [bit_map[bit] for bit in sorted(bit_map) if (value >> bit) & 1]


def error_32bit_to_label(err1: int, err2: int, table: list[str]) -> str:
    """Combine two 16-bit registers into a 32-bit error code and look up."""
    code = (err2 << 16) | err1
    if code < len(table):
        return table[code]
    return f"Unknown error code 0x{code:08X}"


class DeviceParser:
    """Parse raw register values for a specific device."""

    def __init__(self, device: DeviceDefinition):
        self.dev = device
        # Build a lookup: address → Register
        self._reg_map: dict[int, Register] = {}
        for block in (
            device.identity, device.calibration, device.settings,
            device.status, device.daily_energy, device.errors,
            device.warnings, device.commands, device.advanced,
        ):
            for r in block:
                self._reg_map[r.address] = r
        # Build a lookup: high_addr → RegisterPair
        self._pair_map: dict[int, RegisterPair] = {}
        for p in device.energy:
            self._pair_map[p.high_addr] = p

    def get_register(self, address: int) -> Register | None:
        return self._reg_map.get(address)

    def get_pair(self, high_addr: int) -> RegisterPair | None:
        return self._pair_map.get(high_addr)

    def decode_register(self, address: int, raw: int) -> Any:
        """Decode a single register value."""
        reg = self._reg_map.get(address)
        if reg is None:
            return raw

        # Bitmask → labels
        if reg.bit_map:
            return bitmask_to_labels(raw, reg.bit_map)

        # Enum → label
        if reg.enum_map is not None:
            if isinstance(reg.enum_map, dict) and isinstance(next(iter(reg.enum_map)), str):
                # String-keyed enum (e.g. {"SBU": "SBU"})
                return reg.enum_map.get(raw, str(raw))
            return reg.enum_map.get(raw, str(raw))

        # Apply coefficient
        value = raw if reg.coefficient == 1.0 else raw * reg.coefficient
        return value

    def decode_pair(self, high: int, low: int) -> float:
        """Decode a 32-bit value from two 16-bit registers."""
        pair = None
        for p in self.dev.energy:
            if p.high_addr == high or p.low_addr == low:
                pair = p
                break
        if pair is None:
            return (high * 65536 + low) * 0.1

        # PV3500PRO: kWh = H*1000 + L (no ×0.1)
        if self.dev.energy_no_decimal:
            return high * 1000 + low
        return (high * 1000 + low) * pair.coefficient

    def decode_32bit_error(self, err1: int, err2: int) -> str:
        """Decode 32-bit error code."""
        table = self.dev.error_table_32 if self.dev.error_table_32 else ERROR_TABLE_32
        return error_32bit_to_label(err1, err2, table)

    def decode_arrow_flag(self, flag: int) -> dict[str, Any]:
        """Decode 10-bit arrow flag for 1.04.14 hybrid inverters."""
        return {
            "pv_connected": bool(flag & 0x01),
            "load_connected": bool(flag & 0x02),
            "battery_connected": bool(flag & 0x04),
            "ac_connected": bool(flag & 0x08),
            "pv_current_direction": (flag >> 3) & 0x03,
            "load_current_direction": (flag >> 5) & 0x03,
            "battery_current_direction": (flag >> 7) & 0x03,
            "ac_current_direction": (flag >> 9) & 0x03,
        }

    def build_status_dict(self, registers: dict[int, int]) -> dict[str, Any]:
        """Build a dictionary of all status values."""
        result: dict[str, Any] = {}
        for addr, raw in registers.items():
            reg = self._reg_map.get(addr)
            if reg is None:
                continue
            decoded = self.decode_register(addr, raw)
            result[reg.name] = {
                "address": addr,
                "raw": raw,
                "value": decoded,
                "coefficient": reg.coefficient,
                "signed": reg.signed,
                "unit": reg.unit,
                "description": reg.description,
            }
        return result

    def build_identity_dict(self, registers: dict[int, int]) -> dict[str, Any]:
        """Build identity information."""
        result: dict[str, Any] = {}
        for r in self.dev.identity:
            if r.address in registers:
                result[r.name] = {
                    "address": r.address,
                    "raw": registers[r.address],
                    "value": self.decode_register(r.address, registers[r.address]),
                }
        return result

    def build_energy_dict(self, registers: dict[int, int]) -> dict[str, Any]:
        """Build energy counter values."""
        result: dict[str, Any] = {}
        for high_addr, pair in self._pair_map.items():
            if high_addr in registers and (high_addr + 1) in registers:
                value = self.decode_pair(registers[high_addr], registers[high_addr + 1])
                result[pair.name] = {
                    "high_addr": high_addr,
                    "low_addr": pair.low_addr,
                    "raw_high": registers[high_addr],
                    "raw_low": registers[high_addr + 1],
                    "value": value,
                    "unit": pair.unit,
                    "description": pair.description,
                }
        return result

    def build_daily_energy_dict(self, registers: dict[int, int]) -> dict[str, Any]:
        """Build daily energy values."""
        result: dict[str, Any] = []
        for r in self.dev.daily_energy:
            if r.address in registers:
                value = self.decode_register(r.address, registers[r.address])
                result.append({
                    "name": r.name,
                    "address": r.address,
                    "raw": registers[r.address],
                    "value": value,
                    "unit": r.unit,
                })
        return result

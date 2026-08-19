"""CLI entry point for the Modbus device reader."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Optional

try:
    from .modbus_client import ModbusRTUClient
except ImportError:
    from modbus_client import ModbusRTUClient

try:
    from .devices.definitions import DEVICE_REGISTRY, PROTOCOL_MAP, ID_MAP, DeviceDefinition
except ImportError:
    from devices.definitions import DEVICE_REGISTRY, PROTOCOL_MAP, ID_MAP, DeviceDefinition

try:
    from .devices.parser import DeviceParser
except ImportError:
    from devices.parser import DeviceParser

log = logging.getLogger(__name__)


def resolve_device(
    device_name: Optional[str],
    protocol: Optional[str],
    device_id: int,
    port: str,
    baudrate: Optional[int],
) -> tuple[DeviceDefinition, int]:
    """Resolve which device definition to use.

    Priority: explicit device name > protocol type > device ID lookup > default.
    """
    # 1. Explicit device name
    if device_name and device_name in DEVICE_REGISTRY:
        dev = DEVICE_REGISTRY[device_name]
        actual_baud = baudrate or dev.default_baudrate
        actual_id = device_id or dev.default_device_id
        return dev, actual_id

    # 2. Protocol type
    if protocol and protocol in PROTOCOL_MAP:
        dev = DEVICE_REGISTRY[PROTOCOL_MAP[protocol]]
        actual_baud = baudrate or dev.default_baudrate
        actual_id = device_id or dev.default_device_id
        return dev, actual_id

    # 3. Device ID lookup
    if device_id in ID_MAP:
        dev = DEVICE_REGISTRY[ID_MAP[device_id]]
        actual_baud = baudrate or dev.default_baudrate
        return dev, device_id

    # 4. Default: use first EP series device
    if baudrate is None:
        baudrate = 9600
    if device_name is None:
        device_name = "ep2000pro"
    dev = DEVICE_REGISTRY[device_name]
    return dev, device_id


def cmd_read(args: argparse.Namespace) -> int:
    """Read all registers from a device and display parsed values."""
    dev, device_id = resolve_device(
        args.device, args.protocol, args.device_id,
        args.port, args.baudrate,
    )
    log.info("Reading %s (ID=%d, baud=%d)", dev.name, device_id, args.baudrate or dev.default_baudrate)

    with ModbusRTUClient(
        port=args.port,
        baudrate=args.baudrate or dev.default_baudrate,
        parity=args.parity,
        stopbits=args.stopbits,
        timeout=args.timeout,
    ) as client:
        # Read all blocks
        raw_data = client.read_multiple_blocks(device_id, dev.scan_schedule)

    parser = DeviceParser(dev)

    # Merge all registers into one dict
    all_regs: dict[int, int] = {}
    for start, values in raw_data.items():
        for i, val in enumerate(values):
            all_regs[start + i] = val

    # Build output sections
    output: dict[str, Any] = {}
    output["device"] = {
        "name": dev.name,
        "protocol": dev.protocol_type,
        "device_id": device_id,
        "baudrate": args.baudrate or dev.default_baudrate,
    }

    # Identity
    identity_regs = {k: v for k, v in all_regs.items()
                     if k in {r.address for r in dev.identity}}
    output["identity"] = parser.build_identity_dict(identity_regs)

    # Status
    status_regs = {k: v for k, v in all_regs.items()
                   if k in {r.address for r in dev.status}}
    output["status"] = parser.build_status_dict(status_regs)

    # Settings (only those that were read)
    settings_regs = {k: v for k, v in all_regs.items()
                     if k in {r.address for r in dev.settings}}
    output["settings"] = parser.build_status_dict(settings_regs)

    # Calibration
    cal_regs = {k: v for k, v in all_regs.items()
                if k in {r.address for r in dev.calibration}}
    output["calibration"] = parser.build_status_dict(cal_regs)

    # Energy
    output["energy"] = parser.build_energy_dict(all_regs)

    # Daily energy
    output["daily_energy"] = parser.build_daily_energy_dict(all_regs)

    # Errors
    if dev.needs_32bit_errors:
        err1 = all_regs.get(25261, 0)
        err2 = all_regs.get(25262, 0)
        output["errors_32bit"] = {
            "err1_raw": err1,
            "err2_raw": err2,
            "decoded": parser.decode_32bit_error(err1, err2),
        }
    else:
        for err_reg in dev.errors:
            if err_reg.address in all_regs:
                raw = all_regs[err_reg.address]
                labels = parser.decode_register(err_reg.address, raw)
                if isinstance(labels, list):
                    output[f"errors_{err_reg.name}"] = {
                        "raw": raw,
                        "active_faults": labels,
                    }

    # Warnings
    for warn_reg in dev.warnings:
        if warn_reg.address in all_regs:
            raw = all_regs[warn_reg.address]
            labels = parser.decode_register(warn_reg.address, raw)
            if isinstance(labels, list):
                output[f"warnings_{warn_reg.name}"] = {
                    "raw": raw,
                    "active_warnings": labels,
                }

    # Arrow flag
    if dev.needs_arrow_flag and 25279 in all_regs:
        output["arrow_flag"] = parser.decode_arrow_flag(all_regs[25279])

    # Commands
    if dev.commands:
        cmd_regs = {k: v for k, v in all_regs.items()
                    if k in {r.address for r in dev.commands}}
        output["commands"] = parser.build_status_dict(cmd_regs)

    # Output format
    if args.json:
        print(json.dumps(output, indent=2, default=str))
    else:
        _print_table(output)

    return 0


def cmd_write(args: argparse.Namespace) -> int:
    """Write a single register value."""
    dev, device_id = resolve_device(
        args.device, args.protocol, args.device_id,
        args.port, args.baudrate,
    )

    addr = args.address
    value = args.value

    # Validate address is writable
    if addr not in dev.writable_addrs:
        print(f"ERROR: Register {addr} is not writable for {dev.name}", file=sys.stderr)
        print(f"Writable addresses: {sorted(dev.writable_addrs)}", file=sys.stderr)
        return 1

    reg = dev.get_register(addr)
    if reg and reg.enum_map and not isinstance(next(iter(reg.enum_map), None), int):
        # String-keyed enum: try to map value
        if str(value) in reg.enum_map:
            value = int(list(reg.enum_map.keys())[list(reg.enum_map.values()).index(str(value))])
        else:
            print(f"ERROR: Invalid value '{value}' for {reg.name}", file=sys.stderr)
            print(f"Valid values: {list(reg.enum_map.values())}", file=sys.stderr)
            return 1

    print(f"Writing 0x{addr:04X} = {value} on {dev.name} (ID={device_id})...")

    with ModbusRTUClient(
        port=args.port,
        baudrate=args.baudrate or dev.default_baudrate,
        parity=args.parity,
        stopbits=args.stopbits,
        timeout=args.timeout,
    ) as client:
        try:
            client.write_single_register(device_id, addr, value)
            print(f"OK: Wrote 0x{addr:04X} = {value}")
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    """Scan for devices on the serial port."""
    scan_start = args.scan_start
    if args.device:
        dev = DEVICE_REGISTRY.get(args.device)
        if dev:
            scan_start = dev.scan_start

    print(f"Scanning for devices on {args.port} (start addr={scan_start})...")

    with ModbusRTUClient(
        port=args.port,
        baudrate=args.baudrate or 9600,
        parity=args.parity,
        stopbits=args.stopbits,
        timeout=args.timeout,
    ) as client:
        found = client.scan_device_ids(scan_start)

    if found:
        print(f"\nFound {len(found)} device(s) at IDs: {found}")
        for dev_id in found:
            dev_key = ID_MAP.get(dev_id, "unknown")
            dev_name = DEVICE_REGISTRY.get(dev_key, DEVICE_REGISTRY.get("ep2000pro"))
            print(f"  ID {dev_id:3d} → {dev_name.name} (protocol {dev_name.protocol_type})")
    else:
        print("\nNo devices found. Check wiring and power.")

    return 0 if found else 1


def cmd_list(args: argparse.Namespace) -> int:
    """List all supported devices."""
    print("Supported devices:")
    print(f"{'Name':<25} {'Protocol':<12} {'Baud':>6} {'Default ID':>10}")
    print("-" * 60)
    for key, dev in sorted(DEVICE_REGISTRY.items()):
        print(f"{dev.name:<25} {dev.protocol_type:<12} {dev.default_baudrate:>6} {dev.default_device_id:>10}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed register map for a device."""
    dev, _ = resolve_device(
        args.device, args.protocol, args.device_id,
        args.port, args.baudrate,
    )
    parser = DeviceParser(dev)

    print(f"\n{'='*60}")
    print(f"  {dev.name}")
    print(f"  Protocol: {dev.protocol_type}")
    print(f"  Default baudrate: {dev.default_baudrate}")
    print(f"  Default device ID: {dev.default_device_id}")
    print(f"  Scan start address: {dev.scan_start}")
    print(f"{'='*60}\n")

    # Identity
    if dev.identity:
        print("--- Identity Registers ---")
        _print_register_table(dev.identity)
        print()

    # Calibration
    if dev.calibration:
        print("--- Calibration Registers ---")
        _print_register_table(dev.calibration)
        print()

    # Settings
    if dev.settings:
        print("--- Settings Registers (writable) ---")
        _print_register_table(dev.settings)
        print()

    # Status
    if dev.status:
        print("--- Status Registers ---")
        _print_register_table(dev.status)
        print()

    # Energy
    if dev.energy:
        print("--- Energy Counters ---")
        for pair in dev.energy:
            print(f"  {pair.high_addr:5d} / {pair.low_addr:5d}  {pair.name:<35} {pair.coefficient} {pair.unit}")
        print()

    # Scan schedule
    print("--- Scan Schedule ---")
    for start, count in dev.scan_schedule:
        print(f"  {start:5d} - {start + count - 1:5d}  ({count} registers)")
    print()

    # Writable addresses
    print(f"Writable addresses ({len(dev.writable_addrs)} total):")
    print(f"  {sorted(dev.writable_addrs)}")
    print()

    return 0


def _print_table(output: dict) -> None:
    """Pretty-print the output dict as tables."""
    for section, data in output.items():
        if section == "device":
            print(f"\n{'='*60}")
            print(f"  Device: {data['name']}")
            print(f"  Protocol: {data['protocol']}")
            print(f"  Device ID: {data['device_id']}")
            print(f"  Baudrate: {data['baudrate']}")
            print(f"{'='*60}")
            continue

        if not data:
            continue

        if isinstance(data, dict):
            # Check if it's a nested dict with 'raw'/'value' keys
            first_val = next(iter(data.values()), None)
            if first_val and isinstance(first_val, dict) and "raw" in first_val:
                print(f"\n--- {section.upper()} ---")
                print(f"{'Addr':>6} {'Name':<35} {'Raw':>8} {'Value':>12} {'Unit':>6}")
                print("-" * 75)
                for name, info in data.items():
                    addr = info.get("address", "?")
                    raw = info.get("raw", "?")
                    val = info.get("value", "?")
                    unit = info.get("unit", "")
                    if isinstance(val, list):
                        val = ", ".join(str(v) for v in val)
                    print(f"{addr:>6} {name:<35} {raw:>8} {str(val):>12} {unit:>6}")
                continue

            # Regular dict
            print(f"\n--- {section.upper()} ---")
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        val_str = json.dumps(v, default=str)
                        print(f"  {k}: {val_str}")
                    else:
                        print(f"  {k}: {v}")
            continue

        if isinstance(data, list):
            print(f"\n--- {section.upper()} ---")
            for item in data:
                if isinstance(item, dict):
                    print(f"  {item.get('name', '?')}: {item.get('value', '?')} {item.get('unit', '')}")
            continue

        print(f"\n--- {section.upper()} ---")
        print(f"  {data}")


def _print_register_table(registers: list) -> None:
    """Print a register table."""
    print(f"{'Addr':>6} {'Name':<35} {'Coeff':>6} {'Signed':>6} {'Description'}")
    print("-" * 80)
    for r in registers:
        signed_str = "Y" if r.signed else "N"
        coeff_str = str(r.coefficient)
        print(f"{r.address:>6} {r.name:<35} {coeff_str:>6} {signed_str:>6} {r.description}")


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="modbus_cli",
        description="Read/write Modbus RTU solar power devices",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-p", "--port", default="/dev/ttyUSB0", help="Serial port (default: /dev/ttyUSB0)")
    parser.add_argument("-b", "--baudrate", type=int, default=None, help="Baudrate (auto-detect if not set)")
    parser.add_argument("--parity", default="N", choices=["N", "E", "O"], help="Parity (default: N)")
    parser.add_argument("--stopbits", type=int, default=1, choices=[1, 2], help="Stop bits (default: 1)")
    parser.add_argument("--timeout", type=float, default=1.0, help="Read timeout in seconds (default: 1.0)")
    parser.add_argument("-d", "--device", default=None, help="Device model name")
    parser.add_argument("--protocol", default=None, help="Protocol type")
    parser.add_argument("-i", "--device-id", type=int, default=0, help="Device/slave ID")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # read
    read_p = subparsers.add_parser("read", help="Read all registers from a device")
    read_p.add_argument("--json", action="store_true", help="Output as JSON")

    # write
    write_p = subparsers.add_parser("write", help="Write a single register")
    write_p.add_argument("address", type=int, help="Register address")
    write_p.add_argument("value", type=int, help="Value to write")

    # scan
    scan_p = subparsers.add_parser("scan", help="Scan for devices on the bus")
    scan_p.add_argument("--scan-start", type=int, default=None, help="Start address for scan")

    # list
    subparsers.add_parser("list", help="List all supported devices")

    # info
    info_p = subparsers.add_parser("info", help="Show detailed register map for a device")

    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "read": cmd_read,
        "write": cmd_write,
        "scan": cmd_scan,
        "list": cmd_list,
        "info": cmd_info,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

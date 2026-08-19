# Modbus CLI — Solar Power Device Reader

Python command-line tool for reading/writing Modbus RTU registers on solar
inverters, PV chargers, and hybrid inverters.

## Supported Devices

| Model | Protocol | Baudrate | Default ID |
|---|---|---|---|
| PC1800 | Pc1800 | 9600 | 1 |
| PH1800 / EP1800 / Cdy10414M | Ph18Series | 19200 | 4 |
| PV3500PRO | Ph18Series | 19200 | 4 |
| EP2000PRO / PV2000PRO | EPSeries | 9600 | 10 |
| EP3300 | EPSeries | 9600 | 10 |
| EP3300 TLV | EPSeries | 9600 | 10 |
| PV2000PK | EPSeries | 9600 | 10 |
| PH1000 | Ph1000 | 9600 | 5 |
| PH5000 (3-phase) | Ph5000 | 9600 | 6 |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### List supported devices

```bash
python main.py list
```

### Scan for devices on the bus

```bash
python main.py scan --port /dev/ttyUSB0 --baudrate 9600
```

### Read all registers from a device

```bash
# Auto-detect device by ID
python main.py read --port /dev/ttyUSB0 --device-id 10

# Explicit device
python main.py read --port /dev/ttyUSB0 --device ep3300

# JSON output
python main.py read --port /dev/ttyUSB0 --device ep3300 --json > data.json
```

### Show detailed register map

```bash
python main.py info --device ph1800
```

### Write a register

```bash
# Write a value (must be in the device's writable address list)
python main.py write --port /dev/ttyUSB0 --device ep3300 31006 0
# Write enum value
python main.py write --port /dev/ttyUSB0 --device pc1800 10101 1
```

### Options

```
-h, --help            Show help
-v, --verbose         Enable debug logging
-p PORT, --port PORT  Serial port (default: /dev/ttyUSB0)
-b BAUDRATE, --baudrate BAUDRATE  Baudrate (auto-detect if not set)
--parity {N,E,O}      Parity (default: N)
--stopbits {1,2}      Stop bits (default: 1)
--timeout TIMEOUT     Read timeout in seconds (default: 1.0)
-d DEVICE, --device DEVICE  Device model name
--protocol PROTOCOL   Protocol type (Pc1800, Ph18Series, EPSeries, Ph1000, Ph5000)
-i DEVICE_ID, --device-id DEVICE_ID  Device/slave ID
```

## Output Format

Without `--json`, output is printed as human-readable tables:

```
============================================================
  Device: EP3300
  Protocol: EPSeries
  Device ID: 10
  Baudrate: 9600
============================================================

--- IDENTITY ---
  Addr    Name                      Raw     Value   Unit
---------------------------------------------------------------------------
 30000  MachineTypeI                    3      EP3300
 30001  SoftwareVersionI               166  166-00XXX-YY

--- STATUS ---
  Addr    Name                      Raw     Value   Unit
---------------------------------------------------------------------------
 30005  GridVoltage                     230  230.0     V
 30006  GridFrequency                  500   50.0    Hz
 30014  BatteryVoltage                  530   53.0     V
 30017  BatterySoc                       85       85    %
 ...
```

## Architecture

```
main.py              CLI entry point (argparse)
modbus_client.py     Modbus RTU communication (pymodbus)
devices/
  __init__.py        Package exports
  definitions.py     Register maps, enums, fault tables
  parser.py          Decode raw registers → engineering values
```

## Requirements

- Python 3.10+
- pymodbus >= 3.6.0
- pyserial >= 3.5

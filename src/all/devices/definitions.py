"""Device definitions — register maps, enums, fault tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Register:
    """Single 16-bit register definition."""

    address: int
    name: str
    coefficient: float = 1.0
    signed: bool = True
    description: str = ""
    unit: str = ""
    enum_map: Optional[dict] = None  # {value: label}
    bit_map: Optional[dict] = None  # {bit: label}


@dataclass
class RegisterPair:
    """Two 16-bit registers forming a 32-bit value."""

    high_addr: int
    low_addr: int
    name: str
    coefficient: float = 0.1
    signed: bool = False
    description: str = ""
    unit: str = ""


@dataclass
class DeviceDefinition:
    """Complete protocol definition for one device model."""

    name: str
    protocol_type: str
    default_baudrate: int
    default_device_id: int
    scan_start: int

    # Register blocks
    identity: list[Register] = field(default_factory=list)
    calibration: list[Register] = field(default_factory=list)
    settings: list[Register] = field(default_factory=list)
    status: list[Register] = field(default_factory=list)
    energy: list[RegisterPair] = field(default_factory=list)
    daily_energy: list[Register] = field(default_factory=list)
    errors: list[Register] = field(default_factory=list)
    warnings: list[Register] = field(default_factory=list)
    commands: list[Register] = field(default_factory=list)
    advanced: list[Register] = field(default_factory=list)

    # 32-bit error code table
    error_table_32: list[str] = field(default_factory=list)

    # Scan schedule: list of (start_address, count)
    scan_schedule: list[tuple[int, int]] = field(default_factory=list)

    # Writable addresses (for write operations)
    writable_addrs: list[int] = field(default_factory=list)

    # Special parsing flags
    needs_arrow_flag: bool = False
    needs_32bit_errors: bool = False
    energy_no_decimal: bool = False  # PV3500PRO: kWh = H*1000+L, no ×0.1


# ──────────────────────────────────────────────────────────────────────
# Common enum / table helpers
# ──────────────────────────────────────────────────────────────────────

WORK_STATE_INV = {
    0: "PowerOn",
    1: "SelfTest",
    2: "OffGrid",
    3: "Grid-Tie",
    4: "ByPass",
    5: "Stop",
    6: "GridCharging",
}

WORK_STATE_EP = {
    0: "",
    1: "",
    2: "",
    3: "",
    4: "",
    5: "",
    6: "",
    7: "",
}

WORK_STATE_EP3300 = {
    0: "SELF_CHECK",
    1: "BACKUP",
    2: "LINE",
    3: "STOP",
    4: "CHARGER",
    5: "SOFT_START",
    6: "POWER_OFF",
    7: "STANDBY",
    8: "DEBUG",
}

WORK_STATE_EP3300TLV = {
    0: "SELF_CHECK",
    1: "BACKUP",
    2: "LINE",
    3: "STOP",
    4: "DEBUG",
    5: "SOFT_START",
    6: "POWER_OFF",
    7: "STANDBY",
}

WORK_STATE_EP2000 = {
    0: "",
    1: "",
    2: "",
    3: "",
    4: "",
    5: "",
    6: "",
    7: "",
    8: "",
}

WORK_STATE_PV2000PK = {
    0: "",
    1: "INIT",
    2: "SELF_CHECK",
    3: "BACKUP",
    4: "LINE",
    5: "STOP",
    6: "POWER_OFF",
    7: "CHARGER",
    8: "SOFT_START",
}

BATTERY_TYPE = {
    0: "Lead Acid",
    1: "GEL",
    2: "AGM",
    3: "Lithium",
    4: "User Defined",
}

RELAY_STATE = {0: "Disconnect", 1: "Connect"}

AVR_STATE = {
    0: "BYPASS",
    1: "STEPDOWN",
    2: "BOOST",
    3: "EBOOST",
}

CHARGE_STAGE = {0: "CC", 1: "CV", 2: "FV"}

ENERGY_USE_MODE = {
    0: "STORE",
    1: "LOAD_FIRST",
    2: "UPS",
    3: "GENERATOR",
}

GRID_FREQ_TYPE = {50: "50 Hz", 60: "60 Hz"}

GRID_VOLT_TYPE = {
    110: "110V",
    115: "115V",
    120: "120V",
    220: "220V",
    230: "230V",
    240: "240V",
}

OUTPUT_PRIORITY = {0: "Solar first", 1: "Grid first", 2: "SBU"}

CHG_PRIORITY = {
    0: "Solar first",
    1: "Only solar",
    2: "Grid first",
    3: "Union charge",
}

INPUT_RANGE = {0: "Wide", 1: "Narrow"}

SEARCH_TIME = {5: "5 s", 30: "30 s"}

BATTERY_CHARGE_STATUS = {
    0: "STANDBY",
    1: "DISCHG",
    2: "CONST_SMALL_CHG",
    3: "CONST_LARGE_CHG",
    4: "CONST_VOLT_CHG",
    5: "FLOAT_VOLT_CHG",
}

# Common 16-bit fault bitmask (PC1800 / charger / 1.04.14 inverter)
COMMON_FAULT_BITS = {
    0: "Hardware protection",
    1: "Over current",
    2: "Current sensor error",
    3: "Over temperature",
    4: "PV voltage too high",
    5: "PV voltage too low",
    6: "Battery voltage too high",
    7: "Battery voltage too low",
    8: "Current uncontrollable",
    9: "Parameter error",
}

COMMON_WARNING_BITS = {0: "Fan error"}

# EP3300 alarm bitmask
EP3300_ALARM_BITS = {
    0: "Inverter over temperature",
    1: "Battery over temperature",
    2: "Battery voltage too high",
    3: "Battery voltage too low",
    4: "Over load",
}

# EP2000PRO alarm bitmask
EP2000_ALARM_BITS = {
    0: "Battery voltage too low",
    1: "Over load",
    2: "Battery voltage too high",
    3: "Parameter error",
}

# PH1000/PH5000 32-bit error table
ERROR_TABLE_32 = [
    "Hardware protection",
    "Over current",
    "Current sensor error",
    "Over temperature",
    "PV voltage too high",
    "PV voltage too low",
    "Battery voltage too high",
    "Battery voltage too low",
    "Current uncontrollable",
    "Parameter error",
    "Inverter over temperature",
    "Over load",
    "Output short circuit",
    "Output voltage too high",
    "Output voltage too low",
    "Grid voltage too high",
    "Grid voltage too low",
    "Grid frequency too high",
    "Grid frequency too low",
    "Grid over current",
    "Grid over voltage",
    "Grid over frequency",
    "Grid under voltage",
    "Grid under frequency",
    "Anti-backflow over current",
    "Anti-backflow over voltage",
    "Anti-backflow over frequency",
    "PV over voltage",
    "PV under voltage",
    "PV reverse polarity",
    "Battery over temperature",
    "Battery over voltage",
]

PH1000_WARNING_BITS = {
    0: "Fan error",
    1: "Battery over temperature",
    2: "Battery over voltage",
    3: "PV over voltage",
    4: "PV under voltage",
    5: "PV reverse polarity",
    6: "Grid over voltage",
    7: "Grid under voltage",
    8: "Grid over frequency",
    9: "Grid under frequency",
    10: "Grid over current",
    11: "Anti-backflow over current",
    12: "Anti-backflow over voltage",
    13: "Anti-backflow over frequency",
}

# ──────────────────────────────────────────────────────────────────────
# Device definitions
# ──────────────────────────────────────────────────────────────────────

def _make_pc1800() -> DeviceDefinition:
    """PC1800 PV Charger."""
    return DeviceDefinition(
        name="PC1800",
        protocol_type="Pc1800",
        default_baudrate=9600,
        default_device_id=1,
        scan_start=10000,
        identity=[
            Register(10000, "MachineTypeH", description="2 ASCII chars"),
            Register(10001, "MachineTypeL", description="Numeric suffix"),
            Register(10002, "SerialNumberH", description="Serial high (5 digits)"),
            Register(10003, "SerialNumberL", description="Serial low (5 digits)"),
            Register(10004, "HardwareVersion", description="HW version"),
            Register(10005, "SoftwareVersion", description="SW version"),
            Register(10006, "PvVoltageC", description="PV voltage calibration"),
            Register(10007, "BatteryVoltageC", description="Batt voltage calibration"),
            Register(10008, "ChargerCurrentC", description="Charger current calibration"),
        ],
        settings=[
            Register(10101, "ChargerWorkEnable", coefficient=1.0, signed=True,
                     enum_map={0: "OFF", 1: "ON"}, description="0=OFF, 1=ON"),
            Register(10103, "BatteryFloatVoltage", coefficient=0.1, signed=True,
                     unit="V", description="Float voltage"),
            Register(10104, "BatteryAbsorptionVoltage", coefficient=0.1, signed=True,
                     unit="V", description="Absorption voltage"),
            Register(10105, "BatteryLowVoltage", coefficient=0.1, signed=True,
                     unit="V", description="Low voltage"),
            Register(10107, "BatteryHighVoltage", coefficient=0.1, signed=True,
                     unit="V", description="High voltage"),
            Register(10108, "MaxChargerCurrent", coefficient=0.1, signed=True,
                     unit="A", description="Max charger current"),
            Register(10110, "BatteryType", coefficient=1.0, signed=True,
                     enum_map=BATTERY_TYPE, description="Battery type"),
            Register(10111, "BatteryAh", coefficient=1.0, signed=True,
                     unit="Ah", description="Battery capacity"),
            Register(10112, "RemoveAccumulatedData", coefficient=1.0, signed=True,
                     description="Reset accumulated data"),
            Register(10113, "BatteryVoltageGrade", coefficient=1.0, signed=True,
                     enum_map={0: "auto", 12: "12V", 24: "24V", 36: "36V", 48: "48V"},
                     description="0=auto, 12/24/36/48V"),
            Register(10116, "CvChargingMaxTime", coefficient=1.0, signed=True,
                     unit="min", description="CV charging max time"),
            Register(10117, "TempCompensationRatio", coefficient=0.1, signed=True,
                     unit="mV/C", description="Temp compensation"),
            Register(10118, "BatteryEqualizationEnable", coefficient=1.0, signed=True,
                     description="EQ enable"),
            Register(10119, "BatteryEqualizationVoltage", coefficient=0.1, signed=True,
                     unit="V", description="EQ voltage"),
            Register(10120, "MaxCurrentOfBatteryEqualization", coefficient=0.1, signed=True,
                     unit="A", description="Max EQ current"),
            Register(10121, "BatteryEqualizedTime", coefficient=1.0, signed=True,
                     unit="min", description="EQ duration"),
            Register(10122, "BatteryEqualizedTimeout", coefficient=1.0, signed=True,
                     unit="min", description="EQ timeout"),
            Register(10123, "EqualizationInterval", coefficient=1.0, signed=True,
                     unit="days", description="EQ interval"),
            Register(10124, "EqualizationActivedImmediately", coefficient=1.0, signed=True,
                     description="Force EQ now"),
            Register(10125, "SystemSetting", coefficient=1.0, signed=True,
                     description="Bitmask: bit2=PageLock, bit6=Backlight"),
            Register(10126, "ResetTheParameter", coefficient=1.0, signed=True,
                     description="Factory reset"),
        ],
        status=[
            Register(15201, "ChargerWorkstate", coefficient=1.0, signed=False,
                     enum_map={0: "Init", 1: "Selftest", 2: "Work", 3: "Stop"},
                     description="Work state"),
            Register(15202, "MpptState", coefficient=1.0, signed=False,
                     enum_map={0: "Stop", 1: "MPPT", 2: "Current limiting"},
                     description="MPPT state"),
            Register(15203, "ChargingState", coefficient=1.0, signed=False,
                     enum_map={0: "Stop", 1: "Absorb", 2: "Float", 3: "EQ"},
                     description="Charging state"),
            Register(15205, "PvVoltage", coefficient=0.1, signed=True, unit="V",
                     description="PV voltage"),
            Register(15206, "BatteryVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Battery voltage"),
            Register(15207, "ChargerCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Charger current"),
            Register(15208, "ChargerPower", coefficient=1.0, signed=True, unit="W",
                     description="Charger power"),
            Register(15209, "RadiatorTemp", coefficient=1.0, signed=True, unit="C",
                     description="Radiator temp"),
            Register(15210, "ExternalTemp", coefficient=1.0, signed=True, unit="C",
                     description="External temp"),
            Register(15211, "BatteryRelay", coefficient=1.0, signed=False,
                     enum_map=RELAY_STATE, description="Battery relay"),
            Register(15212, "PvRelay", coefficient=1.0, signed=False,
                     enum_map=RELAY_STATE, description="PV relay"),
            Register(15213, "ErrorMessage", coefficient=1.0, signed=False,
                     bit_map=COMMON_FAULT_BITS, description="16-bit fault bitmask"),
            Register(15214, "WarningMessage", coefficient=1.0, signed=False,
                     bit_map=COMMON_WARNING_BITS, description="16-bit warning bitmask"),
            Register(15215, "BattVolGrade", coefficient=1.0, signed=False, unit="V",
                     description="Battery voltage grade"),
            Register(15216, "RatedCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Rated current"),
            Register(15217, "AccumulatedPvPowerH", coefficient=1000.0, signed=True,
                     description="Energy high word"),
            Register(15218, "AccumulatedPvPowerL", coefficient=0.1, signed=True,
                     unit="kWh", description="Energy low word"),
            Register(15219, "AccumulatedDay", coefficient=1.0, signed=True,
                     description="Accumulated days"),
            Register(15220, "AccumulatedHour", coefficient=1.0, signed=True,
                     description="Accumulated hours"),
            Register(15221, "AccumulatedMinute", coefficient=1.0, signed=True,
                     description="Accumulated minutes"),
            Register(15222, "CommunicationProtocolEdition", coefficient=1.0, signed=False,
                     description="Protocol edition (e.g. 10414)"),
            Register(15223, "SOC", coefficient=1.0, signed=False, unit="%",
                     description="State of charge"),
            Register(15224, "ArrowFlag", coefficient=1.0, signed=False,
                     description="10-bit: bit0=PV, bit2=batt charge"),
        ],
        scan_schedule=[
            (10000, 9),
            (10101, 25),
            (15201, 24),
        ],
        writable_addrs=[
            10002, 10003, 10006, 10007, 10008,
            10101, 10103, 10104, 10105, 10108, 10110, 10111,
            10112, 10113, 10116, 10117, 10118, 10119, 10120,
            10121, 10122, 10123, 10124, 10125, 10126,
            15205, 15206, 15207,
        ],
    )


def _make_ph1800() -> DeviceDefinition:
    """PH1800 / EP1800 / Cdy10414M hybrid inverter (protocol 1.04.14)."""
    # Charger calibration registers (1xxxx)
    _charger_cal = [
        Register(10006, "PvVoltageC", description="PV voltage calibration"),
        Register(10007, "ChrBatteryVoltageC", description="Batt voltage calibration"),
        Register(10008, "ChargerCurrentC", description="Charger current calibration"),
    ]
    # Charger settings registers (10103-10111)
    _charger_settings = [
        Register(10103, "FloatVoltage", coefficient=0.1, signed=True, unit="V"),
        Register(10104, "AbsorptionVoltage", coefficient=0.1, signed=True, unit="V"),
        Register(10105, "ChrBatteryLowVoltage", coefficient=0.1, signed=True, unit="V"),
        Register(10108, "MaxChargerCurrent", coefficient=0.1, signed=True, unit="A"),
        Register(10110, "BatteryType", coefficient=1.0, signed=True, enum_map=BATTERY_TYPE),
        Register(10111, "BatteryAh", coefficient=1.0, signed=True, unit="Ah"),
    ]
    # Charger status registers (15201-15216)
    _charger_status = [
        Register(15201, "ChrWorkstateNo", coefficient=1.0, signed=False,
                 enum_map={0: "Init", 1: "Selftest", 2: "Work", 3: "Stop"}),
        Register(15202, "MpptStateNo", coefficient=1.0, signed=False,
                 enum_map={0: "Stop", 1: "MPPT", 2: "Current limiting"}),
        Register(15203, "ChargingStateNo", coefficient=1.0, signed=False,
                 enum_map={0: "Stop", 1: "Absorb", 2: "Float", 3: "EQ"}),
        Register(15205, "PvVoltage", coefficient=0.1, signed=True, unit="V"),
        Register(15206, "ChrBatteryVoltage", coefficient=0.1, signed=True, unit="V"),
        Register(15207, "ChargerCurrent", coefficient=0.1, signed=True, unit="A"),
        Register(15208, "ChargerPower", coefficient=1.0, signed=True, unit="W"),
        Register(15209, "RadiatorTemp", coefficient=1.0, signed=True, unit="C"),
        Register(15210, "ExternalTemp", coefficient=1.0, signed=True, unit="C"),
        Register(15211, "BatteryRelayNo", coefficient=1.0, signed=False, enum_map=RELAY_STATE),
        Register(15212, "PvRelayNo", coefficient=1.0, signed=False, enum_map=RELAY_STATE),
        Register(15213, "ChrError1", coefficient=1.0, signed=False, bit_map=COMMON_FAULT_BITS),
        Register(15214, "ChrWarning1", coefficient=1.0, signed=False, bit_map=COMMON_WARNING_BITS),
        Register(15215, "BattVolGrade", coefficient=1.0, signed=False, unit="V"),
        Register(15216, "RatedCurrent", coefficient=0.1, signed=True, unit="A"),
    ]

    return DeviceDefinition(
        name="PH1800 / EP1800 / Cdy10414M",
        protocol_type="Ph18Series",
        default_baudrate=19200,
        default_device_id=4,
        scan_start=20000,
        identity=[
            Register(20000, "MachineTypeH", coefficient=1.0, signed=False,
                     description="2 ASCII chars"),
            Register(20001, "MachineTypeL", coefficient=1.0, signed=False,
                     description="Numeric suffix"),
            Register(20002, "SerialNumberH", coefficient=1.0, signed=True,
                     description="Serial high (5 digits)"),
            Register(20003, "SerialNumberL", coefficient=1.0, signed=True,
                     description="Serial low (5 digits)"),
            Register(20004, "HardwareNo", coefficient=1.0, signed=False,
                     description="HW version (X.XX)"),
            Register(20005, "SoftwareNo", coefficient=1.0, signed=False,
                     description="SW version"),
            Register(20006, "ProtocolEditionNo", coefficient=1.0, signed=False,
                     description="Protocol edition (10414 → 1.04.14)"),
        ],
        calibration=[
            Register(20009, "BatteryVoltageC", coefficient=1.0, signed=True,
                     description="Battery voltage calibration"),
            Register(20010, "InverterVoltageC", coefficient=1.0, signed=True,
                     description="Inverter voltage calibration"),
            Register(20011, "GridVoltageC", coefficient=1.0, signed=True,
                     description="Grid voltage calibration"),
            Register(20012, "BusVoltageC", coefficient=1.0, signed=True,
                     description="Bus voltage calibration"),
            Register(20013, "ControlCurrentC", coefficient=1.0, signed=True,
                     description="Control current calibration"),
            Register(20014, "InverterCurrentC", coefficient=1.0, signed=True,
                     description="Inverter current calibration"),
            Register(20015, "GridCurrentC", coefficient=1.0, signed=True,
                     description="Grid current calibration"),
            Register(20016, "LoadCurrentC", coefficient=1.0, signed=True,
                     description="Load current calibration"),
            *_charger_cal,
        ],
        settings=[
            Register(20101, "InverterOffgridWorkEnable", coefficient=1.0, signed=True,
                     description="Off-grid work enable"),
            Register(20102, "InverterOutputVoltageSet", coefficient=0.1, signed=True,
                     unit="V", description="Output voltage set"),
            Register(20103, "InverterOutputFrequencySet", coefficient=0.01, signed=True,
                     unit="Hz", description="Output frequency set"),
            Register(20104, "InverterSearchModeEnable", coefficient=1.0, signed=True,
                     description="Search mode enable"),
            Register(20108, "InverterDischargerToGridEnable", coefficient=1.0, signed=True,
                     description="Discharge to grid enable"),
            Register(20109, "EnergyUseMode", coefficient=1.0, signed=False,
                     enum_map={"SBU": "SBU", "SUB": "SUB", "UTI": "UTI", "SOL": "SOL"},
                     description="Energy use mode"),
            Register(20111, "GridProtectStandard", coefficient=1.0, signed=False,
                     enum_map={"VDE4105": "VDE4105", "UPS": "UPS", "Home": "Home", "GEN": "GEN"},
                     description="Grid protection standard"),
            Register(20112, "SolarUseAim", coefficient=1.0, signed=False,
                     enum_map={"LBU": "LBU", "BLU": "BLU"},
                     description="Solar use aim"),
            Register(20113, "InverterMaxDischargerCurrent", coefficient=0.1, signed=True,
                     unit="A", description="Max discharge current"),
            Register(20118, "BatteryStopDischargingVoltage", coefficient=0.1, signed=True,
                     unit="V", description="Stop discharge voltage"),
            Register(20119, "BatteryStopChargingVoltage", coefficient=0.1, signed=True,
                     unit="V", description="Stop charge voltage"),
            Register(20125, "GridMaxChargerCurrentSet", coefficient=0.1, signed=True,
                     unit="A", description="Max grid charger current"),
            Register(20127, "BatteryLowVoltage", coefficient=0.1, signed=True,
                     unit="V", description="Low voltage"),
            Register(20128, "BatteryHighVoltage", coefficient=0.1, signed=True,
                     unit="V", description="High voltage"),
            Register(20132, "MaxCombineChargerCurrent", coefficient=0.1, signed=True,
                     unit="A", description="Max combined charger current"),
            Register(20142, "SystemSetting", coefficient=1.0, signed=False,
                     description="16-bit: bit0=OLRestartForbid, bit1=OTRestartForbid, "
                                 "bit2=OLBypassForbid, bit3=PageLock, bit4=GridBuzz, "
                                 "bit5=BuzzForbid, bit6=Backlight, bit7=RecordFault"),
            Register(20143, "ChargerSourcePriority", coefficient=1.0, signed=False,
                     enum_map={0: "Solar first", 2: "Solar+Utility", 3: "Only Solar"},
                     description="Charger source priority"),
            *_charger_settings,
        ],
        status=[
            Register(25201, "WorkStateNo", coefficient=1.0, signed=False,
                     enum_map=WORK_STATE_INV, description="Work state"),
            Register(25202, "AcVoltageGrade", coefficient=1.0, signed=False, unit="V",
                     description="AC voltage grade"),
            Register(25203, "RatedPower", coefficient=1.0, signed=False, unit="VA",
                     description="Rated power"),
            Register(25205, "BatteryVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Battery voltage"),
            Register(25206, "InverterVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Inverter voltage"),
            Register(25207, "GridVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Grid voltage"),
            Register(25208, "BusVoltage", coefficient=1.0, signed=True,
                     description="Bus voltage"),
            Register(25209, "ControlCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Control current"),
            Register(25210, "InverterCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Inverter current"),
            Register(25211, "GridCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Grid current"),
            Register(25212, "LoadCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Load current"),
            Register(25213, "PInverter", coefficient=1.0, signed=True, unit="W",
                     description="Inverter power"),
            Register(25214, "PGrid", coefficient=1.0, signed=True, unit="W",
                     description="Grid power"),
            Register(25215, "PLoad", coefficient=1.0, signed=True, unit="W",
                     description="Load power"),
            Register(25216, "LoadPercent", coefficient=1.0, signed=False, unit="%",
                     description="Load percentage"),
            Register(25217, "SInverter", coefficient=1.0, signed=True, unit="VA",
                     description="Inverter apparent power"),
            Register(25218, "SGrid", coefficient=1.0, signed=True, unit="VA",
                     description="Grid apparent power"),
            Register(25219, "Sload", coefficient=1.0, signed=True, unit="VA",
                     description="Load apparent power"),
            Register(25221, "Qinverter", coefficient=1.0, signed=True, unit="var",
                     description="Inverter reactive power"),
            Register(25222, "Qgrid", coefficient=1.0, signed=True, unit="var",
                     description="Grid reactive power"),
            Register(25223, "Qload", coefficient=1.0, signed=True, unit="var",
                     description="Load reactive power"),
            Register(25225, "InverterFrequency", coefficient=0.01, signed=True, unit="Hz",
                     description="Inverter frequency"),
            Register(25226, "GridFrequency", coefficient=0.01, signed=True, unit="Hz",
                     description="Grid frequency"),
            Register(25229, "InverterMaxNumber", coefficient=1.0, signed=False,
                     description="Max inverter count"),
            Register(25230, "CombineType", coefficient=1.0, signed=False,
                     description="Combination type"),
            Register(25231, "InverterNumber", coefficient=1.0, signed=False,
                     description="Inverter count"),
            Register(25233, "AcRadiatorTemp", coefficient=1.0, signed=True, unit="C",
                     description="AC radiator temp"),
            Register(25234, "TransformerTemp", coefficient=1.0, signed=True, unit="C",
                     description="Transformer temp"),
            Register(25235, "DcRadiatorTemp", coefficient=1.0, signed=True, unit="C",
                     description="DC radiator temp"),
            Register(25237, "InverterRelayStateNo", coefficient=1.0, signed=False,
                     enum_map=RELAY_STATE, description="Inverter relay"),
            Register(25238, "GridRelayStateNo", coefficient=1.0, signed=False,
                     enum_map=RELAY_STATE, description="Grid relay"),
            Register(25239, "LoadRelayStateNo", coefficient=1.0, signed=False,
                     enum_map=RELAY_STATE, description="Load relay"),
            Register(25240, "NLineRelayStateNo", coefficient=1.0, signed=False,
                     enum_map=RELAY_STATE, description="Neutral line relay"),
            Register(25241, "DcRelayStateNo", coefficient=1.0, signed=False,
                     enum_map=RELAY_STATE, description="DC relay"),
            Register(25242, "EarthRelayStateNo", coefficient=1.0, signed=False,
                     enum_map=RELAY_STATE, description="Earth relay"),
            Register(25261, "Error1", coefficient=1.0, signed=False,
                     bit_map=COMMON_FAULT_BITS, description="Inverter faults bits 0-15"),
            Register(25262, "Error2", coefficient=1.0, signed=False,
                     bit_map=COMMON_FAULT_BITS, description="Inverter faults bits 16-31"),
            Register(25263, "Error3", coefficient=1.0, signed=False,
                     description="Reserved"),
            Register(25265, "Warning1", coefficient=1.0, signed=False,
                     bit_map=COMMON_WARNING_BITS, description="Inverter warnings bits 0-15"),
            Register(25266, "Warning2", coefficient=1.0, signed=False,
                     bit_map=COMMON_WARNING_BITS, description="Inverter warnings bits 16-31"),
            Register(25273, "BattPower", coefficient=1.0, signed=True, unit="W",
                     description="Battery power"),
            Register(25274, "BattCurrent", coefficient=1.0, signed=True, unit="A",
                     description="Battery current"),
            Register(25275, "BattVoltageGrade", coefficient=1.0, signed=False, unit="V",
                     description="Battery voltage grade"),
            Register(25277, "RatedPowerW", coefficient=1.0, signed=True, unit="W",
                     description="Rated power W"),
            Register(25278, "CommunicationProtocolEdition", coefficient=1.0, signed=False,
                     description="Protocol edition"),
            *_charger_status,
        ],
        energy=[
            RegisterPair(25245, 25246, "AccumulatedChargerPower", coefficient=0.1,
                         unit="kWh", description="Total charged energy"),
            RegisterPair(25247, 25248, "AccumulatedDischargerPower", coefficient=0.1,
                         unit="kWh", description="Total discharged energy"),
            RegisterPair(25249, 25250, "AccumulatedBuyPower", coefficient=0.1,
                         unit="kWh", description="Total buy energy"),
            RegisterPair(25251, 25252, "AccumulatedSellPower", coefficient=0.1,
                         unit="kWh", description="Total sell energy"),
            RegisterPair(25253, 25254, "AccumulatedLoadPower", coefficient=0.1,
                         unit="kWh", description="Total load energy"),
            RegisterPair(25255, 25256, "AccumulatedSelfusePower", coefficient=0.1,
                         unit="kWh", description="Total self-use energy"),
            RegisterPair(25257, 25258, "AccumulatedPvsellPower", coefficient=0.1,
                         unit="kWh", description="Total PV-sell energy"),
            RegisterPair(25259, 25260, "AccumulatedGridChargerPower", coefficient=0.1,
                         unit="kWh", description="Total grid-charger energy"),
        ],
        daily_energy=[
            Register(25329, "DailyEnergy", coefficient=0.1, signed=True, unit="kWh",
                     description="Daily energy"),
        ],
        errors=[
            Register(25261, "Error1", coefficient=1.0, signed=False,
                     bit_map=COMMON_FAULT_BITS, description="Inverter fault bits 0-15"),
            Register(25262, "Error2", coefficient=1.0, signed=False,
                     bit_map=COMMON_FAULT_BITS, description="Inverter fault bits 16-31"),
        ],
        warnings=[
            Register(25265, "Warning1", coefficient=1.0, signed=False,
                     bit_map=COMMON_WARNING_BITS, description="Inverter warning bits 0-15"),
            Register(25266, "Warning2", coefficient=1.0, signed=False,
                     bit_map=COMMON_WARNING_BITS, description="Inverter warning bits 16-31"),
        ],
        scan_schedule=[
            (10001, 8),
            (10103, 10),
            (15201, 21),
            (20000, 17),
            (20101, 43),
            (25201, 79),
        ],
        writable_addrs=[
            10103, 10104, 10105, 10108, 10110,
            20101, 20102, 20103, 20104, 20108, 20109, 20111, 20112, 20113,
            20118, 20119, 20125, 20127, 20128, 20132, 20142, 20143,
        ],
        needs_arrow_flag=True,
    )


def _make_pv3500pro() -> DeviceDefinition:
    """PV3500PRO — similar to 1.04.14 but no protocol edition / arrow flag."""
    base = _make_ph1800()
    base.name = "PV3500PRO"
    base.energy_no_decimal = True  # kWh = H*1000+L, no ×0.1
    base.needs_arrow_flag = False
    # Remove protocol edition registers
    base.identity = [r for r in base.identity if r.address != 20006]
    base.status = [r for r in base.status if r.address not in (25277, 25278)]
    # 25275 = SOC instead of voltage grade
    for r in base.status:
        if r.address == 25275:
            r.name = "BattSOC"
            r.unit = "%"
            r.description = "Battery SOC"
            r.enum_map = None
    return base


def _make_ep2000pro() -> DeviceDefinition:
    """EP2000PRO / PV2000PRO."""
    return DeviceDefinition(
        name="EP2000PRO / PV2000PRO",
        protocol_type="EPSeries",
        default_baudrate=9600,
        default_device_id=10,
        scan_start=30000,
        identity=[
            Register(30000, "MachineType", coefficient=1.0, signed=False,
                     enum_map={0: "EP2000PRO", 2: "PV2000PRO", 3: "EP3300"},
                     description="Machine type"),
            Register(30001, "SoftwareVersion", coefficient=1.0, signed=False,
                     description="Software version"),
        ],
        status=[
            Register(30002, "WorkState", coefficient=1.0, signed=False,
                     description="Work state (uint)"),
            Register(30003, "BatClass", coefficient=1.0, signed=False, unit="V",
                     description="Battery class"),
            Register(30004, "RatedPower", coefficient=1.0, signed=False, unit="W",
                     description="Rated power"),
            Register(30005, "GridVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Grid voltage"),
            Register(30006, "GridFrequency", coefficient=0.1, signed=True, unit="Hz",
                     description="Grid frequency"),
            Register(30007, "OutputVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Output voltage"),
            Register(30008, "OutputFrequency", coefficient=0.1, signed=True, unit="Hz",
                     description="Output frequency"),
            Register(30009, "LoadCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Load current"),
            Register(30010, "LoadPower", coefficient=1.0, signed=True, unit="W",
                     description="Load power"),
            Register(30012, "LoadPercent", coefficient=1.0, signed=False, unit="%",
                     description="Load percentage"),
            Register(30013, "LoadState", coefficient=1.0, signed=False,
                     description="Load state"),
            Register(30014, "BatteryVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Battery voltage"),
            Register(30015, "BatteryCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Battery current"),
            Register(30017, "BatterySoc", coefficient=1.0, signed=False, unit="%",
                     description="Battery SOC"),
            Register(30018, "TransformerTemp", coefficient=1.0, signed=True, unit="C",
                     description="Transformer temp"),
            Register(30019, "AvrState", coefficient=1.0, signed=False,
                     enum_map=AVR_STATE, description="AVR state"),
            Register(30020, "BuzzerState", coefficient=1.0, signed=False,
                     enum_map={0: "Normal", 1: "Silence"},
                     description="Buzzer state"),
            Register(30021, "FaultId", coefficient=1.0, signed=False,
                     description="Single fault ID"),
            Register(30022, "AlarmId", coefficient=1.0, signed=False,
                     bit_map=EP2000_ALARM_BITS, description="16-bit alarm bitmask"),
            Register(30023, "ChargeState", coefficient=1.0, signed=False,
                     enum_map=CHARGE_STAGE, description="Charge stage"),
            Register(30024, "ChargeFlag", coefficient=1.0, signed=False,
                     description="Grid charge flag"),
            Register(30025, "MainSw", coefficient=1.0, signed=False,
                     description="Main switch"),
            Register(30026, "DelayType", coefficient=1.0, signed=False,
                     description="Delay type"),
        ],
        settings=[
            Register(31000, "GridFrequencyType", coefficient=1.0, signed=False,
                     enum_map=GRID_FREQ_TYPE, description="Grid freq type"),
            Register(31001, "GridVoltageType", coefficient=1.0, signed=False,
                     enum_map=GRID_VOLT_TYPE, description="Grid voltage type"),
            Register(31002, "ShutdownVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Shutdown voltage"),
            Register(31003, "AbsorptionChargeVoltage", coefficient=0.1, signed=True,
                     unit="V", description="Absorption voltage"),
            Register(31004, "FloatChargeVoltage", coefficient=0.1, signed=True,
                     unit="V", description="Float voltage"),
            Register(31005, "BulkCurrent", coefficient=1.0, signed=True, unit="A",
                     description="Bulk current"),
            Register(31006, "Buzzer", coefficient=1.0, signed=False,
                     enum_map={0: "Normal", 1: "Silence"}, description="Buzzer"),
            Register(31007, "EnableGridCharge", coefficient=1.0, signed=True,
                     description="Enable grid charging"),
            Register(31009, "EnableBacklight", coefficient=1.0, signed=False,
                     description="Enable backlight"),
            Register(31016, "UtilityPowerOn", coefficient=1.0, signed=True,
                     description="Utility power on"),
            Register(31017, "EnableOverLoadRecover", coefficient=1.0, signed=False,
                     description="Enable over-load recovery"),
        ],
        calibration=[
            Register(31100, "BatteryVoltageCC", coefficient=1.0, signed=True,
                     description="Battery voltage calibration"),
            Register(31101, "BatteryChargeCurrentCC", coefficient=1.0, signed=True,
                     description="Battery charge current calibration"),
            Register(31102, "GridVoltageCC", coefficient=1.0, signed=True,
                     description="Grid voltage calibration"),
            Register(31103, "OutputVoltageCC", coefficient=1.0, signed=True,
                     description="Output voltage calibration"),
            Register(31104, "LoadCurrentCC", coefficient=1.0, signed=True,
                     description="Load current calibration"),
            Register(31105, "BatteryDischargeCurrentCC", coefficient=1.0, signed=True,
                     description="Battery discharge current calibration"),
        ],
        scan_schedule=[
            (30000, 27),
            (31000, 10),
            (31011, 8),
            (31100, 6),
        ],
        writable_addrs=[
            31000, 31001, 31002, 31003, 31004, 31005, 31006, 31007,
            31009, 31016, 31017,
            31100, 31101, 31102, 31103, 31104, 31105,
        ],
    )


def _make_ep3300() -> DeviceDefinition:
    """EP3300."""
    base = _make_ep2000pro()
    base.name = "EP3300"
    # Update status with EP3300-specific fields
    base.status = [
        Register(30000, "MachineTypeI", coefficient=1.0, signed=False,
                 enum_map={0: "EP2000PRO", 2: "PV2000PRO", 3: "EP3300"},
                 description="Machine type"),
        Register(30001, "SoftwareVersionI", coefficient=1.0, signed=False,
                 description="SW version (5 digits → 166-00XXX-YY)"),
        Register(30002, "WorkStateI", coefficient=1.0, signed=False,
                 enum_map=WORK_STATE_EP3300, description="Work state"),
        Register(30003, "BatClass", coefficient=1.0, signed=False, unit="V",
                 description="Battery class"),
        Register(30004, "RatedPower", coefficient=1.0, signed=False, unit="W",
                 description="Rated power"),
        Register(30005, "GridVoltage", coefficient=0.1, signed=True, unit="V",
                 description="Grid voltage"),
        Register(30006, "GridFrequency", coefficient=0.1, signed=True, unit="Hz",
                 description="Grid frequency"),
        Register(30007, "OutputVoltage", coefficient=0.1, signed=True, unit="V",
                 description="Output voltage"),
        Register(30008, "OutputFrequency", coefficient=0.1, signed=True, unit="Hz",
                 description="Output frequency"),
        Register(30009, "LoadCurrent", coefficient=0.1, signed=True, unit="A",
                 description="Load current"),
        Register(30010, "LoadPower", coefficient=1.0, signed=True, unit="W",
                 description="Load power"),
        Register(30012, "LoadPercent", coefficient=1.0, signed=False, unit="%",
                 description="Load percentage"),
        Register(30014, "BatteryVoltage", coefficient=0.1, signed=True, unit="V",
                 description="Battery voltage"),
        Register(30015, "BatteryCurrent", coefficient=0.1, signed=True, unit="A",
                 description="Battery current"),
        Register(30016, "BatteryTemperature", coefficient=1.0, signed=True, unit="C",
                 description="Battery temperature"),
        Register(30017, "BatterySoc", coefficient=1.0, signed=False, unit="%",
                 description="Battery SOC"),
        Register(30018, "TransformerTemp", coefficient=1.0, signed=True, unit="C",
                 description="Transformer temp"),
        Register(30020, "BuzzerStateI", coefficient=1.0, signed=False,
                 enum_map={0: "Normal", 1: "Silence"}, description="Buzzer"),
        Register(30021, "SystemFaultId", coefficient=1.0, signed=False,
                 description="System fault ID"),
        Register(30022, "SystemAlarmId", coefficient=1.0, signed=False,
                 bit_map=EP3300_ALARM_BITS, description="16-bit alarm bitmask"),
        Register(30023, "ChargeStageI", coefficient=1.0, signed=False,
                 enum_map=CHARGE_STAGE, description="Charge stage"),
        Register(30024, "GridChargeFlagI", coefficient=1.0, signed=False,
                 enum_map={0: "No grid charge", 1: "Grid charge"},
                 description="Grid charge flag"),
        Register(30025, "GridState", coefficient=1.0, signed=False,
                 enum_map={0: "No grid", 1: "Normal", 2: "Abnormal"},
                 description="Grid state"),
    ]
    base.settings = [
        *base.settings,
        Register(31014, "Point2Inv", coefficient=0.1, signed=True, unit="V",
                 description="Point 2 inverter"),
        Register(31015, "Point2Grid", coefficient=0.1, signed=True, unit="V",
                 description="Point 2 grid"),
        Register(31020, "PowerSavingModeEnable", coefficient=1.0, signed=False,
                 description="Power saving mode"),
        Register(31021, "SearchTime", coefficient=1.0, signed=False,
                 enum_map={5: "5 s", 30: "30 s"}, description="Search time"),
        Register(31022, "OutputSourcePriority", coefficient=1.0, signed=False,
                 enum_map={0: "Grid", 1: "Battery"}, description="Output source priority"),
        Register(31023, "AcInputVoltageRange", coefficient=1.0, signed=False,
                 enum_map=INPUT_RANGE, description="AC input voltage range"),
    ]
    base.calibration = [
        *base.calibration,
        Register(31108, "BatteryDischargeCurrentCC", coefficient=1.0, signed=True,
                 description="Battery discharge current calibration"),
    ]
    # Serial number
    base.identity.extend([
        Register(31200, "SerialNumberH", coefficient=1.0, signed=True,
                 description="Serial high (5 digits)"),
        Register(31201, "SerialNumberL", coefficient=1.0, signed=True,
                 description="Serial low (5 digits)"),
    ])
    # Commands
    base.commands = [
        Register(32000, "RestoreFactorySettings", coefficient=1.0, signed=False,
                 description="Restore factory settings"),
        Register(32001, "RemoteReset", coefficient=1.0, signed=False,
                 description="Remote reset"),
    ]
    base.scan_schedule = [
        (30000, 26),
        (31000, 10),
        (31011, 8),
        (31020, 4),
        (31100, 10),
        (31200, 2),
        (32000, 2),
    ]
    base.writable_addrs = [
        31000, 31001, 31002, 31003, 31004, 31005, 31006, 31007,
        31009, 31014, 31015, 31020, 31021, 31022, 31023,
        31100, 31101, 31102, 31103, 31104, 31108,
    ]
    return base


def _make_ep3300tlv() -> DeviceDefinition:
    """EP3300 TLV — three-line voltage (L1/L2 output)."""
    base = _make_ep3300()
    base.name = "EP3300 TLV"
    # Update work state
    for r in base.status:
        if r.address == 30002:
            r.enum_map = WORK_STATE_EP3300TLV
    # Add L1/L2 registers
    l1l2_status = [
        Register(30032, "InputVoltage", coefficient=0.1, signed=True, unit="V",
                 description="Input voltage"),
        Register(30033, "InputFrequency", coefficient=0.1, signed=True, unit="Hz",
                 description="Input frequency"),
        Register(30036, "L1OutputVoltage", coefficient=0.1, signed=True, unit="V",
                 description="L1 output voltage"),
        Register(30037, "L1OutputCurrent", coefficient=0.1, signed=True, unit="A",
                 description="L1 output current"),
        Register(30038, "L1Power", coefficient=1.0, signed=True, unit="W",
                 description="L1 power"),
        Register(30039, "L1ApparentPower", coefficient=1.0, signed=True, unit="VA",
                 description="L1 apparent power"),
        Register(30040, "L1Percent", coefficient=1.0, signed=False, unit="%",
                 description="L1 load percentage"),
        Register(30041, "L2OutputVoltage", coefficient=0.1, signed=True, unit="V",
                 description="L2 output voltage"),
        Register(30042, "L2OutputCurrent", coefficient=0.1, signed=True, unit="A",
                 description="L2 output current"),
        Register(30043, "L2Power", coefficient=1.0, signed=True, unit="W",
                 description="L2 power"),
        Register(30044, "L2ApparentPower", coefficient=1.0, signed=True, unit="VA",
                 description="L2 apparent power"),
        Register(30045, "L2Percent", coefficient=1.0, signed=False, unit="%",
                 description="L2 load percentage"),
        Register(30046, "L12OutputVoltage", coefficient=0.1, signed=True, unit="V",
                 description="L1-L2 output voltage"),
        Register(30047, "OutputFrequency", coefficient=0.1, signed=True, unit="Hz",
                 description="Output frequency"),
        Register(30048, "TotalPLoad", coefficient=1.0, signed=True, unit="W",
                 description="Total load power"),
        Register(30049, "TotalSLoad", coefficient=1.0, signed=True, unit="VA",
                 description="Total load apparent power"),
        Register(30050, "TotalLoadPercent", coefficient=1.0, signed=False, unit="%",
                 description="Total load percentage"),
    ]
    base.status.extend(l1l2_status)
    # L1/L2 calibration
    base.calibration.extend([
        Register(31111, "L1OutputVoltageCC", coefficient=1.0, signed=True,
                 description="L1 voltage calibration"),
        Register(31112, "L1OutputCurrentCC", coefficient=1.0, signed=True,
                 description="L1 current calibration"),
        Register(31113, "L2OutputVoltageCC", coefficient=1.0, signed=True,
                 description="L2 voltage calibration"),
        Register(31114, "L2OutputCurrentCC", coefficient=1.0, signed=True,
                 description="L2 current calibration"),
        Register(31115, "L12OutputVoltageCC", coefficient=1.0, signed=True,
                 description="L1-L2 voltage calibration"),
        Register(31116, "OutputFrequencyCC", coefficient=1.0, signed=True,
                 description="Output frequency calibration"),
    ])
    base.scan_schedule = [
        (30000, 27),
        (30030, 20),
        (31000, 10),
        (31011, 8),
        (31020, 9),
        (31100, 17),
        (31200, 2),
    ]
    base.writable_addrs.extend([
        31111, 31112, 31113, 31114, 31115, 31116, 31200, 31201,
    ])
    return base


def _make_pv2000pk() -> DeviceDefinition:
    """PV2000PK."""
    return DeviceDefinition(
        name="PV2000PK",
        protocol_type="EPSeries",
        default_baudrate=9600,
        default_device_id=10,
        scan_start=30000,
        identity=[
            Register(30000, "MachineType", coefficient=1.0, signed=False,
                     description="Machine type"),
            Register(30001, "SoftwareVersion", coefficient=1.0, signed=False,
                     description="Software version"),
        ],
        status=[
            Register(30002, "WorkState", coefficient=1.0, signed=False,
                     enum_map=WORK_STATE_PV2000PK, description="Work state"),
            Register(30003, "BatClass", coefficient=1.0, signed=False, unit="V",
                     description="Battery class"),
            Register(30004, "RatedPower", coefficient=1.0, signed=False, unit="W",
                     description="Rated power"),
            Register(30005, "GridVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Grid voltage"),
            Register(30006, "GridFrequency", coefficient=0.1, signed=True, unit="Hz",
                     description="Grid frequency"),
            Register(30007, "OutputVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Output voltage"),
            Register(30008, "OutputFrequency", coefficient=0.1, signed=True, unit="Hz",
                     description="Output frequency"),
            Register(30009, "LoadCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Load current"),
            Register(30010, "LoadPower", coefficient=1.0, signed=True, unit="W",
                     description="Load power"),
            Register(30011, "LoadVA", coefficient=1.0, signed=True, unit="VA",
                     description="Load apparent power"),
            Register(30012, "LoadPercent", coefficient=1.0, signed=False, unit="%",
                     description="Load percentage"),
            Register(30014, "BatteryVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Battery voltage"),
            Register(30015, "BatteryCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Battery current"),
            Register(30017, "BatterySOC", coefficient=1.0, signed=False, unit="%",
                     description="Battery SOC"),
            Register(30018, "InverterTransformerTemp", coefficient=1.0, signed=True,
                     unit="C", description="Inverter transformer temp"),
            Register(30019, "AVRState", coefficient=1.0, signed=False,
                     enum_map=AVR_STATE, description="AVR state"),
            Register(30021, "SystemFaultID", coefficient=1.0, signed=False,
                     description="System fault ID"),
            Register(30022, "SystemAlarmID", coefficient=1.0, signed=False,
                     description="9-item alarm array"),
            Register(30023, "ChargeStage", coefficient=1.0, signed=False,
                     enum_map=CHARGE_STAGE, description="Charge stage"),
            Register(30024, "GridChargeFlag", coefficient=1.0, signed=False,
                     description="Grid charge flag"),
            Register(30025, "MainSW", coefficient=1.0, signed=False,
                     description="Main switch"),
            Register(30026, "DelayType", coefficient=1.0, signed=False,
                     description="Delay type"),
            Register(30030, "PVStart", coefficient=1.0, signed=False,
                     description="PV start"),
            Register(30031, "PVFlag", coefficient=1.0, signed=False,
                     description="PV flag"),
            Register(30032, "PVChgFlag", coefficient=1.0, signed=False,
                     description="PV charge flag"),
            Register(30033, "PvTemp", coefficient=1.0, signed=True, unit="C",
                     description="PV temp"),
            Register(30034, "PvV", coefficient=0.1, signed=True, unit="V",
                     description="PV voltage"),
            Register(30035, "PvI", coefficient=0.1, signed=True, unit="A",
                     description="PV current"),
            Register(30036, "PVPower", coefficient=1.0, signed=True, unit="W",
                     description="PV power"),
            Register(30040, "ChgSource", coefficient=1.0, signed=False,
                     description="Charge source"),
            Register(30041, "OutSource", coefficient=1.0, signed=False,
                     description="Output source"),
        ],
        settings=[
            Register(31000, "GridFrequencyType", coefficient=1.0, signed=False,
                     enum_map=GRID_FREQ_TYPE, description="Grid freq type"),
            Register(31001, "GridVoltageType", coefficient=1.0, signed=False,
                     enum_map={220: "220V", 230: "230V"}, description="Grid voltage type"),
            Register(31002, "ShutdownVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Shutdown voltage"),
            Register(31003, "AbsorptionChargeVoltage", coefficient=0.1, signed=True,
                     unit="V", description="Absorption voltage"),
            Register(31004, "FloatChargeVoltage", coefficient=0.1, signed=True,
                     unit="V", description="Float voltage"),
            Register(31005, "BulkCurrent", coefficient=1.0, signed=True, unit="A",
                     description="Bulk current"),
            Register(31006, "Buzzer", coefficient=1.0, signed=False,
                     description="Buzzer"),
            Register(31009, "Enablebacklight", coefficient=1.0, signed=False,
                     description="Enable backlight"),
            Register(31011, "GridChargeCurrent", coefficient=1.0, signed=True,
                     unit="A", description="Grid charge current"),
            Register(31012, "OutPriority", coefficient=1.0, signed=False,
                     enum_map=OUTPUT_PRIORITY, description="Output priority"),
            Register(31013, "ChgPriority", coefficient=1.0, signed=False,
                     enum_map=CHG_PRIORITY, description="Charge priority"),
            Register(31014, "Point2Inv", coefficient=0.1, signed=True, unit="V",
                     description="Point 2 inverter"),
            Register(31015, "Point2Grid", coefficient=0.1, signed=True, unit="V",
                     description="Point 2 grid"),
            Register(31017, "EnableOverloadRecover", coefficient=1.0, signed=False,
                     description="Enable overload recover"),
        ],
        calibration=[
            Register(31100, "BatteryVoltageCC", coefficient=1.0, signed=True,
                     description="Battery voltage calibration"),
            Register(31101, "BatteryChargeCurrentCC", coefficient=1.0, signed=True,
                     description="Battery charge current calibration"),
            Register(31102, "GridVoltageCC", coefficient=1.0, signed=True,
                     description="Grid voltage calibration"),
            Register(31103, "OutputVoltageCC", coefficient=1.0, signed=True,
                     description="Output voltage calibration"),
            Register(31104, "LoadCurrentCC", coefficient=1.0, signed=True,
                     description="Load current calibration"),
            Register(31105, "BatteryDischargeCurrentCC", coefficient=1.0, signed=True,
                     description="Battery discharge current calibration"),
            Register(31106, "PvVoltageCC", coefficient=1.0, signed=True,
                     description="PV voltage calibration"),
            Register(31107, "PvCurrentCC", coefficient=1.0, signed=True,
                     description="PV current calibration"),
        ],
        scan_schedule=[
            (30000, 27),
            (30030, 12),
            (31000, 10),
            (31011, 8),
            (31100, 8),
        ],
        writable_addrs=[
            31000, 31001, 31002, 31003, 31004, 31005, 31006, 31009,
            31011, 31012, 31013, 31014, 31015, 31017,
            31100, 31101, 31102, 31103, 31104, 31105, 31106, 31107,
        ],
    )


def _make_ph1000() -> DeviceDefinition:
    """PH1000 hybrid inverter."""
    return DeviceDefinition(
        name="PH1000",
        protocol_type="Ph1000",
        default_baudrate=9600,
        default_device_id=5,
        scan_start=20001,
        identity=[
            Register(20001, "SerialnumberHigh", coefficient=1.0, signed=True,
                     description="Serial high"),
            Register(20002, "SerialnumberMiddle", coefficient=1.0, signed=True,
                     description="Serial middle"),
            Register(20003, "SerialnumberLow", coefficient=1.0, signed=True,
                     description="Serial low"),
            Register(20004, "Hardwareversion", coefficient=1.0, signed=False,
                     description="HW version (VX.Y)"),
            Register(20005, "Softwareversion", coefficient=1.0, signed=False,
                     description="SW version (hex → X.XY)"),
        ],
        settings=[
            Register(10105, "BatteryLowVoltage", coefficient=0.01, signed=True,
                     unit="V", description="Low voltage"),
            Register(10107, "BatteryHighvoltage", coefficient=0.01, signed=True,
                     unit="V", description="High voltage"),
            Register(10108, "MaxChargerCurrent", coefficient=1.0, signed=True,
                     unit="A", description="Max charger current"),
            Register(10110, "BatteryType", coefficient=1.0, signed=True,
                     enum_map={0: "Lead acid", 1: "Lithium"}, description="Battery type"),
            Register(10111, "BatteryAh", coefficient=1.0, signed=True, unit="Ah",
                     description="Battery capacity"),
            Register(10113, "EnergyUseMode", coefficient=1.0, signed=False,
                     enum_map=ENERGY_USE_MODE, description="Energy use mode"),
            Register(10114, "BatteryConstVoltChargeVoltage", coefficient=0.01,
                     signed=True, unit="V", description="Const volt charge"),
            Register(10115, "BatteryFloatChargeVoltage", coefficient=0.01,
                     signed=True, unit="V", description="Float charge"),
            Register(10116, "BatteryStopDisChargeVoltage", coefficient=0.01,
                     signed=True, unit="V", description="Stop discharge"),
            Register(20106, "InverterChargerFromGridEnable", coefficient=1.0,
                     signed=True, description="Charger from grid enable"),
            Register(20108, "InverterDisChargerToGridEnable", coefficient=1.0,
                     signed=True, description="Discharge to grid enable"),
            Register(20133, "ChargerStartTime", coefficient=1.0, signed=False,
                     description="Charger start time"),
            Register(20134, "ChargerEndTime", coefficient=1.0, signed=False,
                     description="Charger end time"),
            Register(20135, "AntiReflux", coefficient=1.0, signed=False,
                     description="Anti-reflux"),
            Register(20136, "Bypass", coefficient=1.0, signed=False,
                     description="Bypass"),
            Register(20161, "GridTieSafetyType", coefficient=1.0, signed=False,
                     description="Grid-tie safety standard"),
            Register(20183, "ReconnectTime", coefficient=1.0, signed=False,
                     unit="s", description="Reconnect time"),
            Register(20184, "StartdelayTime", coefficient=1.0, signed=False,
                     unit="s", description="Start delay time"),
            Register(20189, "LocalControl", coefficient=1.0, signed=False,
                     description="Local control"),
            Register(20190, "PfCharacteristicCurve", coefficient=1.0, signed=False,
                     description="P(f) curve"),
            Register(20191, "OutputQMode", coefficient=1.0, signed=False,
                     description="Output Q mode"),
            Register(20192, "ActivePowerSetting", coefficient=1.0, signed=False,
                     unit="%", description="Active power setting"),
            Register(20193, "ReactivePowerSetting", coefficient=1.0, signed=False,
                     unit="VAR", description="Reactive power setting"),
            Register(20194, "PfSetting", coefficient=0.001, signed=False,
                     description="PF setting"),
            Register(20211, "InverterRunStop", coefficient=1.0, signed=False,
                     description="Inverter run/stop"),
            Register(20213, "Removetheaccumulateddata", coefficient=1.0, signed=False,
                     description="Reset accumulated data"),
            Register(20039, "DCMPPTModeSet", coefficient=1.0, signed=False,
                     enum_map={0: "MPPT", 1: "DC source mode"},
                     description="DC MPPT mode"),
        ],
        status=[
            Register(15205, "WorkStateI", coefficient=1.0, signed=False,
                     enum_map=WORK_STATE_INV, description="Work state"),
            Register(15206, "BatteryVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Battery voltage"),
            Register(15207, "BatteryCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Battery current"),
            Register(15208, "BatteryPower", coefficient=1.0, signed=True, unit="W",
                     description="Battery power"),
            Register(15209, "ChargerTemperature", coefficient=0.1, signed=True,
                     unit="C", description="Charger temp"),
            Register(15210, "PV1Voltage", coefficient=0.1, signed=True, unit="V",
                     description="PV1 voltage"),
            Register(15211, "PV1Current", coefficient=0.01, signed=True, unit="A",
                     description="PV1 current"),
            Register(15212, "PV1Power", coefficient=1.0, signed=True, unit="W",
                     description="PV1 power"),
            Register(15213, "PV2Voltage", coefficient=0.1, signed=True, unit="V",
                     description="PV2 voltage"),
            Register(15214, "PV2Current", coefficient=0.01, signed=True, unit="A",
                     description="PV2 current"),
            Register(15215, "PV2Power", coefficient=1.0, signed=True, unit="W",
                     description="PV2 power"),
            Register(15216, "PV3Voltage", coefficient=0.1, signed=True, unit="V",
                     description="PV3 voltage"),
            Register(15217, "PV3Current", coefficient=0.01, signed=True, unit="A",
                     description="PV3 current"),
            Register(15218, "PV3Power", coefficient=1.0, signed=True, unit="W",
                     description="PV3 power"),
            Register(15219, "PvPower", coefficient=1.0, signed=True, unit="W",
                     description="Total PV power"),
            Register(15220, "BusVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Bus voltage"),
            Register(15221, "InverterVoltage", coefficient=0.1, signed=True, unit="V",
                     description="Inverter voltage"),
            Register(15222, "InverterCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Inverter current"),
            Register(15223, "SInverter", coefficient=1.0, signed=True, unit="VAR",
                     description="Inverter apparent power"),
            Register(15224, "Qinverter", coefficient=1.0, signed=True, unit="VAR",
                     description="Inverter reactive power"),
            Register(15225, "LoadCurrent", coefficient=0.1, signed=True, unit="A",
                     description="Load current"),
            Register(15226, "LoadPower", coefficient=1.0, signed=True, unit="W",
                     description="Load power"),
            Register(15227, "VgirdR", coefficient=0.1, signed=True, unit="V",
                     description="Grid R-phase voltage"),
            Register(15228, "VgirdS", coefficient=0.1, signed=True, unit="V",
                     description="Grid S-phase voltage"),
            Register(15229, "VgirdT", coefficient=0.1, signed=True, unit="V",
                     description="Grid T-phase voltage"),
            Register(15230, "IgirdR", coefficient=0.1, signed=True, unit="A",
                     description="Grid R-phase current"),
            Register(15231, "IgirdS", coefficient=0.1, signed=True, unit="A",
                     description="Grid S-phase current"),
            Register(15232, "IgirdT", coefficient=0.1, signed=True, unit="A",
                     description="Grid T-phase current"),
            Register(15233, "GridPower", coefficient=1.0, signed=True, unit="W",
                     description="Grid power"),
            Register(15234, "GridFrequency", coefficient=0.01, signed=True, unit="Hz",
                     description="Grid frequency"),
            Register(25233, "InverterTemperature", coefficient=0.1, signed=True,
                     unit="C", description="Inverter temp"),
            Register(25264, "ConnectTime", coefficient=1.0, signed=False,
                     unit="s", description="Connect time"),
            Register(25265, "WarningMessage1", coefficient=1.0, signed=False,
                     bit_map=PH1000_WARNING_BITS, description="16-bit warning bitmask"),
            Register(25274, "BatterySoc", coefficient=1.0, signed=False, unit="%",
                     description="Battery SOC"),
            Register(25355, "BatteryChargeStatus", coefficient=1.0, signed=False,
                     enum_map=BATTERY_CHARGE_STATUS, description="Battery charge status"),
            Register(25356, "BatteryReconnectTime", coefficient=1.0, signed=False,
                     unit="s", description="Battery reconnect time"),
        ],
        energy=[
            RegisterPair(25245, 25246, "TotalRechargeEnergy", coefficient=0.1,
                         unit="kWh", description="Total charged energy"),
            RegisterPair(25247, 25248, "TotalDischargeEnergy", coefficient=0.1,
                         unit="kWh", description="Total discharged energy"),
            RegisterPair(25251, 25252, "TotalSellEnergy", coefficient=0.1,
                         unit="kWh", description="Total sell energy"),
            RegisterPair(25257, 25258, "TotalGenerateEnergy", coefficient=0.1,
                         unit="kWh", description="Total generated energy"),
        ],
        daily_energy=[
            Register(25329, "DailySellEnergy", coefficient=0.1, signed=True,
                     unit="kWh", description="Daily sell energy"),
            Register(25330, "DailyGenerateEnergy", coefficient=0.1, signed=True,
                     unit="kWh", description="Daily generated energy"),
            Register(25331, "DailyRechargeEnergy", coefficient=0.1, signed=True,
                     unit="kWh", description="Daily recharge energy"),
            Register(25332, "DailyDischargeEnergy", coefficient=0.1, signed=True,
                     unit="kWh", description="Daily discharge energy"),
        ],
        errors=[
            Register(25261, "Errormessage1", coefficient=1.0, signed=False,
                     description="Error high word (32-bit combined)"),
            Register(25262, "Errormessage2", coefficient=1.0, signed=False,
                     description="Error low word (32-bit combined)"),
        ],
        scan_schedule=[
            (10105, 12),
            (15205, 30),
            (20001, 39),
            (20106, 4),
            (20133, 9),
            (20161, 60),
            (25201, 74),
            (25329, 18),
            (25347, 8),
            (25355, 2),
            (10275, 15),
        ],
        writable_addrs=[
            10105, 10107, 10108, 10110, 10111, 10113, 10114, 10115, 10116,
            20201, 20202, 20203, 20205, 20206, 20207,
            20106, 20133, 20134, 20135, 20136, 20161,
            20183, 20184, 20189, 20190, 20191, 20192, 20193, 20194,
            20211, 20213, 20001, 20002, 20003, 20039,
        ],
        error_table_32=ERROR_TABLE_32,
        needs_32bit_errors=True,
    )


def _make_ph5000() -> DeviceDefinition:
    """PH5000 3-phase grid-tie inverter."""
    base = _make_ph1000()
    base.name = "PH5000"
    base.protocol_type = "Ph5000"
    base.default_device_id = 6
    base.scan_start = 20001
    # Remove charger settings (not present in PH5000)
    base.settings = [r for r in base.settings if r.address >= 20000]
    base.settings.append(
        Register(20135, "AntiReflux", coefficient=1.0, signed=False,
                 description="Anti-reflux"),
    )
    base.scan_schedule = [
        (15205, 30),
        (20001, 5),
        (20135, 1),
        (20161, 59),
        (25201, 33),
        (25257, 8),
        (25329, 26),
    ]
    base.writable_addrs = [
        20201, 20202, 20203, 20205, 20206, 20207,
        20161, 20183, 20184, 20189, 20190, 20191, 20192, 20193, 20194,
        20211, 20213, 20001, 20002, 20003, 20135,
    ]
    return base


# ──────────────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────────────

DEVICE_REGISTRY: dict[str, DeviceDefinition] = {
    "pc1800": _make_pc1800(),
    "ph1800": _make_ph1800(),
    "ep1800": _make_ph1800(),
    "cdy10414": _make_ph1800(),
    "pv3500pro": _make_pv3500pro(),
    "ep2000pro": _make_ep2000pro(),
    "pv2000pro": _make_ep2000pro(),
    "ep3300": _make_ep3300(),
    "ep3300tlv": _make_ep3300tlv(),
    "pv2000pk": _make_pv2000pk(),
    "ph1000": _make_ph1000(),
    "ph5000": _make_ph5000(),
}

# Map protocol type strings to device key
PROTOCOL_MAP: dict[str, str] = {
    "Pc1800": "pc1800",
    "Ph18Series": "ph1800",
    "EPSeries": "ep2000pro",
    "Ph1000": "ph1000",
    "Ph5000": "ph5000",
}

# Map default device IDs to device key
ID_MAP: dict[int, str] = {
    1: "pc1800",
    4: "ph1800",
    5: "ph1000",
    6: "ph5000",
    10: "ep2000pro",
}

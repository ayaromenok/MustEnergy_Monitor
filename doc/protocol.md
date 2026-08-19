# Device Communication Protocol Description

> The sources describe **Modbus RTU** communication with solar power equipment:
> PV chargers, hybrid inverters (PV + battery + grid) and grid-tie inverters.
> Version 2.2.81

---

## 1. Overview

| Item | Value |
|---|---|
| Physical layer | RS-485 serial port (one port = one `Courier` / bus) |
| Link protocol | Modbus RTU (framing/CRC handled by external `Infrastructure` library) |
| Data model | 16-bit registers, big-endian (high/low word pairs for 32-bit values) |
| Addressing | Device (slave) ID 1…254, register numbers as listed below |
| Reading | Batched multi-register reads (see §4 "Scan schedule") |
| Writing | Single-register writes to the "writable" addresses listed per device |

### 1.1 Communication parameters (`CommParams`)

Per port the application stores:

| Parameter | Default | Notes |
|---|---|---|
| `PortBaudrate` | see table below | |
| `DataBit` | 8 | |
| `StopBits` | 1 (one stop bit) | `StopBits = 1` |
| `Parity` | none | `System.IO.Ports.Parity` |
| `Handshake` | none | |
| `Dtr` / `Rts` | false | |
| `DeviceIds` | see table below | each id must be 1…254 |
| `ScanStartAddress` | see table below | first register probed during device scan |
| `ScanFieldCnt` | 1 | registers read per scan transaction |
| `AfterScanTxWait` | 100 ms | wait after a scan transaction |
| `ProtocolType` | – | one of `EPSeries`, `Ph5000`, `Ph1000`, `Pc1800`, `Ph18Series` |

Factory defaults (`PmEntities.DefaultParamses`):

| Protocol type | Baudrate | Device ID(s) | Scan start | Extra |
|---|---|---|---|---|
| `Pc1800` | 9600 | 1 | 10000 | |
| `Ph1000` | 9600 | 5 | 20001 | |
| `Ph5000` | 9600 | 6 | 20001 | |
| `EPSeries` | 9600 | 10 | 30000 | |
| `Ph18Series` | 19200 | 4 | 20000 | `AfterScanTxWait = 300 ms`, `ScanFieldCnt = 7` |

### 1.2 Register binding convention (`[Modbus]` attribute)

Every monitored property is annotated:

```csharp
[Modbus(registerAddress, coefficient, signed)]
```

* `registerAddress` – 16-bit register number (decimal).
* `coefficient` – engineering value = raw register value × coefficient
  (e.g. `0.1` → value in 0.1 V / 0.1 A steps, `0.01` → Hz).
* `signed` – `true`: raw 16-bit value is two's-complement (signed);
  `false`: unsigned.

### 1.3 General decoding rules

* **Versions** – integer register formatted as `X.YY` (e.g. `10414` → `1.04.14`);
  hex versions formatted like `0x1234` → `12.34`.
* **Machine type** – high word = 2 ASCII characters, low word = numeric suffix
  (e.g. `"EP" + 3300`). For protocol editions < 1.04.13 the high word is not
  available and the type is shown as `"PV" + low word`.
* **Serial numbers** – 2×16-bit (H/L) or 3×16-bit (H/M/L) words,
  zero-padded to 5 digits per word.
* **Energy counters** – high/low 16-bit word pairs:
  * 1.04.14 hybrids: `kWh = (H*1000 + L) * 0.1`
  * PV3500PRO: `kWh = H*1000 + L` (no ×0.1)
  * PH1000/PH5000: `kWh = (H*65536 + L) * 0.1` (32-bit value)
* **Error/warning registers** – 16-bit bitmasks; each bit = one fault/warning.
  Some devices combine two 16-bit registers into a 32-bit value
  `(Err2 << 16) | Err1` and look up in a 32-entry message table.
* **Arrow flag** – 10-bit bitmask (1.04.14 hybrids) used for UI animation of
  PV/load/battery/AC connection and current direction.
* **Time** – accumulated day/hour/minute registers combined into a `TimeSpan`.

---

## 2. PV Charger — PC1800 (`Pc1800M`)

| Protocol type | Baudrate | Device ID | Scan start |
|---|---|---|---|
| `Pc1800` | 9600 | 1 | 10000 |

### 2.1 Identity (registers 10000–10008)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 10000 | MachineTypeH | 1 | true | High word (2 ASCII chars) |
| 10001 | MachineType | 1 | false | Low word (numeric suffix) |
| 10002 | SerialNumberH | 1 | true | Serial number high (5 digits) |
| 10003 | SerialNumberL | 1 | true | Serial number low (5 digits) |
| 10004 | HardwareVersion | 1 | false | Hardware version |
| 10005 | SoftwareVersion | 1 | false | Software version |
| 10006 | PvVoltageC | 1 | true | PV voltage calibration |
| 10007 | BatteryVoltageC | 1 | true | Battery voltage calibration |
| 10008 | ChargerCurrentC | 1 | true | Charger current calibration |

### 2.2 Settings (registers 10101–10126) — writable

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 10101 | ChargerWorkEnable | 1 | true | 0=OFF, 1=ON |
| 10103 | BatteryFloatVoltage | 0.1 | true | Float voltage (0.1 V) |
| 10104 | BatteryAbsorptionVoltage | 0.1 | true | Absorption voltage (0.1 V) |
| 10105 | BatteryLowVoltage | 0.1 | true | Low voltage (0.1 V) |
| 10107 | BatteryHighVoltage | 0.1 | true | High voltage (0.1 V) |
| 10108 | MaxChargerCurrent | 0.1 | true | Max charger current (0.1 A) |
| 10110 | BatteryType | 1 | true | Battery type (see §6) |
| 10111 | BatteryAh | 1 | true | Battery capacity (Ah) |
| 10112 | RemoveTheAccumulatedData | 1 | true | Reset accumulated data |
| 10113 | BatteryVoltageGrade | 1 | true | 0=auto, 12/24/36/48 V |
| 10116 | CvCharingMaxTime | 1 | true | CV charging max time (min) |
| 10117 | BtsTmperatureCompensationRatio | 0.1 | true | Temp compensation (0.1 mV/°C) |
| 10118 | BatteryEqualizationEnable | 1 | true | Equalization enable |
| 10119 | BatteryEqualizationVoltage | 0.1 | true | Equalization voltage (0.1 V) |
| 10120 | TheMaxCurrentOfBatteryEqualization | 0.1 | true | Max EQ current (0.1 A) |
| 10121 | BatteryEqualizedTime | 1 | true | EQ duration (min) |
| 10122 | BatteryEqualizedTimeout | 1 | true | EQ timeout (min) |
| 10123 | EqualizationInterval | 1 | true | EQ interval (days) |
| 10124 | EqualizationActivedImmediately | 1 | true | Force EQ now |
| 10125 | SystemSetting | 1 | true | Bitmask: bit2=AutoTurnPageFlagForbid, bit6=LcdLightEnable |
| 10126 | ResetTheParameter | 1 | true | Factory reset |

### 2.3 Status (registers 15201–15224)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 15201 | ChargerWorkstate | 1 | false | 0=Init, 1=Selftest, 2=Work, 3=Stop |
| 15202 | MpptState | 1 | false | 0=Stop, 1=MPPT, 2=Current limiting |
| 15203 | ChargingState | 1 | false | 0=Stop, 1=Absorb, 2=Float, 3=EQ |
| 15205 | PvVoltage | 0.1 | true | PV voltage (0.1 V) |
| 15206 | BatteryVoltage | 0.1 | true | Battery voltage (0.1 V) |
| 15207 | ChargerCurrent | 0.1 | true | Charger current (0.1 A) |
| 15208 | ChargerPower | 1 | true | Charger power (W) |
| 15209 | RadiatorTemp | 1 | true | Radiator temp (°C) |
| 15210 | ExternalTemp | 1 | true | External temp (°C) |
| 15211 | BatteryRelay | 1 | false | 0=Disconnect, 1=Connect |
| 15212 | PvRelay | 1 | false | 0=Disconnect, 1=Connect |
| 15213 | ErrorMessage | 1 | false | 16-bit fault bitmask (see §2.4) |
| 15214 | WarningMessage | 1 | false | 16-bit warning bitmask (see §2.4) |
| 15215 | BattVolGrade | 1 | false | Battery voltage grade (V) |
| 15216 | RatedCurrent | 0.1 | true | Rated current (0.1 A) |
| 15217 | AccumulatedPvPowerH | 1000.0 | true | Energy high word |
| 15218 | AccumulatedPvPowerL | 0.1 | true | Energy low word (×0.1 kWh) |
| 15219 | AccumulatedDay | 1 | true | Accumulated days |
| 15220 | AccumulatedHour | 1 | true | Accumulated hours |
| 15221 | AccumulatedMinute | 1 | true | Accumulated minutes |
| 15222 | CommunicationProtocolEdition | 1 | false | Protocol edition (e.g. 10414) |
| 15223 | SOC | 1 | false | State of charge (%) |
| 15224 | ArrowFlag | 1 | false | 10-bit: bit0=PV current, bit2=battery charge |

### 2.4 Fault & Warning codes

**Faults (15213 bitmask):**

| Bit | Meaning |
|---|---|
| 0 | Hardware protection |
| 1 | Over current |
| 2 | Current sensor error |
| 3 | Over temperature |
| 4 | PV voltage is too high |
| 5 | PV voltage is too low |
| 6 | Battery voltage is too high |
| 7 | Battery voltage is too low |
| 8 | Current is uncontrollable |
| 9 | Parameter error |

**Warnings (15214 bitmask):**

| Bit | Meaning |
|---|---|
| 0 | Fan error |

---

## 3. 1.04.14 Hybrid Inverters — Ph1800M, Cdy10414M, Ep180010414M

| Protocol type | Baudrate | Device ID | Scan start |
|---|---|---|---|
| `Ph18Series` | 19200 | 4 | 20000 |

These three models share the same register map. Differences:
* **Cdy10414M** — full inverter + charger (all registers), standard edition 1.04.14,
  displays "Recommended version" if mismatch.
* **Ep180010414M** — inverter + charger settings only; **no** charger status registers
  (15201–15221) or charger errors.
* **Ph1800M** — full inverter + charger, includes charger serial number parsing and
  accumulated time.

### 3.1 Inverter Identity (registers 20000–20008)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 20000 | MachineTypeH | 1 | false | 2 ASCII chars |
| 20001 | MachineTypeL | 1 | false | Numeric suffix |
| 20002 | SerialNumberH | 1 | true | Serial high (5 digits) |
| 20003 | SerialNumberL | 1 | true | Serial low (5 digits) |
| 20004 | HardwareNo | 1 | false | Hardware version (X.XX) |
| 20005 | SoftwareNo | 1 | false | Software version |
| 20006 | ProtocalEditionNo | 1 | false | Protocol edition (e.g. 10414 → 1.04.14) |

### 3.2 Inverter Calibration (registers 20009–20016)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 20009 | BatteryVoltageC | 1 | true | Battery voltage calibration |
| 20010 | InverterVoltageC | 1 | true | Inverter voltage calibration |
| 20011 | GridVoltageC | 1 | true | Grid voltage calibration |
| 20012 | BusVoltageC | 1 | true | Bus voltage calibration |
| 20013 | ControlCurrentC | 1 | true | Control current calibration |
| 20014 | InverterCurrentC | 1 | true | Inverter current calibration |
| 20015 | GridCurrentC | 1 | true | Grid current calibration |
| 20016 | LoadCurrentC | 1 | true | Load current calibration |

### 3.3 Inverter Settings (registers 20101–20143) — writable

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 20101 | InverterOffgridWorkEnable | 1 | true | Off-grid work enable |
| 20102 | InverterOutputVoltageSet | 0.1 | true | Output voltage set (0.1 V) |
| 20103 | InverterOutputFrequencySet | 0.01 | true | Output frequency set (0.01 Hz) |
| 20104 | InverterSearchModeEnable | 1 | true | Search mode enable |
| 20108 | InverterDischargerToGridEnable | 1 | true | Discharge to grid enable |
| 20109 | EnergyUseMode | 1 | false | SBU / SUB / UTI / SOL |
| 20111 | GridProtectStandard | 1 | false | VDE4105 / UPS / Home / GEN |
| 20112 | SolarUseAim | 1 | false | LBU / BLU |
| 20113 | InverterMaxDischargerCurrent | 0.1 | true | Max discharge current (0.1 A) |
| 20118 | BatteryStopDischargingVoltage | 0.1 | true | Stop discharge voltage (0.1 V) |
| 20119 | BatteryStopChargingVoltage | 0.1 | true | Stop charge voltage (0.1 V) |
| 20125 | GridMaxChargerCurrentSet | 0.1 | true | Max grid charger current (0.1 A) |
| 20127 | BatteryLowVoltage | 0.1 | true | Low voltage (0.1 V) |
| 20128 | BatteryHighVoltage | 0.1 | true | High voltage (0.1 V) |
| 20132 | MaxCombineChargerCurrent | 0.1 | true | Max combined charger current (0.1 A) |
| 20142 | SystemSetting | 1 | false | 16-bit: bit0=OverLoadRestartForbid, bit1=OverTempRestartForbid, bit2=OverLoadBypassForbid, bit3=AutoTurnPageFlagForbid, bit4=GridBuzzEnable, bit5=BuzzForbide, bit6=LcdLightEnable, bit7=RecordFaultForbid |
| 20143 | ChargerSourcePriority | 1 | false | 0=Solar first, 2=Solar+Utility, 3=Only Solar |

### 3.4 Inverter Status (registers 25201–25279)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 25201 | WorkStateNo | 1 | false | 0=PowerOn, 1=SelfTest, 2=OffGrid, 3=Grid-Tie, 4=ByPass, 5=Stop, 6=GridCharging |
| 25202 | AcVoltageGrade | 1 | false | AC voltage grade (V) |
| 25203 | RatedPower | 1 | false | Rated power (VA) |
| 25205 | BatteryVoltage | 0.1 | true | Battery voltage (0.1 V) |
| 25206 | InverterVoltage | 0.1 | true | Inverter voltage (0.1 V) |
| 25207 | GridVoltage | 0.1 | true | Grid voltage (0.1 V) |
| 25208 | BusVoltage | 1 | true | Bus voltage |
| 25209 | ControlCurrent | 0.1 | true | Control current (0.1 A) |
| 25210 | InverterCurrent | 0.1 | true | Inverter current (0.1 A) |
| 25211 | GridCurrent | 0.1 | true | Grid current (0.1 A) |
| 25212 | LoadCurrent | 0.1 | true | Load current (0.1 A) |
| 25213 | PInverter | 1 | true | Inverter power (W) |
| 25214 | PGrid | 1 | true | Grid power (W) |
| 25215 | PLoad | 1 | true | Load power (W) |
| 25216 | LoadPercent | 1 | false | Load percentage (%) |
| 25217 | SInverter | 1 | true | Inverter apparent power (VA) |
| 25218 | SGrid | 1 | true | Grid apparent power (VA) |
| 25219 | Sload | 1 | true | Load apparent power (VA) |
| 25221 | Qinverter | 1 | true | Inverter reactive power (var) |
| 25222 | Qgrid | 1 | true | Grid reactive power (var) |
| 25223 | Qload | 1 | true | Load reactive power (var) |
| 25225 | InverterFrequency | 0.01 | true | Inverter frequency (0.01 Hz) |
| 25226 | GridFrequency | 0.01 | true | Grid frequency (0.01 Hz) |
| 25229 | InverterMaxNumber | 1 | false | Max inverter count |
| 25230 | CombineType | 1 | false | Combination type |
| 25231 | InverterNumber | 1 | false | Inverter count |
| 25233 | AcRadiatorTemp | 1 | true | AC radiator temp (°C) |
| 25234 | TransformerTemp | 1 | true | Transformer temp (°C) |
| 25235 | DcRadiatorTemp | 1 | true | DC radiator temp (°C) |
| 25237 | InverterRelayStateNo | 1 | false | 0=Disconnect, 1=Connect |
| 25238 | GridRelayStateNo | 1 | false | 0=Disconnect, 1=Connect |
| 25239 | LoadRelayStateNo | 1 | false | 0=Disconnect, 1=Connect |
| 25240 | NLineRelayStateNo | 1 | false | Neutral line relay |
| 25241 | DcRelayStateNo | 1 | false | DC relay |
| 25242 | EarthRelayStateNo | 1 | false | Earth relay |
| 25245/25246 | AccumulatedChargerPower H/L | 0.1 | true | Total charged energy (kWh) |
| 25247/25248 | AccumulatedDischargerPower H/L | 0.1 | true | Total discharged energy (kWh) |
| 25249/25250 | AccumulatedBuyPower H/L | 0.1 | true | Total buy energy (kWh) |
| 25251/25252 | AccumulatedSellPower H/L | 0.1 | true | Total sell energy (kWh) |
| 25253/25254 | AccumulatedLoadPower H/L | 0.1 | true | Total load energy (kWh) |
| 25255/25256 | AccumulatedSelfusePower H/L | 0.1 | true | Total self-use energy (kWh) |
| 25257/25258 | AccumulatedPvsellPower H/L | 0.1 | true | Total PV-sell energy (kWh) |
| 25259/25260 | AccumulatedGridChargerPower H/L | 0.1 | true | Total grid-charger energy (kWh) |
| 25261 | Error1 | 1 | false | Inverter fault bitmask (bits 0–15) |
| 25262 | Error2 | 1 | false | Inverter fault bitmask (bits 16–31) |
| 25263 | Error3 | 1 | false | Reserved |
| 25265 | Warning1 | 1 | false | Inverter warning bitmask (bits 0–15) |
| 25266 | Warning2 | 1 | false | Inverter warning bitmask (bits 16–31) |
| 25273 | BattPower | 1 | true | Battery power (W) |
| 25274 | BattCurrent | 1 | true | Battery current (A) |
| 25275 | BattVoltageGrade | 1 | false | Battery voltage grade (V) |
| 25277 | RatedPowerW | 1 | true | Rated power (W) |
| 25278 | CommunicationProtocalEdition | 1 | false | Protocol edition |
| 25279 | ArrowFlag | 1 | false | 10-bit: PV conn, load conn, batt conn, AC conn, PV current, load current, batt current (2 bits), AC current (2 bits) |

### 3.5 Charger Identity (registers 10001–10008)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 10001 | ChrMachineType | 1 | false | Machine type |
| 10002 | ChrSerialNumberH | 1 | true | Serial high |
| 10003 | ChrSerialNumberL | 1 | true | Serial low |
| 10004 | ChrHardwareNo | 1 | false | Hardware version |
| 10005 | ChrSoftwareNo | 1 | false | Software version |
| 10006 | PvVoltageC | 1 | true | PV voltage calibration |
| 10007 | ChrBatteryVoltageC | 1 | true | Battery voltage calibration |
| 10008 | ChargerCurrentC | 1 | true | Charger current calibration |

### 3.6 Charger Settings (registers 10103–10111) — writable

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 10103 | FloatVoltage | 0.1 | true | Float voltage (0.1 V) |
| 10104 | AbsorptionVoltage | 0.1 | true | Absorption voltage (0.1 V) |
| 10105 | ChrBatteryLowVoltage | 0.1 | true | Low voltage (0.1 V) |
| 10108 | MaxChargerCurrent | 0.1 | true | Max charger current (0.1 A) |
| 10110 | BatteryType | 1 | true | Battery type (see §6) |
| 10111 | BatteryAh | 1 | true | Battery capacity (Ah) |

### 3.7 Charger Status (registers 15201–15224)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 15201 | ChrWorkstateNo | 1 | false | 0=Init, 1=Selftest, 2=Work, 3=Stop |
| 15202 | MpptStateNo | 1 | false | 0=Stop, 1=MPPT, 2=Current limiting |
| 15203 | ChargingStateNo | 1 | false | 0=Stop, 1=Absorb, 2=Float, 3=EQ |
| 15205 | PvVoltage | 0.1 | true | PV voltage (0.1 V) |
| 15206 | ChrBatteryVoltage | 0.1 | true | Battery voltage (0.1 V) |
| 15207 | ChargerCurrent | 0.1 | true | Charger current (0.1 A) |
| 15208 | ChargerPower | 1 | true | Charger power (W) |
| 15209 | RadiatorTemp | 1 | true | Radiator temp (°C) |
| 15210 | ExternalTemp | 1 | true | External temp (°C) |
| 15211 | BatteryRelayNo | 1 | false | 0=Disconnect, 1=Connect |
| 15212 | PvRelayNo | 1 | false | 0=Disconnect, 1=Connect |
| 15213 | ChrError1 | 1 | false | Charger fault bitmask (bits 0–15) |
| 15214 | ChrWarning1 | 1 | false | Charger warning bitmask (bits 0–15) |
| 15215 | BattVolGrade | 1 | false | Battery voltage grade (V) |
| 15216 | RatedCurrent | 0.1 | true | Rated current (0.1 A) |
| 15217/15218 | AccumulatedPvPower H/L | 0.1 | true | Total PV energy (kWh) |
| 15219 | AccumulatedDay | 1 | true | Accumulated days |
| 15220 | AccumulatedHour | 1 | true | Accumulated hours |
| 15221 | AccumulatedMinute | 1 | true | Accumulated minutes |

### 3.8 Inverter Fault Codes

| Bit | Meaning |
|---|---|
| 0 | Hardware protection |
| 1 | Over current |
| 2 | Current sensor error |
| 3 | Over temperature |
| 4 | PV voltage is too high |
| 5 | PV voltage is too low |
| 6 | Battery voltage is too high |
| 7 | Battery voltage is too low |
| 8 | Current is uncontrollable |
| 9 | Parameter error |

### 3.9 Inverter Warning Codes

| Bit | Meaning |
|---|---|
| 0 | Fan error |

### 3.10 Charger Fault Codes

| Bit | Meaning |
|---|---|
| 0 | Hardware protection |
| 1 | Over current |
| 2 | Current sensor error |
| 3 | Over temperature |
| 4 | PV voltage is too high |
| 5 | PV voltage is too low |
| 6 | Battery voltage is too high |
| 7 | Battery voltage is too low |
| 8 | Current is uncontrollable |
| 9 | Parameter error |

### 3.11 Charger Warning Codes

| Bit | Meaning |
|---|---|
| 0 | Fan error |

---

## 4. PV3500PRO (`Pv3500ProM`)

| Protocol type | Baudrate | Device ID | Scan start |
|---|---|---|---|
| `Ph18Series` | 19200 | 4 | 20000 |

Same register map as the 1.04.14 hybrids with these differences:
* No `20006` (protocol edition), no `25278`, no `25279` (ArrowFlag).
* `25275` = Battery SOC (not voltage grade).
* No `25277` (RatedPowerW).
* Animation uses WorkState/BattCurrent/PGrid/ChargerPower instead of ArrowFlag.
* Energy: `kWh = H*1000 + L` (no ×0.1 multiplier).
* WritableAttrs: 20002, 20009–20016, 20101–20143, 10002–10008, 10103–10111.

---

## 5. EP Series — Ep2000ProM, Ep3300M, Ep3300TlvM, Pv2000PkM

| Protocol type | Baudrate | Device ID | Scan start |
|---|---|---|---|
| `EPSeries` | 9600 | 10 | 30000 |

### 5.1 EP2000PRO (`Ep2000ProM`)

#### Status (registers 30000–30026)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 30000 | MachineType | 1 | false | 0=EP2000PRO, 2=PV2000PRO, 3=EP3300 |
| 30001 | SoftwareVersion | 1 | false | Software version |
| 30002 | WorkState | 1 | false | uint (see §5.4) |
| 30003 | BatClass | 1 | false | Battery class (V) |
| 30004 | RatedPower | 1 | false | Rated power (W) |
| 30005 | GridVoltage | 0.1 | true | Grid voltage (0.1 V) |
| 30006 | GridFrequency | 0.1 | true | Grid frequency (0.1 Hz) |
| 30007 | OutputVoltage | 0.1 | true | Output voltage (0.1 V) |
| 30008 | OutputFrequency | 0.1 | true | Output frequency (0.1 Hz) |
| 30009 | LoadCurrent | 0.1 | true | Load current (0.1 A) |
| 30010 | LoadPower | 1 | true | Load power (W) |
| 30012 | LoadPercent | 1 | false | Load percentage (%) |
| 30013 | LoadState | 1 | false | Load state |
| 30014 | BatteryVoltage | 0.1 | true | Battery voltage (0.1 V) |
| 30015 | BatteryCurrent | 0.1 | true | Battery current (0.1 A) |
| 30017 | BatterySoc | 1 | false | Battery SOC (%) |
| 30018 | TransformerTemp | 1 | true | Transformer temp (°C) |
| 30019 | AvrState | 1 | false | AVR state (see §5.5) |
| 30020 | BuzzerState | 1 | false | 0=Normal, 1=Silence |
| 30021 | FaultId | 1 | false | Single fault ID (see §5.2) |
| 30022 | AlarmId | 1 | false | 16-bit alarm bitmask (see §5.3) |
| 30023 | ChargeState | 1 | false | Charge state |
| 30024 | ChargeFlag | 1 | false | Grid charge flag |
| 30025 | MainSw | 1 | false | Main switch |
| 30026 | DelayType | 1 | false | Delay type |

#### Settings (registers 31000–31017) — writable

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 31000 | GridFrequencyType | 1 | false | 50/60 Hz |
| 31001 | GridVoltageType | 1 | false | 110/115/120/220/230/240 V |
| 31002 | ShutdownVoltage | 0.1 | true | Shutdown voltage (0.1 V) |
| 31003 | AbsorptionChargeVoltage | 0.1 | true | Absorption voltage (0.1 V) |
| 31004 | FloatChargeVoltage | 0.1 | true | Float voltage (0.1 V) |
| 31005 | BulkCurrent | 1 | true | Bulk current (A) |
| 31006 | Buzzer | 1 | false | Normal / Silence |
| 31007 | EnableGridCharge | 1 | true | Enable grid charging |
| 31009 | EnableBacklight | 1 | false | Enable backlight |
| 31016 | UtilityPowerOn | 1 | true | Utility power on |
| 31017 | EnableOverLoadRecover | 1 | false | Enable over-load recovery |

#### Calibration (registers 31100–31105)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 31100 | BatteryVoltageCC | 1 | true | Battery voltage calibration |
| 31101 | BatteryChargeCurrentCC | 1 | true | Battery charge current calibration |
| 31102 | GridVoltageCC | 1 | true | Grid voltage calibration |
| 31103 | OutputVoltageCC | 1 | true | Output voltage calibration |
| 31104 | LoadCurrentCC | 1 | true | Load current calibration |
| 31105 | BatteryDischargeCurrentCC | 1 | true | Battery discharge current calibration |

### 5.2 EP3300 (`Ep3300M`)

Same status registers as EP2000PRO with these differences:
* `30000` = `MachineTypeI` (0=EP2000PRO, 2=PV2000PRO, 3=EP3300)
* `30001` = `SoftwareVersionI` — 5 digits → `"166-00XXX-YY"`
* `30002` = `WorkStateI` (see §5.4)
* `30016` = `BatteryTemperature` (°C) — additional
* `30020` = `BuzzerStateI` (0=Normal, 1=Silence)
* `30021` = `SystemFaultId` — fault dict (see §5.2)
* `30022` = `SystemAlarmId` — 16-bit alarm bitmask (see §5.3)
* `30023` = `ChargeStageI` (0=CC, 1=CV, 2=FV)
* `30024` = `GridChargeFlagI` (0=no grid charge, 1=grid charge)
* `30025` = `GridState` (0=no grid, 1=normal, 2=abnormal)

#### Additional settings

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 31014 | Point2Inv | 0.1 | true | Point 2 inverter (0.1 V) |
| 31015 | Point2Grid | 0.1 | true | Point 2 grid (0.1 V) |
| 31020 | PowerSavingModeEnable | 1 | false | Power saving mode |
| 31021 | SearchTime | 1 | false | Search time (5/30 s) |
| 31022 | OutputSourcePriority | 1 | false | Grid / Battery |
| 31023 | AcInputVoltageRange | 1 | false | Wide / Narrow |

#### Additional calibration

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 31108 | BatteryDischargeCurrentCC | 1 | true | Battery discharge current calibration |

#### Serial number (31200–31201)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 31200 | SerialNumberH | 1 | true | Serial high (5 digits) |
| 31201 | SerialNumberL | 1 | true | Serial low (5 digits) |

#### Commands (32000–32001)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 32000 | RestoreFactorySettings | 1 | false | Restore factory settings |
| 32001 | RemoteReset | 1 | false | Remote reset |

### 5.3 EP3300 TLV (`Ep3300TlvM`) — three-line voltage (L1/L2 output)

Same as EP3300 with these additions:

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 30032 | InputVoltage | 0.1 | true | Input voltage (0.1 V) |
| 30033 | InputFrequency | 0.1 | true | Input frequency (0.1 Hz) |
| 30036 | L1OutputVoltage | 0.1 | true | L1 output voltage (0.1 V) |
| 30037 | L1OutputCurrent | 0.1 | true | L1 output current (0.1 A) |
| 30038 | L1Power | 1 | true | L1 power (W) |
| 30039 | L1ApparentPower | 1 | true | L1 apparent power (VA) |
| 30040 | L1Percent | 1 | false | L1 load percentage (%) |
| 30041 | L2OutputVoltage | 0.1 | true | L2 output voltage (0.1 V) |
| 30042 | L2OutputCurrent | 0.1 | true | L2 output current (0.1 A) |
| 30043 | L2Power | 1 | true | L2 power (W) |
| 30044 | L2ApparentPower | 1 | true | L2 apparent power (VA) |
| 30045 | L2Percent | 1 | false | L2 load percentage (%) |
| 30046 | L12OutputVoltage | 0.1 | true | L1-L2 output voltage (0.1 V) |
| 30047 | OutputFrequency | 0.1 | true | Output frequency (0.1 Hz) |
| 30048 | TotalPLoad | 1 | true | Total load power (W) |
| 30049 | TotalSLoad | 1 | true | Total load apparent power (VA) |
| 30050 | TotalLoadPercent | 1 | false | Total load percentage (%) |

#### L1/L2 calibration

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 31111 | L1OutputVoltageCC | 1 | true | L1 voltage calibration |
| 31112 | L1OutputCurrentCC | 1 | true | L1 current calibration |
| 31113 | L2OutputVoltageCC | 1 | true | L2 voltage calibration |
| 31114 | L2OutputCurrentCC | 1 | true | L2 current calibration |
| 31115 | L12OutputVoltageCC | 1 | true | L1-L2 voltage calibration |
| 31116 | OutputFrequencyCC | 1 | true | Output frequency calibration |

#### Work state array (different from EP3300):
0=SELF_CHECK, 1=BACKUP, 2=LINE, 3=STOP, 4=DEBUG, 5=SOFT_START, 6=POWER_OFF, 7=STANDBY

### 5.4 EP2000PRO / EP3300 Work States

| Value | EP2000PRO | EP3300 |
|---|---|---|
| 0 | "" | SELF_CHECK |
| 1 | "" | BACKUP |
| 2 | "" | LINE |
| 3 | "" | STOP |
| 4 | "" | CHARGER |
| 5 | "" | SOFT_START |
| 6 | "" | POWER_OFF |
| 7 | "" | STANDBY |
| 8 | — | DEBUG |

### 5.5 EP2000PRO AVR State

| Value | Meaning |
|---|---|
| 0 | BYPASS |
| 1 | STEP DOWN |
| 2 | BOOST |
| 3 | EXTENDED BOOST |

### 5.6 EP Series Fault & Alarm Codes

**Fault ID (single integer):**

| Code | Meaning |
|---|---|
| 1 | Fan error |
| 2 | Inverter over temperature |
| 3 | Battery voltage too high |
| 4 | Battery voltage too low |
| 5 | Output short circuit |
| 6 | Output voltage too high |
| 7 | Over load |
| 11 | Main relay failed |
| 28 | Rated load recognition failed |
| 41 | Grid voltage too low |
| 42 | Grid voltage too high |
| 43 | Grid frequency too low |
| 44 | Grid frequency too high |
| 45 | AVR failed |
| 51 | Over current |
| 58 | Output voltage too low |

**Alarm bitmask (16 bits):**

| Bit | Meaning |
|---|---|
| 0 | Inverter over temperature |
| 1 | Battery over temperature |
| 2 | Battery voltage too high |
| 3 | Battery voltage too low |
| 4 | Over load |

---

## 6. PV2000PK (`Pv2000PkM`)

| Protocol type | Baudrate | Device ID | Scan start |
|---|---|---|---|
| `EPSeries` | 9600 | 10 | 30000 |

### Status (registers 30000–30050)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 30000 | MachineType | 1 | false | Machine type |
| 30001 | SoftwareVersion | 1 | false | Software version |
| 30002 | WorkState | 1 | false | 0="", 1=INIT, 2=SELF_CHECK, 3=BACKUP, 4=LINE, 5=STOP, 6=POWER_OFF, 7=CHARGER, 8=SOFT_START |
| 30003 | BatClass | 1 | false | Battery class (V) |
| 30004 | RatedPower | 1 | false | Rated power (W) |
| 30005 | GridVoltage | 0.1 | true | Grid voltage (0.1 V) |
| 30006 | GridFrequency | 0.1 | true | Grid frequency (0.1 Hz) |
| 30007 | OutputVoltage | 0.1 | true | Output voltage (0.1 V) |
| 30008 | OutputFrequency | 0.1 | true | Output frequency (0.1 Hz) |
| 30009 | LoadCurrent | 0.1 | true | Load current (0.1 A) |
| 30010 | LoadPower | 1 | true | Load power (W) |
| 30011 | LoadVA | 1 | true | Load apparent power (VA) |
| 30012 | LoadPercent | 1 | false | Load percentage (%) |
| 30014 | BatteryVoltage | 0.1 | true | Battery voltage (0.1 V) |
| 30015 | BatteryCurrent | 0.1 | true | Battery current (0.1 A) |
| 30017 | BatterySOC | 1 | false | Battery SOC (%) |
| 30018 | InverterTransformerTemp | 1 | true | Inverter transformer temp (°C) |
| 30019 | AVRState | 1 | false | 0=BYPASS, 1=STEPDOWN, 2=BOOST, 3=EBOOST |
| 30021 | SystemFaultID | 1 | false | Fault code (see §6.2) |
| 30022 | SystemAlarmID | 1 | false | 9-item alarm array |
| 30023 | ChargeStage | 1 | false | CC/CV/FV |
| 30024 | GridChargeFlag | 1 | false | Grid charge flag |
| 30025 | MainSW | 1 | false | Main switch |
| 30026 | DelayType | 1 | false | Delay type |
| 30030 | PVStart | 1 | false | PV start |
| 30031 | PVFlag | 1 | false | PV flag |
| 30032 | PVChgFlag | 1 | false | PV charge flag |
| 30033 | PvTemp | 1 | true | PV temp (°C) |
| 30034 | PvV | 0.1 | true | PV voltage (0.1 V) |
| 30035 | PvI | 0.1 | true | PV current (0.1 A) |
| 30036 | PVPower | 1 | true | PV power (W) |
| 30040 | ChgSource | 1 | false | Charge source |
| 30041 | OutSource | 1 | false | Output source |

### Settings

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 31000 | GridFrequencyType | 1 | false | 50/60 Hz |
| 31001 | GridVoltageType | 1 | false | 220/230 V |
| 31002 | ShutdownVoltage | 0.1 | true | Shutdown voltage (0.1 V) |
| 31003 | AbsorptionChargeVoltage | 0.1 | true | Absorption voltage (0.1 V) |
| 31004 | FloatChargeVoltage | 0.1 | true | Float voltage (0.1 V) |
| 31005 | BulkCurrent | 1 | true | Bulk current (A) |
| 31006 | Buzzer | 1 | false | Buzzer |
| 31009 | Enablebacklight | 1 | false | Enable backlight |
| 31011 | GridChargeCurrent | 1 | true | Grid charge current (A) |
| 31012 | OutPriority | 1 | false | 0=Solar first, 1=Grid first, 2=SBU |
| 31013 | ChgPriority | 1 | false | 0=Solar first, 1=Only solar, 2=Grid first, 3=Union charge |
| 31014 | Point2Inv | 0.1 | true | Point 2 inverter (0.1 V) |
| 31015 | Point2Grid | 0.1 | true | Point 2 grid (0.1 V) |
| 31017 | EnableOverloadRecover | 1 | false | Enable overload recover |

### Calibration

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 31100 | BatteryVoltageCC | 1 | true | Battery voltage calibration |
| 31101 | BatteryChargeCurrentCC | 1 | true | Battery charge current calibration |
| 31102 | GridVoltageCC | 1 | true | Grid voltage calibration |
| 31103 | OutputVoltageCC | 1 | true | Output voltage calibration |
| 31104 | LoadCurrentCC | 1 | true | Load current calibration |
| 31105 | BatteryDischargeCurrentCC | 1 | true | Battery discharge current calibration |
| 31106 | PvVoltageCC | 1 | true | PV voltage calibration |
| 31107 | PvCurrentCC | 1 | true | PV current calibration |

### 6.2 PV2000PK Fault & Alarm Codes

**Fault codes:**

| Code | Meaning |
|---|---|
| 2 | Inverter over temperature |
| 3 | Battery voltage too high |
| 4 | Battery voltage too low |
| 5 | Output short circuit |
| 6 | Output voltage too high |
| 7 | Over load |
| 11 | Main relay failed |
| 33 | Solar charger driver fault |
| 41 | Input voltage too low |
| 42 | Input voltage too high |
| 43 | Input frequency too low |
| 44 | Input frequency too high |
| 45 | AVR fault |
| 51 | Over current |
| 58 | Output voltage too low |
| 73 | Solar charger stops due to high PV voltage |
| 75 | Solar charger over temperature |
| 78 | PV reverse polarity |

**Alarm array (9 items):**

| Index | Meaning |
|---|---|
| 0 | Battery voltage too low |
| 1 | Over load |
| 2 | Grid voltage lower than normal |
| 3 | Grid voltage higher than normal |
| 4 | Grid frequency too low |
| 5 | Grid frequency too high |
| 6 | PV over temperature |
| 7 | Battery voltage too high |
| 8 | Parameter error |

---

## 7. PH1000 (`Ph1000M`) — Hybrid Inverter

| Protocol type | Baudrate | Device ID | Scan start |
|---|---|---|---|
| `Ph1000` | 9600 | 5 | 20001 |

### 7.1 Charger Settings (registers 10105–10116) — writable

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 10105 | BatteryLowVoltage | 0.01 | true | Low voltage (0.01 V) |
| 10107 | BatteryHighvoltage | 0.01 | true | High voltage (0.01 V) |
| 10108 | MaxChargerCurrent | 1 | true | Max charger current (A) |
| 10110 | BatteryType | 1 | true | 0=Lead acid, 1=Lithium |
| 10111 | BatteryAh | 1 | true | Battery capacity (Ah) |
| 10113 | EnergyUseMode | 1 | false | 0=STORE, 1=LOAD_FIRST, 2=UPS, 3=GENERATOR |
| 10114 | BatteryConstVoltChargeVoltage | 0.01 | true | Const volt charge (0.01 V) |
| 10115 | BatteryFloatChargeVoltage | 0.01 | true | Float charge (0.01 V) |
| 10116 | BatteryStopDisChargeVoltage | 0.01 | true | Stop discharge (0.01 V) |

### 7.2 Status (registers 15205–15234)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 15205 | WorkStateI | 1 | false | 0=PowerOn, 1=SelfTest, 2=OffGrid, 3=Grid-Tie, 4=ByPass, 5=Stop |
| 15206 | BatteryVoltage | 0.1 | true | Battery voltage (0.1 V) |
| 15207 | BatteryCurrent | 0.1 | true | Battery current (0.1 A) |
| 15208 | BatteryPower | 1 | true | Battery power (W) |
| 15209 | ChargerTemperature | 0.1 | true | Charger temp (0.1 °C) |
| 15210 | PV1Voltage | 0.1 | true | PV1 voltage (0.1 V) |
| 15211 | PV1Current | 0.01 | true | PV1 current (0.01 A) |
| 15212 | PV1Power | 1 | true | PV1 power (W) |
| 15213 | PV2Voltage | 0.1 | true | PV2 voltage (0.1 V) |
| 15214 | PV2Current | 0.01 | true | PV2 current (0.01 A) |
| 15215 | PV2Power | 1 | true | PV2 power (W) |
| 15216 | PV3Voltage | 0.1 | true | PV3 voltage (0.1 V) |
| 15217 | PV3Current | 0.01 | true | PV3 current (0.01 A) |
| 15218 | PV3Power | 1 | true | PV3 power (W) |
| 15219 | PvPower | 1 | true | Total PV power (W) |
| 15220 | BusVoltage | 0.1 | true | Bus voltage (0.1 V) |
| 15221 | InverterVoltage | 0.1 | true | Inverter voltage (0.1 V) |
| 15222 | InverterCurrent | 0.1 | true | Inverter current (0.1 A) |
| 15223 | SInverter | 1 | true | Inverter apparent power (VAR) |
| 15224 | Qinverter | 1 | true | Inverter reactive power (VAR) |
| 15225 | LoadCurrent | 0.1 | true | Load current (0.1 A) |
| 15226 | LoadPower | 1 | true | Load power (W) |
| 15227 | VgirdR | 0.1 | true | Grid R-phase voltage (0.1 V) |
| 15228 | VgirdS | 0.1 | true | Grid S-phase voltage (0.1 V) |
| 15229 | VgirdT | 0.1 | true | Grid T-phase voltage (0.1 V) |
| 15230 | IgirdR | 0.1 | true | Grid R-phase current (0.1 A) |
| 15231 | IgirdS | 0.1 | true | Grid S-phase current (0.1 A) |
| 15232 | IgirdT | 0.1 | true | Grid T-phase current (0.1 A) |
| 15233 | GridPower | 1 | true | Grid power (W) |
| 15234 | GridFrequency | 0.01 | true | Grid frequency (0.01 Hz) |

### 7.3 Info (registers 20001–20005, 20039)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 20001 | SerialnumberHigh | 1 | true | Serial number high |
| 20002 | SerialnumberMiddle | 1 | true | Serial number middle |
| 20003 | SerialnumberLow | 1 | true | Serial number low |
| 20004 | Hardwareversion | 1 | false | HW version (VX.Y) |
| 20005 | Softwareversion | 1 | false | SW version (hex → X.XY) |
| 20039 | DCMPPTModeSet | 1 | false | 0=MPPT, 1=DC source mode |

### 7.4 Inverter Settings (registers 20106–20219) — writable

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 20106 | InverterChargerFromGridEnable | 1 | true | Charger from grid enable |
| 20108 | InverterdDisChargerToGridEnable | 1 | true | Discharge to grid enable |
| 20133 | ChargerStartTime | 1 | false | Charger start time |
| 20134 | ChargerEndTime | 1 | false | Charger end time |
| 20135 | AntiReflux | 1 | false | Anti-reflux |
| 20136 | Bypass | 1 | false | Bypass |
| 20137–20141 | Discharge time windows | — | — | Time windows |
| 20161 | GridTieSafetyType | 1 | false | Grid-tie safety standard (16 types) |
| 20165–20168 | LVP protection (slow/fast) | 20.0 | true | Trip values and times |
| 20169–20172 | OVP protection (slow/fast) | 20.0 | true | Trip values and times |
| 20173–20176 | LFP protection (slow/fast) | 20.0 | true | Trip values and times |
| 20177–20180 | OFP protection (slow/fast) | 20.0 | true | Trip values and times |
| 20183 | ReconnectTime | 1 | false | Reconnect time (seconds) |
| 20184 | StartdelayTime | 1 | false | Start delay time (seconds) |
| 20185 | QuCharacteristicCurveStartPoint | 1 | false | Q(U) curve start point |
| 20189 | LocalControl | 1 | false | Local control |
| 20190 | PfCharacteristicCurve | 1 | false | P(f) curve |
| 20191 | OutputQMode | 1 | false | Output Q mode |
| 20192 | ActivePowerSetting | 1 | false | Active power setting (%) |
| 20193 | ReactivePowerSetting | 1 | false | Reactive power setting (VAR) |
| 20194 | PfSetting | 0.001 | false | PF setting (0.001) |
| 20195–20200 | Connection ranges (Vac/Fac) | — | — | Grid connection limits |
| 20201–20207 | Date/time | 1 | false | Real-time clock |
| 20211 | InverterRunStop | 1 | false | Inverter run/stop |
| 20213 | Removetheaccumulateddata | 1 | false | Reset accumulated data |
| 20215–20219 | Power limiting (frequency-based) | — | — | Frequency-based power limiting |

### 7.5 Status / Energy (registers 25201–25356)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 25206–25210 | InternalSoftwareVersion 1–5 | 1 | false | Internal SW versions |
| 25212 | ActivePowerRead | 1 | false | Active power read (%) |
| 25233 | InverterTemperature | 0.1 | true | Inverter temp (0.1 °C) |
| 25245/25246 | TotalRechargeEnergy H/L | 0.1 | true | Total charged energy (kWh) |
| 25247/25248 | TotalDischargeEnergy H/L | 0.1 | true | Total discharged energy (kWh) |
| 25251/25252 | TotalSellEnergy H/L | 0.1 | true | Total sell energy (kWh) |
| 25257/25258 | TotalGenerateEnergy H/L | 0.1 | true | Total generated energy (kWh) |
| 25261/25262 | Errormessage1/2 | 1 | false | 32-bit error code |
| 25264 | ConnectTime | 1 | false | Connect time (seconds) |
| 25265 | WarningMessage1 | 1 | false | 16-bit warning bitmask |
| 25274 | BatterySoc | 1 | false | Battery SOC (%) |
| 25329 | DailySellEnergy | 0.1 | true | Daily sell energy (0.1 kWh) |
| 25330 | DailyGenerateEnergy | 0.1 | true | Daily generated energy (0.1) |
| 25331 | DailyRechargeEnergy | 0.1 | true | Daily recharge energy (0.1) |
| 25332 | DailyDischargeEnergy | 0.1 | true | Daily discharge energy (0.1) |
| 25333–25342 | Auto-test registers | — | — | Process, TestStep, TimeCount, VfValue, etc. |
| 25355 | BatteryChargeStatus | 1 | false | 0=STANDBY, 1=DISCHG, 2=CONST_SMALL_CHG, 3=CONST_LARGE_CHG, 4=CONST_VOLT_CHG, 5=FLOAT_VOLT_CHG |
| 25356 | BatteryReconnectTime | 1 | false | Battery reconnect time |

### 7.6 Advanced Settings (registers 10275–10289) — writable

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 10275 | USPowerDecRate | — | — | US power dec rate |
| 10276 | USPowerIncRate | — | — | US power inc rate |
| 10277 | GridVoltageStep | — | — | Grid voltage step |
| 10278 | FrequencyStop | — | — | Frequency stop |
| 10279 | PFSetting | — | — | PF setting |
| 10280 | QSetting | — | — | Q setting |
| 10281 | FBatPowerDecPerCmdSet | — | — | FBat power dec per cmd |
| 20163 | EnableSpi | — | — | Enable SPI |

### 7.7 Error & Warning Codes (32-bit combined)

The 32-bit error code `(Err2 << 16) | Err1` is looked up in a 32-entry table:

| Index | Meaning |
|---|---|
| 0 | Hardware protection |
| 1 | Over current |
| 2 | Current sensor error |
| 3 | Over temperature |
| 4 | PV voltage too high |
| 5 | PV voltage too low |
| 6 | Battery voltage too high |
| 7 | Battery voltage too low |
| 8 | Current uncontrollable |
| 9 | Parameter error |
| 10 | Inverter over temperature |
| 11 | Over load |
| 12 | Output short circuit |
| 13 | Output voltage too high |
| 14 | Output voltage too low |
| 15 | Grid voltage too high |
| 16 | Grid voltage too low |
| 17 | Grid frequency too high |
| 18 | Grid frequency too low |
| 19 | Grid over current |
| 20 | Grid over voltage |
| 21 | Grid over frequency |
| 22 | Grid under voltage |
| 23 | Grid under frequency |
| 24 | Anti-backflow over current |
| 25 | Anti-backflow over voltage |
| 26 | Anti-backflow over frequency |
| 27 | PV over voltage |
| 28 | PV under voltage |
| 29 | PV reverse polarity |
| 30 | Battery over temperature |
| 31 | Battery over voltage |

### 7.8 Warning Codes (16-bit)

| Bit | Meaning |
|---|---|
| 0 | Fan error |
| 1 | Battery over temperature |
| 2 | Battery over voltage |
| 3 | PV over voltage |
| 4 | PV under voltage |
| 5 | PV reverse polarity |
| 6 | Grid over voltage |
| 7 | Grid under voltage |
| 8 | Grid over frequency |
| 9 | Grid under frequency |
| 10 | Grid over current |
| 11 | Anti-backflow over current |
| 12 | Anti-backflow over voltage |
| 13 | Anti-backflow over frequency |

---

## 8. PH5000 (`Ph5000M`) — 3-Phase Grid-Tie Inverter

| Protocol type | Baudrate | Device ID | Scan start |
|---|---|---|---|
| `Ph5000` | 9600 | 6 | 20001 |

### 8.1 Status (registers 15205–15234)

Same layout as PH1000 (15205–15234) but **3-phase grid** — registers 15227–15232 represent GridVoltage, GridCurrent per phase (R/S/T).

### 8.2 Info (registers 20001–20005)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 20001 | SerialnumberHigh | 1 | true | Serial number high |
| 20002 | SerialnumberMiddle | 1 | true | Serial number middle |
| 20003 | SerialnumberLow | 1 | true | Serial number low |
| 20004 | Hardwareversion | 1 | false | HW version |
| 20005 | Softwareversion | 1 | false | SW version |

### 8.3 Inverter Settings (registers 20135–20219) — writable

Same as PH1000 §7.4 (anti-reflux, grid-tie safety, protection, date/time, etc.).

### 8.4 Status / Energy (registers 25201–25356)

| Addr | Name | Coeff | Signed | Description |
|---|---|---|---|---|
| 25206–25210 | InternalSoftwareVersion 1–5 | 1 | false | Internal SW versions |
| 25233 | InverterTemperature | 0.1 | true | Inverter temp (0.1 °C) |
| 25257/25258 | TotalGenerateEnergy H/L | 0.1 | true | Total generated energy (kWh) |
| 25261/25262 | Errormessage1/2 | 1 | false | 32-bit error code |
| 25264 | ConnectTime | 1 | false | Connect time (seconds) |
| 25330 | DailyGenerateEnergy | 0.1 | true | Daily generated energy (0.1) |
| 25333–25346 | Auto-test registers | — | — | LVP/OVP/LFP/OFP slow/fast settings |
| 25347–25353 | Auto-test results | — | — | Test results |
| 25354 | AutoTestState | 1 | false | Auto-test state |
| 20162 | AutoTestStartCmd | 1 | false | Start auto-test command |

### 8.5 Error & Warning Codes

Same 32-entry error table and 16-bit warning table as PH1000 (§7.7–7.8).

### 8.6 Work States

| Value | Meaning |
|---|---|
| 0 | PowerOn |
| 1 | SelfTest |
| 2 | OffGrid |
| 3 | Grid-Tie |
| 4 | ByPass |
| 5 | Stop |

---

## 9. Scan Schedule (Batch Reads)

Defined in `MyDbInitializer.Seed()` as `InfoOfGetData` entries:

### EP3300 (ID 10)

| Start | Count | Registers |
|---|---|---|
| 30000 | 26 | 30000–30025 |
| 31000 | 10 | 31000–31009 |
| 31011 | 8 | 31011–31018 |
| 31020 | 4 | 31020–31023 |
| 31100 | 10 | 31100–31109 |
| 31200 | 2 | 31200–31201 |
| 32000 | 2 | 32000–32001 |

### EP2000PRO (ID 10)

| Start | Count | Registers |
|---|---|---|
| 30000 | 27 | 30000–30026 |
| 31000 | 10 | 31000–31009 |
| 31011 | 8 | 31011–31018 |
| 31100 | 6 | 31100–31105 |

### EP3300TLV (ID 10)

| Start | Count | Registers |
|---|---|---|
| 30000 | 27 | 30000–30026 |
| 30030 | 20 | 30030–30049 |
| 31000 | 10 | 31000–31009 |
| 31011 | 8 | 31011–31018 |
| 31020 | 9 | 31020–31028 |
| 31100 | 17 | 31100–31116 |
| 31200 | 2 | 31200–31201 |

### PV2000PK (ID 10)

| Start | Count | Registers |
|---|---|---|
| 30000 | 27 | 30000–30026 |
| 30030 | 12 | 30030–30041 |
| 31000 | 10 | 31000–31009 |
| 31011 | 8 | 31011–31018 |
| 31100 | 8 | 31100–31107 |

### PH1000 (ID 5)

| Start | Count | Registers |
|---|---|---|
| 10105 | 12 | 10105–10116 |
| 15205 | 30 | 15205–15234 |
| 20001 | 39 | 20001–20039 |
| 20106 | 4 | 20106–20109 |
| 20133 | 9 | 20133–20141 |
| 20161 | 60 | 20161–20220 |
| 25201 | 74 | 25201–25274 |
| 25329 | 18 | 25329–25346 |
| 25347 | 8 | 25347–25354 |
| 25355 | 2 | 25355–25356 |
| 10275 | 15 | 10275–10289 |

### PH5000 (ID 6)

| Start | Count | Registers |
|---|---|---|
| 15205 | 30 | 15205–15234 |
| 20001 | 5 | 20001–20005 |
| 20135 | 1 | 20135 |
| 20161 | 59 | 20161–20219 |
| 25201 | 33 | 25201–25233 |
| 25257 | 8 | 25257–25264 |
| 25329 | 26 | 25329–25354 |

### PC1800 (ID 1)

| Start | Count | Registers |
|---|---|---|
| 10000 | 9 | 10000–10008 |
| 10101 | 25 | 10101–10125 |
| 15201 | 24 | 15201–15224 |

### PH1800 / SP1800 (ID 4)

| Start | Count | Registers |
|---|---|---|
| 10001 | 8 | 10001–10008 |
| 10103 | 10 | 10103–10112 |
| 15201 | 21 | 15201–15221 |
| 20000 | 17 | 20000–20016 |
| 20101 | 43 | 20101–20143 |
| 25201 | 79 | 25201–25279 |

### EP1800 (ID 4) — inverter only (no charger status)

| Start | Count | Registers |
|---|---|---|
| 20000 | 17 | 20000–20016 |
| 20101 | 43 | 20101–20143 |
| 25201 | 79 | 25201–25279 |
| 10103 | 10 | 10103–10112 |

### PV3500PRO (ID 4)

| Start | Count | Registers |
|---|---|---|
| 20001 | 16 | 20001–20016 |
| 20101 | 43 | 20101–20143 |
| 25201 | 38 | 25201–25238 |
| 25239 | 37 | 25239–25275 |
| 10001 | 8 | 10001–10008 |
| 10103 | 10 | 10103–10112 |
| 15201 | 21 | 15201–15221 |

---

## 10. Battery Type Enum

| Value | Meaning |
|---|---|
| 0 | Lead Acid |
| 1 | GEL |
| 2 | AGM |
| 3 | Lithium |
| 4 | User Defined |
| 5 | — |
| 6 | — |

---

## 11. Grid-Tie Safety Types (16 types)

Defined in `Ph1000M.GridTieSafetyTypeArr` (16 entries, index 0–15):

| Value | Meaning |
|---|---|
| 0 | VDE0126 |
| 1 | AS4777 |
| 2 | UL1741 |
| 3 | C10/11 |
| 4 | ONS |
| 5 | C20/11 |
| 6 | — |
| 7 | — |
| 8 | — |
| 9 | — |
| 10 | — |
| 11 | — |
| 12 | — |
| 13 | — |
| 14 | — |
| 15 | — |

---

## 12. Notes and Caveats

* **Decompiled source** — the `Infrastructure` library (containing `Helper`, `ModbusAttribute`, and actual Modbus RTU framing) is external and not included. The protocol analysis is based solely on register addresses, coefficients, signed flags, and parsing logic visible in the `Domin.Entities` classes.
* **Function codes** — not present in these sources. Batch reads most likely use Modbus function 03 (Read Holding Registers); single writes use function 06 (Write Single Register).
* **Known quirks in the source:**
  * In `Ep180010414M`, register 25259 is mapped to both `AccumulatedBuyPowerL` and `AccumulatedGridChargerPowerH` — a decompilation artifact or conflict.
  * In `Cdy10414M`, `LoadCurrent` has a display name of `"Battery voltage"` — likely a copy-paste bug.
  * In `Pv3500ProM`, `WritableAttrs` contains `2000` which is likely a typo for `20000`.
  * In `Ep3300M`, `AffectAddress` contains `31001` twice (duplicate entry).
  * Energy scaling differs between device families (×0.1 vs no multiplier).
* **Protocol edition** — `10414` maps to version string `"1.04.14"`. The `Ph1800M` and `Cdy10414M` classes display a "Recommended version" warning if the device's protocol edition doesn't match the expected one.

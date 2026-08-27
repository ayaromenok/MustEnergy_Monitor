"""Modbus RTU communication layer."""

from __future__ import annotations

import struct
import logging
from typing import Optional

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

log = logging.getLogger(__name__)


class ModbusRTUClient:
    """Thin wrapper around pymodbus ModbusSerialClient."""

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        timeout: float = 1.0,
    ):
        self._client: Optional[ModbusSerialClient] = None
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout

    # ------------------------------------------------------------------
    def connect(self) -> None:
        self._client = ModbusSerialClient(
            port=self._port,
            baudrate=self._baudrate,
            bytesize=self._bytesize,
            parity=self._parity,
            stopbits=self._stopbits,
            timeout=self._timeout,
        )
        if not self._client.connect():
            raise ConnectionError(f"Could not connect to {self._port}")
        log.info("Connected to %s @ %d", self._port, self._baudrate)

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *a):
        self.disconnect()

    # -- bulk reads ----------------------------------------------------
    def read_holding_registers(
        self, device_id: int, start: int, count: int
    ) -> list[int]:
        """Read *count* holding registers from *device_id*."""
        resp = self._client.read_holding_registers(
            address=start, count=count, device_id=device_id
        )
        if resp.isError():
            raise ModbusException(
                f"Read error at addr={start} count={count} slave={device_id}"
            )
        return list(resp.registers)

    def read_multiple_blocks(
        self, device_id: int, blocks: list[tuple[int, int]]
    ) -> dict[int, list[int]]:
        """Read multiple non-contiguous block ranges.

        Parameters
        ----------
        blocks : list[(start, count)]
            Each tuple is (start_address, number_of_registers).

        Returns
        -------
        dict mapping start_address -> list of register values.
        """
        result: dict[int, list[int]] = {}
        for start, count in blocks:
            try:
                result[start] = self.read_holding_registers(device_id, start, count)
            except ModbusException as exc:
                log.warning("Block %d-%d failed: %s", start, start + count - 1, exc)
                result[start] = [0] * count
        return result

    # -- single register write -----------------------------------------
    def write_single_register(
        self, device_id: int, address: int, value: int
    ) -> None:
        """Write a single holding register."""
        resp = self._client.write_register(
            address=address, value=value, device_id=device_id
        )
        if resp.isError():
            raise ModbusException(
                f"Write error at addr={address} slave={device_id}"
            )
        log.debug("Wrote 0x%04X -> %d on slave %d", address, value, device_id)

    # -- write multiple registers --------------------------------------
    def write_multiple_registers(
        self, device_id: int, address: int, values: list[int]
    ) -> None:
        """Write consecutive holding registers."""
        resp = self._client.write_registers(
            address=address, values=values, device_id=device_id
        )
        if resp.isError():
            raise ModbusException(
                f"Multi-write error at addr={address} slave={device_id}"
            )
        log.debug(
            "Wrote %d registers starting at 0x%04X on slave %d",
            len(values),
            address,
            device_id,
        )

    # -- scan / discovery ----------------------------------------------
    def scan_device_ids(
        self, start_addr: int, end_addr: Optional[int] = None
    ) -> list[int]:
        """Scan device IDs 1-254 by reading a known register.

        Returns list of responding device IDs.
        """
        if end_addr is None:
            end_addr = start_addr + 10
        found: list[int] = []
        for dev_id in range(1, 255):
            try:
                self.read_holding_registers(dev_id, start_addr, 1)
                found.append(dev_id)
                log.info("Found device at ID %d", dev_id)
            except ModbusException:
                pass
        return found

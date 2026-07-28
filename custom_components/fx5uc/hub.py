"""Modbus TCP hub for Mitsubishi FX5UC PLC."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusIOException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_INPUT_COUNT,
    CONF_INPUT_START,
    CONF_OUTPUT_COUNT,
    CONF_OUTPUT_START,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_INPUT_COUNT,
    DEFAULT_INPUT_START,
    DEFAULT_OUTPUT_COUNT,
    DEFAULT_OUTPUT_START,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class FX5UCHub:
    """Manages the Modbus TCP connection to a Mitsubishi FX5UC PLC."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the hub."""
        self.hass = hass
        self.host: str = config[CONF_HOST]
        self.port: int = config.get(CONF_PORT, DEFAULT_PORT)
        self.slave: int = config.get(CONF_SLAVE, DEFAULT_SLAVE)
        self.scan_interval: int = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        self.input_start: int = config.get(CONF_INPUT_START, DEFAULT_INPUT_START)
        self.input_count: int = config.get(CONF_INPUT_COUNT, DEFAULT_INPUT_COUNT)
        self.output_start: int = config.get(CONF_OUTPUT_START, DEFAULT_OUTPUT_START)
        self.output_count: int = config.get(CONF_OUTPUT_COUNT, DEFAULT_OUTPUT_COUNT)

        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()
        self.available: bool = False

    @property
    def client(self) -> AsyncModbusTcpClient:
        """Return the Modbus client."""
        if self._client is None:
            raise ConnectionException("Modbus client not initialized")
        return self._client

    async def async_connect(self) -> bool:
        """Connect to the PLC."""
        try:
            self._client = AsyncModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=5,
                retries=3,
            )
            connected = await self._client.connect()
            self.available = connected
            if connected:
                _LOGGER.info(
                    "Connected to FX5UC at %s:%s", self.host, self.port
                )
            else:
                _LOGGER.error(
                    "Failed to connect to FX5UC at %s:%s", self.host, self.port
                )
            return connected
        except Exception as err:
            _LOGGER.error("Error connecting to FX5UC: %s", err)
            self.available = False
            return False

    async def async_disconnect(self) -> None:
        """Disconnect from the PLC."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self.available = False
            _LOGGER.info("Disconnected from FX5UC at %s:%s", self.host, self.port)

    async def _call_modbus(self, func_name: str, *args, **kwargs):
        """Universal helper to call pymodbus methods across different versions."""
        func = getattr(self.client, func_name)
        # Try different parameter names used by different pymodbus versions
        for param_name in ("unit", "slave", "device_id"):
            try:
                kw = dict(kwargs)
                kw[param_name] = self.slave
                return await func(*args, **kw)
            except TypeError:
                continue
        # Fallback to default args without explicit slave/unit
        return await func(*args, **kwargs)

    async def async_read_inputs(self) -> list[bool]:
        """Read discrete inputs (X) from the PLC."""
        async with self._lock:
            try:
                result = await self._call_modbus(
                    "read_discrete_inputs",
                    address=self.input_start,
                    count=self.input_count,
                )

                if result.isError():
                    _LOGGER.error("Modbus error reading inputs (X%s..): %s", self.input_start, result)
                    raise ModbusIOException(f"Error reading inputs: {result}")
                self.available = True
                bits = list(result.bits[: self.input_count])
                _LOGGER.info("FX5UC Inputs read (X%s..X%s): %s", self.input_start, self.input_start + self.input_count - 1, bits[:8])
                return bits
            except ConnectionException as err:
                self.available = False
                raise UpdateFailed(f"Connection lost to FX5UC: {err}") from err
            except Exception as err:
                raise UpdateFailed(f"Error reading inputs: {err}") from err

    async def async_read_coils(self) -> list[bool]:
        """Read coils / outputs (Y) from the PLC."""
        async with self._lock:
            try:
                result = await self._call_modbus(
                    "read_coils",
                    address=self.output_start,
                    count=self.output_count,
                )

                if result.isError():
                    _LOGGER.error("Modbus error reading coils (Y%s..): %s", self.output_start, result)
                    raise ModbusIOException(f"Error reading coils: {result}")
                self.available = True
                bits = list(result.bits[: self.output_count])
                _LOGGER.info("FX5UC Coils read (Y%s..Y%s): %s", self.output_start, self.output_start + self.output_count - 1, bits[:8])
                return bits
            except ConnectionException as err:
                self.available = False
                raise UpdateFailed(f"Connection lost to FX5UC: {err}") from err
            except Exception as err:
                raise UpdateFailed(f"Error reading coils: {err}") from err

    async def async_write_coil(self, address: int, value: bool) -> bool:
        """Write a single coil / output (Y)."""
        async with self._lock:
            try:
                _LOGGER.info("Sending write command to FX5UC coil Y%s = %s", address, value)
                result = await self._call_modbus(
                    "write_coil",
                    address=address,
                    value=value,
                )

                if result.isError():
                    _LOGGER.error("Error writing coil Y%s: %s", address, result)
                    return False
                _LOGGER.info("Successfully wrote coil Y%s = %s on FX5UC", address, value)
                return True
            except ConnectionException as err:
                self.available = False
                _LOGGER.error("Connection lost writing coil Y%s: %s", address, err)
                return False
            except Exception as err:
                _LOGGER.error("Error writing coil Y%s: %s", address, err)
                return False

    async def async_test_connection(self) -> bool:
        """Test connection by attempting to connect via TCP and read a coil."""
        try:
            client = AsyncModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=5,
            )
            connected = await client.connect()
            if not connected:
                return False

            # Try to read — even a Modbus exception response means
            # the TCP connection to the PLC works fine.
            try:
                result = await self._call_modbus(
                    "read_coils",
                    address=self.output_start,
                    count=1,
                )
                # Any response (even error) means PLC is reachable
                _LOGGER.debug("Test read result: %s", result)
            except Exception as read_err:
                # Read failed but TCP connected — PLC is reachable
                _LOGGER.debug("Test read error (TCP OK): %s", read_err)

            client.close()
            return True
        except Exception as err:
            _LOGGER.error("Test connection failed: %s", err)
            return False


class FX5UCCoordinator(DataUpdateCoordinator):
    """Coordinator to poll FX5UC inputs and outputs."""

    def __init__(self, hass: HomeAssistant, hub: FX5UCHub) -> None:
        """Initialize the coordinator."""
        self.hub = hub
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{hub.host}",
            update_interval=timedelta(seconds=hub.scan_interval),
        )

    async def _async_update_data(self) -> dict[str, list[bool]]:
        """Fetch data from the PLC.

        Returns dict with 'inputs' and 'outputs' lists of booleans.
        Gracefully handles Modbus errors — returns False for unreadable I/O.
        """
        # Reconnect if needed
        if not self.hub.available:
            try:
                connected = await self.hub.async_connect()
                if not connected:
                    raise UpdateFailed(
                        f"Cannot connect to FX5UC at {self.hub.host}:{self.hub.port}"
                    )
            except UpdateFailed:
                raise
            except Exception as err:
                raise UpdateFailed(f"Connection error: {err}") from err

        # Read inputs — gracefully handle errors
        inputs: list[bool] = [False] * self.hub.input_count
        try:
            inputs = await self.hub.async_read_inputs()
        except UpdateFailed:
            _LOGGER.warning("Could not read inputs from FX5UC — using defaults")
        except Exception as err:
            _LOGGER.warning("Error reading inputs: %s", err)

        # Read outputs — gracefully handle errors
        outputs: list[bool] = [False] * self.hub.output_count
        try:
            outputs = await self.hub.async_read_coils()
        except UpdateFailed:
            _LOGGER.warning("Could not read outputs from FX5UC — using defaults")
        except Exception as err:
            _LOGGER.warning("Error reading outputs: %s", err)

        return {
            "inputs": inputs,
            "outputs": outputs,
            "available": self.hub.available,
        }


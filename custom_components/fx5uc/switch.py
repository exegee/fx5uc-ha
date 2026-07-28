"""Switch platform for Mitsubishi FX5UC — PLC outputs (Y)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_IO_NAMES,
    CONF_OUTPUT_COUNT,
    CONF_OUTPUT_START,
    DEFAULT_OUTPUT_COUNT,
    DEFAULT_OUTPUT_START,
    DOMAIN,
)
from .hub import FX5UCCoordinator, FX5UCHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FX5UC switch entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: FX5UCHub = data["hub"]
    coordinator: FX5UCCoordinator = data["coordinator"]

    output_start = entry.data.get(CONF_OUTPUT_START, DEFAULT_OUTPUT_START)
    output_count = entry.data.get(CONF_OUTPUT_COUNT, DEFAULT_OUTPUT_COUNT)
    io_names: dict[str, str] = entry.options.get(CONF_IO_NAMES, {})

    entities = []
    for i in range(output_count):
        address = output_start + i
        alias_key = f"output_{address}"
        alias = io_names.get(alias_key)

        entities.append(
            FX5UCSwitch(
                coordinator=coordinator,
                hub=hub,
                entry_id=entry.entry_id,
                address=address,
                index=i,
                alias=alias,
            )
        )

    async_add_entities(entities)


class FX5UCSwitch(CoordinatorEntity[FX5UCCoordinator], SwitchEntity):
    """Represents a single PLC output (Y) as a Home Assistant switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FX5UCCoordinator,
        hub: FX5UCHub,
        entry_id: str,
        address: int,
        index: int,
        alias: str | None = None,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._hub = hub
        self._address = address
        self._index = index
        self._alias = alias

        # Unique ID ensures HA tracks this entity across restarts
        self._attr_unique_id = f"{entry_id}_output_{address}"
        self._attr_icon = "mdi:toggle-switch-outline"

        # Entity name — alias or default Y address
        if alias:
            self._attr_name = alias
        else:
            self._attr_name = f"Y{address}"

        # Device info — groups all entities under one device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": f"FX5UC ({hub.host})",
            "manufacturer": "Mitsubishi Electric",
            "model": "FX5UC PLC",
            "sw_version": "1.0.2",
        }

    @property
    def available(self) -> bool:
        """Return True if the hub is available."""
        return self._hub.available and super().available

    @property
    def is_on(self) -> bool | None:
        """Return the current state of the output."""
        if self.coordinator.data is None:
            return None
        outputs = self.coordinator.data.get("outputs", [])
        if self._index < len(outputs):
            return outputs[self._index]
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the output ON."""
        success = await self._hub.async_write_coil(self._address, True)
        if success:
            # Request immediate data refresh
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the output OFF."""
        success = await self._hub.async_write_coil(self._address, False)
        if success:
            await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

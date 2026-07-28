"""Binary sensor platform for Mitsubishi FX5UC — PLC inputs (X)."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_INPUT_COUNT,
    CONF_INPUT_START,
    CONF_IO_NAMES,
    DEFAULT_INPUT_COUNT,
    DEFAULT_INPUT_START,
    DOMAIN,
)
from .hub import FX5UCCoordinator, FX5UCHub
from .diagnostics_sensor import FX5UCConnectionStatus

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FX5UC binary sensor entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: FX5UCHub = data["hub"]
    coordinator: FX5UCCoordinator = data["coordinator"]

    input_start = entry.data.get(CONF_INPUT_START, DEFAULT_INPUT_START)
    input_count = entry.data.get(CONF_INPUT_COUNT, DEFAULT_INPUT_COUNT)
    io_names: dict[str, str] = entry.options.get(CONF_IO_NAMES, {})

    # Connection status sensor
    entities: list = [
        FX5UCConnectionStatus(coordinator, hub, entry.entry_id)
    ]

    # Input sensors
    for i in range(input_count):
        address = input_start + i
        alias_key = f"input_{address}"
        alias = io_names.get(alias_key)

        entities.append(
            FX5UCBinarySensor(
                coordinator=coordinator,
                hub=hub,
                entry_id=entry.entry_id,
                address=address,
                index=i,
                alias=alias,
            )
        )

    async_add_entities(entities)


class FX5UCBinarySensor(CoordinatorEntity[FX5UCCoordinator], BinarySensorEntity):
    """Represents a single PLC input (X) as a Home Assistant binary sensor."""

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
        """Initialize the binary sensor entity."""
        super().__init__(coordinator)
        self._hub = hub
        self._address = address
        self._index = index
        self._alias = alias

        # Unique ID ensures HA tracks this entity across restarts
        self._attr_unique_id = f"{entry_id}_input_{address}"

        # Entity name — alias or default X address
        if alias:
            self._attr_name = alias
        else:
            self._attr_name = f"X{address}"

        # Device info — groups all entities under one device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": f"FX5UC ({hub.host})",
            "manufacturer": "Mitsubishi Electric",
            "model": "FX5UC",
        }

    @property
    def available(self) -> bool:
        """Return True if the hub is available."""
        return self._hub.available and super().available

    @property
    def is_on(self) -> bool | None:
        """Return the current state of the input."""
        if self.coordinator.data is None:
            return None
        inputs = self.coordinator.data.get("inputs", [])
        if self._index < len(inputs):
            return inputs[self._index]
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

"""Sensor platform for Mitsubishi FX5UC — connection status."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hub import FX5UCCoordinator, FX5UCHub

_LOGGER = logging.getLogger(__name__)


class FX5UCConnectionStatus(CoordinatorEntity[FX5UCCoordinator], BinarySensorEntity):
    """Binary sensor showing PLC connection status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Connection"

    def __init__(
        self,
        coordinator: FX5UCCoordinator,
        hub: FX5UCHub,
        entry_id: str,
    ) -> None:
        """Initialize the connection status sensor."""
        super().__init__(coordinator)
        self._hub = hub
        self._attr_unique_id = f"{entry_id}_connection_status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": f"FX5UC ({hub.host})",
            "manufacturer": "Mitsubishi Electric",
            "model": "FX5UC PLC",
            "sw_version": "1.0.3",
        }

    @property
    def is_on(self) -> bool:
        """Return True if connected to PLC."""
        return self._hub.available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

"""The Mitsubishi FX5UC integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .hub import FX5UCCoordinator, FX5UCHub

_LOGGER = logging.getLogger(__name__)

type FX5UCConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: FX5UCConfigEntry) -> bool:
    """Set up FX5UC from a config entry."""
    hub = FX5UCHub(hass, dict(entry.data))

    connected = await hub.async_connect()
    if not connected:
        _LOGGER.error(
            "Could not connect to FX5UC at %s:%s",
            hub.host,
            hub.port,
        )
        return False

    coordinator = FX5UCCoordinator(hass, hub)

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store hub and coordinator for platforms to access
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "hub": hub,
        "coordinator": coordinator,
    }

    # Forward setup to platforms (switch, binary_sensor)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register listener for options updates (alias changes)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: FX5UCConfigEntry
) -> None:
    """Handle options update — reload integration to apply alias changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: FX5UCConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        hub: FX5UCHub = data["hub"]
        await hub.async_disconnect()

    return unload_ok

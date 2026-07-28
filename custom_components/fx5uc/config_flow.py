"""Config flow for Mitsubishi FX5UC integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_HOST,
    CONF_INPUT_COUNT,
    CONF_INPUT_START,
    CONF_IO_NAMES,
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
    MAX_IO_COUNT,
)
from .hub import FX5UCHub

_LOGGER = logging.getLogger(__name__)


class FX5UCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mitsubishi FX5UC."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Connection parameters."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if already configured with same host
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})

            # Test connection
            hub = FX5UCHub(self.hass, user_input)
            can_connect = await hub.async_test_connection()

            if can_connect:
                self._data = user_input
                return await self.async_step_io_config()
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                    vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=255)
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                }
            ),
            errors=errors,
        )

    async def async_step_io_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: I/O address configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            title = f"FX5UC ({self._data[CONF_HOST]})"
            return self.async_create_entry(title=title, data=self._data)

        return self.async_show_form(
            step_id="io_config",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_INPUT_START, default=DEFAULT_INPUT_START
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=9999)),
                    vol.Required(
                        CONF_INPUT_COUNT, default=DEFAULT_INPUT_COUNT
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_IO_COUNT)),
                    vol.Required(
                        CONF_OUTPUT_START, default=DEFAULT_OUTPUT_START
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=9999)),
                    vol.Required(
                        CONF_OUTPUT_COUNT, default=DEFAULT_OUTPUT_COUNT
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_IO_COUNT)),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> FX5UCOptionsFlowHandler:
        """Get the options flow handler."""
        return FX5UCOptionsFlowHandler()


class FX5UCOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for FX5UC — alias naming and scan interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Main options step — choose what to configure."""
        if user_input is not None:
            action = user_input.get("action", "aliases")
            if action == "aliases_inputs":
                return await self.async_step_aliases_inputs()
            elif action == "aliases_outputs":
                return await self.async_step_aliases_outputs()
            elif action == "settings":
                return await self.async_step_settings()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="aliases_inputs"): vol.In(
                        {
                            "aliases_inputs": "Nazwy wejść (X)",
                            "aliases_outputs": "Nazwy wyjść (Y)",
                            "settings": "Ustawienia połączenia",
                        }
                    ),
                }
            ),
        )

    async def async_step_aliases_inputs(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure aliases for inputs."""
        entry_data = self.config_entry.data
        io_names: dict[str, str] = dict(
            self.config_entry.options.get(CONF_IO_NAMES, {})
        )
        input_start = entry_data.get(CONF_INPUT_START, DEFAULT_INPUT_START)
        input_count = entry_data.get(CONF_INPUT_COUNT, DEFAULT_INPUT_COUNT)

        if user_input is not None:
            # Save aliases — merge with existing
            for i in range(input_count):
                addr = input_start + i
                key = f"input_{addr}"
                form_key = f"name_input_{addr}"
                name = user_input.get(form_key, "").strip()
                if name:
                    io_names[key] = name
                elif key in io_names:
                    del io_names[key]

            new_options = dict(self.config_entry.options)
            new_options[CONF_IO_NAMES] = io_names
            return self.async_create_entry(data=new_options)

        # Build form with current aliases
        schema_dict: dict[Any, Any] = {}
        for i in range(input_count):
            addr = input_start + i
            key = f"input_{addr}"
            current_name = io_names.get(key, "")
            schema_dict[
                vol.Optional(f"name_input_{addr}", default=current_name)
            ] = str

        return self.async_show_form(
            step_id="aliases_inputs",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_aliases_outputs(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure aliases for outputs."""
        entry_data = self.config_entry.data
        io_names: dict[str, str] = dict(
            self.config_entry.options.get(CONF_IO_NAMES, {})
        )
        output_start = entry_data.get(CONF_OUTPUT_START, DEFAULT_OUTPUT_START)
        output_count = entry_data.get(CONF_OUTPUT_COUNT, DEFAULT_OUTPUT_COUNT)

        if user_input is not None:
            for i in range(output_count):
                addr = output_start + i
                key = f"output_{addr}"
                form_key = f"name_output_{addr}"
                name = user_input.get(form_key, "").strip()
                if name:
                    io_names[key] = name
                elif key in io_names:
                    del io_names[key]

            new_options = dict(self.config_entry.options)
            new_options[CONF_IO_NAMES] = io_names
            return self.async_create_entry(data=new_options)

        schema_dict: dict[Any, Any] = {}
        for i in range(output_count):
            addr = output_start + i
            key = f"output_{addr}"
            current_name = io_names.get(key, "")
            schema_dict[
                vol.Optional(f"name_output_{addr}", default=current_name)
            ] = str

        return self.async_show_form(
            step_id="aliases_outputs",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure connection settings."""
        if user_input is not None:
            new_options = dict(self.config_entry.options)
            new_options[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]
            return self.async_create_entry(data=new_options)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current_interval
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                }
            ),
        )

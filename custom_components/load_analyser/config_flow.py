"""Config flow for Load Analyser."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import CONF_ENERGY_SENSOR, CONF_POWER_SENSOR, CONF_PROGRAM_SENSOR, CONF_STATE_SENSOR, DOMAIN

class LoadAnalyserConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{DOMAIN}_{user_input[CONF_NAME].lower().replace(' ', '_')}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_NAME, default="Appliance 1"): str,
            vol.Required(CONF_POWER_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(CONF_ENERGY_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(CONF_PROGRAM_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(CONF_STATE_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor", "binary_sensor"])),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

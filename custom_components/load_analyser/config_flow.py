"""Config flow for Load Analyser."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_BLOCKED_WINDOW_ENTITY, CONF_EARLIEST_START_ENTITY, CONF_ENERGY_SENSOR,
    CONF_GREEN_WINDOW_ENTITY, CONF_LATEST_FINISH_ENTITY, CONF_POWER_SENSOR,
    CONF_PROGRAM_SENSOR, CONF_STATE_SENSOR, CONF_TARIFF_SENSOR, DOMAIN,
)

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
            vol.Optional(CONF_TARIFF_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(CONF_GREEN_WINDOW_ENTITY): selector.EntitySelector(selector.EntitySelectorConfig()),
            vol.Optional(CONF_BLOCKED_WINDOW_ENTITY): selector.EntitySelector(selector.EntitySelectorConfig()),
            vol.Optional(CONF_EARLIEST_START_ENTITY): selector.EntitySelector(selector.EntitySelectorConfig()),
            vol.Optional(CONF_LATEST_FINISH_ENTITY): selector.EntitySelector(selector.EntitySelectorConfig()),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return LoadAnalyserOptionsFlow(config_entry)


class LoadAnalyserOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema({
            vol.Optional("scan_interval", default=current.get("scan_interval", 60)): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            vol.Optional("active_power_threshold", default=current.get("active_power_threshold", 10)): vol.Coerce(float),
            vol.Optional("finish_delay", default=current.get("finish_delay", 5)): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            vol.Optional("learning_min_runtime_minutes", default=current.get("learning_min_runtime_minutes", 5)): vol.Coerce(float),
            vol.Optional("learning_min_samples", default=current.get("learning_min_samples", 3)): vol.All(vol.Coerce(int), vol.Range(min=2)),
            vol.Optional("learning_min_energy_kwh", default=current.get("learning_min_energy_kwh", 0.001)): vol.Coerce(float),
            vol.Optional("cost_search_hours", default=current.get("cost_search_hours", 24)): vol.All(vol.Coerce(int), vol.Range(min=1, max=72)),
            vol.Optional("cost_candidate_interval", default=current.get("cost_candidate_interval", 5)): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            vol.Optional("tariff_timezone", default=current.get("tariff_timezone", "Europe/London")): str,
            vol.Optional("tariff_price_unit", default=current.get("tariff_price_unit", "p_per_kwh")): selector.SelectSelector(selector.SelectSelectorConfig(options=["p_per_kwh", "gbp_per_kwh"])),
            vol.Optional("schedule_strategy", default=current.get("schedule_strategy", "cheapest_absolute")): selector.SelectSelector(selector.SelectSelectorConfig(options=["cheapest_absolute", "cheapest_earliest_finish", "cheapest_latest_finish"])),
            vol.Optional("schedule_window_preference", default=current.get("schedule_window_preference", "any")): selector.SelectSelector(selector.SelectSelectorConfig(options=["any", "overnight_only", "prefer_overnight", "daytime_only", "prefer_daytime"])),
            vol.Optional("schedule_overnight_start", default=current.get("schedule_overnight_start", "20:00")): str,
            vol.Optional("schedule_overnight_end", default=current.get("schedule_overnight_end", "08:00")): str,
            vol.Optional("schedule_equivalent_cost_tolerance_pence", default=current.get("schedule_equivalent_cost_tolerance_pence", 0)): vol.Coerce(float),
            vol.Optional("schedule_preference_weight_pence", default=current.get("schedule_preference_weight_pence", 0.1)): vol.Coerce(float),
            vol.Optional("program_policies_json", default=current.get("program_policies_json", "[]")): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema)

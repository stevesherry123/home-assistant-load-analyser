"""Data coordination and cycle learning for Load Analyser."""
from __future__ import annotations

from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import logging
from homeassistant.helpers.storage import Store

from .const import CONF_POWER_SENSOR, DEFAULT_SCAN_INTERVAL, DOMAIN

class LoadAnalyserCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.power_sensor = entry.data[CONF_POWER_SENSOR]
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        super().__init__(hass, logging.getLogger(__package__), name=DOMAIN, update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL))

    async def _async_update_data(self) -> dict:
        state = self.hass.states.get(self.power_sensor)
        if state is None:
            raise UpdateFailed(f"Source entity {self.power_sensor} is unavailable")
        try:
            power = float(state.state)
        except ValueError as err:
            raise UpdateFailed(f"Source entity {self.power_sensor} is not numeric") from err
        return {"power": power, "source_entity": self.power_sensor, "source_updated": state.last_updated.isoformat()}

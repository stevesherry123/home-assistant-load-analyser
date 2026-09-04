"""Sensors exposed by Load Analyser."""
from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import LoadAnalyserCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LoadAnalyserPowerSensor(coordinator, entry)])

class LoadAnalyserPowerSensor(CoordinatorEntity[LoadAnalyserCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Current power"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:flash"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_current_power"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": entry.title, "manufacturer": "Load Analyser"}

    @property
    def native_value(self):
        return self.coordinator.data.get("power") if self.coordinator.data else None

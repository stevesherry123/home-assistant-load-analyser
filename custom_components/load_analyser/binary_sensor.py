"""Readiness sensors for Load Analyser."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LoadAnalyserCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GoodToStartSensor(coordinator, entry), AutomationReadySensor(coordinator, entry)])


class BaseReadinessSensor(CoordinatorEntity[LoadAnalyserCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": entry.title}

    @property
    def extra_state_attributes(self):
        advice = self.coordinator.data.get("schedule_advice", {})
        return {"reason": advice.get("reason"), "recommended_start": advice.get("recommended_start"), "confidence": advice.get("confidence")}


class GoodToStartSensor(BaseReadinessSensor):
    _attr_name = "Good to start"
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "good_to_start")

    @property
    def is_on(self):
        return bool(self.coordinator.data.get("schedule_advice", {}).get("good_to_start"))


class AutomationReadySensor(BaseReadinessSensor):
    _attr_name = "Automation ready"
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "automation_ready")

    @property
    def is_on(self):
        return bool(self.coordinator.data.get("schedule_advice", {}).get("automation_ready"))

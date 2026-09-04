"""Maintenance buttons for Load Analyser."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LoadAnalyserCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RecalculateButton(coordinator, entry), ResetLearningButton(coordinator, entry)])


class BaseButton(CoordinatorEntity[LoadAnalyserCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: LoadAnalyserCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": entry.title}


class RecalculateButton(BaseButton):
    _attr_name = "Recalculate"
    _attr_icon = "mdi:calculator-variant"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "recalculate")

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class ResetLearningButton(BaseButton):
    _attr_name = "Reset learning"
    _attr_icon = "mdi:database-refresh"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "reset_learning")

    async def async_press(self) -> None:
        await self.coordinator.async_reset_learning()

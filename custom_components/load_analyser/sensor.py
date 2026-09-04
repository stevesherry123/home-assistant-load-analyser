"""Native sensors exposed by Load Analyser."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LoadAnalyserCoordinator


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def _recommendation_attributes(data: dict[str, Any]) -> dict[str, Any]:
    recommendation = data.get("recommendation", {})
    return {
        "reason": recommendation.get("reason"),
        "finish": recommendation.get("finish"),
        "confidence": recommendation.get("confidence"),
        "energy_kwh": recommendation.get("energy_kwh"),
        "negative_price_run": recommendation.get("negative_price_run"),
        "overnight_comparison": recommendation.get("overnight_comparison"),
        "daytime_comparison": recommendation.get("daytime_comparison"),
        "greenest_comparison": recommendation.get("greenest_comparison"),
        "decision_policy": recommendation.get("decision_policy"),
        "program_diagnostics": recommendation.get("program_diagnostics", []),
    }


def _intent_attributes(data: dict[str, Any], intent: str) -> dict[str, Any]:
    return dict(data.get("recommendation", {}).get(f"{intent}_recommendation") or {})


@dataclass(frozen=True, kw_only=True)
class Description:
    key: str
    name: str
    value: Callable[[dict[str, Any]], Any]
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    icon: str | None = None
    attributes: Callable[[dict[str, Any]], dict[str, Any]] | None = None


DESCRIPTIONS = (
    Description(key="current_power", name="Current power", value=lambda d: d.get("power"), unit=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    Description(key="current_energy", name="Current energy", value=lambda d: d.get("energy"), unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY),
    Description(key="cycle_state", name="Cycle state", value=lambda d: d.get("cycle_state"), icon="mdi:state-machine", attributes=lambda d: {"cycle_start": d.get("cycle_start"), "sample_count": d.get("sample_count"), "data_quality": d.get("data_quality")}),
    Description(key="program", name="Program", value=lambda d: d.get("program"), icon="mdi:format-list-bulleted"),
    Description(key="sample_count", name="Sample count", value=lambda d: d.get("sample_count"), icon="mdi:counter"),
    Description(key="peak_power", name="Peak power", value=lambda d: d.get("peak_power"), unit=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER),
    Description(key="last_program", name="Last program", value=lambda d: d.get("last_cycle", {}).get("program", "unknown"), icon="mdi:format-list-bulleted"),
    Description(key="last_runtime", name="Last runtime", value=lambda d: d.get("last_cycle", {}).get("runtime_minutes"), unit=UnitOfTime.MINUTES, device_class=SensorDeviceClass.DURATION),
    Description(key="last_energy", name="Last energy", value=lambda d: d.get("last_cycle", {}).get("energy_kwh"), unit=UnitOfEnergy.KILO_WATT_HOUR, device_class=SensorDeviceClass.ENERGY, attributes=lambda d: {"source": d.get("last_cycle", {}).get("energy_source"), "data_quality": "measured"}),
    Description(key="total_runs", name="Total runs", value=lambda d: d.get("total_runs"), state_class=SensorStateClass.TOTAL, icon="mdi:counter"),
    Description(key="learned_programs", name="Learned programs", value=lambda d: d.get("learned_programs"), icon="mdi:database-check", attributes=lambda d: {"programs": list(d.get("program_models", {}).values())}),
    Description(key="confidence", name="Model confidence", value=lambda d: max((m.get("confidence", 0) for m in d.get("program_models", {}).values()), default=0), unit=PERCENTAGE, icon="mdi:gauge"),
    Description(key="source_freshness", name="Source freshness", value=lambda d: _timestamp(d.get("source_updated")), device_class=SensorDeviceClass.TIMESTAMP),
    Description(key="cost_status", name="Cost status", value=lambda d: d.get("recommendation", {}).get("status", "not_ready"), icon="mdi:cash-clock", attributes=_recommendation_attributes),
    Description(key="recommended_program", name="Recommended program", value=lambda d: d.get("recommendation", {}).get("program", "none"), icon="mdi:format-list-checks"),
    Description(key="cheapest_start", name="Cheapest start", value=lambda d: d.get("recommendation", {}).get("start"), device_class=SensorDeviceClass.TIMESTAMP),
    Description(key="cheapest_cost", name="Cheapest cost", value=lambda d: d.get("recommendation", {}).get("total_cost_pence"), unit="p", icon="mdi:currency-gbp"),
    Description(key="potential_saving", name="Potential saving", value=lambda d: d.get("recommendation", {}).get("potential_saving_pence"), unit="p", icon="mdi:piggy-bank"),
    Description(key="cost_if_started_now", name="Cost if started now", value=lambda d: d.get("recommendation", {}).get("cost_if_started_now_pence"), unit="p", icon="mdi:cash-clock"),
    Description(key="cost_confidence", name="Cost confidence", value=lambda d: d.get("recommendation", {}).get("confidence"), unit=PERCENTAGE, icon="mdi:gauge"),
    Description(key="recommended_finish", name="Recommended finish", value=lambda d: _timestamp(d.get("recommendation", {}).get("finish")), device_class=SensorDeviceClass.TIMESTAMP),
    Description(key="current_energy_price", name="Current energy price", value=lambda d: d.get("recommendation", {}).get("current_price_p_per_kwh"), unit="p/kWh", icon="mdi:cash-sync"),
    Description(key="tariff_horizon", name="Tariff horizon", value=lambda d: d.get("recommendation", {}).get("forecast_hours"), unit="h", icon="mdi:timeline-clock"),
    Description(key="cost_forecast", name="Cost forecast", value=lambda d: len(d.get("recommendation", {}).get("cost_forecast", [])), icon="mdi:chart-timeline-variant", attributes=lambda d: {"forecast": d.get("recommendation", {}).get("cost_forecast", []), "diagnostics": d.get("recommendation", {}).get("forecast_diagnostics", [])}),
    Description(key="now_recommendation", name="Now recommendation", value=lambda d: (d.get("recommendation", {}).get("now_recommendation") or {}).get("start", "not_ready"), icon="mdi:play-circle", attributes=lambda d: _intent_attributes(d, "now")),
    Description(key="soon_recommendation", name="Soon recommendation", value=lambda d: (d.get("recommendation", {}).get("soon_recommendation") or {}).get("start", "not_ready"), icon="mdi:clock-fast", attributes=lambda d: _intent_attributes(d, "soon")),
    Description(key="overnight_recommendation", name="Overnight recommendation", value=lambda d: (d.get("recommendation", {}).get("overnight_recommendation") or {}).get("start", "not_ready"), icon="mdi:weather-night", attributes=lambda d: _intent_attributes(d, "overnight")),
    Description(key="negative_price_recommendation", name="Negative price recommendation", value=lambda d: (d.get("recommendation", {}).get("negative_price_recommendation") or {}).get("start", "not_ready"), icon="mdi:transmission-tower-export", attributes=lambda d: _intent_attributes(d, "negative_price")),
    Description(key="greenest_recommendation", name="Greenest recommendation", value=lambda d: (d.get("recommendation", {}).get("greenest_recommendation") or {}).get("start", "not_ready"), icon="mdi:leaf", attributes=lambda d: _intent_attributes(d, "greenest")),
    Description(key="program_policies", name="Program policies", value=lambda d: len(d.get("recommendation", {}).get("program_policies", [])), icon="mdi:tune-variant", attributes=lambda d: {"policies": d.get("recommendation", {}).get("program_policies", [])}),
    Description(key="profile_data", name="Profile data", value=lambda d: len(d.get("program_models", {})), icon="mdi:chart-line", attributes=lambda d: {"program_profiles": list(d.get("program_models", {}).values())}),
    Description(key="last_discarded_cycle", name="Last discarded cycle", value=lambda d: "ready" if d.get("last_discarded_cycle") else "none", icon="mdi:delete-clock", attributes=lambda d: d.get("last_discarded_cycle") or {}),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LoadAnalyserSensor(coordinator, entry, description) for description in DESCRIPTIONS])


class LoadAnalyserSensor(CoordinatorEntity[LoadAnalyserCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: LoadAnalyserCoordinator, entry: ConfigEntry, description: Description) -> None:
        super().__init__(coordinator)
        self.description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_icon = description.icon
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Load Analyser",
            "model": "Flexible load analyser",
        }

    @property
    def native_value(self):
        return self.description.value(self.coordinator.data or {})

    @property
    def extra_state_attributes(self):
        return self.description.attributes(self.coordinator.data or {}) if self.description.attributes else None

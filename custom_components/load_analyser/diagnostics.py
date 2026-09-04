"""Privacy-safe diagnostics for Load Analyser."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    active = coordinator.persisted.get("active_cycle")
    return {
        "entry": {
            "title": entry.title,
            "configured_source_kinds": sorted(entry.data),
            "options": {key: value for key, value in entry.options.items() if "entity" not in key},
        },
        "runtime": {
            "available": coordinator.last_update_success,
            "entity_count": len(entities),
            "active_cycle": bool(active),
            "active_sample_count": len(active.get("samples", [])) if active else 0,
        },
        "storage": {
            "schema_version": coordinator.persisted.get("schema_version"),
            "raw_cycle_count": len(coordinator.persisted.get("raw_cycles", [])),
            "learned_program_count": len(coordinator.persisted.get("program_models", {})),
            "discarded_cycle_count": len(coordinator.persisted.get("discarded_cycles", [])),
        },
    }

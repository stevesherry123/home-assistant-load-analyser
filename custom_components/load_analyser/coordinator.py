"""Native Home Assistant coordinator for Load Analyser."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_BLOCKED_WINDOW_ENTITY,
    CONF_EARLIEST_START_ENTITY,
    CONF_ENERGY_SENSOR,
    CONF_GREEN_WINDOW_ENTITY,
    CONF_LATEST_FINISH_ENTITY,
    CONF_POWER_SENSOR,
    CONF_PROGRAM_SENSOR,
    CONF_STATE_SENSOR,
    CONF_TARIFF_SENSOR,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .costing import recommend_cycle, tariff_periods_from_entity
from .legacy_runtime import blocked_windows_from_entity, datetime_from_entity_state, green_windows_from_entity, resolve_program_policies, schedule_advice

LOGGER = logging.getLogger(__package__)
STORAGE_VERSION = 1
MAX_CYCLE_MINUTES = 240
PROFILE_BINS = 20


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number == number else None
    except (TypeError, ValueError):
        return None


def _program(value: Any) -> str:
    text = str(value or "").strip()
    return "unknown" if not text or text.lower() in {STATE_UNKNOWN, STATE_UNAVAILABLE, "none"} else text


def _profile_energy(samples: list[dict[str, Any]]) -> float | None:
    usable = [(float(row["offset_seconds"]), _number(row.get("power_w"))) for row in samples]
    usable = [(offset, power) for offset, power in usable if power is not None]
    if len(usable) < 2:
        return None
    watt_seconds = sum((b[0] - a[0]) * (a[1] + b[1]) / 2 for a, b in zip(usable, usable[1:]))
    return round(watt_seconds / 3_600_000, 6)


def _normalise_profile(samples: list[dict[str, Any]], bins: int = PROFILE_BINS) -> list[float]:
    points = [(float(row["offset_seconds"]), _number(row.get("power_w"))) for row in samples]
    points = [(offset, power) for offset, power in points if power is not None]
    if not points:
        return []
    if len(points) == 1:
        return [round(points[0][1], 2)] * bins
    end = max(points[-1][0], 1.0)
    result: list[float] = []
    cursor = 0
    for index in range(bins):
        target = end * index / max(bins - 1, 1)
        while cursor + 1 < len(points) and points[cursor + 1][0] < target:
            cursor += 1
        left = points[cursor]
        right = points[min(cursor + 1, len(points) - 1)]
        ratio = 0 if right[0] == left[0] else (target - left[0]) / (right[0] - left[0])
        result.append(round(left[1] + (right[1] - left[1]) * ratio, 2))
    return result


class LoadAnalyserCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Observe one appliance and retain its learned model."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.config = {**entry.data, **entry.options}
        self.store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self.persisted: dict[str, Any] = {}
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=int(self.config.get("scan_interval", DEFAULT_SCAN_INTERVAL))),
        )

    async def async_load(self) -> None:
        loaded = await self.store.async_load()
        self.persisted = loaded if isinstance(loaded, dict) else {}
        self.persisted.setdefault("schema_version", STORAGE_VERSION)
        self.persisted.setdefault("raw_cycles", [])
        self.persisted.setdefault("program_models", {})
        self.persisted.setdefault("active_cycle", None)
        self.persisted.setdefault("discarded_cycles", [])

    async def async_reset_learning(self) -> None:
        """Remove learned history while retaining configuration."""
        self.persisted = {
            "schema_version": STORAGE_VERSION,
            "raw_cycles": [],
            "program_models": {},
            "active_cycle": None,
            "discarded_cycles": [],
        }
        await self.store.async_save(self.persisted)
        await self.async_request_refresh()

    def _state(self, key: str):
        entity_id = self.config.get(key)
        return self.hass.states.get(entity_id) if entity_id else None

    async def _async_update_data(self) -> dict[str, Any]:
        power_state = self._state(CONF_POWER_SENSOR)
        if power_state is None:
            raise UpdateFailed("The configured power source is unavailable")
        power = _number(power_state.state)
        if power is None:
            raise UpdateFailed("The configured power source is not numeric")

        now = datetime.now(timezone.utc)
        active_threshold = float(self.config.get("active_power_threshold", 10))
        active = power >= active_threshold
        cycle = self.persisted.get("active_cycle")
        changed = False

        program_state = self._state(CONF_PROGRAM_SENSOR)
        program = _program(program_state.state if program_state else None)
        energy_state = self._state(CONF_ENERGY_SENSOR)
        energy = _number(energy_state.state if energy_state else None)

        if active and cycle is None:
            cycle = {
                "id": now.isoformat(),
                "start": now.isoformat(),
                "program": program,
                "start_energy_kwh": energy,
                "samples": [],
                "finish_candidate": None,
            }
            self.persisted["active_cycle"] = cycle
            changed = True

        if cycle is not None:
            started = datetime.fromisoformat(cycle["start"])
            elapsed = max(0.0, (now - started).total_seconds())
            if elapsed <= MAX_CYCLE_MINUTES * 60:
                cycle["samples"].append({"offset_seconds": round(elapsed), "power_w": power})
                if cycle.get("program") == "unknown" and program != "unknown":
                    cycle["program"] = program
                changed = True

            if active:
                cycle["finish_candidate"] = None
            elif cycle.get("finish_candidate") is None:
                cycle["finish_candidate"] = now.isoformat()
            else:
                candidate = datetime.fromisoformat(cycle["finish_candidate"])
                finish_delay = int(self.config.get("finish_delay", 5))
                if (now - candidate).total_seconds() >= finish_delay * 60:
                    self._finalise_cycle(cycle, now, energy)
                    cycle = None
                    changed = True

        if changed:
            await self.store.async_save(self.persisted)

        models = self.persisted["program_models"]
        last = self.persisted.get("last_cycle") or {}
        recommendation = self._recommend(models, now)
        advice = schedule_advice(
            recommendation,
            self.config,
            now,
            cycle_running=cycle is not None,
            active_cycle_start=cycle.get("start") if cycle else None,
        )
        return {
            "power": power,
            "energy": energy,
            "cycle_state": "running" if cycle else "idle",
            "program": cycle.get("program") if cycle else program,
            "cycle_start": cycle.get("start") if cycle else None,
            "sample_count": len(cycle.get("samples", [])) if cycle else 0,
            "last_cycle": deepcopy(last),
            "last_discarded_cycle": deepcopy(self.persisted.get("last_discarded_cycle") or {}),
            "peak_power": max((_number(row.get("power_w")) or 0 for row in cycle.get("samples", [])), default=0) if cycle else 0,
            "total_runs": len(self.persisted["raw_cycles"]),
            "learned_programs": len(models),
            "program_models": deepcopy(models),
            "source_updated": power_state.last_updated.isoformat(),
            "data_quality": "measured",
            "recommendation": recommendation,
            "schedule_advice": advice,
        }

    def _recommend(self, models: dict[str, Any], now: datetime) -> dict[str, Any]:
        tariff_state = self._state(CONF_TARIFF_SENSOR)
        if tariff_state is None:
            return {"status": "not_configured", "reason": "tariff_source_not_configured"}
        try:
            periods = tariff_periods_from_entity(
                {"state": tariff_state.state, "attributes": dict(tariff_state.attributes)},
                reference_utc=now,
                timezone_name=str(self.config.get("tariff_timezone", self.hass.config.time_zone)),
                price_unit=str(self.config.get("tariff_price_unit", "p_per_kwh")),
            )
            import json
            configured_policies = json.loads(str(self.config.get("program_policies_json", "[]")))
            policies = resolve_program_policies(models, configured_policies)
            green_state = self._state(CONF_GREEN_WINDOW_ENTITY)
            blocked_state = self._state(CONF_BLOCKED_WINDOW_ENTITY)
            green_windows, _ = green_windows_from_entity(
                {"state": green_state.state, "attributes": dict(green_state.attributes)} if green_state else None,
                start=now, end=now + timedelta(hours=int(self.config.get("cost_search_hours", 24))),
                naive_timezone=self.hass.config.time_zone,
            )
            blocked_windows, _ = blocked_windows_from_entity(
                {"state": blocked_state.state, "attributes": dict(blocked_state.attributes)} if blocked_state else None,
                start=now, end=now + timedelta(hours=int(self.config.get("cost_search_hours", 24))),
                naive_timezone=self.hass.config.time_zone,
            )
            earliest_state = self._state(CONF_EARLIEST_START_ENTITY)
            latest_state = self._state(CONF_LATEST_FINISH_ENTITY)
            result = recommend_cycle(
                list(models.values()), policies, periods,
                reference_utc=now,
                search_hours=int(self.config.get("cost_search_hours", 24)),
                candidate_interval_minutes=int(self.config.get("cost_candidate_interval", 5)),
                schedule_timezone=str(self.config.get("tariff_timezone", self.hass.config.time_zone)),
                schedule_strategy=str(self.config.get("schedule_strategy", "cheapest_absolute")),
                equivalent_cost_tolerance_pence=float(self.config.get("schedule_equivalent_cost_tolerance_pence", 0)),
                preference_weight_pence=float(self.config.get("schedule_preference_weight_pence", 0.1)),
                window_preference=str(self.config.get("schedule_window_preference", "any")),
                overnight_start=str(self.config.get("schedule_overnight_start", "20:00")),
                overnight_end=str(self.config.get("schedule_overnight_end", "08:00")),
                earliest_start_utc=datetime_from_entity_state({"state": earliest_state.state} if earliest_state else None, naive_timezone=self.hass.config.time_zone),
                latest_finish_utc=datetime_from_entity_state({"state": latest_state.state} if latest_state else None, naive_timezone=self.hass.config.time_zone),
                green_windows=green_windows,
                blocked_windows=blocked_windows,
            )
            result["program_policies"] = policies
            return result
        except (TypeError, ValueError, KeyError) as err:
            LOGGER.warning("Unable to calculate recommendation: %s", type(err).__name__)
            return {"status": "invalid", "reason": type(err).__name__}

    def _finalise_cycle(self, cycle: dict[str, Any], finished: datetime, end_energy: float | None) -> None:
        if any(row.get("id") == cycle.get("id") for row in self.persisted["raw_cycles"]):
            self.persisted["active_cycle"] = None
            return
        started = datetime.fromisoformat(cycle["start"])
        runtime = round((finished - started).total_seconds() / 60, 2)
        profile_energy = _profile_energy(cycle["samples"])
        meter_energy = None
        if end_energy is not None and cycle.get("start_energy_kwh") is not None:
            delta = end_energy - float(cycle["start_energy_kwh"])
            meter_energy = round(delta, 6) if delta >= 0 else None
        record = {
            "schema_version": STORAGE_VERSION,
            "id": cycle["id"],
            "program": cycle.get("program", "unknown"),
            "start": cycle["start"],
            "finish": finished.isoformat(),
            "runtime_minutes": runtime,
            "energy_kwh": profile_energy if profile_energy is not None else meter_energy,
            "energy_source": "power_profile" if profile_energy is not None else "meter_delta",
            "meter_energy_kwh": meter_energy,
            "samples": cycle["samples"],
        }
        quality_issue = self._quality_issue(record)
        if quality_issue:
            record["exclusion_reason"] = quality_issue
            self.persisted["discarded_cycles"].append(record)
            self.persisted["discarded_cycles"] = self.persisted["discarded_cycles"][-20:]
            self.persisted["last_discarded_cycle"] = record
            self.persisted["active_cycle"] = None
            return
        self.persisted["raw_cycles"].append(record)
        self.persisted["raw_cycles"] = self.persisted["raw_cycles"][-50:]
        self.persisted["last_cycle"] = record
        self.persisted["active_cycle"] = None
        self._update_model(record)

    def _quality_issue(self, cycle: dict[str, Any]) -> str | None:
        if cycle.get("program") == "unknown":
            return "program_unknown"
        if cycle["runtime_minutes"] < float(self.config.get("learning_min_runtime_minutes", 5)):
            return "runtime_below_minimum"
        if len(cycle["samples"]) < int(self.config.get("learning_min_samples", 3)):
            return "sample_count_below_minimum"
        energy = cycle.get("energy_kwh")
        if energy is None or energy < float(self.config.get("learning_min_energy_kwh", 0.001)):
            return "energy_below_minimum"
        return None

    def _update_model(self, cycle: dict[str, Any]) -> None:
        program = cycle["program"]
        model = self.persisted["program_models"].setdefault(program, {"program": program, "runs": 0})
        runs = int(model.get("runs", 0)) + 1
        old_runtime = float(model.get("expected_runtime_minutes", cycle["runtime_minutes"]))
        old_energy = float(model.get("expected_energy_kwh", cycle.get("energy_kwh") or 0))
        energy = float(cycle.get("energy_kwh") or old_energy)
        profile = _normalise_profile(cycle["samples"])
        old_profile = model.get("representative_profile_w") or profile
        model.update({
            "runs": runs,
            "expected_runtime_minutes": round(old_runtime + (cycle["runtime_minutes"] - old_runtime) / runs, 2),
            "expected_energy_kwh": round(old_energy + (energy - old_energy) / runs, 6),
            "representative_profile_w": [round(old + (new - old) / runs, 2) for old, new in zip(old_profile, profile)],
            "confidence": min(100, runs * 20),
            "last_seen": cycle["finish"],
            "data_quality": "measured",
        })
    CONF_GREEN_WINDOW_ENTITY,
    CONF_LATEST_FINISH_ENTITY,

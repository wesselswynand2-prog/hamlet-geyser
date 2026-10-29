"""Runtime controller: reads sensors, decides, switches the geyser, keeps history."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import logic
from .const import (
    CONF_BATTERY_INVERT,
    CONF_BATTERY_POWER,
    CONF_BATTERY_SOC,
    CONF_COLLECTOR_MODE,
    CONF_COLLECTOR_TEMP,
    COLLECTOR_GEYSERWISE,
    COLLECTOR_NONE,
    COLLECTOR_SHELLY,
    CONF_PUMP_ENTITY,
    CONF_TANK_BOTTOM_TEMP,
    CONF_GEYSER_POWER,
    CONF_GEYSER_SWITCH,
    CONF_GEYSER_TEMP,
    CONF_GRID_INVERT,
    CONF_GRID_POWER,
    CONF_GRID_STATUS,
    CONF_LOAD_POWER,
    CONF_NAME,
    CONF_SOLAR_POWER,
    DOMAIN,
    SAMPLE_MINUTES,
    SIGNAL_UPDATE,
    UPDATE_INTERVAL_S,
)

_LOGGER = logging.getLogger(__name__)
STORE_VERSION = 1
BAD_STATES = (STATE_UNAVAILABLE, STATE_UNKNOWN, None, "", "none")
GRID_UP_WORDS = {"on", "true", "connected", "available", "grid", "ok", "online", "1", "yes"}


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


class GeyserController:
    """One geyser."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store: Store = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self.settings: dict = dict(logic.DEFAULT_SETTINGS)
        self.mode = "auto"
        self.boost_until: datetime | None = None
        self.decision: logic.Decision | None = None
        self.live: dict[str, Any] = {}
        self.history: dict[str, list] = {}  # "YYYY-MM-DD" -> [[minute, solar, load, geyser, soc, temp, on], ...]
        self.energy: dict[str, dict[str, float]] = {}  # day -> {solar, load, geyser, solar_to_geyser} kWh
        self._bucket: dict[str, Any] = {}
        self._last_tick: datetime | None = None
        self._unsubs: list[CALLBACK_TYPE] = []
        self._listeners: list[Callable[[], None]] = []
        self._last_command: datetime | None = None
        # spare-solar go-ahead from Hamlet Home (None = decide on our own surplus)
        self.solar_grant: bool | None = None
        self.solar_grant_why: str = ""
        self.solar_via_full = False
        self.live_pump: dict[str, Any] = {}
        # solar collector / pump
        self.pump_mode = "auto"
        self.pump_decision: logic.PumpDecision | None = None
        self._pump_on_since: datetime | None = None

    # ------------------------------------------------------------------ config
    @property
    def conf(self) -> dict:
        return {**self.entry.data, **self.entry.options}

    @property
    def collector_mode(self) -> str:
        return self.conf.get(CONF_COLLECTOR_MODE) or COLLECTOR_NONE

    @property
    def name(self) -> str:
        return self.conf.get(CONF_NAME, "Geyser")

    def _watched_entities(self) -> list[str]:
        c = self.conf
        ids: list[str] = []
        for key in (CONF_GEYSER_SWITCH, CONF_GEYSER_POWER, CONF_GEYSER_TEMP, CONF_BATTERY_SOC, CONF_BATTERY_POWER, CONF_GRID_POWER, CONF_GRID_STATUS,
                    CONF_COLLECTOR_TEMP, CONF_PUMP_ENTITY, CONF_TANK_BOTTOM_TEMP):
            ids += _as_list(c.get(key))
        ids += _as_list(c.get(CONF_SOLAR_POWER)) + _as_list(c.get(CONF_LOAD_POWER))
        return ids

    # --------------------------------------------------------------- lifecycle
    async def async_start(self) -> None:
        data = await self.store.async_load() or {}
        self.settings = {**logic.DEFAULT_SETTINGS, **data.get("settings", {})}
        self.mode = data.get("mode", "auto")
        self.pump_mode = data.get("pump_mode", "auto")
        if data.get("boost_until"):
            self.boost_until = dt_util.parse_datetime(data["boost_until"])
        self.history = data.get("history", {})
        self.energy = data.get("energy", {})
        self._prune()

        self._unsubs.append(async_track_state_change_event(self.hass, self._watched_entities(), self._on_state_change))
        self._unsubs.append(async_track_time_interval(self.hass, self._on_tick, timedelta(seconds=UPDATE_INTERVAL_S)))
        await self.async_evaluate()

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self.store.async_save(self._store_data())

    def _store_data(self) -> dict:
        return {
            "settings": self.settings,
            "mode": self.mode,
            "pump_mode": self.pump_mode,
            "boost_until": self.boost_until.isoformat() if self.boost_until else None,
            "history": self.history,
            "energy": self.energy,
        }

    def _save(self, delay: float = 2) -> None:
        self.store.async_delay_save(self._store_data, delay)

    def _prune(self) -> None:
        keep = {(dt_util.now().date() - timedelta(days=n)).isoformat() for n in range(2)}
        self.history = {k: v for k, v in self.history.items() if k in keep}
        energy_keep = {(dt_util.now().date() - timedelta(days=n)).isoformat() for n in range(31)}
        self.energy = {k: v for k, v in self.energy.items() if k in energy_keep}

    # -------------------------------------------------------------- listeners
    @callback
    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(cb)

        def remove() -> None:
            if cb in self._listeners:
                self._listeners.remove(cb)

        return remove

    def _notify(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Listener failed")

    async def _on_state_change(self, event: Event) -> None:
        await self.async_evaluate()

    async def _on_tick(self, now: datetime) -> None:
        self._sample()
        await self.async_evaluate()

    # ------------------------------------------------------------------ reading
    def _float(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in BAD_STATES:
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None
        unit = (state.attributes.get("unit_of_measurement") or "").strip()
        if unit == "kW":
            value *= 1000
        elif unit == "MW":
            value *= 1_000_000
        elif unit == "°F":
            value = (value - 32) * 5 / 9
        return value

    def _sum(self, ids: Any) -> float | None:
        values = [self._float(e) for e in _as_list(ids)]
        values = [v for v in values if v is not None]
        return sum(values) if values else None

    def _grid_available(self) -> bool | None:
        entity_id = self.conf.get(CONF_GRID_STATUS)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in BAD_STATES:
            return None
        raw = str(state.state).strip().lower()
        if self._grid_sensor_is_alarm(entity_id, state):
            # "Grid lost" alarm (e.g. Victron: 0 = ok, 1 = warning, 2 = alarm) or a problem sensor
            try:
                return float(raw) == 0
            except ValueError:
                return raw in {"off", "false", "ok", "no alarm", "none", "normal"}
        try:
            # a grid voltage or frequency sensor
            number = float(raw)
            unit = state.attributes.get("unit_of_measurement")
            if unit == "Hz":
                return number > 40
            return number > 150
        except ValueError:
            return raw in GRID_UP_WORDS

    @staticmethod
    def _grid_sensor_is_alarm(entity_id: str, state) -> bool:
        if state.attributes.get("device_class") == "problem":
            return True
        name = f"{entity_id} {state.attributes.get('friendly_name', '')}".lower()
        return any(word in name for word in ("alarm", "lost", "loss", "fail", "outage", "problem"))

    def _raw_state(self, entity_id: str | None) -> str | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        return None if state is None else f"{entity_id} = {state.state}"

    def _pump_is_on(self) -> bool | None:
        entity_id = self.conf.get(CONF_PUMP_ENTITY)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in BAD_STATES:
            return None
        raw = str(state.state).strip().lower()
        try:
            return float(raw) > 0  # pump power / speed sensor
        except ValueError:
            return raw in GRID_UP_WORDS or raw in {"running", "pumping", "active"}

    def read_inputs(self) -> logic.Inputs:
        c = self.conf
        now = dt_util.now()
        switch = self.hass.states.get(c.get(CONF_GEYSER_SWITCH, ""))
        is_on = None
        if switch is not None and switch.state not in BAD_STATES:
            is_on = switch.state == STATE_ON
        # Anti-chatter counts only our own switching; HA stamps every entity as
        # "just changed" at startup, which would otherwise delay control after a reboot.
        last_change = self._last_command

        battery_w = self._sum(c.get(CONF_BATTERY_POWER))
        if battery_w is not None and c.get(CONF_BATTERY_INVERT):
            battery_w = -battery_w
        grid_w = self._sum(c.get(CONF_GRID_POWER))
        if grid_w is not None and c.get(CONF_GRID_INVERT):
            grid_w = -grid_w
        solar_w = self._sum(c.get(CONF_SOLAR_POWER))
        load_w = self._sum(c.get(CONF_LOAD_POWER))
        if load_w is None and solar_w is not None and (grid_w is not None or battery_w is not None):
            # Energy balance: load = solar + grid import - battery charge
            load_w = max(solar_w + (grid_w or 0) - (battery_w or 0), 0)

        geyser_w = self._sum(c.get(CONF_GEYSER_POWER))
        if geyser_w is None and is_on is not None:
            # No meter on the geyser: assume rated power while the relay is on
            geyser_w = float(self.settings["geyser_rated_w"]) if is_on else 0.0

        return logic.Inputs(
            now=now,
            mode=self.mode,
            boost_until=self.boost_until,
            is_on=is_on,
            last_change=last_change,
            temp=self._float(c.get(CONF_GEYSER_TEMP)),
            solar_w=solar_w,
            load_w=load_w,
            geyser_w=geyser_w,
            battery_soc=self._float(c.get(CONF_BATTERY_SOC)),
            battery_w=battery_w,
            grid_w=grid_w,
            grid_available=self._grid_available(),
            solar_grant=self.solar_grant,
            solar_grant_why=self.solar_grant_why,
        )

    # -------------------------------------------------------------- decision
    async def _async_evaluate_pump(self, inp: logic.Inputs) -> None:
        """Run or monitor the collector pump; fills inp.collector_* for the element logic."""
        mode = self.collector_mode
        if mode == COLLECTOR_NONE:
            self.pump_decision = None
            return
        c = self.conf
        collector = self._float(c.get(CONF_COLLECTOR_TEMP))
        tank_bottom = self._float(c.get(CONF_TANK_BOTTOM_TEMP))
        tank = tank_bottom if tank_bottom is not None else inp.temp
        pump_on = self._pump_is_on()
        inp.collector_temp = collector
        self.live_pump = {"collector_temp": collector, "tank_bottom_temp": tank_bottom, "pump_on": pump_on}

        if mode == COLLECTOR_SHELLY:
            if pump_on is None:
                self.pump_decision = logic.PumpDecision(False, "Offline", "Pump relay is unavailable")
                inp.collector_heating = False
                return
            if pump_on and self._pump_on_since is None:
                self._pump_on_since = inp.now
            pd = logic.decide_pump(logic.PumpInputs(
                now=inp.now, mode=self.pump_mode, collector_temp=collector, tank_temp=tank,
                is_on=pump_on, on_since=self._pump_on_since), self.settings)
            self.pump_decision = pd
            if pd.on != pump_on:
                self._pump_on_since = inp.now if pd.on else None
                await self.hass.services.async_call(
                    "homeassistant", "turn_on" if pd.on else "turn_off", {"entity_id": c[CONF_PUMP_ENTITY]}, blocking=False)
            elif not pd.on:
                self._pump_on_since = None
            inp.collector_heating = pd.on and not pd.frost
            return

        # Geyserwise runs the pump itself: monitor only
        dt = None if collector is None or tank is None else collector - tank
        if pump_on is None:
            # no pump status mapped: estimate from the temperature difference
            pump_on = dt is not None and dt >= self.settings["pump_dt_on"]
            prefix = "Estimated: "
        else:
            prefix = ""
        if collector is None:
            self.pump_decision = logic.PumpDecision(False, "No sensor", "Collector temperature unavailable")
        elif pump_on:
            extra = f", {dt:.0f}°C hotter than tank" if dt is not None else ""
            self.pump_decision = logic.PumpDecision(True, "Pumping", f"{prefix}Geyserwise pumping, collector {collector:.0f}°C{extra}")
        else:
            self.pump_decision = logic.PumpDecision(False, "Idle", f"{prefix}Geyserwise pump off, collector {collector:.0f}°C")
        inp.collector_heating = bool(pump_on) and collector is not None and collector > (self.settings["frost_temp"] + 5)

    async def async_evaluate(self) -> None:
        inp = self.read_inputs()
        switch_id = self.conf.get(CONF_GEYSER_SWITCH)
        self.live_pump = {}
        await self._async_evaluate_pump(inp)

        if inp.is_on is None:
            self.decision = logic.Decision(
                False, None, "Offline",
                f"Can't reach the geyser switch ({switch_id}). Check the Shelly has power and Wi-Fi"
                + (" – if it's on non-essentials, this is normal while the grid is down." if inp.grid_available is False else "."))
        else:
            self.decision = logic.decide(inp, self.settings)
            if self.decision.boost_expired and self.mode == "boost":
                self.mode = "auto"
                self.boost_until = None
                self._save()
            if self.decision.on != inp.is_on:
                service = "turn_on" if self.decision.on else "turn_off"
                _LOGGER.debug("%s: %s (%s)", self.name, service, self.decision.reason)
                self._last_command = inp.now
                await self.hass.services.async_call("homeassistant", service, {"entity_id": switch_id}, blocking=False)

        self.live = {
            "temp": inp.temp,
            "solar_w": inp.solar_w,
            "load_w": inp.load_w,
            "geyser_w": inp.geyser_w,
            "battery_soc": inp.battery_soc,
            "battery_w": inp.battery_w,
            "grid_w": inp.grid_w,
            "grid_available": inp.grid_available,
            "grid_status_raw": self._raw_state(self.conf.get(CONF_GRID_STATUS)),
            "is_on": inp.is_on,
            "surplus_w": self.decision.surplus_w,
            **self.live_pump,
        }
        self._notify()

    # --------------------------------------------------------------- history
    def _sample(self) -> None:
        now = dt_util.now()
        live = self.live
        if not live:
            return
        day = now.date().isoformat()

        # energy integration
        if self._last_tick is not None:
            hours = min((now - self._last_tick).total_seconds(), 300) / 3600
            totals = self.energy.setdefault(day, {"solar": 0.0, "load": 0.0, "geyser": 0.0, "geyser_solar": 0.0, "import": 0.0})
            solar = max(live.get("solar_w") or 0, 0)
            load = max(live.get("load_w") or 0, 0)
            geyser = max(live.get("geyser_w") or 0, 0)
            totals["solar"] += solar * hours / 1000
            totals["load"] += load * hours / 1000
            totals["geyser"] += geyser * hours / 1000
            if live.get("grid_w") is not None:
                totals["import"] = totals.get("import", 0.0) + max(live["grid_w"], 0) * hours / 1000
            # geyser energy covered by solar: whatever solar is left after other loads
            other = max(load - geyser, 0)
            totals["geyser_solar"] += min(geyser, max(solar - other, 0)) * hours / 1000
        self._last_tick = now

        # 5-minute averaged chart buckets
        slot = (now.hour * 60 + now.minute) // SAMPLE_MINUTES * SAMPLE_MINUTES
        bucket = self._bucket
        if bucket and (bucket["day"] != day or bucket["slot"] != slot):
            self._flush_bucket()
            bucket = self._bucket
        if not bucket:
            bucket.update({"day": day, "slot": slot, "n": 0, "solar": 0.0, "load": 0.0, "geyser": 0.0, "soc": None, "temp": None, "on": 0,
                           "col": None, "pump": 0})
        bucket["n"] += 1
        for key, src in (("solar", "solar_w"), ("load", "load_w"), ("geyser", "geyser_w")):
            bucket[key] += max(live.get(src) or 0, 0)
        if live.get("battery_soc") is not None:
            bucket["soc"] = live["battery_soc"]
        if live.get("temp") is not None:
            bucket["temp"] = live["temp"]
        if live.get("is_on"):
            bucket["on"] = 1
        if live.get("collector_temp") is not None:
            bucket["col"] = live["collector_temp"]
        if live.get("pump_on"):
            bucket["pump"] = 1

    def _flush_bucket(self) -> None:
        b = self._bucket
        if b and b["n"]:
            n = b["n"]
            row = [b["slot"], round(b["solar"] / n), round(b["load"] / n), round(b["geyser"] / n),
                   None if b["soc"] is None else round(b["soc"], 1),
                   None if b["temp"] is None else round(b["temp"], 1), b["on"],
                   None if b.get("col") is None else round(b["col"], 1), b.get("pump", 0)]
            rows = self.history.setdefault(b["day"], [])
            if rows and rows[-1][0] == row[0]:
                rows[-1] = row
            else:
                rows.append(row)
            self._prune()
            self._save(60)
        self._bucket = {}

    # ---------------------------------------------------------------- actions
    async def async_set_mode(self, mode: str, minutes: float | None = None) -> None:
        if mode not in logic.MODES:
            raise ValueError(f"Unknown mode {mode}")
        self.mode = mode
        if mode == "boost":
            self.boost_until = dt_util.now() + timedelta(minutes=minutes or self.settings["boost_minutes"])
        else:
            self.boost_until = None
        self._last_command = None  # user action overrides anti-chatter
        self._save()
        await self._evaluate_now()

    async def async_set_pump_mode(self, mode: str) -> None:
        if mode not in logic.PUMP_MODES:
            raise ValueError(f"Unknown pump mode {mode}")
        if self.collector_mode != COLLECTOR_SHELLY:
            raise ValueError("The pump is run by the Geyserwise controller")
        self.pump_mode = mode
        self._pump_on_since = None
        self._save()
        await self.async_evaluate()

    async def _evaluate_now(self) -> None:
        # Ignore anti-chatter for direct user actions
        saved = self.settings["min_switch_seconds"]
        self.settings["min_switch_seconds"] = 0
        try:
            await self.async_evaluate()
        finally:
            self.settings["min_switch_seconds"] = saved

    async def async_update_settings(self, new: dict, admin: bool) -> None:
        cleaned = logic.validate_settings(new, admin)
        self.settings.update(cleaned)
        self._save()
        await self.async_evaluate()

    # --------------------------------------------------------------- snapshot
    def snapshot(self, include_history: bool = False) -> dict:
        d = self.decision
        now = dt_util.now()
        nxt = logic.next_schedule_start(self.settings, now)
        c = self.conf
        snap = {
            "entry_id": self.entry.entry_id,
            "name": self.name,
            "mode": self.mode,
            "pump_mode": self.pump_mode,
            "pump": None if self.pump_decision is None else {
                "on": self.pump_decision.on, "status": self.pump_decision.status,
                "reason": self.pump_decision.reason, "frost": self.pump_decision.frost,
            },
            "boost_until": self.boost_until.isoformat() if self.boost_until else None,
            "live": self.live,
            "decision": None if d is None else {
                "on": d.on, "source": d.source, "status": d.status, "reason": d.reason,
                "target": d.target, "held": d.held,
            },
            "next_schedule": nxt.isoformat() if nxt else None,
            "energy_today": self.energy.get(now.date().isoformat(), {}),
            "settings": self.settings,
            "features": {
                "temp": bool(c.get(CONF_GEYSER_TEMP)),
                "geyser_meter": bool(c.get(CONF_GEYSER_POWER)),
                "battery": bool(c.get(CONF_BATTERY_SOC)),
                "battery_power": bool(c.get(CONF_BATTERY_POWER)),
                "grid": bool(c.get(CONF_GRID_POWER)),
                "grid_status": bool(c.get(CONF_GRID_STATUS)),
                "load_meter": bool(c.get(CONF_LOAD_POWER)),
                "collector": self.collector_mode,
                "pump_status": bool(c.get(CONF_PUMP_ENTITY)),
            },
        }
        if include_history:
            today = now.date()
            snap["history"] = {
                "today": self._rows_with_bucket(today.isoformat()),
                "yesterday": self.history.get((today - timedelta(days=1)).isoformat(), []),
            }
            snap["energy_yesterday"] = self.energy.get((today - timedelta(days=1)).isoformat(), {})
        return snap

    def _rows_with_bucket(self, day: str) -> list:
        rows = list(self.history.get(day, []))
        b = self._bucket
        if b and b.get("day") == day and b["n"]:
            n = b["n"]
            rows.append([b["slot"], round(b["solar"] / n), round(b["load"] / n), round(b["geyser"] / n),
                         b["soc"], b["temp"], b["on"], b.get("col"), b.get("pump", 0)])
        return rows

    # ------------------------------------------------------- Hamlet Home link
    def solar_load(self) -> dict | None:
        """Describe this geyser as a switchable solar load for Hamlet Home's priority sharing."""
        if self.decision is None or not self.live:
            return None
        inp = self.read_inputs()
        running_on_solar = bool(inp.is_on) and self.decision.source == "solar"
        # heating for another reason (schedule, boost, on) is a fixed load, not shared solar
        fixed = bool(inp.is_on) and not running_on_solar
        rated = float(self.settings["geyser_rated_w"])
        return {
            "id": f"geyser:{self.entry.entry_id}",
            "name": self.name,
            "kind": "geyser",
            "wants": (not fixed) and logic.wants_solar(inp, self.settings),
            "running": running_on_solar,
            "power": (self.live.get("geyser_w") or rated) if running_on_solar else rated,
            "draw": (self.live.get("geyser_w") or rated) if running_on_solar else 0.0,
            "start_w": float(self.settings["surplus_on_w"]),
            "keep_w": float(self.settings["surplus_off_w"]),
            "via_full": self.solar_via_full,
        }

    async def async_set_solar_grant(self, grant: bool | None, why: str = "", via_full: bool = False) -> None:
        changed = grant != self.solar_grant
        self.solar_grant, self.solar_grant_why, self.solar_via_full = grant, why, via_full
        if changed:
            await self.async_evaluate()

"""Pure geyser decision logic (no Home Assistant imports, so it is unit-testable).

All powers are in watts. Battery power is positive while CHARGING, grid power is
positive while IMPORTING (the controller normalises inverter sign conventions
before calling into here).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

MODES = ["auto", "boost", "on", "off"]
PUMP_MODES = ["auto", "on", "off"]

DEFAULT_SETTINGS: dict = {
    # Temperatures (only used when a temperature sensor is mapped)
    "target_temp": 55,  # schedule heating target
    "solar_target_temp": 65,  # heat further when energy is free
    "boost_temp": 65,
    "max_temp": 70,  # hard safety ceiling for every mode
    "hysteresis": 4,
    # Boost
    "boost_minutes": 60,
    # Solar heating
    "solar_enabled": True,
    "geyser_rated_w": 3000,
    "surplus_on_w": 2500,  # start when spare solar exceeds this
    "surplus_off_w": 800,  # keep going while spare solar stays above this
    "soc_full_on": 95,  # battery practically full -> MPPT is throttling, use it
    "soc_full_off": 88,
    "max_battery_discharge_w": 600,  # tolerated battery draw while solar-heating
    # Protection
    "min_soc": 35,  # never heat from the battery below this (auto/boost)
    "outage_min_soc": 70,  # schedules may only run on battery above this when grid is down
    "schedules_need_grid": False,  # stricter: schedules only when grid is up
    "min_switch_seconds": 120,
    # Solar collector (thermal) + circulation pump
    "collector_priority": True,  # element waits while the collector can do the job
    "pump_dt_on": 8,  # start pump when collector is this much hotter than the tank
    "pump_dt_off": 3,  # stop when the difference drops to this
    "pump_tank_max": 75,  # stop pumping heat in above this tank temperature
    "collector_max": 130,  # stagnation protection: stop pump above this (resumes 10 °C lower)
    "frost_enabled": True,  # run pump when the collector is near freezing (direct systems)
    "frost_temp": 4,
    "pump_min_run_seconds": 60,
    # Schedules: day 0 = Monday
    "schedules": [
        {"enabled": True, "days": [0, 1, 2, 3, 4, 5, 6], "start": "04:30", "end": "06:00", "target": 55},
        {"enabled": True, "days": [0, 1, 2, 3, 4, 5, 6], "start": "16:30", "end": "18:00", "target": 55},
    ],
}

USER_KEYS = {
    "target_temp",
    "solar_target_temp",
    "boost_temp",
    "boost_minutes",
    "solar_enabled",
    "collector_priority",
    "schedules",
}


@dataclass
class Inputs:
    now: datetime
    mode: str = "auto"
    boost_until: datetime | None = None
    is_on: bool | None = None
    last_change: datetime | None = None
    temp: float | None = None
    solar_w: float | None = None
    load_w: float | None = None  # whole house, INCLUDING the geyser
    geyser_w: float | None = None
    battery_soc: float | None = None
    battery_w: float | None = None
    grid_w: float | None = None
    grid_available: bool | None = None
    collector_temp: float | None = None
    collector_heating: bool | None = None  # pump is moving solar heat into the tank right now
    solar_grant: bool | None = None  # set by Hamlet Home when spare solar is shared by priority
    solar_grant_why: str = ""


@dataclass
class Decision:
    on: bool
    source: str | None  # schedule | solar | boost | manual | None
    status: str  # short, for a badge
    reason: str  # one human sentence
    target: float | None = None
    surplus_w: float | None = None
    boost_expired: bool = False
    held: bool = False  # anti-chatter kept the previous state


def parse_hm(value: str) -> int:
    hours, minutes = value.split(":")[:2]
    return int(hours) * 60 + int(minutes)


def _window_active(sched: dict, now: datetime) -> bool:
    start, end = parse_hm(sched["start"]), parse_hm(sched["end"])
    minute = now.hour * 60 + now.minute
    days = sched.get("days", list(range(7)))
    if start == end:
        return False
    if start < end:
        return now.weekday() in days and start <= minute < end
    # wraps past midnight: started today, or started yesterday
    if minute >= start:
        return now.weekday() in days
    return minute < end and (now.weekday() - 1) % 7 in days


def active_schedule(settings: dict, now: datetime) -> dict | None:
    for sched in settings.get("schedules", []):
        if sched.get("enabled", True) and _window_active(sched, now):
            return sched
    return None


def next_schedule_start(settings: dict, now: datetime) -> datetime | None:
    best: datetime | None = None
    for sched in settings.get("schedules", []):
        if not sched.get("enabled", True) or sched["start"] == sched["end"]:
            continue
        start = parse_hm(sched["start"])
        for offset in range(8):
            day = now + timedelta(days=offset)
            if day.weekday() not in sched.get("days", list(range(7))):
                continue
            candidate = day.replace(hour=start // 60, minute=start % 60, second=0, microsecond=0)
            if candidate > now:
                if best is None or candidate < best:
                    best = candidate
                break
    return best


def solar_surplus(inp: Inputs) -> float | None:
    """Spare power available for the geyser right now.

    Solar minus the house load that is NOT the geyser, plus whatever is flowing
    into the battery (that energy could go to the geyser instead).
    """
    if inp.solar_w is None:
        return None
    geyser = inp.geyser_w if inp.geyser_w is not None else 0.0
    if inp.load_w is not None:
        other_load = max(inp.load_w - geyser, 0.0)
        return inp.solar_w - other_load
    if inp.grid_w is not None and inp.battery_w is not None:
        # surplus = export + battery charge + what the geyser already takes
        return -inp.grid_w + inp.battery_w + geyser
    return None


def _kw(watts: float) -> str:
    return f"{watts / 1000:.1f} kW"


def decide(inp: Inputs, s: dict) -> Decision:
    has_temp = inp.temp is not None
    hyst = s["hysteresis"]
    heating = bool(inp.is_on)

    def temp_ok(target: float) -> bool:
        """True if we should (keep) heating toward target, with hysteresis."""
        if not has_temp:
            return True
        if heating:
            return inp.temp < target
        return inp.temp <= target - hyst

    surplus = solar_surplus(inp)
    boost_expired = False
    mode = inp.mode

    if mode == "boost" and (inp.boost_until is None or inp.boost_until <= inp.now):
        mode = "auto"
        boost_expired = True

    # ---- hard safety, all modes -------------------------------------------
    if has_temp and inp.temp >= s["max_temp"]:
        return _finish(inp, s, Decision(False, None, "Hot", f"At {inp.temp:.0f}°C, safety limit {s['max_temp']}°C", None, surplus, boost_expired), force=True)

    if mode == "off":
        return _finish(inp, s, Decision(False, None, "Off", "Switched off by user", None, surplus), force=True)

    if mode == "on":
        return _finish(inp, s, Decision(True, "manual", "On", "Manually switched on", s["max_temp"] if has_temp else None, surplus), force=True)

    soc = inp.battery_soc
    grid_down = inp.grid_available is False
    battery_low = soc is not None and soc < s["min_soc"]

    if mode == "boost":
        target = s["boost_temp"]
        mins = max(int((inp.boost_until - inp.now).total_seconds() // 60), 0)
        if grid_down and battery_low:
            return _finish(inp, s, Decision(False, None, "Blocked", f"Boost paused: grid down and battery {soc:.0f}% is below {s['min_soc']}%", target, surplus))
        if not temp_ok(target):
            return _finish(inp, s, Decision(False, "boost", "Hot", f"Boost: already at {inp.temp:.0f}°C ({mins} min left)", target, surplus))
        return _finish(inp, s, Decision(True, "boost", "Boost", f"Boost heating, {mins} min left", target, surplus), force=True)

    # ---- auto -------------------------------------------------------------
    # 1. free solar first
    if s.get("solar_enabled", True) and inp.solar_grant is not None:
        # Hamlet Home shares spare solar between loads by priority
        if inp.solar_grant and temp_ok(s["solar_target_temp"]):
            return _finish(inp, s, Decision(True, "solar", "Solar", f"Heating on {inp.solar_grant_why or 'spare solar'}", s["solar_target_temp"], surplus))
    elif s.get("solar_enabled", True) and surplus is not None:
        want_solar = False
        why = ""
        if heating:
            if surplus >= s["surplus_off_w"]:
                want_solar, why = True, f"spare solar {_kw(surplus)}"
            elif soc is not None and soc >= s["soc_full_off"] and (inp.battery_w is None or inp.battery_w >= -s["max_battery_discharge_w"]):
                want_solar, why = True, f"battery full ({soc:.0f}%)"
        else:
            if surplus >= s["surplus_on_w"]:
                want_solar, why = True, f"spare solar {_kw(surplus)}"
            elif soc is not None and soc >= s["soc_full_on"] and (inp.solar_w or 0) > 300:
                want_solar, why = True, f"battery full ({soc:.0f}%)"
        if want_solar and temp_ok(s["solar_target_temp"]):
            return _finish(inp, s, Decision(True, "solar", "Solar", f"Heating on {why}", s["solar_target_temp"], surplus))

    # 2. schedules
    sched = active_schedule(s, inp.now)
    if sched is not None:
        target = sched.get("target", s["target_temp"])
        if grid_down:
            if s.get("schedules_need_grid"):
                return _finish(inp, s, Decision(False, None, "Blocked", "Schedule paused: grid is down", target, surplus))
            if soc is not None and soc < s["outage_min_soc"]:
                return _finish(inp, s, Decision(False, None, "Blocked", f"Schedule paused: grid down, battery {soc:.0f}% below {s['outage_min_soc']}%", target, surplus))
        if battery_low and not (inp.grid_available is True):
            return _finish(inp, s, Decision(False, None, "Blocked", f"Schedule paused: battery {soc:.0f}% below {s['min_soc']}%", target, surplus))
        if not temp_ok(target):
            return _finish(inp, s, Decision(False, "schedule", "Ready", f"Water at {inp.temp:.0f}°C, schedule target {target}°C reached", target, surplus))
        if (s.get("collector_priority", True) and inp.collector_heating
                and inp.collector_temp is not None and inp.collector_temp >= target):
            return _finish(inp, s, Decision(False, "collector", "Collector", f"Solar collector heating the tank ({inp.collector_temp:.0f}°C), element waiting", target, surplus))
        return _finish(inp, s, Decision(True, "schedule", "Schedule", f"Scheduled heating until {sched['end']}", target, surplus))

    nxt = next_schedule_start(s, inp.now)
    if nxt is None:
        when = "no schedules set"
    elif nxt.date() == inp.now.date():
        when = f"next schedule {nxt:%H:%M}"
    else:
        when = f"next schedule {nxt:%a %H:%M}"
    if has_temp:
        reason = f"Idle at {inp.temp:.0f}°C, {when}"
    else:
        reason = f"Idle, {when}"
    return _finish(inp, s, Decision(False, None, "Idle", reason, None, surplus, boost_expired))


def _finish(inp: Inputs, s: dict, d: Decision, force: bool = False) -> Decision:
    """Apply anti-chatter: don't flip the relay again within min_switch_seconds."""
    if inp.mode == "boost" and inp.boost_until is not None and inp.boost_until <= inp.now:
        d.boost_expired = True
    if force or inp.is_on is None or inp.last_change is None or d.on == inp.is_on:
        return d
    if (inp.now - inp.last_change).total_seconds() < s["min_switch_seconds"]:
        d.on = inp.is_on
        d.held = True
    return d


def validate_settings(new: dict, admin: bool) -> dict:
    """Return a cleaned settings dict, raising ValueError on bad input."""
    cleaned: dict = {}
    for key, value in new.items():
        if key not in DEFAULT_SETTINGS:
            continue
        if not admin and key not in USER_KEYS:
            raise ValueError(f"Only an administrator can change '{key}'")
        if key == "schedules":
            scheds = []
            for item in value:
                start, end = str(item["start"]), str(item["end"])
                parse_hm(start), parse_hm(end)
                days = sorted({int(d) for d in item.get("days", []) if 0 <= int(d) <= 6})
                target = float(item.get("target", DEFAULT_SETTINGS["target_temp"]))
                if not 30 <= target <= 75:
                    raise ValueError("Schedule target must be 30–75 °C")
                scheds.append({"enabled": bool(item.get("enabled", True)), "days": days, "start": start[:5], "end": end[:5], "target": target})
            cleaned[key] = scheds
        elif isinstance(DEFAULT_SETTINGS[key], bool):
            cleaned[key] = bool(value)
        else:
            cleaned[key] = float(value)
    merged_max = cleaned.get("max_temp", None)
    for key in ("target_temp", "solar_target_temp", "boost_temp"):
        if key in cleaned and not 30 <= cleaned[key] <= 75:
            raise ValueError(f"{key} must be 30–75 °C")
    if merged_max is not None and not 40 <= merged_max <= 80:
        raise ValueError("max_temp must be 40–80 °C")
    return cleaned


# ---------------------------------------------------------------------- pump
@dataclass
class PumpInputs:
    now: datetime
    mode: str = "auto"
    collector_temp: float | None = None
    tank_temp: float | None = None
    is_on: bool | None = None
    on_since: datetime | None = None  # when we last started the pump


@dataclass
class PumpDecision:
    on: bool
    status: str
    reason: str
    frost: bool = False
    held: bool = False


def decide_pump(inp: PumpInputs, s: dict) -> PumpDecision:
    """Differential controller for a solar collector circulation pump."""
    running = bool(inp.is_on)
    col, tank = inp.collector_temp, inp.tank_temp

    if inp.mode == "off":
        return PumpDecision(False, "Off", "Pump switched off by user")
    if inp.mode == "on":
        return PumpDecision(True, "On", "Pump manually on")
    if col is None:
        return PumpDecision(False, "No sensor", "Collector temperature unavailable")

    # Frost protection first: circulate warm tank water through the panel
    if s.get("frost_enabled", True) and col <= s["frost_temp"]:
        return PumpDecision(True, "Frost", f"Frost protection, collector {col:.0f}°C", frost=True)

    # Stagnation / overheat: stop at the limit, and don't restart until 10 °C below it
    if col >= s["collector_max"] or (not running and col >= s["collector_max"] - 10):
        return PumpDecision(False, "Overheat", f"Collector {col:.0f}°C above {s['collector_max']:.0f}°C, pump stopped to protect the system")

    if tank is None:
        return PumpDecision(False, "No sensor", "Tank temperature unavailable")
    if tank >= s["pump_tank_max"]:
        return PumpDecision(False, "Tank full", f"Tank at {tank:.0f}°C, limit {s['pump_tank_max']:.0f}°C")

    dt = col - tank
    want = dt > s["pump_dt_off"] if running else dt >= s["pump_dt_on"]
    if want:
        d = PumpDecision(True, "Pumping", f"Collector {col:.0f}°C is {dt:.0f}°C hotter than tank")
    else:
        d = PumpDecision(False, "Idle", f"Collector {col:.0f}°C, tank {tank:.0f}°C (needs +{s['pump_dt_on']:.0f}°C)")

    # minimum run time once started
    if running and not d.on and inp.on_since is not None:
        if (inp.now - inp.on_since).total_seconds() < s["pump_min_run_seconds"]:
            d.on, d.held = True, True
    return d



def wants_solar(inp: Inputs, s: dict) -> bool:
    """Would the geyser heat on spare solar right now if it were given the go-ahead?"""
    if inp.mode != "auto" or not s.get("solar_enabled", True) or inp.is_on is None:
        return False
    if inp.temp is None:
        return True
    if inp.temp >= s["max_temp"]:
        return False
    target = s["solar_target_temp"]
    return inp.temp < target if inp.is_on else inp.temp <= target - s["hysteresis"]

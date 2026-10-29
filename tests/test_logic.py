"""Decision logic tests: run with `pytest tests/test_logic.py`."""
import importlib.util
import pathlib
from datetime import datetime, timedelta

spec = importlib.util.spec_from_file_location(
    "logic", pathlib.Path(__file__).parents[1] / "custom_components/hamlet_geyser/logic.py")
logic = importlib.util.module_from_spec(spec)
import sys
sys.modules["logic"] = logic
spec.loader.exec_module(logic)

S = dict(logic.DEFAULT_SETTINGS)
WED_NOON = datetime(2026, 10, 28, 12, 0)
WED_5AM = datetime(2026, 10, 28, 5, 0)
LONG_AGO = WED_NOON - timedelta(hours=1)


def inp(**kw):
    base = dict(now=WED_NOON, mode="auto", is_on=False, last_change=LONG_AGO)
    base.update(kw)
    return logic.Inputs(**base)


def test_solar_surplus_starts_heating():
    d = logic.decide(inp(solar_w=5000, load_w=1200, geyser_w=0, temp=50), S)
    assert d.on and d.source == "solar"
    assert round(d.surplus_w) == 3800


def test_surplus_excludes_geyser_own_load():
    # geyser already on drawing 3kW; other load 800 -> surplus 1700 still above off threshold
    d = logic.decide(inp(is_on=True, solar_w=2500, load_w=3800, geyser_w=3000, temp=50), S)
    assert d.on and d.source == "solar"


def test_small_surplus_does_not_start():
    d = logic.decide(inp(solar_w=2000, load_w=600, geyser_w=0, temp=50), S)
    assert not d.on


def test_battery_full_throttled_mppt():
    # Victron throttles PV when battery is full, so surplus looks small
    d = logic.decide(inp(solar_w=900, load_w=700, geyser_w=0, battery_soc=98, battery_w=0, temp=50), S)
    assert d.on and "battery full" in d.reason


def test_battery_full_stops_when_draining():
    d = logic.decide(inp(is_on=True, solar_w=1500, load_w=4500, geyser_w=3000, battery_soc=92, battery_w=-2000, temp=50), S)
    assert not d.on


def test_solar_respects_solar_target():
    d = logic.decide(inp(solar_w=6000, load_w=500, temp=66), S)
    assert not d.on


def test_schedule_heats():
    d = logic.decide(inp(now=WED_5AM, last_change=WED_5AM - timedelta(hours=1), solar_w=0, load_w=500, temp=45, grid_available=True), S)
    assert d.on and d.source == "schedule"


def test_schedule_target_reached_with_hysteresis():
    s = dict(S)
    now = WED_5AM
    # off at 52 °C, target 55, hysteresis 4 -> must not start (52 > 51)
    assert not logic.decide(inp(now=now, last_change=now - timedelta(hours=1), temp=52, grid_available=True), s).on
    # on at 54 -> keep heating until 55
    assert logic.decide(inp(now=now, is_on=True, last_change=now - timedelta(hours=1), temp=54, grid_available=True), s).on
    assert not logic.decide(inp(now=now, is_on=True, last_change=now - timedelta(hours=1), temp=55, grid_available=True), s).on


def test_loadshedding_blocks_schedule_on_lowish_battery():
    d = logic.decide(inp(now=WED_5AM, last_change=WED_5AM - timedelta(hours=1), temp=40, grid_available=False, battery_soc=60), S)
    assert not d.on and d.status == "Blocked"
    d = logic.decide(inp(now=WED_5AM, last_change=WED_5AM - timedelta(hours=1), temp=40, grid_available=False, battery_soc=85), S)
    assert d.on


def test_schedules_need_grid_option():
    s = {**S, "schedules_need_grid": True}
    d = logic.decide(inp(now=WED_5AM, last_change=WED_5AM - timedelta(hours=1), temp=40, grid_available=False, battery_soc=100), s)
    assert not d.on


def test_low_battery_blocks_but_grid_up_allows():
    args = dict(now=WED_5AM, last_change=WED_5AM - timedelta(hours=1), temp=40, battery_soc=20)
    assert not logic.decide(inp(**args), S).on  # grid unknown
    assert logic.decide(inp(grid_available=True, **args), S).on


def test_boost_and_expiry():
    d = logic.decide(inp(mode="boost", boost_until=WED_NOON + timedelta(minutes=30), temp=50), S)
    assert d.on and d.source == "boost" and "30 min" in d.reason
    d = logic.decide(inp(mode="boost", boost_until=WED_NOON - timedelta(minutes=1), temp=50, solar_w=0, load_w=500), S)
    assert d.boost_expired and not d.on


def test_max_temp_safety_beats_manual_on():
    d = logic.decide(inp(mode="on", is_on=True, temp=71), S)
    assert not d.on and d.status == "Hot"


def test_off_mode():
    assert not logic.decide(inp(mode="off", is_on=True, solar_w=9000, load_w=0), S).on


def test_anti_chatter_holds_state():
    d = logic.decide(inp(is_on=True, last_change=WED_NOON - timedelta(seconds=30), solar_w=0, load_w=500, temp=50), S)
    assert d.on and d.held


def test_no_temp_sensor_still_works():
    d = logic.decide(inp(now=WED_5AM, last_change=WED_5AM - timedelta(hours=1), grid_available=True), S)
    assert d.on and d.source == "schedule"


def test_midnight_wrap_schedule():
    s = {**S, "schedules": [{"enabled": True, "days": [1], "start": "23:00", "end": "01:00", "target": 55}]}
    tue_late = datetime(2026, 10, 27, 23, 30)  # Tuesday
    wed_early = datetime(2026, 10, 28, 0, 30)
    assert logic.active_schedule(s, tue_late)
    assert logic.active_schedule(s, wed_early)
    assert not logic.active_schedule(s, datetime(2026, 10, 29, 0, 30))


def test_surplus_from_grid_and_battery_when_no_load_sensor():
    i = inp(solar_w=4000, grid_w=-1500, battery_w=1200, geyser_w=0)
    assert logic.solar_surplus(i) == 2700


def test_next_schedule_and_idle_reason():
    d = logic.decide(inp(solar_w=0, load_w=500, temp=50), S)
    assert "next schedule 16:30" in d.reason


def test_validate_settings_permissions():
    try:
        logic.validate_settings({"min_soc": 10}, admin=False)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    cleaned = logic.validate_settings({"schedules": [{"start": "05:00", "end": "06:00", "days": [0, 9], "target": 50}]}, admin=False)
    assert cleaned["schedules"][0]["days"] == [0]


# ------------------------------------------------------------- collector pump
def pump(**kw):
    base = dict(now=WED_NOON, mode="auto", is_on=False)
    base.update(kw)
    return logic.decide_pump(logic.PumpInputs(**base), S)


def test_pump_differential_on_off():
    assert pump(collector_temp=60, tank_temp=50).on            # dt 10 >= 8
    assert not pump(collector_temp=55, tank_temp=50).on        # dt 5 < 8, not running
    assert pump(collector_temp=55, tank_temp=50, is_on=True, on_since=LONG_AGO).on      # keeps running > 3
    assert not pump(collector_temp=52, tank_temp=50, is_on=True, on_since=LONG_AGO).on  # dt 2 <= 3


def test_pump_min_run_time():
    d = pump(collector_temp=51, tank_temp=50, is_on=True, on_since=WED_NOON - timedelta(seconds=20))
    assert d.on and d.held


def test_pump_tank_max_and_overheat():
    assert not pump(collector_temp=95, tank_temp=76).on
    d = pump(collector_temp=135, tank_temp=60, is_on=True, on_since=LONG_AGO)
    assert not d.on and d.status == "Overheat"
    assert not pump(collector_temp=125, tank_temp=60).on       # still in the 10 °C cool-down band
    assert pump(collector_temp=125, tank_temp=60, is_on=True, on_since=LONG_AGO).on
    assert pump(collector_temp=115, tank_temp=60).on


def test_pump_frost_protection():
    d = pump(collector_temp=2, tank_temp=45)
    assert d.on and d.frost
    assert not logic.decide_pump(logic.PumpInputs(now=WED_NOON, collector_temp=2, tank_temp=45), {**S, "frost_enabled": False}).on


def test_pump_manual_modes():
    assert pump(mode="on", collector_temp=10, tank_temp=60).on
    assert not pump(mode="off", collector_temp=90, tank_temp=40).on


def test_element_waits_for_hot_collector():
    args = dict(now=WED_5AM, last_change=WED_5AM - timedelta(hours=1), temp=40, grid_available=True)
    d = logic.decide(inp(collector_heating=True, collector_temp=70, **args), S)
    assert not d.on and d.source == "collector"
    # collector too cool to reach 55 °C target: element helps
    assert logic.decide(inp(collector_heating=True, collector_temp=45, **args), S).on
    # option off: element runs regardless
    assert logic.decide(inp(collector_heating=True, collector_temp=70, **args), {**S, "collector_priority": False}).on


def test_solar_grant_from_hamlet_home():
    # grant overrides own surplus maths both ways
    d = logic.decide(inp(solar_w=0, load_w=500, temp=50, solar_grant=True, solar_grant_why="spare solar (priority 1)"), S)
    assert d.on and d.source == "solar" and "priority 1" in d.reason
    d = logic.decide(inp(solar_w=9000, load_w=500, temp=50, solar_grant=False), S)
    assert not d.on
    # still respects solar target temperature
    assert not logic.decide(inp(temp=66, solar_grant=True), S).on


def test_wants_solar():
    assert logic.wants_solar(inp(temp=50), S)
    assert not logic.wants_solar(inp(temp=63), S)              # off and within hysteresis of 65
    assert logic.wants_solar(inp(temp=63, is_on=True), S)      # on: keep going to 65
    assert not logic.wants_solar(inp(temp=50, mode="off"), S)

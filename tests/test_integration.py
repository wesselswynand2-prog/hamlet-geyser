"""End-to-end test inside a real Home Assistant instance (pytest-homeassistant-custom-component)."""
import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

DOMAIN = "hamlet_geyser"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def _setup(hass: HomeAssistant, collector: dict | None = None):
    for mod in ("http", "frontend"):
        assert await async_setup_component(hass, mod, {})
    hass.states.async_set("switch.geyser", "off")
    hass.states.async_set("sensor.geyser_power", "0", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.geyser_temp", "50", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.pv1", "3.0", {"unit_of_measurement": "kW"})
    hass.states.async_set("sensor.pv2", "2000", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.load", "900", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.soc", "80", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.batt", "-500", {"unit_of_measurement": "W"})  # sunsynk: + discharge
    hass.states.async_set("binary_sensor.grid", "on")

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {
        "name": "Main geyser", "geyser_switch": "switch.geyser",
        "geyser_power": "sensor.geyser_power", "geyser_temp": "sensor.geyser_temp"})
    assert result["step_id"] == "energy"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {
        "preset": "sunsynk", "solar_power": ["sensor.pv1", "sensor.pv2"], "load_power": ["sensor.load"],
        "battery_soc": "sensor.soc", "battery_power": "sensor.batt", "grid_status": "binary_sensor.grid"})
    assert result["step_id"] == "collector"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], collector or {"collector_mode": "none"})
    assert result["step_id"] == "signs", result.get("errors")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"battery_invert": True, "grid_invert": False})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    return result["result"]


async def test_full_flow(hass: HomeAssistant, hass_ws_client):
    calls_on = async_mock_service(hass, "homeassistant", "turn_on")
    calls_off = async_mock_service(hass, "homeassistant", "turn_off")
    entry = await _setup(hass)

    # 5 kW solar (kW unit converted) - 900 W load = 4.1 kW spare -> solar heating
    assert calls_on and calls_on[-1].data["entity_id"] == "switch.geyser"
    status = hass.states.get("sensor.main_geyser_status")
    assert status.state == "Solar", status
    assert float(hass.states.get("sensor.main_geyser_spare_solar").state) == 4100
    assert hass.states.get("select.main_geyser_mode").state == "auto"

    # panel registered, dashboard card loaded automatically
    assert "hamlet-geyser" in hass.data["frontend_panels"]
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
    assert any("hamlet-geyser-card.js" in u for u in hass.data[DATA_EXTRA_MODULE_URL].urls)

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": f"{DOMAIN}/list"})
    msg = await client.receive_json()
    assert msg["success"] and msg["result"][0]["name"] == "Main geyser"

    await client.send_json({"id": 2, "type": f"{DOMAIN}/state", "entry_id": entry.entry_id})
    msg = await client.receive_json()
    snap = msg["result"]
    assert snap["live"]["battery_w"] == 500  # inverted: -500 discharging raw -> +500? raw -500 means charging on sunsynk
    assert snap["live"]["solar_w"] == 5000
    assert snap["features"]["temp"] is True

    # Off mode via websocket switches off
    hass.states.async_set("switch.geyser", "on")
    await hass.async_block_till_done()
    await client.send_json({"id": 3, "type": f"{DOMAIN}/set_mode", "entry_id": entry.entry_id, "mode": "off"})
    msg = await client.receive_json()
    assert msg["success"] and msg["result"]["mode"] == "off"
    await hass.async_block_till_done()
    assert calls_off and calls_off[-1].data["entity_id"] == "switch.geyser"

    # Settings: schedules saved, admin-only key accepted for admin user
    await client.send_json({"id": 4, "type": f"{DOMAIN}/save_settings", "entry_id": entry.entry_id,
                            "settings": {"min_soc": 40, "schedules": [{"enabled": True, "days": [0, 1], "start": "05:00", "end": "06:00", "target": 58}]}})
    msg = await client.receive_json()
    assert msg["success"], msg
    assert msg["result"]["settings"]["min_soc"] == 40
    assert msg["result"]["settings"]["schedules"][0]["target"] == 58

    # Bad input rejected
    await client.send_json({"id": 5, "type": f"{DOMAIN}/save_settings", "entry_id": entry.entry_id,
                            "settings": {"schedules": [{"start": "nope", "end": "06:00"}]}})
    msg = await client.receive_json()
    assert not msg["success"]

    # Subscribe pushes snapshots
    await client.send_json({"id": 6, "type": f"{DOMAIN}/subscribe", "entry_id": entry.entry_id})
    msg = await client.receive_json()
    assert msg["success"]
    msg = await client.receive_json()
    assert msg["type"] == "event" and msg["event"]["mode"] == "off"

    # Boost button
    await hass.services.async_call("button", "press", {"entity_id": "button.main_geyser_boost"}, blocking=True)
    assert hass.states.get("select.main_geyser_mode").state == "boost"

    # Unload removes panel
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert "hamlet-geyser" not in hass.data["frontend_panels"]
    assert not any("hamlet-geyser-card.js" in u for u in hass.data[DATA_EXTRA_MODULE_URL].urls)


async def test_options_flow_can_clear_optional(hass: HomeAssistant):
    async_mock_service(hass, "homeassistant", "turn_on")
    async_mock_service(hass, "homeassistant", "turn_off")
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"name": "Main geyser", "geyser_switch": "switch.geyser"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"preset": "victron", "solar_power": ["sensor.pv1"]})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"collector_mode": "none"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"battery_invert": False, "grid_invert": False})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    controller = hass.data[DOMAIN][entry.entry_id]
    assert controller.conf["geyser_temp"] is None
    assert controller.conf["battery_soc"] is None
    assert controller.snapshot()["features"]["temp"] is False


async def test_energy_and_history(hass: HomeAssistant):
    from datetime import timedelta
    async_mock_service(hass, "homeassistant", "turn_on")
    async_mock_service(hass, "homeassistant", "turn_off")
    entry = await _setup(hass)
    c = hass.data[DOMAIN][entry.entry_id]
    c._sample()
    c._last_tick -= timedelta(seconds=360)  # capped at 300 s
    c._sample()
    today = c.snapshot(include_history=True)
    e = today["energy_today"]
    assert abs(e["solar"] - 5000 * 300 / 3600 / 1000) < 0.001
    assert abs(e["load"] - 900 * 300 / 3600 / 1000) < 0.001
    assert len(today["history"]["today"]) == 1  # open bucket included
    assert today["history"]["today"][0][1] == 5000
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.main_geyser_solar_today").state) >= 0
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_collector_shelly_pump(hass: HomeAssistant, hass_ws_client):
    on = async_mock_service(hass, "homeassistant", "turn_on")
    off = async_mock_service(hass, "homeassistant", "turn_off")
    hass.states.async_set("sensor.collector", "72", {"unit_of_measurement": "°C"})
    hass.states.async_set("switch.pump", "off")

    # validation: shelly mode needs a switch
    for mod in ("http", "frontend"):
        assert await async_setup_component(hass, mod, {})
    entry = await _setup(hass, {"collector_mode": "shelly", "collector_temp": "sensor.collector", "pump_entity": "switch.pump"})
    c = hass.data[DOMAIN][entry.entry_id]
    # collector 72 vs tank 50 -> pump on
    assert any(call.data["entity_id"] == "switch.pump" for call in on)
    assert c.pump_decision.on and c.pump_decision.status == "Pumping"
    assert hass.states.get("sensor.main_geyser_collector").state == "72.0"
    assert hass.states.get("select.main_geyser_pump_mode").state == "auto"

    # tank reaches limit -> pump off
    hass.states.async_set("switch.pump", "on")
    hass.states.async_set("sensor.geyser_temp", "76", {"unit_of_measurement": "°C"})
    c._pump_on_since = None
    await hass.async_block_till_done()
    assert any(call.data["entity_id"] == "switch.pump" for call in off)

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": f"{DOMAIN}/set_pump_mode", "entry_id": entry.entry_id, "mode": "off"})
    msg = await client.receive_json()
    assert msg["success"] and msg["result"]["pump_mode"] == "off"
    assert msg["result"]["features"]["collector"] == "shelly"
    assert msg["result"]["live"]["collector_temp"] == 72


async def test_collector_shelly_requires_switch(hass: HomeAssistant):
    for mod in ("http", "frontend"):
        assert await async_setup_component(hass, mod, {})
    hass.states.async_set("sensor.collector", "72")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "G", "geyser_switch": "switch.geyser"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"preset": "victron", "solar_power": ["sensor.pv1"]})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"collector_mode": "shelly", "collector_temp": "sensor.collector"})
    assert result["step_id"] == "collector" and result["errors"] == {"pump_entity": "pump_required"}


async def test_collector_geyserwise_monitor(hass: HomeAssistant, hass_ws_client):
    on = async_mock_service(hass, "homeassistant", "turn_on")
    async_mock_service(hass, "homeassistant", "turn_off")
    hass.states.async_set("sensor.collector", "80", {"unit_of_measurement": "°C"})
    hass.states.async_set("binary_sensor.gw_pump", "on")
    entry = await _setup(hass, {"collector_mode": "geyserwise", "collector_temp": "sensor.collector", "pump_entity": "binary_sensor.gw_pump"})
    # no spare solar so the element would only run on schedule
    hass.states.async_set("sensor.pv1", "0", {"unit_of_measurement": "kW"})
    hass.states.async_set("sensor.pv2", "0", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    c = hass.data[DOMAIN][entry.entry_id]
    assert c.pump_decision.on and "Geyserwise" in c.pump_decision.reason
    # never commands the Geyserwise pump
    assert not any(call.data["entity_id"] == "binary_sensor.gw_pump" for call in on)
    # during a schedule the element waits for the hot collector
    inp = c.read_inputs()
    inp.now = inp.now.replace(hour=5, minute=0)
    inp.is_on = False
    await c._async_evaluate_pump(inp)
    d = __import__("custom_components.hamlet_geyser.logic", fromlist=["decide"]).decide(inp, c.settings)
    assert not d.on and d.source == "collector"
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": f"{DOMAIN}/set_pump_mode", "entry_id": entry.entry_id, "mode": "on"})
    msg = await client.receive_json()
    assert not msg["success"]  # pump belongs to Geyserwise


async def test_grid_alarm_sensor_and_offline(hass: HomeAssistant):
    async_mock_service(hass, "homeassistant", "turn_on")
    async_mock_service(hass, "homeassistant", "turn_off")
    entry = await _setup(hass)
    c = hass.data[DOMAIN][entry.entry_id]
    # point grid status at a Victron-style "grid lost alarm"
    hass.config_entries.async_update_entry(entry, options={**entry.options, "grid_status": "sensor.victron_grid_lost_alarm"})
    await hass.async_block_till_done()
    c = hass.data[DOMAIN][entry.entry_id]
    hass.states.async_set("sensor.victron_grid_lost_alarm", "0")
    assert c._grid_available() is True
    hass.states.async_set("sensor.victron_grid_lost_alarm", "2")
    assert c._grid_available() is False
    hass.states.async_set("sensor.victron_grid_lost_alarm", "Ok")
    assert c._grid_available() is True
    # voltage sensor still works
    hass.states.async_set("sensor.ac_in_voltage", "231", {"unit_of_measurement": "V"})
    hass.config_entries.async_update_entry(entry, options={**entry.options, "grid_status": "sensor.ac_in_voltage"})
    await hass.async_block_till_done()
    c = hass.data[DOMAIN][entry.entry_id]
    assert c._grid_available() is True
    # unavailable relay -> helpful message
    hass.states.async_set("switch.geyser", "unavailable")
    await hass.async_block_till_done()
    assert c.decision.status == "Offline" and "switch.geyser" in c.decision.reason
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_card_file_is_served(hass: HomeAssistant, hass_client):
    async_mock_service(hass, "homeassistant", "turn_on")
    async_mock_service(hass, "homeassistant", "turn_off")
    entry = await _setup(hass)
    client = await hass_client()
    for name in ("hamlet-geyser-card.js", "hamlet-geyser-panel.js"):
        resp = await client.get(f"/hamlet_geyser_static/{name}")
        assert resp.status == 200, name
        body = await resp.text()
        assert "customElements.define" in body
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

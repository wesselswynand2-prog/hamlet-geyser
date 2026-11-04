"""Status, solar surplus and daily energy sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.util import dt as dt_util

from .const import COLLECTOR_NONE, DOMAIN
from .entity import GeyserEntity


async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]
    extra = [CollectorSensor(c)] if c.collector_mode != COLLECTOR_NONE else []
    async_add_entities(extra + [
        GeyserStatusSensor(c),
        GeyserSurplusSensor(c),
        GeyserPowerSensor(c),
        GeyserEnergySensor(c, "solar"),
        GeyserEnergySensor(c, "load"),
        GeyserEnergySensor(c, "geyser"),
        GeyserEnergySensor(c, "geyser_solar"),
    ])


class GeyserStatusSensor(GeyserEntity, SensorEntity):
    _attr_icon = "mdi:water-boiler"

    def __init__(self, controller):
        super().__init__(controller, "status")

    @property
    def native_value(self):
        d = self.controller.decision
        return d.status if d else None

    @property
    def extra_state_attributes(self):
        d = self.controller.decision
        if d is None:
            return {}
        return {"reason": d.reason, "heating": d.on, "source": d.source, "target_temp": d.target}


class GeyserSurplusSensor(GeyserEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:solar-power-variant"

    def __init__(self, controller):
        super().__init__(controller, "surplus")

    @property
    def native_value(self):
        value = self.controller.live.get("surplus_w")
        return None if value is None else round(value)


class GeyserPowerSensor(GeyserEntity, SensorEntity):
    """What the geyser draws: the meter when there is one, else the element rating while it's switched on
    (Geyserwise / relay without power metering). Lets Hamlet Home and the Energy dashboard count it."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:water-boiler"

    def __init__(self, controller):
        super().__init__(controller, "geyser_power")

    @property
    def native_value(self):
        value = self.controller.live.get("geyser_w")
        return None if value is None else round(max(value, 0))

    @property
    def extra_state_attributes(self):
        from .const import CONF_GEYSER_POWER  # noqa: PLC0415
        c = {**self.controller.entry.data, **self.controller.entry.options}
        metered = bool(c.get(CONF_GEYSER_POWER))
        heating = None if metered else self.controller.element_heating()
        return {"estimated": not metered,
                "estimated_from": None if metered else ("element status" if heating is not None else "switch"),
                "rated_w": None if metered else self.controller.settings.get("geyser_rated_w")}


class GeyserEnergySensor(GeyserEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    def __init__(self, controller, kind: str):
        super().__init__(controller, f"energy_{kind}")
        self.kind = kind

    @property
    def native_value(self):
        today = self.controller.energy.get(dt_util.now().date().isoformat(), {})
        return round(today.get(self.kind, 0.0), 3)


class CollectorSensor(GeyserEntity, SensorEntity):
    """Collector temperature, with pump state and reason as attributes."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "°C"
    _attr_icon = "mdi:solar-panel"

    def __init__(self, controller):
        super().__init__(controller, "collector_status")

    @property
    def native_value(self):
        value = self.controller.live.get("collector_temp")
        return None if value is None else round(value, 1)

    @property
    def extra_state_attributes(self):
        p = self.controller.pump_decision
        attrs = {"control": self.controller.collector_mode, "pump_mode": self.controller.pump_mode}
        if p is not None:
            attrs.update({"pump_on": p.on, "pump_status": p.status, "reason": p.reason})
        return attrs

"""Mode select: auto / boost / on / off."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .const import DOMAIN
from .entity import GeyserEntity
from .const import COLLECTOR_SHELLY
from .logic import MODES, PUMP_MODES


async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]
    entities = [GeyserModeSelect(c)]
    if c.collector_mode == COLLECTOR_SHELLY:
        entities.append(PumpModeSelect(c))
    async_add_entities(entities)


class GeyserModeSelect(GeyserEntity, SelectEntity):
    _attr_options = MODES
    _attr_icon = "mdi:water-boiler-auto"

    def __init__(self, controller):
        super().__init__(controller, "mode")

    @property
    def current_option(self):
        return self.controller.mode

    @property
    def extra_state_attributes(self):
        return {"boost_until": self.controller.boost_until.isoformat() if self.controller.boost_until else None}

    async def async_select_option(self, option: str) -> None:
        await self.controller.async_set_mode(option)


class PumpModeSelect(GeyserEntity, SelectEntity):
    _attr_options = PUMP_MODES
    _attr_icon = "mdi:pump"

    def __init__(self, controller):
        super().__init__(controller, "pump_mode")

    @property
    def current_option(self):
        return self.controller.pump_mode

    async def async_select_option(self, option: str) -> None:
        await self.controller.async_set_pump_mode(option)

"""Boost button."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import GeyserEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([GeyserBoostButton(hass.data[DOMAIN][entry.entry_id])])


class GeyserBoostButton(GeyserEntity, ButtonEntity):
    _attr_icon = "mdi:fire"

    def __init__(self, controller):
        super().__init__(controller, "boost")

    async def async_press(self) -> None:
        await self.controller.async_set_mode("boost")

"""Config flow: the installer maps the client's own entities."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BATTERY_INVERT,
    CONF_BATTERY_POWER,
    CONF_BATTERY_SOC,
    CONF_COLLECTOR_MODE,
    CONF_COLLECTOR_TEMP,
    COLLECTOR_MODES,
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
    CONF_PRESET,
    CONF_SOLAR_POWER,
    DOMAIN,
    PRESET_INVERT,
    PRESETS,
)

ENTITY_KEYS = [
    CONF_GEYSER_SWITCH, CONF_GEYSER_POWER, CONF_GEYSER_TEMP, CONF_SOLAR_POWER, CONF_LOAD_POWER,
    CONF_BATTERY_SOC, CONF_BATTERY_POWER, CONF_GRID_POWER, CONF_GRID_STATUS,
]


def _sensor(device_class: str | None = None, multiple: bool = False) -> selector.EntitySelector:
    # device_class is deliberately not enforced: template / Modbus sensors often lack one
    cfg: dict[str, Any] = {"domain": ["sensor", "input_number"], "multiple": multiple}
    return selector.EntitySelector(selector.EntitySelectorConfig(**cfg))


def _geyser_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_NAME, default="Geyser"): str,
        vol.Required(CONF_GEYSER_SWITCH): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["switch", "input_boolean", "light"])
        ),
        vol.Optional(CONF_GEYSER_POWER): _sensor("power"),
        vol.Optional(CONF_GEYSER_TEMP): _sensor("temperature"),
    })


def _energy_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_PRESET, default="victron"): selector.SelectSelector(
            selector.SelectSelectorConfig(options=PRESETS, translation_key="preset", mode=selector.SelectSelectorMode.DROPDOWN)
        ),
        vol.Required(CONF_SOLAR_POWER): _sensor("power", multiple=True),
        vol.Optional(CONF_LOAD_POWER): _sensor("power", multiple=True),
        vol.Optional(CONF_BATTERY_SOC): _sensor("battery"),
        vol.Optional(CONF_BATTERY_POWER): _sensor("power"),
        vol.Optional(CONF_GRID_POWER): _sensor("power", multiple=True),
        vol.Optional(CONF_GRID_STATUS): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "sensor", "switch", "input_boolean"])
        ),
    })


def _collector_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_COLLECTOR_MODE, default=COLLECTOR_NONE): selector.SelectSelector(
            selector.SelectSelectorConfig(options=COLLECTOR_MODES, translation_key="collector_mode", mode=selector.SelectSelectorMode.LIST)
        ),
        vol.Optional(CONF_COLLECTOR_TEMP): _sensor(),
        vol.Optional(CONF_PUMP_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["switch", "input_boolean", "binary_sensor", "sensor"])
        ),
        vol.Optional(CONF_TANK_BOTTOM_TEMP): _sensor(),
    })


def _collector_errors(hass, data: dict) -> dict:
    mode = data.get(CONF_COLLECTOR_MODE, COLLECTOR_NONE)
    errors: dict = {}
    if mode == COLLECTOR_NONE:
        return errors
    if not data.get(CONF_COLLECTOR_TEMP):
        errors[CONF_COLLECTOR_TEMP] = "collector_temp_required"
    if mode == COLLECTOR_SHELLY:
        pump = data.get(CONF_PUMP_ENTITY) or ""
        if not pump:
            errors[CONF_PUMP_ENTITY] = "pump_required"
        elif pump.split(".")[0] not in ("switch", "input_boolean"):
            errors[CONF_PUMP_ENTITY] = "pump_must_be_switch"
    return errors


def _signs_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_BATTERY_INVERT, default=False): selector.BooleanSelector(),
        vol.Required(CONF_GRID_INVERT, default=False): selector.BooleanSelector(),
    })


class HamletGeyserConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_GEYSER_SWITCH])
            self._abort_if_unique_id_configured()
            self._data.update(user_input)
            return await self.async_step_energy()
        return self.async_show_form(step_id="user", data_schema=_geyser_schema())

    async def async_step_energy(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_collector()
        return self.async_show_form(step_id="energy", data_schema=_energy_schema())

    async def async_step_collector(self, user_input: dict | None = None) -> ConfigFlowResult:
        errors: dict = {}
        if user_input is not None:
            errors = _collector_errors(self.hass, user_input)
            if not errors:
                self._data.update(user_input)
                return await self.async_step_signs()
        schema = _collector_schema()
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="collector", data_schema=schema, errors=errors)

    async def async_step_signs(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)
        defaults = PRESET_INVERT.get(self._data.get(CONF_PRESET), {})
        schema = self.add_suggested_values_to_schema(_signs_schema(), defaults)
        return self.async_show_form(step_id="signs", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HamletGeyserOptionsFlow()


class HamletGeyserOptionsFlow(OptionsFlow):
    """Re-map entities later (e.g. after replacing a relay)."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    @property
    def _current(self) -> dict:
        return {**self.config_entry.data, **self.config_entry.options}

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update({k: None for k in (CONF_GEYSER_POWER, CONF_GEYSER_TEMP)})
            self._data.update(user_input)
            return await self.async_step_energy()
        schema = self.add_suggested_values_to_schema(_geyser_schema(), self._current)
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_energy(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update({k: None for k in (CONF_LOAD_POWER, CONF_BATTERY_SOC, CONF_BATTERY_POWER, CONF_GRID_POWER, CONF_GRID_STATUS)})
            self._data.update(user_input)
            return await self.async_step_collector()
        schema = self.add_suggested_values_to_schema(_energy_schema(), self._current)
        return self.async_show_form(step_id="energy", data_schema=schema)

    async def async_step_collector(self, user_input: dict | None = None) -> ConfigFlowResult:
        errors: dict = {}
        if user_input is not None:
            errors = _collector_errors(self.hass, user_input)
            if not errors:
                self._data.update({k: None for k in (CONF_COLLECTOR_TEMP, CONF_PUMP_ENTITY, CONF_TANK_BOTTOM_TEMP)})
                self._data.update(user_input)
                return await self.async_step_signs()
        schema = self.add_suggested_values_to_schema(_collector_schema(), user_input or self._current)
        return self.async_show_form(step_id="collector", data_schema=schema, errors=errors)

    async def async_step_signs(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)
        schema = self.add_suggested_values_to_schema(_signs_schema(), self._current)
        return self.async_show_form(step_id="signs", data_schema=schema)

"""Constants for Hamlet Geyser."""
DOMAIN = "hamlet_geyser"
VERSION = "1.3.0"

PANEL_URL_PATH = "hamlet-geyser"
PANEL_COMPONENT = "hamlet-geyser-panel"
STATIC_URL = "/hamlet_geyser_static"

CONF_NAME = "name"
CONF_PRESET = "preset"
CONF_GEYSER_SWITCH = "geyser_switch"
CONF_GEYSER_POWER = "geyser_power"
CONF_GEYSER_TEMP = "geyser_temp"
CONF_SOLAR_POWER = "solar_power"
CONF_LOAD_POWER = "load_power"
CONF_BATTERY_SOC = "battery_soc"
CONF_BATTERY_POWER = "battery_power"
CONF_GRID_POWER = "grid_power"
CONF_GRID_STATUS = "grid_status"
CONF_BATTERY_INVERT = "battery_invert"
CONF_GRID_INVERT = "grid_invert"

PRESET_VICTRON = "victron"
PRESET_SUNSYNK = "sunsynk"
PRESET_OTHER = "other"
PRESETS = [PRESET_VICTRON, PRESET_SUNSYNK, PRESET_OTHER]

# Sign convention defaults per preset (True = sensor reports discharge/export as positive)
PRESET_INVERT = {
    PRESET_VICTRON: {CONF_BATTERY_INVERT: False, CONF_GRID_INVERT: False},
    PRESET_SUNSYNK: {CONF_BATTERY_INVERT: True, CONF_GRID_INVERT: False},
    PRESET_OTHER: {CONF_BATTERY_INVERT: False, CONF_GRID_INVERT: False},
}

SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"
UPDATE_INTERVAL_S = 30
SAMPLE_MINUTES = 5

# Solar collector (thermal) with circulation pump
CONF_COLLECTOR_MODE = "collector_mode"
CONF_COLLECTOR_TEMP = "collector_temp"
CONF_PUMP_ENTITY = "pump_entity"
CONF_TANK_BOTTOM_TEMP = "tank_bottom_temp"
COLLECTOR_NONE = "none"
COLLECTOR_GEYSERWISE = "geyserwise"  # Geyserwise runs the pump, we monitor it
COLLECTOR_SHELLY = "shelly"  # we switch the pump with a separate relay
COLLECTOR_MODES = [COLLECTOR_NONE, COLLECTOR_GEYSERWISE, COLLECTOR_SHELLY]

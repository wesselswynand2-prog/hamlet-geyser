# Hamlet Geyser

Smart geyser control for Home Assistant: schedules, spare-solar heating, battery and load-shedding protection, boost, and a live solar-vs-load view. Installs as a **Geyser** page in the Home Assistant sidebar, plus normal entities for automations.

Works with **Victron** (GX / Modbus TCP) and **Sunsynk / Deye** (Solar Assistant or Solarman), or any system that exposes power sensors. Switch the geyser with a **Shelly** relay (Pro 1PM / Plus 1PM recommended — gives watts) or a **Geyserwise**-type controller's switch entity.

## Install on a client's Home Assistant

**Option A – HACS (recommended)**
1. HACS → ⋮ → Custom repositories → add `https://github.com/wesselswynand2-prog/hamlet-geyser`, type *Integration*.
2. Search **Hamlet Geyser** → Download, restart Home Assistant. Updates then appear in Settings → Updates.

**Option B – upload the zip + one terminal command (recommended for updates)**
1. Upload `hamlet-geyser.zip` into the Home Assistant config folder (Samba share, or Studio Code Server / File editor → upload).
2. Open the **Terminal & SSH** add-on and run:
   - **First time on a client:**
     `cd /config 2>/dev/null || cd /homeassistant; mkdir -p /tmp/hg && unzip -oq "$(ls -t hamlet-geyser*.zip | head -1)" -d /tmp/hg && sh /tmp/hg/hamlet_geyser/hamlet-update.sh`
   - **Every update after that:** `sh /config/hamlet-update.sh` (or `sh /homeassistant/hamlet-update.sh`)
3. The script:
   - installs the new version and keeps the previous one in `hamlet_geyser_backup`;
   - deletes the uploaded zip;
   - restarts Home Assistant.

   Settings and schedules are kept. Add `--no-restart` to skip the restart.

**Option C – manual copy**
1. Copy `custom_components/hamlet_geyser` into the client's `/config/custom_components/` (Samba, File editor or Studio Code Server add-on).
2. Restart Home Assistant.

Then: **Settings → Devices & services → Add integration → Hamlet Geyser** and map the entities (4 short steps). Repeat for a second geyser — the page shows tabs.

## Mapping cheat-sheet

| Field | Victron | Sunsynk / Deye |
|---|---|---|
| Geyser switch | Shelly `switch.…` | Shelly or Geyserwise switch |
| Geyser power | Shelly power sensor | Shelly power sensor |
| Water temp | Geyserwise / DS18B20 probe | same |
| Solar (pick all) | MPPT PV power (+ PV inverter AC) | PV1 + PV2 power (or total PV) |
| House load (pick all) | AC consumption L1/L2/L3 | Load power |
| Battery SoC | Battery SoC | Battery SoC |
| Battery power | Battery power (+ charging) | Battery power (+ **discharging** → tick invert) |
| Grid power | Grid L1/L2/L3 (+ import) | Grid power (+ import) |
| Grid available | AC-in voltage (L1), or the Grid lost alarm (0 = grid OK; alarm sensors are detected by name) | Grid voltage or grid-connected sensor |

Leave *House load* empty if there's no sensor — it's calculated as solar + grid − battery.
No geyser meter? Power is estimated from the element rating while the relay is on.
No temperature probe? Everything works; heating just runs for the full time window.

**Check signs after setup:** open the Geyser page → Installer settings → *Live sensor check*. Battery must be positive while charging, grid positive while importing. If not, Devices & services → Hamlet Geyser → Configure → flip the sign options.

## How it decides (Auto mode)

1. **Safety** – above the safety limit (default 70 °C) the element is always off, in every mode.
2. **Spare solar first** – heats when spare solar (solar − house load excluding the geyser + battery charging) is above 2.5 kW, and keeps going while it stays above 0.8 kW. When the battery is full (≥95 %) Victron/Sunsynk throttle the panels, so it also heats then, as long as the battery isn't being drained (> 600 W). Solar may heat up to 65 °C.
3. **Heating times** – heats to the schedule target (default 55 °C) with 4 °C hysteresis.
4. **Protection** – never heats from the battery below 35 % unless the grid is up; during load-shedding schedules only run if the battery is above 70 % (or not at all, if you tick that option). Solar heating still runs.
5. **Relay protection** – at least 2 minutes between automatic switches.

Modes: **Auto**, **Boost** (30 min / 1 h / 2 h, then back to Auto), **On** (until switched back, safety limit still applies), **Off**.
Note: the controller owns the relay. If someone flips the Shelly manually, Auto switches it back — use the On/Off modes instead.

Clients (non-admin users) can change heating times, solar heating, and boost. Thresholds and protection are admin-only.

## Solar geyser / collector with pump (optional)

Setup step 3 asks how the collector pump is run:

| Option | Who runs the pump | What to map |
|---|---|---|
| **No collector** | – | nothing |
| **Geyserwise controls the pump** | Geyserwise (the app only monitors) | Collector temperature, plus the Geyserwise pump status if exposed. Without it, the pump state is estimated from collector vs tank temperature. |
| **Separate Shelly relay runs the pump** | This app | Collector temperature (e.g. Shelly Plus Add-on with a PT1000/NTC probe, or the Geyserwise collector sensor) and the Shelly switch on the pump. A tank-bottom probe is optional but gives better pump control. |

**Pump control (Shelly option):**
- **Normal running:** starts when the collector is 8 °C hotter than the tank, and stops when the difference drops to 3 °C. Minimum run time is 60 s.
- **Tank limit:** stops at a tank temperature of 75 °C.
- **Overheat cut-out:** stops above a collector temperature of 130 °C, and restarts once it is 10 °C below that.
- **Frost protection:** runs the pump when the collector is ≤ 4 °C. Use this for direct (open-loop) systems only. Switch it off for glycol / indirect systems.
- **Modes:** Auto / On / Off on the Geyser page (or `select.<name>_pump_mode`).

**Element vs collector (both options):** with *Let the solar collector heat first* on, a scheduled heating time keeps the element off while the pump is running and the collector is at or above the schedule target. If the collector is cooler than the target, the element still runs. Spare-PV heating isn't affected.

With Geyserwise also switching the element, use its element switch entity as the *Geyser switch* and turn off the Geyserwise's own timers, so the two don't fight.

## Dashboard card

The integration loads a **Hamlet Geyser** card automatically, so there's no resource to add.
Edit dashboard → **Add card** → search **Hamlet Geyser**. Or in YAML:

```yaml
type: custom:hamlet-geyser-card
geyser: Main geyser      # optional – name of the geyser; default is the first one
show_power: true         # solar / house / battery / grid
show_collector: true     # collector + pump (if set up)
show_chart: true         # today's solar vs load
```

The card shows the temperature gauge, status and reason, Auto / Boost / On / Off, the collector and pump, and today's chart. Tap the name or *Schedules ›* to open the full Geyser page.

## Entities (per geyser)

`select.<name>_mode`, `button.<name>_boost`, `sensor.<name>_status` (reason in attributes), `sensor.<name>_spare_solar`, and daily kWh sensors: solar, house load, geyser, geyser from solar. With a collector: `sensor.<name>_collector` (temperature, pump state in attributes), and with the Shelly option `select.<name>_pump_mode`.

## Tests

```
pip install pytest-homeassistant-custom-component
pytest
```

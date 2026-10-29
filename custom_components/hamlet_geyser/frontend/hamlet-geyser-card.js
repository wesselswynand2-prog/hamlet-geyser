/* Hamlet Geyser – dashboard card.
 *
 *   type: custom:hamlet-geyser-card
 *   geyser: Main geyser        # optional: name or entry id, default = first geyser
 *   show_power: true           # solar / house / battery / grid tiles
 *   show_chart: true           # today's solar vs load mini chart
 *   show_collector: true       # collector + pump (only if a collector is set up)
 *
 * Loaded automatically by the Hamlet Geyser integration – no resource to add.
 */
(() => {
const DOMAIN = "hamlet_geyser";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v) => (v === null || v === undefined || Number.isNaN(Number(v)) ? null : Number(v));
const fmtW = (w) => {
  w = num(w); if (w === null) return "–";
  const a = Math.abs(w);
  return a >= 1000 ? `${(w / 1000).toFixed(a >= 10000 ? 0 : 1)} kW` : `${Math.round(w)} W`;
};

const STYLE = `
:host { --c-solar: #eda100; --c-load: #2a78d6; --c-geyser: #e34948; --c-ok: var(--success-color, #2e9e4f);
  --c-warn: var(--warning-color, #e08a00); --c-bad: var(--error-color, #db4437);
  --muted: var(--secondary-text-color); --line: var(--divider-color, rgba(127,127,127,.2)); --accent: var(--primary-color); }
:host([dark]) { --c-solar: #c98500; --c-load: #3987e5; --c-geyser: #d55181; }
ha-card { background: var(--ha-card-background, var(--card-background-color)); border-radius: var(--ha-card-border-radius, 12px); padding: 16px; display: flex; flex-direction: column; gap: 12px; overflow: hidden; }
.head { display: flex; align-items: center; gap: 10px; min-width: 0; }
.head .name { font-size: 16px; font-weight: 500; flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer; }
.head ha-icon { --mdc-icon-size: 22px; color: var(--bc, var(--muted)); }
.badge { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 500; white-space: nowrap;
  background: color-mix(in srgb, var(--bc, var(--muted)) 16%, transparent); }
.badge .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--bc, var(--muted)); }
.badge.pulse .dot { animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: .3; } }
@media (prefers-reduced-motion: reduce) { .badge.pulse .dot, .flow.on::after { animation: none; } }
.main { display: grid; grid-template-columns: 132px minmax(0, 1fr); gap: 14px; align-items: center; }
.gauge { position: relative; width: 132px; }
.gauge svg { display: block; width: 100%; height: auto; }
.gauge .c { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 6px; }
.gauge .t { font-size: 32px; font-weight: 300; line-height: 1; font-variant-numeric: tabular-nums; }
.gauge .t small { font-size: 14px; }
.gauge .s { font-size: 11px; color: var(--muted); margin-top: 2px; }
.stats { display: grid; gap: 6px; min-width: 0; }
.stat { display: flex; align-items: center; gap: 8px; font-size: 13px; min-width: 0; }
.stat ha-icon { --mdc-icon-size: 18px; color: var(--ic, var(--muted)); flex: none; }
.stat .l { color: var(--muted); flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stat .v { font-variant-numeric: tabular-nums; white-space: nowrap; font-weight: 500; }
.reason { font-size: 13px; color: var(--muted); line-height: 1.35; }
.modes { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.modes button { font: inherit; font-size: 13px; padding: 8px 2px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 2px;
  background: transparent; color: var(--primary-text-color); border: 1px solid var(--line); }
.modes button ha-icon { --mdc-icon-size: 20px; }
.modes button[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: var(--text-primary-color, #fff); }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.boost { display: flex; gap: 6px; justify-content: center; }
.chip { font: inherit; font-size: 12px; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--line); background: transparent; color: var(--primary-text-color); cursor: pointer; }
.chip[aria-pressed="true"] { border-color: var(--accent); color: var(--accent); }
.coll { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 10px; font-size: 13px; flex-wrap: wrap; }
.coll .n { font-variant-numeric: tabular-nums; font-size: 18px; }
.coll .lab { color: var(--muted); font-size: 11px; }
.flow { flex: 1; min-width: 40px; height: 4px; border-radius: 2px; background: var(--line); position: relative; overflow: hidden; }
.flow.on { background: color-mix(in srgb, var(--c-solar) 35%, transparent); }
.flow.on::after { content: ""; position: absolute; top: 0; left: -30%; width: 30%; height: 100%; background: var(--c-solar); border-radius: 2px; animation: flow 1.4s linear infinite; }
@keyframes flow { to { left: 100%; } }
.coll .pm { display: flex; gap: 4px; margin-left: auto; }
.chart svg { display: block; width: 100%; height: 90px; }
.legend { display: flex; gap: 12px; font-size: 11px; color: var(--muted); margin-top: 4px; flex-wrap: wrap; }
.key { display: inline-flex; align-items: center; gap: 5px; }
.key i { width: 8px; height: 8px; border-radius: 2px; display: inline-block; }
.foot { display: flex; justify-content: space-between; align-items: center; gap: 12px; font-size: 12px; color: var(--muted); flex-wrap: wrap; }
.foot a { color: var(--accent); text-decoration: none; font-weight: 500; }
.msg { color: var(--muted); font-size: 14px; padding: 8px 0; }
`;

class HamletGeyserCard extends HTMLElement {
  static getStubConfig() { return { type: "custom:hamlet-geyser-card" }; }
  static getConfigElement() { return document.createElement("hamlet-geyser-card-editor"); }

  setConfig(config) {
    this._config = { show_power: true, show_chart: true, show_collector: true, ...config };
    if (this._hass) this._connect(true);
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    this.toggleAttribute("dark", !!hass.themes?.darkMode);
    if (first) this._connect(false);
  }

  getCardSize() { return this._config?.show_chart ? 6 : 4; }
  getGridOptions() { return { columns: 6, min_columns: 4, rows: "auto" }; }

  connectedCallback() {
    if (this._hass && !this._unsub && this._entryId) this._subscribe();
    this._tick = setInterval(() => this._snap && this._render(), 30000);
    this._hist = setInterval(() => this._loadState(), 5 * 60000);
  }
  disconnectedCallback() {
    if (this._unsub) { this._unsub(); this._unsub = null; }
    clearInterval(this._tick); clearInterval(this._hist);
  }

  _shell() {
    if (this._root) return;
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div id="body"><div class="msg">Loading geyser…</div></div></ha-card>`;
    this._root = this.shadowRoot.getElementById("body");
    this._root.addEventListener("click", (ev) => this._click(ev));
  }

  async _connect(reconfigured) {
    this._shell();
    if (reconfigured && this._unsub) { this._unsub(); this._unsub = null; }
    try {
      const list = await this._hass.callWS({ type: `${DOMAIN}/list` });
      const want = (this._config?.geyser || "").toString().trim().toLowerCase();
      const hit = want ? list.find((e) => e.entry_id === this._config.geyser || e.name.toLowerCase() === want) : list[0];
      if (!hit) {
        this._setHTML(this._root, `<div class="msg">${list.length ? `No geyser called “${esc(this._config.geyser)}”. Available: ${list.map((e) => esc(e.name)).join(", ")}` : "Hamlet Geyser isn't set up yet – add it in Settings → Devices &amp; services."}</div>`);
        return;
      }
      this._entryId = hit.entry_id;
      await this._loadState();
      this._subscribe();
    } catch (e) {
      this._setHTML(this._root, `<div class="msg">Hamlet Geyser integration not found (${esc(e.message || e.code || e)}).</div>`);
    }
  }

  async _loadState() {
    if (!this._entryId) return;
    try {
      const s = await this._hass.callWS({ type: `${DOMAIN}/state`, entry_id: this._entryId });
      this._history = s.history?.today || [];
      this._apply(s);
    } catch (e) { /* keep last view */ }
  }

  async _subscribe() {
    if (!this._entryId || this._unsub || !this.isConnected) return;
    try {
      this._unsub = await this._hass.connection.subscribeMessage((snap) => this._apply(snap), { type: `${DOMAIN}/subscribe`, entry_id: this._entryId });
    } catch (e) { /* retry on next connect */ }
  }

  _apply(snap) {
    if (snap.entry_id !== this._entryId) return;
    this._snap = snap;
    this._render();
  }

  _setHTML(el, html) {
    if (!el || el._html === html) return;
    el._html = html; el.innerHTML = html;
  }

  async _click(ev) {
    const t = ev.target.closest("[data-mode],[data-boost],[data-pump],[data-open]");
    if (!t) return;
    if (t.dataset.open !== undefined) {
      history.pushState(null, "", "/hamlet-geyser");
      window.dispatchEvent(new CustomEvent("location-changed"));
      return;
    }
    try {
      let msg;
      if (t.dataset.pump) msg = { type: `${DOMAIN}/set_pump_mode`, entry_id: this._entryId, mode: t.dataset.pump };
      else if (t.dataset.boost) msg = { type: `${DOMAIN}/set_mode`, entry_id: this._entryId, mode: "boost", minutes: Number(t.dataset.boost) };
      else msg = { type: `${DOMAIN}/set_mode`, entry_id: this._entryId, mode: t.dataset.mode };
      this._apply(await this._hass.callWS(msg));
    } catch (e) {
      this._hass.callService?.("persistent_notification", "create", { title: "Hamlet Geyser", message: e.message || String(e) });
    }
  }

  _color(d) {
    if (!d) return "var(--muted)";
    if (d.status === "Blocked" || d.status === "Offline") return "var(--c-warn)";
    if (d.status === "Hot") return "var(--c-bad)";
    if (d.source === "solar" || d.source === "collector") return "var(--c-solar)";
    if (d.source === "boost") return "var(--c-geyser)";
    if (d.on) return "var(--c-load)";
    if (d.status === "Ready") return "var(--c-ok)";
    return "var(--muted)";
  }

  _render() {
    const s = this._snap; if (!s || !this._root) return;
    const cfg = this._config || {};
    const d = s.decision || {}; const L = s.live || {}; const f = s.features || {};
    const color = this._color(d);
    const temp = num(L.temp);
    const target = num(d.target) ?? num(s.settings?.target_temp);
    const hasTemp = f.temp && temp !== null;

    // gauge
    const sweep = 270, r = 54, cx = 66, cy = 66, min = 20, max = 80;
    const frac = (v) => Math.max(0, Math.min(1, (v - min) / (max - min)));
    const arc = (fr) => {
      const a0 = 135 * Math.PI / 180, a = a0 + fr * sweep * Math.PI / 180;
      return `M${(cx + r * Math.cos(a0)).toFixed(1)} ${(cy + r * Math.sin(a0)).toFixed(1)} A${r} ${r} 0 ${fr * sweep > 180 ? 1 : 0} 1 ${(cx + r * Math.cos(a)).toFixed(1)} ${(cy + r * Math.sin(a)).toFixed(1)}`;
    };
    let tick = "";
    if (hasTemp && target !== null) {
      const a = (135 + frac(target) * sweep) * Math.PI / 180;
      tick = `<line x1="${(cx + 46 * Math.cos(a)).toFixed(1)}" y1="${(cy + 46 * Math.sin(a)).toFixed(1)}" x2="${(cx + 62 * Math.cos(a)).toFixed(1)}" y2="${(cy + 62 * Math.sin(a)).toFixed(1)}" stroke="var(--primary-text-color)" stroke-width="2" stroke-linecap="round"/>`;
    }
    const arcColor = color === "var(--muted)" ? "var(--accent)" : color;
    const gauge = `<div class="gauge"><svg viewBox="0 0 132 118" role="img" aria-label="${hasTemp ? `Water ${temp.toFixed(0)} degrees` : "Geyser"}">
        <path d="${arc(1)}" fill="none" stroke="var(--line)" stroke-width="9" stroke-linecap="round"/>
        ${hasTemp ? `<path d="${arc(frac(temp))}" fill="none" stroke="${arcColor}" stroke-width="9" stroke-linecap="round"/>` : d.on ? `<path d="${arc(1)}" fill="none" stroke="${color}" stroke-width="9" stroke-linecap="round"/>` : ""}
        ${tick}</svg>
      <div class="c">${hasTemp
        ? `<div class="t">${temp.toFixed(0)}<small>°C</small></div><div class="s">${target !== null ? `target ${target.toFixed(0)}°` : ""}</div>`
        : `<ha-icon icon="mdi:water-boiler" style="--mdc-icon-size:30px;color:${color}"></ha-icon><div class="s">${d.on ? fmtW(L.geyser_w) : "Off"}</div>`}</div></div>`;

    // side stats
    const stats = [];
    if (cfg.show_power !== false) {
      stats.push(["mdi:solar-power-variant", "var(--c-solar)", "Solar", fmtW(L.solar_w)]);
      stats.push(["mdi:home-lightning-bolt", "var(--c-load)", "House", fmtW(L.load_w)]);
      if (f.battery) stats.push(["mdi:battery-high", "var(--c-ok)", "Battery", num(L.battery_soc) === null ? "–" : `${Math.round(L.battery_soc)}%`]);
      if (f.grid || f.grid_status) stats.push([L.grid_available === false ? "mdi:transmission-tower-off" : "mdi:transmission-tower",
        L.grid_available === false ? "var(--c-warn)" : "var(--muted)", "Grid", L.grid_available === false ? "Down" : num(L.grid_w) === null ? "Up" : fmtW(L.grid_w)]);
    }
    stats.push(["mdi:water-boiler", "var(--c-geyser)", "Element", L.is_on ? fmtW(L.geyser_w) : "Off"]);
    const statsHtml = stats.map(([icon, ic, l, v]) => `<div class="stat" style="--ic:${ic}"><ha-icon icon="${icon}"></ha-icon><span class="l">${l}</span><span class="v">${v}</span></div>`).join("");

    // collector
    let coll = "";
    if (cfg.show_collector !== false && f.collector && f.collector !== "none") {
      const p = s.pump || {};
      const col = num(L.collector_temp), tank = num(L.tank_bottom_temp) ?? temp;
      coll = `<div class="coll">
        <div><div class="lab">Collector</div><div class="n">${col === null ? "–" : col.toFixed(0) + "°"}</div></div>
        <div class="flow ${p.on ? "on" : ""}" title="${esc(p.reason || "")}"></div>
        <div><div class="lab">Tank</div><div class="n">${tank === null ? "–" : tank.toFixed(0) + "°"}</div></div>
        <span class="badge ${p.on ? "pulse" : ""}" style="--bc:${p.on ? "var(--c-solar)" : p.status === "Overheat" ? "var(--c-warn)" : "var(--muted)"}"><span class="dot"></span>${esc(p.frost ? "Frost guard" : p.on ? "Pump on" : ["Overheat", "Tank full", "Offline", "No sensor"].includes(p.status) ? p.status : "Pump off")}</span>
        ${f.collector === "shelly" ? `<div class="pm">${[["auto", "Auto"], ["on", "On"], ["off", "Off"]].map(([m, l]) => `<button class="chip" data-pump="${m}" aria-pressed="${s.pump_mode === m}">${l}</button>`).join("")}</div>` : ""}
      </div>`;
    }

    // boost info
    let boost = "";
    if (s.mode === "boost") {
      boost = `<div class="boost">${[30, 60, 120].map((m) => `<button class="chip" data-boost="${m}">${m < 60 ? m + " min" : m / 60 + " h"}</button>`).join("")}</div>`;
    }

    const modes = [["auto", "mdi:auto-mode", "Auto"], ["boost", "mdi:fire", "Boost"], ["on", "mdi:power", "On"], ["off", "mdi:power-off", "Off"]];
    const html = `
      <div class="head" style="--bc:${color}"><ha-icon icon="mdi:water-boiler"></ha-icon>
        <span class="name" data-open title="Open the full Geyser page">${esc(cfg.title || s.name)}</span>
        <span class="badge ${d.on ? "pulse" : ""}" style="--bc:${color}"><span class="dot"></span>${esc(d.on ? `Heating · ${d.status}` : d.status || "…")}</span></div>
      <div class="main">${gauge}<div class="stats">${statsHtml}</div></div>
      <div class="reason">${esc(d.reason || "")}${s.mode === "boost" && s.boost_until ? ` · ends ${new Date(s.boost_until).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : ""}</div>
      <div class="modes" role="group" aria-label="Geyser mode">${modes.map(([m, icon, label]) => `<button data-mode="${m}" aria-pressed="${s.mode === m}"><ha-icon icon="${icon}"></ha-icon>${label}</button>`).join("")}</div>
      ${boost}
      ${coll}
      ${cfg.show_chart !== false ? `<div class="chart" id="chart">${this._chart()}</div>` : ""}
      <div class="foot"><span>${this._todayText(s)}</span><a href="/hamlet-geyser" data-open>Schedules ›</a></div>`;
    this._setHTML(this._root, html);
  }

  _todayText(s) {
    const e = s.energy_today || {};
    const g = num(e.geyser), gs = num(e.geyser_solar);
    if (g === null) return "";
    return `Today: geyser ${g.toFixed(1)} kWh${g > 0.05 && gs !== null ? ` · ${Math.round((gs / g) * 100)}% solar` : ""}`;
  }

  _chart() {
    const rows = this._history || [];
    if (rows.length < 2) return `<div class="msg" style="font-size:12px">Chart fills in every 5 minutes.</div>`;
    const W = 300, H = 90, pad = 2;
    const peak = Math.max(500, ...rows.map((r) => Math.max(r[1], r[2], r[3])));
    const x = (m) => pad + (m / 1440) * (W - 2 * pad);
    const y = (w) => H - 2 - (w / peak) * (H - 6);
    const segs = []; let cur = [];
    rows.forEach((r, i) => { if (i && r[0] - rows[i - 1][0] > 15) { segs.push(cur); cur = []; } cur.push(r); });
    segs.push(cur);
    const line = (i) => segs.map((sg) => sg.map((r, j) => `${j ? "L" : "M"}${x(r[0]).toFixed(1)} ${y(r[i]).toFixed(1)}`).join("")).join("");
    const area = segs.map((sg) => sg.length < 2 ? "" : `M${x(sg[0][0]).toFixed(1)} ${y(0)}` + sg.map((r) => `L${x(r[0]).toFixed(1)} ${y(r[1]).toFixed(1)}`).join("") + `L${x(sg[sg.length - 1][0]).toFixed(1)} ${y(0)}Z`).join("");
    const hours = [6, 12, 18].map((h) => `<line x1="${x(h * 60)}" x2="${x(h * 60)}" y1="0" y2="${H}" stroke="var(--line)" stroke-dasharray="2 3"/>`).join("");
    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Today's solar, house load and geyser power">
      ${hours}<line x1="0" x2="${W}" y1="${y(0)}" y2="${y(0)}" stroke="var(--line)"/>
      <path d="${area}" fill="var(--c-solar)" opacity=".18"/>
      <path d="${line(1)}" fill="none" stroke="var(--c-solar)" stroke-width="1.6" vector-effect="non-scaling-stroke"/>
      <path d="${line(3)}" fill="none" stroke="var(--c-geyser)" stroke-width="1.6" vector-effect="non-scaling-stroke"/>
      <path d="${line(2)}" fill="none" stroke="var(--c-load)" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>
      <div class="legend"><span class="key"><i style="background:var(--c-solar)"></i>Solar</span><span class="key"><i style="background:var(--c-load)"></i>House</span><span class="key"><i style="background:var(--c-geyser)"></i>Geyser</span><span style="margin-left:auto">peak ${fmtW(peak)}</span></div>`;
  }
}

/* --------------------------------------------------------------- editor */
class HamletGeyserCardEditor extends HTMLElement {
  setConfig(config) { this._config = { ...config }; this._render(); }
  set hass(hass) {
    const first = !this._hass; this._hass = hass;
    if (first) hass.callWS({ type: `${DOMAIN}/list` }).then((l) => { this._list = l; this._render(); }).catch(() => {});
  }
  _render() {
    if (!this._config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const c = this._config, list = this._list || [];
    const check = (k, label) => `<label style="display:flex;gap:8px;align-items:center;margin:6px 0"><input type="checkbox" data-k="${k}" ${c[k] !== false ? "checked" : ""}>${label}</label>`;
    this.shadowRoot.innerHTML = `<div style="display:grid;gap:8px;font-family:inherit">
      <label>Geyser<br><select data-k="geyser" style="width:100%;padding:8px;margin-top:4px">
        <option value="">${list.length ? "First geyser" : "Loading…"}</option>
        ${list.map((e) => `<option value="${esc(e.name)}" ${c.geyser === e.name || c.geyser === e.entry_id ? "selected" : ""}>${esc(e.name)}</option>`).join("")}
      </select></label>
      <label>Title (optional)<br><input data-k="title" value="${esc(c.title || "")}" style="width:100%;padding:8px;margin-top:4px;box-sizing:border-box"></label>
      ${check("show_power", "Show solar / house / battery / grid")}
      ${check("show_collector", "Show solar collector and pump")}
      ${check("show_chart", "Show today's chart")}
    </div>`;
    this.shadowRoot.querySelectorAll("[data-k]").forEach((el) => el.addEventListener("change", () => {
      const k = el.dataset.k;
      const next = { ...this._config };
      const v = el.type === "checkbox" ? el.checked : el.value;
      if (v === "" || v === true) delete next[k]; else next[k] = v;
      this._config = next;
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: next }, bubbles: true, composed: true }));
    }));
  }
}

if (!customElements.get("hamlet-geyser-card")) customElements.define("hamlet-geyser-card", HamletGeyserCard);
if (!customElements.get("hamlet-geyser-card-editor")) customElements.define("hamlet-geyser-card-editor", HamletGeyserCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "hamlet-geyser-card")) {
  window.customCards.push({ type: "hamlet-geyser-card", name: "Hamlet Geyser", description: "Geyser temperature, mode buttons, solar vs load and collector.", preview: true });
}
})();

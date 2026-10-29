/* Hamlet Geyser – sidebar panel for Home Assistant. No build step, no dependencies. */
const DOMAIN = "hamlet_geyser";
const DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v) => (v === null || v === undefined || Number.isNaN(Number(v)) ? null : Number(v));

function fmtW(w) {
  w = num(w);
  if (w === null) return "–";
  const a = Math.abs(w);
  return a >= 1000 ? `${(w / 1000).toFixed(a >= 10000 ? 0 : 1)} kW` : `${Math.round(w)} W`;
}
const fmtKwh = (v) => (num(v) === null ? "–" : `${Number(v).toFixed(1)} kWh`);
const hhmm = (mins) => `${String(Math.floor(mins / 60)).padStart(2, "0")}:${String(mins % 60).padStart(2, "0")}`;

const STYLE = `
:host {
  display: block; min-height: 100%;
  background: var(--primary-background-color);
  color: var(--primary-text-color);
  font-family: var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif);
  --gap: 16px;
  --radius: var(--ha-card-border-radius, 12px);
  --card: var(--card-background-color, #fff);
  --muted: var(--secondary-text-color, #6b6b6b);
  --line: var(--divider-color, rgba(127,127,127,.2));
  --accent: var(--primary-color, #03a9f4);
  --c-solar: #eda100; --c-load: #2a78d6; --c-geyser: #e34948;
  --c-ok: var(--success-color, #2e9e4f); --c-warn: var(--warning-color, #e08a00); --c-bad: var(--error-color, #db4437);
}
:host([dark]) { --c-solar: #c98500; --c-load: #3987e5; --c-geyser: #d55181; }
* { box-sizing: border-box; }
/* embedded inside Hamlet Home: no own header, geyser tabs (if several) as a plain row */
:host([embedded]) { min-height: 0; background: transparent; }
:host([embedded]) .toolbar { position: static; height: auto; min-height: 0; padding: 12px 16px 0; background: none; border: 0;
  color: var(--primary-text-color); max-width: 1240px; margin: 0 auto; }
:host([embedded]) #menu, :host([embedded]) .toolbar .title { display: none; }
:host([embedded]) .toolbar:has(.tabs:empty) { display: none; }
:host([embedded]) .tabs button { padding: 6px 14px; border-radius: 8px 8px 0 0; }
[hidden] { display: none !important; }
.toolbar { display: flex; align-items: center; gap: 8px; height: var(--header-height, 56px); padding: 0 12px;
  background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff);
  border-bottom: var(--app-header-border-bottom, none); position: sticky; top: 0; z-index: 2; }
.toolbar .title { font-size: 20px; font-weight: 400; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tabs { display: flex; gap: 4px; }
.tabs button { background: transparent; border: 0; color: inherit; opacity: .7; padding: 8px 12px; font: inherit; cursor: pointer; border-bottom: 2px solid transparent; }
.tabs button[aria-selected="true"] { opacity: 1; border-bottom-color: currentColor; }
main { max-width: 1240px; margin: 0 auto; padding: var(--gap); display: grid; gap: var(--gap);
  grid-template-columns: minmax(0, 1fr); }
@media (min-width: 900px) { main { grid-template-columns: 380px minmax(0, 1fr); } .span2 { grid-column: 1 / -1; } }
.card { background: var(--card); border-radius: var(--radius); box-shadow: var(--ha-card-box-shadow, none);
  border: 1px solid var(--ha-card-border-color, var(--line)); padding: 16px; min-width: 0; }
h2 { font-size: 16px; font-weight: 500; margin: 0 0 12px; display: flex; align-items: center; gap: 8px; }
h2 .sub { margin-left: auto; font-size: 13px; font-weight: 400; color: var(--muted); }
.muted { color: var(--muted); }
.small { font-size: 13px; }

/* hero */
.hero { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 12px; }
.gauge { width: 240px; max-width: 100%; position: relative; }
.gauge svg { display: block; width: 100%; height: auto; }
.gauge .center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 12px; }
.gauge .big { font-size: 46px; font-weight: 300; line-height: 1; font-variant-numeric: tabular-nums; }
.gauge .big small { font-size: 20px; }
.badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 999px; font-size: 14px; font-weight: 500;
  background: color-mix(in srgb, var(--bc, var(--muted)) 14%, transparent); color: var(--primary-text-color); }
.badge .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--bc, var(--muted)); }
.badge.pulse .dot { animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: .3; } }
.reason { font-size: 14px; color: var(--muted); min-height: 20px; }
.modes { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; width: 100%; }
.modes button { font: inherit; font-size: 14px; padding: 10px 4px; border-radius: 10px; cursor: pointer;
  background: transparent; color: var(--primary-text-color); border: 1px solid var(--line); display: flex; flex-direction: column; align-items: center; gap: 4px; }
.modes button ha-icon { --mdc-icon-size: 22px; }
.modes button[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: var(--text-primary-color, #fff); }
.modes button:focus-visible, button:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.boostbar { display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; }
.chip { font: inherit; font-size: 13px; padding: 6px 12px; border-radius: 999px; border: 1px solid var(--line); background: transparent; color: var(--primary-text-color); cursor: pointer; }
.chip[aria-pressed="true"] { border-color: var(--accent); color: var(--accent); }

/* tiles */
.tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr)); gap: 10px; }
.tile { border: 1px solid var(--line); border-radius: 10px; padding: 12px; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.tile .lab { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--muted); }
.tile .lab ha-icon { --mdc-icon-size: 18px; color: var(--ic, var(--muted)); }
.tile .val { font-size: 24px; font-weight: 400; font-variant-numeric: tabular-nums; white-space: nowrap; }
.tile .note { font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.socbar { height: 6px; border-radius: 3px; background: var(--line); overflow: hidden; margin-top: 4px; }
.socbar i { display: block; height: 100%; border-radius: 3px; background: var(--c-ok); }
.balance { margin-top: 14px; }
.balance .bar { display: flex; height: 14px; border-radius: 7px; overflow: hidden; background: var(--line); gap: 2px; }
.balance .bar i { display: block; height: 100%; }
.balance .legend { display: flex; flex-wrap: wrap; gap: 4px 16px; margin-top: 8px; font-size: 13px; color: var(--muted); }
.key { display: inline-flex; align-items: center; gap: 6px; }
.key i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }

/* chart */
.chartwrap { position: relative; }
.chartwrap svg { display: block; width: 100%; height: 240px; touch-action: pan-y; }
.chartwrap .axis text { fill: var(--muted); font-size: 11px; }
.chartwrap .grid line { stroke: var(--line); }
.tip { position: absolute; pointer-events: none; background: var(--card); border: 1px solid var(--line); border-radius: 8px;
  padding: 8px 10px; font-size: 12px; box-shadow: 0 4px 16px rgba(0,0,0,.15); white-space: nowrap; display: none; z-index: 1; }
.tip b { font-weight: 500; }
.tip .row { display: flex; align-items: center; gap: 6px; justify-content: space-between; }
.tip .row span:last-child { font-variant-numeric: tabular-nums; margin-left: 12px; }
.totals { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 12px; }
.totals > div { border-top: 1px solid var(--line); padding-top: 8px; }
.totals .v { font-size: 20px; font-variant-numeric: tabular-nums; }
.legendrow { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
.seg { display: inline-flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.seg button { font: inherit; font-size: 13px; padding: 4px 12px; border: 0; background: transparent; color: var(--primary-text-color); cursor: pointer; }
.seg button[aria-pressed="true"] { background: var(--accent); color: var(--text-primary-color, #fff); }
.empty { padding: 40px 0; text-align: center; color: var(--muted); font-size: 14px; }

/* forms */
.sched { display: grid; grid-template-columns: auto 1fr; gap: 10px 12px; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--line); }
.sched:last-of-type { border-bottom: 0; }
.sched .times { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.days { display: flex; gap: 4px; flex-wrap: wrap; grid-column: 2; }
.days button { font: inherit; font-size: 12px; width: 34px; height: 30px; border-radius: 8px; border: 1px solid var(--line); background: transparent; color: var(--muted); cursor: pointer; }
.days button[aria-pressed="true"] { background: color-mix(in srgb, var(--accent) 16%, transparent); border-color: var(--accent); color: var(--primary-text-color); }
input[type=time], input[type=number] { font: inherit; font-size: 14px; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--line);
  background: var(--secondary-background-color, transparent); color: var(--primary-text-color); color-scheme: inherit; }
input[type=number] { width: 80px; }
.switch { position: relative; width: 40px; height: 22px; flex: none; }
.switch input { opacity: 0; width: 100%; height: 100%; margin: 0; position: absolute; cursor: pointer; z-index: 1; }
.switch span { position: absolute; inset: 0; border-radius: 11px; background: var(--line); transition: .15s; }
.switch span::after { content: ""; position: absolute; width: 16px; height: 16px; left: 3px; top: 3px; border-radius: 50%; background: #fff; transition: .15s; box-shadow: 0 1px 2px rgba(0,0,0,.3); }
.switch input:checked + span { background: var(--accent); }
.switch input:checked + span::after { transform: translateX(18px); }
.iconbtn { background: transparent; border: 0; color: var(--muted); cursor: pointer; padding: 6px; border-radius: 50%; }
.iconbtn:hover { color: var(--c-bad); }
.actions { display: flex; gap: 8px; justify-content: flex-end; align-items: center; margin-top: 12px; flex-wrap: wrap; }
.btn { font: inherit; font-size: 14px; padding: 8px 16px; border-radius: 8px; border: 1px solid var(--line); background: transparent; color: var(--primary-text-color); cursor: pointer; }
.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--text-primary-color, #fff); }
.btn:disabled { opacity: .5; cursor: default; }
.form { display: grid; gap: 2px; }
.field { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--line); }
.field:last-child { border-bottom: 0; }
.field label { font-size: 14px; }
.field .hint { display: block; font-size: 12px; color: var(--muted); }
.field .ctl { display: flex; align-items: center; gap: 6px; flex: none; font-size: 13px; color: var(--muted); }
.msg { font-size: 13px; }
.msg.err { color: var(--c-bad); }
.msg.ok { color: var(--c-ok); }
details summary { cursor: pointer; font-size: 14px; color: var(--muted); padding: 4px 0; }
.rawgrid { display: grid; grid-template-columns: 1fr auto; gap: 4px 16px; font-size: 13px; margin-top: 8px; }
.rawgrid span:nth-child(even) { font-variant-numeric: tabular-nums; text-align: right; }
.cols2 { display: grid; gap: 0 32px; grid-template-columns: minmax(0, 1fr); }
@media (min-width: 900px) { .cols2 { grid-template-columns: 1fr 1fr; } }
.coll { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; align-items: center; }
.loop { display: flex; align-items: center; gap: 10px; grid-column: span 2; min-width: 0; }
@media (max-width: 520px) { .coll { grid-template-columns: 1fr 1fr; } .loop { grid-column: 1 / -1; } .loop .node { min-width: 0; flex: none; } .pmodes { grid-column: 1 / -1; } }
.loop .node { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; min-width: 96px; }
.loop .node .val { font-size: 24px; font-variant-numeric: tabular-nums; }
.loop .flow { flex: 1; min-width: 60px; height: 4px; border-radius: 2px; background: var(--line); position: relative; overflow: hidden; }
.loop .flow.on { background: color-mix(in srgb, var(--c-solar) 35%, transparent); }
.loop .flow.on::after { content: ""; position: absolute; top: 0; left: -30%; width: 30%; height: 100%; background: var(--c-solar); border-radius: 2px; animation: flow 1.4s linear infinite; }
@keyframes flow { to { left: 100%; } }
@media (prefers-reduced-motion: reduce) { .loop .flow.on::after, .badge.pulse .dot { animation: none; } }
.pmodes { display: flex; gap: 6px; flex-wrap: wrap; }
.loading { padding: 64px; text-align: center; color: var(--muted); }
`;

class HamletGeyserPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._entries = [];
    this._entryId = null;
    this._snap = null;
    this._history = null;
    this._day = "today";
    this._draft = null; // editable copy of settings
    this._dirty = false;
    this._unsub = null;
    this._built = false;
    this._narrow = false;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    const dark = !!hass.themes?.darkMode;
    this.toggleAttribute("dark", dark);
    if (this._menuBtn) this._menuBtn.hass = hass;
    if (first) this._init();
  }
  get hass() { return this._hass; }
  set narrow(v) { this._narrow = v; if (this._menuBtn) this._menuBtn.narrow = v; }
  set panel(v) { this._panel = v; }
  set route(v) { this._route = v; }

  connectedCallback() {
    if (this._hass && !this._unsub && this._entryId) this._subscribe();
    this._histTimer = setInterval(() => this._loadState(), 5 * 60 * 1000);
    this._clock = setInterval(() => this._renderHero(), 30 * 1000);
  }
  disconnectedCallback() {
    this._unsubscribe();
    clearInterval(this._histTimer);
    clearInterval(this._clock);
    this._ro?.disconnect();
  }

  async _init() {
    this._buildShell();
    try {
      this._entries = await this._hass.callWS({ type: `${DOMAIN}/list` });
    } catch (e) {
      this._main.innerHTML = `<div class="card span2 loading">Could not reach the geyser integration: ${esc(e.message)}</div>`;
      return;
    }
    if (!this._entries.length) {
      this._main.innerHTML = `<div class="card span2 loading">No geyser set up yet. Go to Settings → Devices &amp; services → Add integration → Hamlet Geyser.</div>`;
      return;
    }
    let saved = null;
    try { saved = localStorage.getItem("hamlet_geyser_entry"); } catch (e) { /* storage blocked */ }
    this._entryId = this._entries.some((e) => e.entry_id === saved) ? saved : this._entries[0].entry_id;
    this._renderTabs();
    await this._select(this._entryId);
  }

  _buildShell() {
    const root = this.shadowRoot;
    root.innerHTML = `<style>${STYLE}</style>
      <div class="toolbar"><span id="menu"></span><div class="title">Geyser</div><div class="tabs" role="tablist"></div></div>
      <main><div class="card span2 loading">Loading…</div></main>`;
    this._main = root.querySelector("main");
    const mb = document.createElement("ha-menu-button");
    mb.hass = this._hass;
    mb.narrow = this._narrow;
    root.getElementById("menu").appendChild(mb);
    this._menuBtn = mb;
  }

  _renderTabs() {
    const tabs = this.shadowRoot.querySelector(".tabs");
    if (this._entries.length < 2) { tabs.innerHTML = ""; return; }
    tabs.innerHTML = this._entries.map((e) =>
      `<button role="tab" data-id="${esc(e.entry_id)}" aria-selected="${e.entry_id === this._entryId}">${esc(e.name)}</button>`).join("");
    tabs.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => this._select(b.dataset.id)));
  }

  async _select(id) {
    this._unsubscribe();
    this._entryId = id;
    try { localStorage.setItem("hamlet_geyser_entry", id); } catch (e) { /* ignore */ }
    this._renderTabs();
    this._snap = null;
    this._draft = null;
    this._dirty = false;
    this._built = false;
    this._shownSettings = null;
    await this._loadState();
    this._subscribe();
  }

  async _loadState() {
    if (!this._entryId) return;
    try {
      const s = await this._hass.callWS({ type: `${DOMAIN}/state`, entry_id: this._entryId });
      this._history = { today: s.history.today, yesterday: s.history.yesterday, energy_yesterday: s.energy_yesterday };
      this._isAdmin = s.is_admin;
      this._apply(s);
      this._renderChart();
    } catch (e) {
      this._main.innerHTML = `<div class="card span2 loading">${esc(e.message)}</div>`;
    }
  }

  async _subscribe() {
    if (!this._entryId || this._unsub) return;
    try {
      this._unsub = await this._hass.connection.subscribeMessage((snap) => this._apply(snap), { type: `${DOMAIN}/subscribe`, entry_id: this._entryId });
    } catch (e) { console.warn("hamlet_geyser subscribe failed", e); }
  }
  _unsubscribe() { if (this._unsub) { this._unsub(); this._unsub = null; } }

  /** Replace el's markup only if it changed, so controls aren't recreated under the pointer. */
  _setHTML(el, html) {
    if (!el || el._html === html) return false;
    el._html = html;
    el.innerHTML = html;
    return true;
  }

  /** True while the person is typing in one of the settings forms. */
  _editing() {
    const a = this.shadowRoot.activeElement;
    return !!(a && a.closest && a.closest("#scheds, #smart, #inst"));
  }

  _apply(snap) {
    if (snap.entry_id !== this._entryId) return;
    this._snap = snap;
    const settingsJson = JSON.stringify(snap.settings);
    const settingsChanged = settingsJson !== this._shownSettings;
    const redrawForms = settingsChanged && !this._dirty && !this._editing();
    if (redrawForms) this._draft = JSON.parse(settingsJson);
    if (!this._built) this._buildLayout();
    this.shadowRoot.querySelector(".toolbar .title").textContent = this._entries.length > 1 ? "Geyser" : snap.name;
    this._renderHero();
    this._renderTiles();
    this._renderTotals();
    this._renderCollector();
    if (redrawForms) {
      this._shownSettings = settingsJson;
      this._renderSchedules(); this._renderSmart(); this._renderInstaller();
    }
    this._renderRaw();
  }

  _buildLayout() {
    this._main.innerHTML = `
      <section class="card hero"><div class="hero" id="hero" aria-live="polite" style="width:100%"></div><div class="hero" id="heroctl" style="width:100%"></div></section>
      <section class="card"><h2>Right now <span class="sub" id="nowsub"></span></h2><div id="tiles"></div></section>
      <section class="card span2" id="collcard" hidden><h2><ha-icon icon="mdi:solar-panel"></ha-icon>Solar collector <span class="sub" id="collsub"></span></h2><div id="coll"></div></section>
      <section class="card span2">
        <h2>Solar vs house load
          <span class="sub"><span class="seg" id="dayseg">
            <button data-d="today" aria-pressed="true">Today</button><button data-d="yesterday" aria-pressed="false">Yesterday</button>
          </span></span></h2>
        <div class="legendrow" id="legend"></div>
        <div class="chartwrap" id="chart"></div>
        <div class="totals" id="totals"></div>
      </section>
      <section class="card"><h2>Heating times</h2><div id="scheds"></div>
        <div class="actions"><button class="btn" id="addsched">+ Add time</button></div></section>
      <section class="card"><h2>Smart heating</h2><div id="smart" class="form"></div></section>
      <section class="card span2" id="installer" hidden><h2>Installer settings <span class="sub">admin only</span></h2><div id="inst"></div></section>
      <div class="span2 actions" id="savebar" hidden>
        <span class="msg" id="savemsg"></span>
        <button class="btn" id="discard">Discard</button><button class="btn primary" id="save">Save changes</button>
      </div>`;
    this._built = true;
    const root = this.shadowRoot;
    root.querySelectorAll("#dayseg button").forEach((b) => b.addEventListener("click", () => {
      this._day = b.dataset.d;
      root.querySelectorAll("#dayseg button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      this._renderChart(); this._renderTotals();
    }));
    root.getElementById("addsched").addEventListener("click", () => {
      this._draft.schedules.push({ enabled: true, days: [0, 1, 2, 3, 4, 5, 6], start: "12:00", end: "13:00", target: this._draft.target_temp });
      this._markDirty(); this._renderSchedules();
    });
    root.getElementById("save").addEventListener("click", () => this._save());
    root.getElementById("heroctl").addEventListener("click", (ev) => {
      const m = ev.target.closest("[data-mode]"); if (m) return this._setMode(m.dataset.mode);
      const b = ev.target.closest("[data-boost]"); if (b) return this._setMode("boost", Number(b.dataset.boost));
    });
    root.getElementById("coll").addEventListener("click", async (ev) => {
      const b = ev.target.closest("[data-pump]"); if (!b) return;
      try { this._apply(await this._hass.callWS({ type: `${DOMAIN}/set_pump_mode`, entry_id: this._entryId, mode: b.dataset.pump })); }
      catch (e) { alert(e.message); }
    });
    root.getElementById("discard").addEventListener("click", () => {
      this._dirty = false; this._draft = JSON.parse(JSON.stringify(this._snap.settings)); this._shownSettings = JSON.stringify(this._snap.settings);
      this._setMsg(""); this._renderSchedules(); this._renderSmart(); this._renderInstaller(); this._toggleSaveBar();
    });
    this._ro = new ResizeObserver(() => this._renderChart());
    this._ro.observe(root.getElementById("chart"));
    this._renderLegend();
  }

  /* ---------------------------------------------------------------- hero */
  _statusColor(d) {
    if (!d) return "var(--muted)";
    if (d.status === "Blocked" || d.status === "Offline") return "var(--c-warn)";
    if (d.status === "Hot") return "var(--c-bad)";
    if (d.source === "solar" || d.source === "collector") return "var(--c-solar)";
    if (d.source === "boost") return "var(--c-geyser)";
    if (d.on) return "var(--c-load)";
    if (d.status === "Ready") return "var(--c-ok)";
    return "var(--muted)";
  }

  _renderHero() {
    const s = this._snap; if (!s) return;
    const el = this.shadowRoot.getElementById("hero"); if (!el) return;
    const d = s.decision || {};
    const live = s.live || {};
    const temp = num(live.temp);
    const target = num(d.target) ?? num(s.settings.target_temp);
    const min = 20, max = 80, sweep = 270;
    const frac = (v) => Math.max(0, Math.min(1, (v - min) / (max - min)));
    const arc = (f) => {
      const a0 = (135) * Math.PI / 180, a = a0 + f * sweep * Math.PI / 180;
      const r = 100, cx = 120, cy = 120;
      const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0);
      const x1 = cx + r * Math.cos(a), y1 = cy + r * Math.sin(a);
      return `M${x0.toFixed(1)} ${y0.toFixed(1)} A${r} ${r} 0 ${f * sweep > 180 ? 1 : 0} 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`;
    };
    const tick = (v) => {
      const a = (135 + frac(v) * sweep) * Math.PI / 180;
      return `<line x1="${(120 + 88 * Math.cos(a)).toFixed(1)}" y1="${(120 + 88 * Math.sin(a)).toFixed(1)}" x2="${(120 + 112 * Math.cos(a)).toFixed(1)}" y2="${(120 + 112 * Math.sin(a)).toFixed(1)}" stroke="var(--primary-text-color)" stroke-width="2" stroke-linecap="round"/>`;
    };
    const color = this._statusColor(d);
    const hasTemp = s.features.temp && temp !== null;
    const center = hasTemp
      ? `<div class="big">${temp.toFixed(0)}<small>°C</small></div><div class="muted small">${target !== null && s.features.temp ? `target ${target.toFixed(0)}°C` : ""}</div>`
      : `<ha-icon icon="mdi:water-boiler" style="--mdc-icon-size:48px;color:${color}"></ha-icon><div class="big" style="font-size:28px;margin-top:6px">${d.on ? fmtW(live.geyser_w) : "Off"}</div>`;
    const gauge = `<div class="gauge"><svg viewBox="0 0 240 210" role="img" aria-label="${hasTemp ? `Water ${temp.toFixed(0)} degrees` : "Geyser"}">
        <path d="${arc(1)}" fill="none" stroke="var(--line)" stroke-width="14" stroke-linecap="round"/>
        ${hasTemp ? `<path d="${arc(frac(temp))}" fill="none" stroke="${color === "var(--muted)" ? "var(--accent)" : color}" stroke-width="14" stroke-linecap="round"/>` : `<path d="${arc(d.on ? 1 : 0.001)}" fill="none" stroke="${color}" stroke-width="14" stroke-linecap="round" opacity="${d.on ? 1 : 0}"/>`}
        ${hasTemp && target !== null ? tick(target) : ""}
        ${hasTemp ? `<text x="34" y="200" fill="var(--muted)" font-size="11" text-anchor="middle">${min}°</text><text x="206" y="200" fill="var(--muted)" font-size="11" text-anchor="middle">${max}°</text>` : ""}
      </svg><div class="center">${center}</div></div>`;

    let boostInfo = "";
    if (s.mode === "boost" && s.boost_until) {
      const mins = Math.max(0, Math.round((new Date(s.boost_until) - Date.now()) / 60000));
      boostInfo = `<div class="muted small">Boost ends ${new Date(s.boost_until).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} (${mins} min)</div>`;
    }
    const modes = [["auto", "mdi:auto-mode", "Auto"], ["boost", "mdi:fire", "Boost"], ["on", "mdi:power", "On"], ["off", "mdi:power-off", "Off"]];
    this._setHTML(el, `
      ${gauge}
      <span class="badge ${d.on ? "pulse" : ""}" style="--bc:${color}"><span class="dot"></span>${esc(d.on ? `Heating · ${d.status}` : d.status || "…")}</span>
      <div class="reason">${esc(d.reason || "")}</div>
      ${boostInfo}`);
    this._setHTML(this.shadowRoot.getElementById("heroctl"), `
      <div class="modes" role="group" aria-label="Mode">
        ${modes.map(([m, icon, label]) => `<button data-mode="${m}" aria-pressed="${s.mode === m}"><ha-icon icon="${icon}"></ha-icon>${label}</button>`).join("")}
      </div>
      ${s.mode === "boost" ? `<div class="boostbar">${[30, 60, 120].map((m) => `<button class="chip" data-boost="${m}">${m < 60 ? m + " min" : m / 60 + " h"}</button>`).join("")}</div>` : ""}
      ${s.mode === "on" ? `<div class="muted small">Stays on until you switch back to Auto${s.features.temp ? ` (safety limit ${s.settings.max_temp}°C)` : ""}.</div>` : ""}
    `);
  }

  async _setMode(mode, minutes) {
    try {
      const msg = { type: `${DOMAIN}/set_mode`, entry_id: this._entryId, mode };
      if (minutes) msg.minutes = minutes;
      this._apply(await this._hass.callWS(msg));
    } catch (e) { alert(e.message); }
  }

  /* --------------------------------------------------------------- tiles */
  _renderTiles() {
    const s = this._snap; const el = this.shadowRoot.getElementById("tiles"); if (!el) return;
    const L = s.live || {}; const f = s.features;
    const tiles = [];
    tiles.push({ icon: "mdi:solar-power-variant", ic: "var(--c-solar)", lab: "Solar", val: fmtW(L.solar_w),
      note: num(L.surplus_w) !== null ? `spare ${fmtW(Math.max(L.surplus_w, 0))}` : "" });
    tiles.push({ icon: "mdi:home-lightning-bolt", ic: "var(--c-load)", lab: "House load", val: fmtW(L.load_w),
      note: f.load_meter ? "measured" : "calculated" });
    if (f.battery) {
      const bw = num(L.battery_w);
      const soc = num(L.battery_soc);
      tiles.push({ icon: soc === null ? "mdi:battery-unknown" : `mdi:battery${soc >= 95 ? "" : "-" + Math.max(10, Math.round(soc / 10) * 10)}`,
        ic: "var(--c-ok)", lab: "Battery", val: soc === null ? "–" : `${Math.round(soc)}%`,
        note: bw === null ? "" : Math.abs(bw) < 30 ? "idle" : bw > 0 ? `charging ${fmtW(bw)}` : `discharging ${fmtW(-bw)}`,
        soc });
    }
    if (f.grid || f.grid_status) {
      const gw = num(L.grid_w);
      const down = L.grid_available === false;
      tiles.push({ icon: down ? "mdi:transmission-tower-off" : "mdi:transmission-tower", ic: down ? "var(--c-warn)" : "var(--muted)",
        lab: "Grid", val: down ? "Down" : gw === null ? "Up" : fmtW(Math.abs(gw)),
        note: down ? "load-shedding / outage" : gw === null ? "" : Math.abs(gw) < 30 ? "idle" : gw > 0 ? "importing" : "exporting" });
    }
    if (f.collector && f.collector !== "none") {
      const p = s.pump || {};
      tiles.push({ icon: "mdi:solar-panel", ic: "var(--c-solar)", lab: "Collector",
        val: num(L.collector_temp) === null ? "–" : `${Math.round(L.collector_temp)}°C`,
        note: p.frost ? "frost protection" : p.on ? "pump running" : "pump off" });
    }
    tiles.push({ icon: "mdi:water-boiler", ic: "var(--c-geyser)", lab: "Geyser", val: L.is_on ? fmtW(L.geyser_w) : "Off",
      note: L.is_on ? (f.geyser_meter ? "element on" : "estimated") : "element off" });

    this._setHTML(el, `<div class="tiles">${tiles.map((t) => `
      <div class="tile" style="--ic:${t.ic}"><div class="lab"><ha-icon icon="${t.icon}"></ha-icon>${t.lab}</div>
      <div class="val">${t.val}</div>${t.soc !== undefined && t.soc !== null ? `<div class="socbar"><i style="width:${t.soc}%;background:${t.soc < s.settings.min_soc ? "var(--c-warn)" : "var(--c-ok)"}"></i></div>` : ""}
      <div class="note">${esc(t.note)}</div></div>`).join("")}</div>${this._balanceHtml(L)}`);
    const sub = this.shadowRoot.getElementById("nowsub");
    if (sub) sub.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  _balanceHtml(L) {
    const solar = Math.max(num(L.solar_w) || 0, 0);
    const load = Math.max(num(L.load_w) || 0, 0);
    if (!solar && !load) return "";
    const fromSolar = Math.min(solar, load);
    const shortfall = Math.max(load - solar, 0);
    const spare = Math.max(solar - load, 0);
    const total = Math.max(load, solar) || 1;
    const pct = load ? Math.round((fromSolar / load) * 100) : 100;
    return `<div class="balance" aria-label="Load covered by solar ${pct} percent">
      <div class="small" style="margin-bottom:6px">Solar is covering <b>${pct}%</b> of the house right now</div>
      <div class="bar">
        ${fromSolar ? `<i style="width:${(fromSolar / total) * 100}%;background:var(--c-solar)"></i>` : ""}
        ${shortfall ? `<i style="width:${(shortfall / total) * 100}%;background:var(--c-load)"></i>` : ""}
        ${spare ? `<i style="width:${(spare / total) * 100}%;background:var(--c-solar);opacity:.35"></i>` : ""}
      </div>
      <div class="legend">
        <span class="key"><i style="background:var(--c-solar)"></i>Load from solar ${fmtW(fromSolar)}</span>
        ${shortfall ? `<span class="key"><i style="background:var(--c-load)"></i>From battery/grid ${fmtW(shortfall)}</span>` : ""}
        ${spare ? `<span class="key"><i style="background:var(--c-solar);opacity:.35"></i>Spare solar ${fmtW(spare)}</span>` : ""}
      </div></div>`;
  }

  /* --------------------------------------------------------------- chart */
  _renderLegend() {
    const el = this.shadowRoot.getElementById("legend");
    el.innerHTML = `<span class="key"><i style="background:var(--c-solar)"></i>Solar</span>
      <span class="key"><i style="background:var(--c-load)"></i>House load</span>
      <span class="key"><i style="background:var(--c-geyser)"></i>Geyser</span>`;
  }

  _rows() {
    const h = this._history; if (!h) return [];
    return (this._day === "today" ? h.today : h.yesterday) || [];
  }

  _renderChart() {
    const wrap = this.shadowRoot.getElementById("chart"); if (!wrap) return;
    const rows = this._rows();
    if (rows.length < 2) {
      wrap.innerHTML = `<div class="empty">${this._day === "today" ? "Collecting data – the chart fills in every 5 minutes." : "No data for yesterday yet."}</div>`;
      return;
    }
    const W = Math.max(wrap.clientWidth, 280), H = 240;
    const m = { l: 44, r: 8, t: 8, b: 24 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const peak = Math.max(...rows.map((r) => Math.max(r[1], r[2], r[3])), 500);
    const step = [250, 500, 1000, 2000, 2500, 5000, 10000].find((st) => peak / st <= 5) || 20000;
    const ymax = Math.ceil(peak / step) * step;
    const x = (min) => m.l + (min / 1440) * iw;
    const y = (w) => m.t + ih - (w / ymax) * ih;

    // split series into segments at gaps > 15 min so missing data isn't drawn as a line
    const segs = [];
    let cur = [];
    rows.forEach((r, i) => {
      if (i && r[0] - rows[i - 1][0] > 15) { segs.push(cur); cur = []; }
      cur.push(r);
    });
    segs.push(cur);
    const path = (idx) => segs.map((seg) => seg.map((r, i) => `${i ? "L" : "M"}${x(r[0]).toFixed(1)} ${y(r[idx]).toFixed(1)}`).join("")).join("");
    const area = segs.map((seg) => seg.length < 2 ? "" : `M${x(seg[0][0]).toFixed(1)} ${y(0)}` + seg.map((r) => `L${x(r[0]).toFixed(1)} ${y(r[1]).toFixed(1)}`).join("") + `L${x(seg[seg.length - 1][0]).toFixed(1)} ${y(0)}Z`).join("");

    const ticks = [];
    for (let v = 0; v <= ymax; v += step) ticks.push(v);
    const xt = [0, 180, 360, 540, 720, 900, 1080, 1260, 1440];
    const showX = iw < 420 ? xt.filter((_, i) => i % 2 === 0) : xt;

    wrap.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Solar production, house load and geyser power over the day">
      <g class="grid">${ticks.map((v) => `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" ${v ? "" : 'stroke-width="1.5"'}/>`).join("")}</g>
      <g class="axis">${ticks.map((v) => `<text x="${m.l - 6}" y="${y(v) + 4}" text-anchor="end">${v >= 1000 ? (v / 1000).toFixed(v % 1000 ? 1 : 0) + "k" : v}</text>`).join("")}
        ${showX.map((t) => `<text x="${x(t)}" y="${H - 6}" text-anchor="${t === 0 ? "start" : t === 1440 ? "end" : "middle"}">${hhmm(t)}</text>`).join("")}</g>
      <path d="${area}" fill="var(--c-solar)" opacity=".18"/>
      <path d="${path(1)}" fill="none" stroke="var(--c-solar)" stroke-width="2" stroke-linejoin="round"/>
      <path d="${path(3)}" fill="none" stroke="var(--c-geyser)" stroke-width="2" stroke-linejoin="round"/>
      <path d="${path(2)}" fill="none" stroke="var(--c-load)" stroke-width="2" stroke-linejoin="round"/>
      <g id="hover" style="display:none"><line id="hl" y1="${m.t}" y2="${m.t + ih}" stroke="var(--muted)" stroke-dasharray="3 3"/>
        <circle id="h1" r="4.5" fill="var(--c-solar)" stroke="var(--card)" stroke-width="2"/>
        <circle id="h2" r="4.5" fill="var(--c-load)" stroke="var(--card)" stroke-width="2"/>
        <circle id="h3" r="4.5" fill="var(--c-geyser)" stroke="var(--card)" stroke-width="2"/></g>
      <rect id="hit" x="${m.l}" y="0" width="${iw}" height="${H}" fill="transparent"/>
    </svg><div class="tip" id="tip"></div>`;

    const svg = wrap.querySelector("svg"), hover = wrap.querySelector("#hover"), tip = wrap.querySelector("#tip");
    const show = (ev) => {
      const rect = svg.getBoundingClientRect();
      const px = ((ev.clientX - rect.left) / rect.width) * W;
      const min = ((px - m.l) / iw) * 1440;
      let best = rows[0];
      for (const r of rows) if (Math.abs(r[0] - min) < Math.abs(best[0] - min)) best = r;
      const bx = x(best[0]);
      hover.style.display = "";
      hover.querySelector("#hl").setAttribute("x1", bx); hover.querySelector("#hl").setAttribute("x2", bx);
      [1, 2, 3].forEach((i) => { const c = hover.querySelector(`#h${i}`); c.setAttribute("cx", bx); c.setAttribute("cy", y(best[i])); });
      tip.innerHTML = `<b>${hhmm(best[0])}</b>
        <div class="row"><span class="key"><i style="background:var(--c-solar)"></i>Solar</span><span>${fmtW(best[1])}</span></div>
        <div class="row"><span class="key"><i style="background:var(--c-load)"></i>House load</span><span>${fmtW(best[2])}</span></div>
        <div class="row"><span class="key"><i style="background:var(--c-geyser)"></i>Geyser</span><span>${fmtW(best[3])}</span></div>
        ${best[4] !== null && best[4] !== undefined ? `<div class="row"><span>Battery</span><span>${Math.round(best[4])}%</span></div>` : ""}
        ${best[5] !== null && best[5] !== undefined ? `<div class="row"><span>Water</span><span>${Math.round(best[5])}°C</span></div>` : ""}
        ${best[7] !== null && best[7] !== undefined ? `<div class="row"><span>Collector${best[8] ? " (pump on)" : ""}</span><span>${Math.round(best[7])}°C</span></div>` : ""}`;
      tip.style.display = "block";
      const tx = (bx / W) * rect.width;
      const tw = tip.offsetWidth;
      const fitsRight = tx + 12 + tw <= rect.width;
      tip.style.left = `${fitsRight ? tx + 12 : Math.max(tx - tw - 12, 0)}px`;
      tip.style.top = `8px`;
    };
    const hide = () => { hover.style.display = "none"; tip.style.display = "none"; };
    const hit = wrap.querySelector("#hit");
    hit.addEventListener("pointermove", show);
    hit.addEventListener("pointerdown", show);
    hit.addEventListener("pointerleave", hide);
  }

  _renderTotals() {
    const el = this.shadowRoot.getElementById("totals"); if (!el || !this._snap) return;
    const e = (this._day === "today" ? this._snap.energy_today : this._history?.energy_yesterday) || {};
    const solar = num(e.solar), load = num(e.load), geyser = num(e.geyser), gs = num(e.geyser_solar), imp = num(e.import);
    const cover = solar !== null && load ? Math.min(100, Math.round((Math.min(solar, load) / load) * 100)) : null;
    const gpct = geyser ? Math.round(((gs || 0) / geyser) * 100) : null;
    el.innerHTML = `
      <div><div class="muted small">Solar produced</div><div class="v">${fmtKwh(solar)}</div></div>
      <div><div class="muted small">House used</div><div class="v">${fmtKwh(load)}</div></div>
      <div><div class="muted small">Geyser used</div><div class="v">${fmtKwh(geyser)}</div>${gpct !== null ? `<div class="muted small">${gpct}% from solar</div>` : ""}</div>
      ${this._snap.features.grid ? `<div><div class="muted small">Bought from grid</div><div class="v">${fmtKwh(imp)}</div></div>` : ""}
      <div><div class="muted small">Solar vs usage</div><div class="v">${cover === null ? "–" : cover + "%"}</div></div>`;
  }

  /* ----------------------------------------------------------- collector */
  _renderCollector() {
    const card = this.shadowRoot.getElementById("collcard"); if (!card) return;
    const s = this._snap; const mode = s.features.collector;
    card.hidden = !mode || mode === "none";
    if (card.hidden) return;
    const L = s.live || {}; const p = s.pump || {};
    const col = num(L.collector_temp);
    const tank = num(L.tank_bottom_temp) ?? num(L.temp);
    const dt = col !== null && tank !== null ? col - tank : null;
    const shelly = mode === "shelly";
    this.shadowRoot.getElementById("collsub").textContent = shelly ? "pump run by this app" : "pump run by Geyserwise";
    const color = p.status === "Overheat" || p.status === "Offline" || p.status === "No sensor" ? "var(--c-warn)" : p.frost ? "var(--c-load)" : p.on ? "var(--c-solar)" : "var(--muted)";
    const el = this.shadowRoot.getElementById("coll");
    this._setHTML(el, `<div class="coll">
      <div class="loop" aria-label="Collector ${col === null ? "unknown" : Math.round(col) + " degrees"}, tank ${tank === null ? "unknown" : Math.round(tank) + " degrees"}">
        <div class="node"><div class="muted small">Collector</div><div class="val">${col === null ? "–" : col.toFixed(0) + "°C"}</div></div>
        <div class="flow ${p.on ? "on" : ""}" title="${p.on ? "Pump running" : "Pump off"}"></div>
        <div class="node"><div class="muted small">${num(L.tank_bottom_temp) !== null ? "Tank bottom" : "Tank"}</div><div class="val">${tank === null ? "–" : tank.toFixed(0) + "°C"}</div></div>
      </div>
      <div><div class="muted small">Difference</div><div style="font-size:22px;font-variant-numeric:tabular-nums">${dt === null ? "–" : (dt > 0 ? "+" : "") + dt.toFixed(0) + "°C"}</div>
        ${shelly ? `<div class="muted small">starts at +${s.settings.pump_dt_on}°C</div>` : ""}</div>
      <div><span class="badge ${p.on ? "pulse" : ""}" style="--bc:${color}"><span class="dot"></span>Pump · ${esc(p.status || "–")}</span>
        <div class="muted small" style="margin-top:6px">${esc(p.reason || "")}</div></div>
      ${shelly ? `<div class="pmodes" role="group" aria-label="Pump mode">${[["auto", "Auto"], ["on", "On"], ["off", "Off"]].map(([m, l]) =>
        `<button class="chip" data-pump="${m}" aria-pressed="${s.pump_mode === m}">${l}</button>`).join("")}</div>` : ""}
    </div>`);
  }

  /* ----------------------------------------------------------- schedules */
  _markDirty() { this._dirty = true; this._toggleSaveBar(); this._setMsg(""); }
  _toggleSaveBar() { const b = this.shadowRoot.getElementById("savebar"); if (b) b.hidden = !this._dirty; }
  _setMsg(text, kind = "") { const m = this.shadowRoot.getElementById("savemsg"); if (m) { m.textContent = text; m.className = `msg ${kind}`; } }

  _renderSchedules() {
    const el = this.shadowRoot.getElementById("scheds"); if (!el || !this._draft) return;
    const hasTemp = this._snap.features.temp;
    const list = this._draft.schedules;
    if (!list.length) { el.innerHTML = `<div class="muted small" style="padding:8px 0">No heating times. The geyser will only heat on spare solar or when you press Boost.</div>`; return; }
    el.innerHTML = list.map((sc, i) => `
      <div class="sched" data-i="${i}">
        <label class="switch" title="Enabled"><input type="checkbox" data-k="enabled" ${sc.enabled ? "checked" : ""} aria-label="Enable heating time ${i + 1}"><span></span></label>
        <div class="times">
          <input type="time" data-k="start" value="${esc(sc.start)}" aria-label="Start"> <span class="muted">to</span>
          <input type="time" data-k="end" value="${esc(sc.end)}" aria-label="End">
          ${hasTemp ? `<span class="muted small">heat to</span><input type="number" data-k="target" min="30" max="75" step="1" value="${sc.target}" aria-label="Target temperature"><span class="muted small">°C</span>` : ""}
          <button class="iconbtn" data-del title="Remove" aria-label="Remove heating time"><ha-icon icon="mdi:delete-outline"></ha-icon></button>
        </div>
        <div class="days">${DAYS.map((d, di) => `<button data-day="${di}" aria-pressed="${sc.days.includes(di)}">${d}</button>`).join("")}</div>
      </div>`).join("");
    el.querySelectorAll(".sched").forEach((row) => {
      const sc = list[Number(row.dataset.i)];
      row.querySelectorAll("input").forEach((inp) => {
        const update = () => {
          const k = inp.dataset.k;
          if (k === "target" && inp.value === "") return; // still typing
          sc[k] = k === "enabled" ? inp.checked : k === "target" ? Number(inp.value) : inp.value;
          this._markDirty();
        };
        inp.addEventListener("input", update);
        inp.addEventListener("change", update);
      });
      row.querySelectorAll("[data-day]").forEach((b) => b.addEventListener("click", () => {
        const d = Number(b.dataset.day);
        sc.days = sc.days.includes(d) ? sc.days.filter((x) => x !== d) : [...sc.days, d].sort();
        b.setAttribute("aria-pressed", sc.days.includes(d));
        this._markDirty();
      }));
      row.querySelector("[data-del]").addEventListener("click", () => { list.splice(Number(row.dataset.i), 1); this._markDirty(); this._renderSchedules(); });
    });
  }

  _field(key, label, hint, unit, opts = {}) {
    const v = this._draft[key];
    if (opts.bool) {
      return `<div class="field"><label for="f-${key}">${label}${hint ? `<span class="hint">${hint}</span>` : ""}</label>
        <span class="ctl"><span class="switch"><input id="f-${key}" type="checkbox" data-f="${key}" ${v ? "checked" : ""}><span></span></span></span></div>`;
    }
    return `<div class="field"><label for="f-${key}">${label}${hint ? `<span class="hint">${hint}</span>` : ""}</label>
      <span class="ctl"><input id="f-${key}" type="number" data-f="${key}" value="${v}" min="${opts.min ?? 0}" max="${opts.max ?? 99999}" step="${opts.step ?? 1}">${unit}</span></div>`;
  }

  _bindFields(el) {
    el.querySelectorAll("[data-f]").forEach((inp) => {
      const update = () => {
        if (inp.type !== "checkbox" && inp.value === "") return; // still typing
        this._draft[inp.dataset.f] = inp.type === "checkbox" ? inp.checked : Number(inp.value);
        this._markDirty();
      };
      inp.addEventListener("input", update);
      inp.addEventListener("change", update);
    });
  }

  _renderSmart() {
    const el = this.shadowRoot.getElementById("smart"); if (!el || !this._draft) return;
    const t = this._snap.features.temp;
    el.innerHTML = [
      this._field("solar_enabled", "Heat with spare solar", "Uses free solar when the house doesn't need it, or when the battery is full", "", { bool: true }),
      t ? this._field("solar_target_temp", "Solar heats up to", "Store extra heat when the energy is free", "°C", { min: 30, max: 75 }) : "",
      this._snap.features.collector && this._snap.features.collector !== "none"
        ? this._field("collector_priority", "Let the solar collector heat first", "During heating times the element waits while the collector is hot enough to reach the target", "", { bool: true }) : "",
      this._field("boost_minutes", "Boost length", "", "min", { min: 5, max: 480, step: 5 }),
      t ? this._field("boost_temp", "Boost heats up to", "", "°C", { min: 30, max: 75 }) : "",
    ].join("");
    this._bindFields(el);
  }

  _renderInstaller() {
    const card = this.shadowRoot.getElementById("installer"); if (!card) return;
    card.hidden = !this._isAdmin;
    if (!this._isAdmin || !this._draft) return;
    const t = this._snap.features.temp, b = this._snap.features.battery;
    const el = this.shadowRoot.getElementById("inst");
    el.innerHTML = `<div class="cols2"><div class="form">
        ${this._field("geyser_rated_w", "Element rating", "Used to estimate power if there's no meter", "W", { min: 500, max: 6000, step: 50 })}
        ${this._field("surplus_on_w", "Start on spare solar above", "", "W", { min: 0, max: 10000, step: 50 })}
        ${this._field("surplus_off_w", "Keep going while spare solar above", "", "W", { min: 0, max: 10000, step: 50 })}
        ${b ? this._field("soc_full_on", "Battery full: start at", "Victron/Sunsynk throttle solar when full", "%", { min: 50, max: 100 }) : ""}
        ${b ? this._field("soc_full_off", "Battery full: stop below", "", "%", { min: 40, max: 100 }) : ""}
        ${b ? this._field("max_battery_discharge_w", "Allowed battery draw while solar heating", "", "W", { min: 0, max: 5000, step: 50 }) : ""}
      </div><div class="form">
        ${b ? this._field("min_soc", "Never heat from battery below", "Auto and Boost", "%", { min: 0, max: 100 }) : ""}
        ${b ? this._field("outage_min_soc", "Grid down: schedules need battery above", "", "%", { min: 0, max: 100 }) : ""}
        ${this._field("schedules_need_grid", "Grid down: skip schedules completely", "Only solar heating during load-shedding", "", { bool: true })}
        ${t ? this._field("target_temp", "Default schedule target", "", "°C", { min: 30, max: 75 }) : ""}
        ${t ? this._field("max_temp", "Safety limit (all modes)", "", "°C", { min: 40, max: 80 }) : ""}
        ${t ? this._field("hysteresis", "Re-heat after dropping", "", "°C", { min: 1, max: 15 }) : ""}
        ${this._field("min_switch_seconds", "Minimum time between switching", "Protects the relay and element", "s", { min: 30, max: 1800, step: 10 })}
      </div></div>
      ${this._snap.features.collector === "shelly" ? `<h2 style="margin-top:20px">Collector pump</h2><div class="cols2"><div class="form">
        ${this._field("pump_dt_on", "Start pump when collector is hotter by", "", "°C", { min: 2, max: 30 })}
        ${this._field("pump_dt_off", "Stop pump when difference drops to", "", "°C", { min: 0, max: 20 })}
        ${this._field("pump_min_run_seconds", "Minimum pump run time", "", "s", { min: 0, max: 900, step: 10 })}
      </div><div class="form">
        ${this._field("pump_tank_max", "Stop pumping when tank reaches", "", "°C", { min: 40, max: 95 })}
        ${this._field("collector_max", "Collector overheat cut-out", "Pump restarts 10°C below this", "°C", { min: 80, max: 180 })}
        ${this._field("frost_enabled", "Frost protection", "Runs the pump near freezing – direct (open-loop) systems only", "", { bool: true })}
        ${this._field("frost_temp", "Frost protection below", "", "°C", { min: 0, max: 10 })}
      </div></div>` : ""}
      <details style="margin-top:12px"><summary>Live sensor check (use this to verify sign conventions)</summary><div class="rawgrid" id="raw"></div>
      <p class="muted small">Battery should be positive while charging, grid positive while importing. If not, flip the sign options in Settings → Devices &amp; services → Hamlet Geyser → Configure.</p></details>`;
    this._bindFields(el);
    this._renderRaw();
  }

  _renderRaw() {
    const el = this.shadowRoot.getElementById("raw"); if (!el || !this._snap) return;
    const L = this._snap.live || {};
    const fmt = (v, u) => (v === null || v === undefined ? "not mapped / unavailable" : `${Math.round(v * 10) / 10} ${u}`);
    const rows = [
      ["Solar", fmt(L.solar_w, "W")], ["House load", fmt(L.load_w, "W")], ["Geyser", fmt(L.geyser_w, "W")],
      ["Battery SoC", fmt(L.battery_soc, "%")], ["Battery (+ charging)", fmt(L.battery_w, "W")],
      ["Grid (+ importing)", fmt(L.grid_w, "W")], ["Grid available", L.grid_available === null || L.grid_available === undefined ? "not mapped" : L.grid_available ? "yes" : "no"],
      ...(L.grid_status_raw ? [["  read from", L.grid_status_raw]] : []),
      ["Water temperature", fmt(L.temp, "°C")], ["Spare solar", fmt(L.surplus_w, "W")],
      ["Relay", L.is_on === null || L.is_on === undefined ? "unavailable" : L.is_on ? "on" : "off"],
      ...(this._snap.features.collector && this._snap.features.collector !== "none" ? [
        ["Collector", fmt(L.collector_temp, "°C")], ["Tank bottom", fmt(L.tank_bottom_temp, "°C")],
        ["Pump", L.pump_on === null || L.pump_on === undefined ? "not mapped / unavailable" : L.pump_on ? "on" : "off"]] : []),
    ];
    el.innerHTML = rows.map(([a, b]) => `<span class="muted">${a}</span><span>${esc(b)}</span>`).join("");
  }

  async _save() {
    const btn = this.shadowRoot.getElementById("save");
    btn.disabled = true;
    const settings = this._isAdmin ? this._draft : Object.fromEntries(
      ["target_temp", "solar_target_temp", "boost_temp", "boost_minutes", "solar_enabled", "collector_priority", "schedules"].map((k) => [k, this._draft[k]]));
    try {
      const snap = await this._hass.callWS({ type: `${DOMAIN}/save_settings`, entry_id: this._entryId, settings });
      this._dirty = false;
      this._shownSettings = null; // force the forms to show what was saved
      if (this.shadowRoot.activeElement) this.shadowRoot.activeElement.blur();
      this._apply(snap);
      this._toggleSaveBar();
    } catch (e) {
      this._setMsg(e.message || "Could not save", "err");
    } finally { btn.disabled = false; }
  }
}

if (!customElements.get("hamlet-geyser-panel")) customElements.define("hamlet-geyser-panel", HamletGeyserPanel);

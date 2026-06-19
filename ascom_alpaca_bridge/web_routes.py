from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .config import AppConfig


def create_web_router(config: AppConfig) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return _page(config)

    return router


def _page(config: AppConfig) -> str:
    title = "ASCOM Alpaca Bridge"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #eef3f8;
      --panel: #ffffff;
      --panel-soft: #f8fafc;
      --text: #18202a;
      --muted: #647084;
      --muted-soft: #8a96a8;
      --line: #d8dee8;
      --line-soft: #e8edf4;
      --accent: #2563eb;
      --accent-strong: #1d4ed8;
      --danger: #b42318;
      --ok: #087443;
      --warn: #a15c07;
      --shadow: 0 12px 28px rgba(24, 32, 42, 0.07);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      line-height: 1.45;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.92);
      backdrop-filter: blur(10px);
      position: sticky;
      top: 0;
      z-index: 5;
    }}
    .wrap {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }}
    .top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 20px 0;
    }}
    h1 {{
      margin: 0;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .subtitle {{
      margin-top: 4px;
      color: var(--muted);
      font-size: 14px;
    }}
    main {{
      padding: 24px 0 40px;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 0 22px;
    }}
    .status-line {{
      color: var(--muted);
      min-height: 22px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      align-items: flex-start;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-width: 0;
      overflow: hidden;
      box-shadow: var(--shadow);
    }}
    .card-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px 12px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #ffffff 0%, #f9fbfd 100%);
    }}
    .card-title {{
      min-width: 0;
    }}
    .card h2 {{
      margin: 0;
      font-size: 17px;
      letter-spacing: 0;
    }}
    .card-subtitle {{
      margin-top: 3px;
      color: var(--muted);
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 100%;
    }}
    .doc-link {{
      display: inline-flex;
      align-items: center;
      width: fit-content;
      margin-top: 6px;
      color: var(--accent);
      font-size: 13px;
      text-decoration: none;
      border-bottom: 1px solid transparent;
    }}
    .doc-link:hover {{
      border-bottom-color: var(--accent);
    }}
    .pill {{
      border-radius: 999px;
      border: 1px solid var(--line);
      padding: 3px 9px;
      font-size: 12px;
      color: var(--muted);
      white-space: nowrap;
    }}
    .pill.ok {{ color: var(--ok); border-color: #b9e6cf; background: #effaf5; }}
    .pill.err {{ color: var(--danger); border-color: #f3c5c1; background: #fff4f2; }}
    .pill.warn {{ color: var(--warn); border-color: #f5d59b; background: #fff8eb; }}
    .body {{
      padding: 14px 16px 16px;
    }}
    .device-meta {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 12px;
      min-width: 0;
    }}
    .endpoint {{
      overflow-wrap: anywhere;
    }}
    details.device-details {{
      border: 1px solid var(--line-soft);
      border-radius: 7px;
      background: var(--panel-soft);
      margin-bottom: 14px;
      overflow: hidden;
    }}
    details.device-details summary {{
      cursor: pointer;
      color: var(--muted);
      padding: 8px 10px;
      font-size: 13px;
      user-select: none;
    }}
    details.device-details dl {{
      padding: 0 10px 10px;
      margin: 0;
    }}
    .status-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }}
    .metric {{
      border: 1px solid var(--line-soft);
      border-radius: 7px;
      background: var(--panel-soft);
      padding: 9px 10px;
      min-width: 0;
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.25;
      margin-bottom: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .metric-value {{
      color: var(--text);
      font-weight: 650;
      font-size: 16px;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }}
    .secondary-section {{
      margin-bottom: 14px;
      border-top: 1px solid var(--line-soft);
      padding-top: 12px;
    }}
    .section-title {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0;
      margin: 0 0 8px;
    }}
    dl {{
      display: grid;
      grid-template-columns: 128px minmax(0, 1fr);
      gap: 8px 10px;
      margin: 0 0 14px;
    }}
    dt {{
      color: var(--muted);
      min-width: 0;
    }}
    dd {{
      margin: 0;
      min-width: 0;
      overflow-wrap: anywhere;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }}
    .control-stack {{
      display: grid;
      gap: 10px;
    }}
    .control-group {{
      border: 1px solid var(--line-soft);
      border-radius: 7px;
      background: #fff;
      padding: 10px;
    }}
    .control-group h3 {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      margin: 0 0 8px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    button {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      border-radius: 6px;
      min-height: 38px;
      padding: 0 14px;
      cursor: pointer;
      font: inherit;
      touch-action: manipulation;
    }}
    button:hover {{ background: #f8fafc; }}
    button.primary {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }}
    button.primary:hover {{ background: var(--accent-strong); }}
    button:disabled {{
      cursor: default;
      opacity: 0.55;
    }}
    input {{
      width: 112px;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 9px;
      font: inherit;
      background: #fff;
    }}
    select {{
      min-width: 144px;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 9px;
      font: inherit;
      background: #fff;
    }}
    .field {{
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }}
    .field label {{
      color: var(--muted);
    }}
    .slew-pad {{
      display: grid;
      grid-template-columns: 56px 56px 56px;
      grid-template-rows: 44px 44px 44px;
      gap: 8px;
      align-items: stretch;
      justify-content: start;
      margin-top: 10px;
    }}
    .slew-pad button {{
      min-height: 44px;
      padding: 0;
      font-weight: 700;
      font-size: 20px;
    }}
    .slew-up {{ grid-column: 2; grid-row: 1; }}
    .slew-left {{ grid-column: 1; grid-row: 2; }}
    .slew-stop {{ grid-column: 2; grid-row: 2; }}
    .slew-right {{ grid-column: 3; grid-row: 2; }}
    .slew-down {{ grid-column: 2; grid-row: 3; }}
    .slew-stop {{
      border-color: #fecaca;
      background: #fef2f2;
      color: var(--danger);
    }}
    .error {{
      color: var(--danger);
      overflow-wrap: anywhere;
    }}
    .muted {{
      color: var(--muted);
    }}
    .image-preview {{
      display: grid;
      place-items: center;
      min-height: 180px;
      margin-top: 12px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #111827;
      overflow: hidden;
    }}
    .image-preview img {{
      display: block;
      max-width: 100%;
      max-height: 360px;
      width: auto;
      height: auto;
      image-rendering: pixelated;
    }}
    .image-preview span {{
      color: #cbd5e1;
      padding: 16px;
      text-align: center;
    }}
    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 560px) {{
      .wrap {{ width: min(100% - 20px, 1180px); }}
      .top {{ align-items: flex-start; flex-direction: column; }}
      .toolbar {{ align-items: flex-start; flex-direction: column; }}
      .status-grid {{ grid-template-columns: 1fr; }}
      dl {{ grid-template-columns: 104px minmax(0, 1fr); }}
      h1 {{ font-size: 21px; }}
      button {{ min-height: 42px; }}
      input, select {{ width: 100%; min-width: 0; }}
      .field {{
        display: grid;
        grid-template-columns: minmax(80px, 0.45fr) minmax(0, 1fr);
      }}
      .field button {{
        grid-column: 2;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap top">
      <div>
        <h1>{title}</h1>
        <div class="subtitle" id="serverMeta">127.0.0.1:{config.server.port}</div>
      </div>
      <button class="primary" id="refreshButton" type="button">刷新</button>
    </div>
  </header>
  <main class="wrap">
    <div class="toolbar">
      <div class="status-line" id="message">正在读取状态...</div>
      <div class="status-line" id="updated"></div>
    </div>
    <section class="grid" id="devices"></section>
  </main>
  <script>
    const endpoints = {{
      Telescope: ["connected", "rightascension", "declination", "tracking", "slewing", "atpark"],
      Dome: ["connected", "azimuth", "altitude", "shutterstatus", "slaved", "slewing", "atpark"],
      Focuser: ["connected", "position", "ismoving", "temperature", "tempcomp", "maxstep"],
      Camera: ["connected", "camerastate", "imageready", "ccdtemperature", "cooleron", "coolerpower", "percentcompleted", "cameraxsize", "cameraysize", "startx", "starty", "numx", "numy", "binx", "biny"]
    }};
    let configuredDevicesCache = [];

    const stateLabels = {{
      shutterstatus: {{
        0: "Open",
        1: "Closed",
        2: "Opening",
        3: "Closing",
        4: "Error"
      }},
      camerastate: {{
        0: "Idle",
        1: "Waiting",
        2: "Exposing",
        3: "Reading",
        4: "Download",
        5: "Error"
      }}
    }};

    const labels = {{
      connected: "Connected",
      rightascension: "RA",
      declination: "DEC",
      tracking: "Tracking",
      slewing: "Slewing",
      atpark: "At Park",
      azimuth: "Azimuth",
      altitude: "Altitude",
      shutterstatus: "Shutter",
      slaved: "Slaved",
      position: "Position",
      ismoving: "Moving",
      temperature: "Temp",
      tempcomp: "TempComp",
      maxstep: "Max Step",
      camerastate: "State",
      imageready: "Image Ready",
      ccdtemperature: "CCD Temp",
      cooleron: "Cooler",
      coolerpower: "Cooler Power",
      percentcompleted: "Progress",
      cameraxsize: "Camera X",
      cameraysize: "Camera Y",
      startx: "Start X",
      starty: "Start Y",
      numx: "Num X",
      numy: "Num Y",
      binx: "Bin X",
      biny: "Bin Y"
    }};

    const primaryFields = {{
      Telescope: ["rightascension", "declination", "tracking", "slewing", "atpark"],
      Dome: ["azimuth", "shutterstatus", "slaved", "slewing", "atpark"],
      Focuser: ["position", "ismoving", "temperature", "tempcomp", "maxstep"],
      Camera: ["camerastate", "imageready", "ccdtemperature", "cooleron", "coolerpower", "percentcompleted"]
    }};

    const secondaryFields = {{
      Camera: ["cameraxsize", "cameraysize", "startx", "starty", "numx", "numy", "binx", "biny"]
    }};

    const documentLinks = {{
      Telescope: {{
        label: "Link to Alpaca Telescope API document",
        url: "https://ascom-standards.org/alpyca/alpaca.telescope.html"
      }},
      Dome: {{
        label: "Link to Alpaca Dome API document",
        url: "https://ascom-standards.org/alpyca/alpaca.dome.html#alpaca.dome.Dome"
      }},
      Focuser: {{
        label: "Link to Alpaca Focuser API document",
        url: "https://ascom-standards.org/alpyca/alpaca.focuser.html#alpaca.focuser.Focuser"
      }},
      Camera: {{
        label: "Link to Alpaca Camera API document",
        url: "https://ascom-standards.org/alpyca/alpaca.camera.html#alpaca.camera.Camera"
      }}
    }};

    function basePath(device) {{
      return `/api/v1/${{device.DeviceType.toLowerCase()}}/${{device.DeviceNumber}}`;
    }}

    async function getJson(url) {{
      const response = await fetch(url, {{ cache: "no-store" }});
      if (!response.ok) throw new Error(`${{response.status}} ${{response.statusText}}`);
      return response.json();
    }}

    async function getJsonWithTimeout(url, timeoutMs = 900) {{
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {{
        const response = await fetch(url, {{ cache: "no-store", signal: controller.signal }});
        if (!response.ok) throw new Error(`${{response.status}} ${{response.statusText}}`);
        return response.json();
      }} finally {{
        clearTimeout(timer);
      }}
    }}

    async function putForm(url, data = {{}}) {{
      const body = new URLSearchParams({{ ClientTransactionID: String(Date.now() % 1000000), ...data }});
      const response = await fetch(url, {{
        method: "PUT",
        headers: {{ "Content-Type": "application/x-www-form-urlencoded" }},
        body
      }});
      if (!response.ok) throw new Error(`${{response.status}} ${{response.statusText}}`);
      const payload = await response.json();
      if (payload.ErrorNumber && payload.ErrorNumber !== 0) {{
        throw new Error(payload.ErrorMessage || `Alpaca error ${{payload.ErrorNumber}}`);
      }}
      return payload;
    }}

    function formatValue(key, value) {{
      if (value === null || value === undefined) return "n/a";
      if (value && typeof value === "object" && value.kind === "unsupported") return "Unsupported";
      if (value && typeof value === "object" && value.kind === "busy") return "Busy";
      if (value && typeof value === "object" && value.kind === "unavailable") return "Unavailable";
      if (value && typeof value === "object") return JSON.stringify(value);
      if (key === "connected" || key === "tracking" || key === "slewing" || key === "slaved" || key === "ismoving" || key === "tempcomp" || key === "atpark" || key === "imageready" || key === "cooleron") {{
        return value ? "Yes" : "No";
      }}
      if (key === "shutterstatus") return stateLabels.shutterstatus[value] || String(value);
      if (key === "camerastate") return stateLabels.camerastate[value] || String(value);
      if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(4).replace(/0+$/, "").replace(/\\.$/, "");
      return String(value);
    }}

    function labelFor(key) {{
      return labels[key] || key;
    }}

    function documentLink(deviceType) {{
      const link = documentLinks[deviceType];
      if (!link) return "";
      return `<a class="doc-link" href="${{link.url}}" target="_blank" rel="noopener noreferrer">${{link.label}}</a>`;
    }}

    function isUnsupportedPayload(payload) {{
      const message = String(payload.ErrorMessage || "").toLowerCase();
      return payload.ErrorNumber === 0x400 && (
        message.includes("not implemented") ||
        message.includes("not supported") ||
        message.includes("property unknown") ||
        message.includes("未实现") ||
        message.includes("不支持")
      );
    }}

    function fieldValue(payload) {{
      if (payload.ErrorNumber === 0) return payload.Value;
      if (isUnsupportedPayload(payload)) return {{ kind: "unsupported" }};
      if (payload.ErrorNumber === 0x408) return {{ kind: "busy" }};
      if (payload.ErrorNumber === 0x407) return {{ kind: "unavailable" }};
      return `Error: ${{payload.ErrorMessage}}`;
    }}

    function isBusyValue(value) {{
      return value && typeof value === "object" && value.kind === "busy";
    }}

    function cardId(device) {{
      return `device-card-${{device.DeviceType.toLowerCase()}}-${{device.DeviceNumber}}`;
    }}

    function deviceInfoFromPath(path) {{
      const match = String(path || "").match(/\\/api\\/v1\\/([^/]+)\\/(\\d+)/);
      if (!match) return null;
      return {{ type: match[1].toLowerCase(), number: Number(match[2]) }};
    }}

    async function optionalAlpacaValue(url, fallback = null) {{
      try {{
        const payload = await getJsonWithTimeout(url);
        if (payload.ErrorNumber === 0) return payload.Value;
      }} catch (_error) {{
        return fallback;
      }}
      return fallback;
    }}

    function normalizeAxisRanges(value) {{
      const ranges = Array.isArray(value) ? value : [];
      return ranges
        .map((range) => {{
          const minimum = Number(range && (range.Minimum ?? range.minimum));
          const maximum = Number(range && (range.Maximum ?? range.maximum));
          if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || maximum <= 0) return null;
          return {{ minimum: Math.max(0, minimum), maximum }};
        }})
        .filter(Boolean);
    }}

    function telescopeRateOptions(controls) {{
      const axis0 = normalizeAxisRanges(controls.axis0Rates);
      const axis1 = normalizeAxisRanges(controls.axis1Rates);
      const allRanges = [...axis0, ...axis1];
      if (!allRanges.length) return [0.5, 1, 2, 4];
      const minimum = Math.min(...allRanges.map((range) => range.minimum));
      const maximum = Math.max(...allRanges.map((range) => range.maximum));
      const slow = minimum > 0 ? minimum : maximum / 10;
      const medium = (slow + maximum) / 2;
      return [...new Set([slow, medium, maximum].map((value) => Number(value.toPrecision(4))))]
        .filter((value) => Number.isFinite(value) && value > 0);
    }}

    function rateLabel(value, index) {{
      const labels = ["Slow", "Medium", "Fast"];
      const prefix = labels[index] || "Rate";
      return `${{prefix}} (${{formatValue("rate", value)}})`;
    }}

    function selectedTelescopeRate(deviceNumber, options) {{
      const saved = localStorage.getItem(`telescopeMoveRate:${{deviceNumber}}`);
      if (saved && options.some((value) => String(value) === saved)) return saved;
      return String(options[0] ?? 1);
    }}

    async function readDevice(device) {{
      const path = basePath(device);
      const fields = endpoints[device.DeviceType] || ["connected"];
      const values = {{}};
      const connectedField = fields.includes("connected") ? "connected" : null;
      if (connectedField) {{
        try {{
          const payload = await getJsonWithTimeout(`${{path}}/connected`);
          values.connected = fieldValue(payload);
        }} catch (error) {{
          values.connected = {{ kind: "busy" }};
        }}
      }}
      if (values.connected === false) {{
        for (const field of fields) {{
          if (field !== "connected") values[field] = "Connect first";
        }}
        return values;
      }}
      await Promise.all(fields.map(async (field) => {{
        if (field === "connected" && connectedField) return;
        try {{
          const payload = await getJsonWithTimeout(`${{path}}/${{field}}`);
          values[field] = fieldValue(payload);
        }} catch (error) {{
          values[field] = {{ kind: "busy" }};
        }}
      }}));
      if (device.DeviceType === "Telescope") {{
        values.__telescopeControls = {{
          canPark: await optionalAlpacaValue(`${{path}}/canpark`, false),
          canUnpark: await optionalAlpacaValue(`${{path}}/canunpark`, false),
          canFindHome: await optionalAlpacaValue(`${{path}}/canfindhome`, false),
          canSetTracking: await optionalAlpacaValue(`${{path}}/cansettracking`, false),
          axis0Rates: await optionalAlpacaValue(`${{path}}/axisrates?Axis=0`, []),
          axis1Rates: await optionalAlpacaValue(`${{path}}/axisrates?Axis=1`, []),
        }};
      }}
      return values;
    }}

    function row(label, value, key = "") {{
      const rendered = value && typeof value === "object" && value.kind === "unsupported"
        ? `<span class="muted">Unsupported</span>`
        : value && typeof value === "object" && value.kind === "busy"
          ? `<span class="muted">Busy</span>`
        : value && typeof value === "object" && value.kind === "unavailable"
          ? `<span class="muted">Unavailable</span>`
        : String(value).startsWith("Error:")
          ? `<span class="error">${{value}}</span>`
          : formatValue(key, value);
      return `<dt>${{label}}</dt><dd>${{rendered}}</dd>`;
    }}

    function metric(key, value) {{
      const rendered = value && typeof value === "object" && value.kind === "unsupported"
        ? `<span class="muted">Unsupported</span>`
        : value && typeof value === "object" && value.kind === "busy"
          ? `<span class="muted">Busy</span>`
        : value && typeof value === "object" && value.kind === "unavailable"
          ? `<span class="muted">Unavailable</span>`
        : String(value).startsWith("Error:")
          ? `<span class="error">${{value}}</span>`
          : formatValue(key, value);
      return `
        <div class="metric">
          <div class="metric-label">${{labelFor(key)}}</div>
          <div class="metric-value">${{rendered}}</div>
        </div>`;
    }}

    function actionGroup(title, content) {{
      if (!content || !String(content).trim()) return "";
      return `<section class="control-group"><h3>${{title}}</h3>${{content}}</section>`;
    }}

    function commonActions(device) {{
      const path = basePath(device);
      return actionGroup("Connection", `
        <div class="actions">
          <button type="button" data-put="${{path}}/connected" data-field="Connected" data-value="true">Connect</button>
          <button type="button" data-put="${{path}}/connected" data-field="Connected" data-value="false">Disconnect</button>
        </div>`);
    }}

    function telescopeActions(device, values) {{
      const path = basePath(device);
      const controls = values.__telescopeControls || {{}};
      const stateButtons = [];
      if (controls.canPark) stateButtons.push(`<button type="button" data-long-put="${{path}}/park" data-long-label="Park">Park</button>`);
      if (controls.canUnpark) stateButtons.push(`<button type="button" data-long-put="${{path}}/unpark" data-long-label="Unpark">Unpark</button>`);
      if (controls.canFindHome) stateButtons.push(`<button type="button" data-long-put="${{path}}/findhome" data-long-label="Home">Home</button>`);
      if (controls.canSetTracking) {{
        stateButtons.push(`<button type="button" data-put="${{path}}/tracking" data-field="Tracking" data-value="true">Tracking Yes</button>`);
        stateButtons.push(`<button type="button" data-put="${{path}}/tracking" data-field="Tracking" data-value="false">Tracking No</button>`);
      }}
      const rateOptions = telescopeRateOptions(controls);
      const selectedRate = selectedTelescopeRate(device.DeviceNumber, rateOptions);
      const rateOptionHtml = rateOptions
        .map((value, index) => `<option value="${{value}}"${{String(value) === selectedRate ? " selected" : ""}}>${{rateLabel(value, index)}}</option>`)
        .join("");
      return `<div class="control-stack">${{commonActions(device)}}
        ${{stateButtons.length ? actionGroup("Mount State", `<div class="actions">${{stateButtons.join("")}}</div>`) : ""}}
        ${{actionGroup("Manual Motion", `
        <div class="field">
          <label for="telescopeMoveRate${{device.DeviceNumber}}">Move rate</label>
          <select id="telescopeMoveRate${{device.DeviceNumber}}" data-rate-store="telescopeMoveRate:${{device.DeviceNumber}}">${{rateOptionHtml}}</select>
        </div>
        <div class="slew-pad">
          <button class="slew-up" type="button" data-move-axis="${{path}}" data-axis="1" data-sign="1" data-rate-input="telescopeMoveRate${{device.DeviceNumber}}" title="Move axis 1 positive">↑</button>
          <button class="slew-left" type="button" data-move-axis="${{path}}" data-axis="0" data-sign="-1" data-rate-input="telescopeMoveRate${{device.DeviceNumber}}" title="Move axis 0 negative">←</button>
          <button class="slew-stop" type="button" data-stop-axis="${{path}}" title="Stop axis motion">■</button>
          <button class="slew-right" type="button" data-move-axis="${{path}}" data-axis="0" data-sign="1" data-rate-input="telescopeMoveRate${{device.DeviceNumber}}" title="Move axis 0 positive">→</button>
          <button class="slew-down" type="button" data-move-axis="${{path}}" data-axis="1" data-sign="-1" data-rate-input="telescopeMoveRate${{device.DeviceNumber}}" title="Move axis 1 negative">↓</button>
        </div>`)}}</div>`;
    }}

    function domeActions(device) {{
      const path = basePath(device);
      return `<div class="control-stack">${{commonActions(device)}}
        ${{actionGroup("Motion", `
        <div class="field">
          <label for="domeAzimuth">Azimuth</label>
          <input id="domeAzimuth" type="number" step="0.1" inputmode="decimal" placeholder="180">
          <button type="button" data-put="${{path}}/slewtoazimuth" data-input="domeAzimuth" data-field="Azimuth">Slew</button>
        </div>
        <div class="actions">
          <button type="button" data-put="${{path}}/openshutter">Open</button>
          <button type="button" data-put="${{path}}/closeshutter">Close</button>
          <button type="button" data-put="${{path}}/abortslew">Abort</button>
        </div>`)}}</div>`;
    }}

    function focuserActions(device) {{
      const path = basePath(device);
      return `<div class="control-stack">${{commonActions(device)}}
        ${{actionGroup("Focus", `
        <div class="field">
          <label for="focuserPosition">Position</label>
          <input id="focuserPosition" type="number" step="1" inputmode="numeric" placeholder="12000">
          <button type="button" data-put="${{path}}/move" data-input="focuserPosition" data-field="Position">Move</button>
        </div>
        <div class="actions">
          <button type="button" data-put="${{path}}/halt">Halt</button>
          <button type="button" data-put="${{path}}/tempcomp" data-field="TempComp" data-value="true">TempComp On</button>
          <button type="button" data-put="${{path}}/tempcomp" data-field="TempComp" data-value="false">TempComp Off</button>
        </div>`)}}</div>`;
    }}

    function inputPlaceholder(values, key, fallback) {{
      const value = values[key];
      if (value === null || value === undefined) return fallback;
      if (value && typeof value === "object") return fallback;
      if (String(value).startsWith("Error:")) return fallback;
      return formatValue(key, value);
    }}

    function cameraActions(device, values = {{}}) {{
      const path = basePath(device);
      return `<div class="control-stack">${{commonActions(device)}}
        ${{actionGroup("Cooling", `
        <div class="field">
          <label for="cameraTemp">Set Temp</label>
          <input id="cameraTemp" type="number" step="0.1" inputmode="decimal" placeholder="-10">
          <button type="button" data-put="${{path}}/setccdtemperature" data-input="cameraTemp" data-field="SetCCDTemperature">Set</button>
        </div>
        <div class="actions">
          <button type="button" data-put="${{path}}/cooleron" data-field="CoolerOn" data-value="true">Cooler On</button>
          <button type="button" data-put="${{path}}/cooleron" data-field="CoolerOn" data-value="false">Cooler Off</button>
        </div>`) }}
        ${{actionGroup("Sensor Parameters", `
        <div class="field">
          <label for="cameraGain">Gain</label>
          <input id="cameraGain" type="number" step="1" inputmode="numeric" placeholder="100">
          <button type="button" data-put="${{path}}/gain" data-input="cameraGain" data-field="Gain">Set</button>
          <label for="cameraOffset">Offset</label>
          <input id="cameraOffset" type="number" step="1" inputmode="numeric" placeholder="10">
          <button type="button" data-put="${{path}}/offset" data-input="cameraOffset" data-field="Offset">Set</button>
        </div>
        <div class="field">
          <label for="cameraBinX">BinX</label>
          <input id="cameraBinX" type="number" step="1" inputmode="numeric" placeholder="${{inputPlaceholder(values, "binx", "1")}}">
          <button type="button" data-put="${{path}}/binx" data-input="cameraBinX" data-field="BinX">Set</button>
          <label for="cameraBinY">BinY</label>
          <input id="cameraBinY" type="number" step="1" inputmode="numeric" placeholder="${{inputPlaceholder(values, "biny", "1")}}">
          <button type="button" data-put="${{path}}/biny" data-input="cameraBinY" data-field="BinY">Set</button>
        </div>
        <div class="field">
          <label for="cameraStartX">StartX</label>
          <input id="cameraStartX" type="number" step="1" inputmode="numeric" placeholder="${{inputPlaceholder(values, "startx", "0")}}">
          <button type="button" data-put="${{path}}/startx" data-input="cameraStartX" data-field="StartX">Set</button>
          <label for="cameraStartY">StartY</label>
          <input id="cameraStartY" type="number" step="1" inputmode="numeric" placeholder="${{inputPlaceholder(values, "starty", "0")}}">
          <button type="button" data-put="${{path}}/starty" data-input="cameraStartY" data-field="StartY">Set</button>
        </div>
        <div class="field">
          <label for="cameraNumX">NumX</label>
          <input id="cameraNumX" type="number" step="1" inputmode="numeric" placeholder="${{inputPlaceholder(values, "numx", "Camera X")}}">
          <button type="button" data-put="${{path}}/numx" data-input="cameraNumX" data-field="NumX">Set</button>
          <label for="cameraNumY">NumY</label>
          <input id="cameraNumY" type="number" step="1" inputmode="numeric" placeholder="${{inputPlaceholder(values, "numy", "Camera Y")}}">
          <button type="button" data-put="${{path}}/numy" data-input="cameraNumY" data-field="NumY">Set</button>
        </div>
        `)}}
        ${{actionGroup("Exposure", `
        <div class="field">
          <label for="cameraDuration">Duration</label>
          <input id="cameraDuration" type="number" step="0.1" inputmode="decimal" value="1" placeholder="1">
          <button type="button" data-put="${{path}}/startexposure" data-input="cameraDuration" data-field="Duration" data-extra-field="Light" data-extra-value="true">Light</button>
          <button type="button" data-put="${{path}}/startexposure" data-input="cameraDuration" data-field="Duration" data-extra-field="Light" data-extra-value="false">Dark</button>
          <button type="button" data-expose-preview="${{path}}" data-input="cameraDuration" data-preview-target="cameraPreview${{device.DeviceNumber}}" data-light="true">Expose + Preview</button>
        </div>
        <div class="actions">
          <button type="button" data-put="${{path}}/stopexposure">Stop Exposure</button>
          <button type="button" data-put="${{path}}/abortexposure">Abort Exposure</button>
        </div>`) }}
        ${{actionGroup("Preview and Download", `
        <div class="actions">
          <button type="button" data-preview-image="${{path}}/imagearray.png" data-preview-target="cameraPreview${{device.DeviceNumber}}">Preview PNG</button>
          <button type="button" data-preview-image="${{path}}/imagearray.raw.png" data-preview-target="cameraPreview${{device.DeviceNumber}}">Raw Preview</button>
          <button type="button" data-download-image="${{path}}/imagearray.png">Download PNG</button>
          <button type="button" data-download-image="${{path}}/imagearray.raw.png">Download Raw PNG</button>
          <button type="button" data-download-file="${{path}}/imagearray.fits" data-file-extension="fits" data-content-type="application/fits">Download FITS</button>
        </div>
        <div class="image-preview" id="cameraPreview${{device.DeviceNumber}}">
          <span>No preview loaded</span>
        </div>
        <div class="status-line">Preview PNG crops empty borders; Raw Preview keeps the full frame. Both use automatic stretch.</div>`)}}</div>`;
    }}

    function actionsFor(device, values) {{
      if (device.DeviceType === "Dome") return domeActions(device);
      if (device.DeviceType === "Focuser") return focuserActions(device);
      if (device.DeviceType === "Camera") return cameraActions(device, values);
      return telescopeActions(device, values);
    }}

    function card(device, values) {{
      const connected = values.connected === true;
      const badgeClass = connected ? "ok" : (values.connected === false || isBusyValue(values.connected)) ? "warn" : "err";
      const primary = primaryFields[device.DeviceType] || Object.keys(values).filter((key) => !key.startsWith("__") && key !== "connected");
      const secondary = secondaryFields[device.DeviceType] || [];
      const metricHtml = primary
        .filter((key) => Object.prototype.hasOwnProperty.call(values, key))
        .map((key) => metric(key, values[key]))
        .join("");
      const secondaryHtml = secondary
        .filter((key) => Object.prototype.hasOwnProperty.call(values, key))
        .map((key) => row(labelFor(key), values[key], key))
        .join("");
      const detailRows = [
        row("Type", device.DeviceType),
        row("Number", device.DeviceNumber),
        row("Name", device.DeviceName),
        row("Unique ID", device.UniqueID),
        row("URL", basePath(device))
      ].join("");
      return `
        <article class="card" id="${{cardId(device)}}">
          <div class="card-head">
            <div class="card-title">
              <h2>${{device.DeviceType}}</h2>
              <div class="card-subtitle">${{device.DeviceName || "ASCOM Device"}}</div>
              ${{documentLink(device.DeviceType)}}
            </div>
            <span class="pill ${{badgeClass}}">${{formatValue("connected", values.connected)}}</span>
          </div>
          <div class="body">
            <div class="device-meta">
              <span>Device #${{device.DeviceNumber}}</span>
              <span class="endpoint">${{basePath(device)}}</span>
            </div>
            <div class="status-grid">${{metricHtml || metric("connected", values.connected)}}</div>
            ${{secondaryHtml ? `<section class="secondary-section"><h3 class="section-title">Sensor / ROI</h3><dl>${{secondaryHtml}}</dl></section>` : ""}}
            <details class="device-details">
              <summary>Endpoint details</summary>
              <dl>${{detailRows}}</dl>
            </details>
            ${{actionsFor(device, values)}}
          </div>
        </article>`;
    }}

    async function refresh() {{
      const message = document.getElementById("message");
      const updated = document.getElementById("updated");
      const devicesElement = document.getElementById("devices");
      message.textContent = "正在读取状态...";
      try {{
        const configured = await getJson("/management/v1/configureddevices");
        const devices = configured.Value || [];
        configuredDevicesCache = devices;
        const cards = [];
        const readResults = await Promise.all(devices.map(async (device) => [device, await readDevice(device)]));
        for (const [device, values] of readResults) {{
          cards.push(card(device, values));
        }}
        devicesElement.innerHTML = cards.join("");
        message.textContent = devices.length ? `已发现 ${{devices.length}} 个设备` : "未配置设备";
        updated.textContent = new Date().toLocaleString();
      }} catch (error) {{
        message.innerHTML = `<span class="error">${{error.message}}</span>`;
      }}
    }}

    async function refreshDeviceByPath(path) {{
      const info = deviceInfoFromPath(path);
      if (!info) {{
        await refresh();
        return;
      }}
      const devices = configuredDevicesCache || [];
      const device = devices.find((item) =>
        item.DeviceType.toLowerCase() === info.type && Number(item.DeviceNumber) === info.number
      );
      if (!device) {{
        await refresh();
        return;
      }}
      const values = await readDevice(device);
      const current = document.getElementById(cardId(device));
      if (current) {{
        current.outerHTML = card(device, values);
      }} else {{
        await refresh();
      }}
      document.getElementById("updated").textContent = new Date().toLocaleString();
    }}

    function sleep(ms) {{
      return new Promise((resolve) => setTimeout(resolve, ms));
    }}

    async function loadCameraPreview(url, target, successMessage = "相机预览已更新") {{
      if (!target) throw new Error("Preview target is missing");
      target.innerHTML = "<span>Loading preview...</span>";
      const response = await fetch(`${{url}}?t=${{Date.now()}}`, {{ cache: "no-store" }});
      if (!response.ok) throw new Error(`${{response.status}} ${{response.statusText}}`);
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("image/png")) {{
        const payload = await response.json();
        throw new Error(payload.ErrorMessage || "Preview failed");
      }}
      if (target.dataset.objectUrl) {{
        URL.revokeObjectURL(target.dataset.objectUrl);
      }}
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      target.dataset.objectUrl = objectUrl;
      target.innerHTML = `<img src="${{objectUrl}}" alt="Camera preview">`;
      document.getElementById("message").textContent = successMessage;
    }}

    async function readAlpacaValue(url) {{
      const payload = await getJson(url);
      if (payload.ErrorNumber && payload.ErrorNumber !== 0) {{
        throw new Error(payload.ErrorMessage || `Alpaca error ${{payload.ErrorNumber}}`);
      }}
      return payload.Value;
    }}

    async function waitForCameraImageReady(path, target) {{
      const startedAt = Date.now();
      while (Date.now() - startedAt < 120000) {{
        const ready = await readAlpacaValue(`${{path}}/imageready`);
        const percent = await readAlpacaValue(`${{path}}/percentcompleted`).catch(() => null);
        const state = await readAlpacaValue(`${{path}}/camerastate`).catch(() => null);
        const progress = percent === null ? "" : ` ${{percent}}%`;
        const stateText = state === null ? "" : ` / ${{formatValue("camerastate", state)}}`;
        if (target) target.innerHTML = `<span>Exposing${{progress}}${{stateText}}</span>`;
        document.getElementById("message").textContent = `等待相机曝光完成${{progress}}`;
        if (ready) return;
        await sleep(500);
      }}
      throw new Error("等待 ImageReady 超时");
    }}

    document.addEventListener("click", async (event) => {{
      const longPutButton = event.target.closest("button[data-long-put]");
      if (longPutButton) {{
        longPutButton.disabled = true;
        const label = longPutButton.getAttribute("data-long-label") || "Command";
        try {{
          await putForm(longPutButton.getAttribute("data-long-put"));
          document.getElementById("message").textContent = `${{label}} command sent`;
        }} catch (error) {{
          document.getElementById("message").innerHTML = `<span class="error">${{error.message}}</span>`;
        }} finally {{
          longPutButton.disabled = false;
        }}
        return;
      }}

      const moveAxisButton = event.target.closest("button[data-move-axis]");
      if (moveAxisButton) {{
        const input = document.getElementById(moveAxisButton.getAttribute("data-rate-input"));
        const rawRate = input && input.value ? input.value : "1";
        const rate = Number(rawRate);
        if (!Number.isFinite(rate) || rate <= 0) {{
          document.getElementById("message").innerHTML = `<span class="error">请输入有效的转向速度</span>`;
          return;
        }}
        const signedRate = rate * Number(moveAxisButton.getAttribute("data-sign") || "1");
        moveAxisButton.disabled = true;
        try {{
          await putForm(`${{moveAxisButton.getAttribute("data-move-axis")}}/moveaxis`, {{
            Axis: moveAxisButton.getAttribute("data-axis"),
            Rate: String(signedRate)
          }});
          document.getElementById("message").textContent = "Telescope move command sent";
        }} catch (error) {{
          document.getElementById("message").innerHTML = `<span class="error">${{error.message}}</span>`;
        }} finally {{
          moveAxisButton.disabled = false;
        }}
        return;
      }}

      const stopAxisButton = event.target.closest("button[data-stop-axis]");
      if (stopAxisButton) {{
        const path = stopAxisButton.getAttribute("data-stop-axis");
        stopAxisButton.disabled = true;
        try {{
          await putForm(`${{path}}/moveaxis`, {{ Axis: "0", Rate: "0" }});
          await putForm(`${{path}}/moveaxis`, {{ Axis: "1", Rate: "0" }});
          await putForm(`${{path}}/abortslew`).catch(() => null);
          document.getElementById("message").textContent = "Telescope stop command sent";
        }} catch (error) {{
          document.getElementById("message").innerHTML = `<span class="error">${{error.message}}</span>`;
        }} finally {{
          stopAxisButton.disabled = false;
        }}
        return;
      }}

      const exposePreviewButton = event.target.closest("button[data-expose-preview]");
      if (exposePreviewButton) {{
        const input = document.getElementById(exposePreviewButton.getAttribute("data-input"));
        const duration = input && input.value ? input.value : "1";
        if (input && !input.value) input.value = duration;
        const path = exposePreviewButton.getAttribute("data-expose-preview");
        const targetId = exposePreviewButton.getAttribute("data-preview-target");
        const target = document.getElementById(targetId);
        exposePreviewButton.disabled = true;
        try {{
          if (target) target.innerHTML = "<span>Starting exposure...</span>";
          document.getElementById("message").textContent = `正在启动 ${{duration}} 秒曝光...`;
          await putForm(`${{path}}/startexposure`, {{
            Duration: duration,
            Light: exposePreviewButton.getAttribute("data-light") || "true"
          }});
          await waitForCameraImageReady(path, target);
          await loadCameraPreview(`${{path}}/imagearray.png`, document.getElementById(targetId), "曝光完成，预览已更新");
        }} catch (error) {{
          if (target) target.innerHTML = `<span>${{error.message}}</span>`;
          document.getElementById("message").innerHTML = `<span class="error">${{error.message}}</span>`;
        }} finally {{
          exposePreviewButton.disabled = false;
        }}
        return;
      }}

      const previewButton = event.target.closest("button[data-preview-image]");
      if (previewButton) {{
        const target = document.getElementById(previewButton.getAttribute("data-preview-target"));
        previewButton.disabled = true;
        try {{
          await loadCameraPreview(previewButton.getAttribute("data-preview-image"), target);
        }} catch (error) {{
          if (target) target.innerHTML = `<span>${{error.message}}</span>`;
          document.getElementById("message").innerHTML = `<span class="error">${{error.message}}</span>`;
        }} finally {{
          previewButton.disabled = false;
        }}
        return;
      }}

      const downloadButton = event.target.closest("button[data-download-image]");
      if (downloadButton) {{
        downloadButton.disabled = true;
        try {{
          const url = `${{downloadButton.getAttribute("data-download-image")}}?t=${{Date.now()}}`;
          const response = await fetch(url, {{ cache: "no-store" }});
          if (!response.ok) throw new Error(`${{response.status}} ${{response.statusText}}`);
          const contentType = response.headers.get("content-type") || "";
          if (!contentType.includes("image/png")) {{
            const payload = await response.json();
            throw new Error(payload.ErrorMessage || "Download failed");
          }}
          const blob = await response.blob();
          const objectUrl = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = objectUrl;
          anchor.download = `camera-${{new Date().toISOString().replace(/[:.]/g, "-")}}.png`;
          document.body.appendChild(anchor);
          anchor.click();
          anchor.remove();
          URL.revokeObjectURL(objectUrl);
          document.getElementById("message").textContent = "PNG 已准备下载";
        }} catch (error) {{
          document.getElementById("message").innerHTML = `<span class="error">${{error.message}}</span>`;
        }} finally {{
          downloadButton.disabled = false;
        }}
        return;
      }}

      const downloadFileButton = event.target.closest("button[data-download-file]");
      if (downloadFileButton) {{
        downloadFileButton.disabled = true;
        try {{
          const url = `${{downloadFileButton.getAttribute("data-download-file")}}?t=${{Date.now()}}`;
          const response = await fetch(url, {{ cache: "no-store" }});
          if (!response.ok) throw new Error(`${{response.status}} ${{response.statusText}}`);
          const expectedType = downloadFileButton.getAttribute("data-content-type") || "";
          const contentType = response.headers.get("content-type") || "";
          if (expectedType && !contentType.includes(expectedType)) {{
            const payload = await response.json();
            throw new Error(payload.ErrorMessage || "Download failed");
          }}
          const extension = downloadFileButton.getAttribute("data-file-extension") || "dat";
          const blob = await response.blob();
          const objectUrl = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = objectUrl;
          anchor.download = `camera-${{new Date().toISOString().replace(/[:.]/g, "-")}}.${{extension}}`;
          document.body.appendChild(anchor);
          anchor.click();
          anchor.remove();
          URL.revokeObjectURL(objectUrl);
          document.getElementById("message").textContent = `${{extension.toUpperCase()}} 已准备下载`;
        }} catch (error) {{
          document.getElementById("message").innerHTML = `<span class="error">${{error.message}}</span>`;
        }} finally {{
          downloadFileButton.disabled = false;
        }}
        return;
      }}

      const button = event.target.closest("button[data-put]");
      if (!button) return;
      const data = {{}};
      const inputId = button.getAttribute("data-input");
      const field = button.getAttribute("data-field");
      const fixedValue = button.getAttribute("data-value");
      if (field) {{
        const input = inputId ? document.getElementById(inputId) : null;
        const value = fixedValue ?? (input ? input.value : "");
        if (input && value === "") {{
          document.getElementById("message").innerHTML = `<span class="error">请输入 ${{field}}</span>`;
          return;
        }}
        data[field] = value;
      }}
      const extraField = button.getAttribute("data-extra-field");
      const extraValue = button.getAttribute("data-extra-value");
      if (extraField) {{
        data[extraField] = extraValue ?? "";
      }}
      button.disabled = true;
      try {{
        const path = button.getAttribute("data-put");
        await putForm(path, data);
        await refreshDeviceByPath(path);
      }} catch (error) {{
        document.getElementById("message").innerHTML = `<span class="error">${{error.message}}</span>`;
      }} finally {{
        button.disabled = false;
      }}
    }});

    document.addEventListener("change", (event) => {{
      const select = event.target.closest("select[data-rate-store]");
      if (!select) return;
      localStorage.setItem(select.getAttribute("data-rate-store"), select.value);
    }});

    document.getElementById("refreshButton").addEventListener("click", refresh);
    refresh();
  </script>
</body>
</html>"""

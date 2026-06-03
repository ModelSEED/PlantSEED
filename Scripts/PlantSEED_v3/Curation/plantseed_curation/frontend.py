"""Embedded HTML/CSS/JS for the Curation Tool Dashboard.

These three strings are pure UI data; the dashboard serves them as static
assets from /, /static/app.css, and /static/app.js.
"""

INDEX_CSS = r"""
/* ============================================================================
 * PlantSEED Curation Dashboard - v4
 * App-shell layout: sidebar + full-height main. Dense panels. Theme toggle.
 * ============================================================================ */

:root {
  /* Dark (default) — GitHub Primer dark tokens */
  --bg:           #0d1117;
  --bg-elev:      #010409;
  --sidebar:      #010409;
  --panel:        #161b22;
  --panel-2:      #1c2128;
  --panel-3:      #21262d;
  --border:       #30363d;
  --border-soft:  #21262d;
  --text:         #e6edf3;
  --text-2:       #c9d1d9;
  --muted:        #8b949e;
  --dim:          #6e7681;
  --accent:       #2f81f7;
  --accent-fg:    #ffffff;
  --accent-bg:    rgba(47, 129, 247, 0.15);
  --accent-soft:  rgba(47, 129, 247, 0.30);
  --good:         #3fb950;
  --good-bg:      rgba(63, 185, 80, 0.15);
  --warn:         #d29922;
  --warn-bg:      rgba(210, 153, 34, 0.15);
  --bad:          #f85149;
  --bad-bg:       rgba(248, 81, 73, 0.15);
  --new:          #bc8cff;
  --new-bg:       rgba(188, 140, 255, 0.15);
  --code-bg:      #0d1117;
  --hover:        #1c2128;
  --selected-bg:  rgba(47, 129, 247, 0.12);
  --diff-add-bg:  rgba(63, 185, 80, 0.10);
  --diff-rem-bg:  rgba(248, 81, 73, 0.10);
  --diff-add-fg:  #7ee787;
  --diff-rem-fg:  #ff9591;
}

[data-theme="light"] {
  --bg:           #f6f8fa;
  --bg-elev:      #ffffff;
  --sidebar:      #ffffff;
  --panel:        #ffffff;
  --panel-2:      #f6f8fa;
  --panel-3:      #eaeef2;
  --border:       #d0d7de;
  --border-soft:  #d8dee4;
  --text:         #1f2328;
  --text-2:       #424a53;
  --muted:        #59636e;
  --dim:          #818b98;
  --accent:       #0969da;
  --accent-fg:    #ffffff;
  --accent-bg:    rgba(9, 105, 218, 0.10);
  --accent-soft:  rgba(9, 105, 218, 0.25);
  --good:         #1a7f37;
  --good-bg:      rgba(26, 127, 55, 0.08);
  --warn:         #9a6700;
  --warn-bg:      rgba(154, 103, 0, 0.08);
  --bad:          #cf222e;
  --bad-bg:       rgba(207, 34, 46, 0.08);
  --new:          #8250df;
  --new-bg:       rgba(130, 80, 223, 0.08);
  --code-bg:      #f6f8fa;
  --hover:        #f3f4f6;
  --selected-bg:  rgba(9, 105, 218, 0.08);
  --diff-add-bg:  rgba(26, 127, 55, 0.08);
  --diff-rem-bg:  rgba(207, 34, 46, 0.08);
  --diff-add-fg:  #1a7f37;
  --diff-rem-fg:  #cf222e;
}

* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", Roboto, sans-serif;
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  overflow: hidden;
  /* Default render scale: 100% browser zoom felt too small for the user.
     1.15 reproduces their preferred 115% manual zoom. */
  zoom: 1.15;
}
code, pre, .mono { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }

/* ============================================================================
 * App shell
 * ============================================================================ */
.app {
  display: grid;
  grid-template-columns: 188px 1fr;
  height: 100vh;
  overflow: hidden;
}

/* Sidebar -------------------------------------------------------------------- */
.sidebar {
  background: var(--sidebar);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow: hidden;
}
.sidebar .brand {
  padding: 12px 16px 10px;
  font-size: 14px; font-weight: 600;
  letter-spacing: -0.1px;
  border-bottom: 1px solid var(--border-soft);
}
.sidebar .brand .accent { color: var(--accent); }
.sidebar nav {
  flex: 1; display: flex; flex-direction: column;
  padding: 8px 6px;
  overflow-y: auto;
}
.sidebar nav button {
  background: none; border: 0;
  padding: 7px 12px;
  margin: 1px 0;
  color: var(--muted);
  cursor: pointer; text-align: left;
  font-size: 13px; font-family: inherit;
  border-radius: 5px;
  display: flex; align-items: center; justify-content: space-between;
}
.sidebar nav button:hover { color: var(--text); background: var(--hover); }
.sidebar nav button.active {
  color: var(--text); background: var(--accent-bg);
  font-weight: 500;
}
.sidebar nav button .label-count {
  background: var(--panel-3); color: var(--text);
  font-size: 10.5px; font-weight: 600;
  padding: 1px 6px; border-radius: 10px;
  display: none;
}
.sidebar nav button .label-count.visible { display: inline-block; }
.sidebar .footer {
  border-top: 1px solid var(--border-soft);
  padding: 10px 12px;
  display: flex; flex-direction: column; gap: 6px;
}
.sidebar .footer .row {
  display: flex; align-items: center; justify-content: space-between; gap: 6px;
  font-size: 12px;
}
.sidebar .footer .user-block {
  font-size: 12px; color: var(--muted);
}
.sidebar .footer .user-block .username {
  color: var(--text); font-weight: 500; cursor: pointer;
}
.sidebar .footer .user-block .username:hover { text-decoration: underline; color: var(--accent); }
.theme-toggle {
  background: none; border: 1px solid var(--border);
  color: var(--muted); border-radius: 4px;
  padding: 3px 8px; font-size: 11px; cursor: pointer;
  font-family: inherit;
}
.theme-toggle:hover { color: var(--text); border-color: var(--accent); }

/* Main column ---------------------------------------------------------------- */
.main {
  display: flex; flex-direction: column;
  overflow: hidden;
  min-width: 0;
}
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
  background: var(--panel);
  height: 42px;
  flex-shrink: 0;
}
.topbar .section-title {
  font-size: 14px; font-weight: 600; color: var(--text);
}
.topbar .status {
  display: flex; align-items: center; gap: 14px;
  font-size: 12px; color: var(--muted);
}
.topbar .status .item { display: flex; gap: 5px; align-items: center; }
.topbar .status .item .label { color: var(--dim); }
.topbar .status .item .value { color: var(--text); }
.topbar .status .item .value.muted { color: var(--muted); }
.topbar .status .reload {
  background: none; border: 0; color: var(--accent);
  cursor: pointer; font-size: 12px; padding: 0;
  font-family: inherit;
}
.topbar .status .reload:hover { text-decoration: underline; }

.content {
  flex: 1;
  padding: 12px;
  overflow: hidden;
  min-height: 0;
}
.section {
  display: none; height: 100%; min-height: 0;
  flex-direction: column;
}
.section.active { display: flex; }

/* ============================================================================
 * Grid layouts per section — each panel fills available height & scrolls.
 * ============================================================================ */
.grid-curate {
  display: grid;
  grid-template-columns: minmax(260px, 0.85fr) minmax(320px, 1fr) minmax(320px, 1.15fr);
  gap: 12px;
  flex: 1; min-height: 0;
}
.grid-files {
  display: grid;
  grid-template-columns: minmax(220px, 0.6fr) minmax(360px, 1.6fr);
  gap: 12px;
  flex: 1; min-height: 0;
}
.grid-browse {
  display: grid;
  grid-template-columns: minmax(220px, 0.55fr) minmax(280px, 1.1fr) minmax(280px, 1.1fr);
  gap: 12px;
  flex: 1; min-height: 0;
}
.col-stack { display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.col-stack > .panel { min-height: 0; }
.flex-1 { flex: 1; min-height: 0; }

/* ============================================================================
 * Panel
 * ============================================================================ */
.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  min-height: 0;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.panel-scroll { overflow-y: auto; flex: 1; min-height: 0; margin: 0 -4px; padding: 0 4px; }
.panel.scroll { overflow-y: auto; }
.panel > h2 {
  margin: 0 0 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .6px;
  display: flex; justify-content: space-between; align-items: center;
  flex-shrink: 0;
}
.panel > h2 .right {
  font-size: 11px; text-transform: none; letter-spacing: 0;
  color: var(--dim); font-weight: 400;
}
.panel > h2 .right.actions { display: flex; gap: 4px; }

/* ============================================================================
 * Form elements
 * ============================================================================ */
input[type=text], input[type=search], input[type=number], select, textarea {
  background: var(--code-bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 5px 8px;
  width: 100%;
  font-family: inherit;
  font-size: 12.5px;
}
input:focus, select:focus, textarea:focus {
  outline: 0;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-bg);
}
input.invalid, select.invalid {
  border-color: var(--bad);
  box-shadow: 0 0 0 3px var(--bad-bg);
}
textarea { min-height: 140px; resize: vertical; font-family: ui-monospace, monospace; }
label {
  display: block;
  font-size: 11px; color: var(--muted);
  margin: 8px 0 3px;
  text-transform: uppercase; letter-spacing: .4px;
  font-weight: 600;
}
label:first-child { margin-top: 0; }
.field-error { color: var(--bad); font-size: 11.5px; margin-top: 3px; }
.help {
  color: var(--muted); font-size: 11.5px;
  margin-top: 4px; line-height: 1.4;
}
.help code {
  background: var(--panel-3); color: var(--accent);
  padding: 0 4px; border-radius: 3px; font-size: 11px;
}
.subtle { color: var(--muted); font-size: 12px; }
.dim    { color: var(--dim); }

/* ============================================================================
 * Buttons
 * ============================================================================ */
button.btn {
  background: var(--panel-3);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 4px 12px;
  font-size: 12.5px; cursor: pointer;
  font-family: inherit;
  display: inline-flex; align-items: center; gap: 5px;
}
button.btn:hover:not(:disabled) { background: var(--hover); border-color: var(--border); }
button.btn:disabled { opacity: 0.5; cursor: not-allowed; }
button.btn.primary {
  background: var(--accent); color: var(--accent-fg);
  border-color: var(--accent); font-weight: 500;
}
button.btn.primary:hover:not(:disabled) { filter: brightness(1.1); }
button.btn.danger { color: var(--bad); }
button.btn.danger:hover:not(:disabled) { background: var(--bad-bg); border-color: var(--bad); }
button.btn.warn   { color: var(--warn); }
button.btn.warn:hover:not(:disabled)   { background: var(--warn-bg); border-color: var(--warn); }
button.btn.good   { color: var(--good); }
button.btn.good:hover:not(:disabled)   { background: var(--good-bg); border-color: var(--good); }
button.btn.small  { padding: 3px 8px; font-size: 11.5px; }
button.btn.tiny   { padding: 1px 6px; font-size: 11px; }
button.btn.link   {
  background: none; border: 0; color: var(--accent);
  padding: 0; cursor: pointer; font-family: inherit;
  text-decoration: none;
}
button.btn.link:hover { text-decoration: underline; }

.toolbar { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.toolbar-spacer { flex: 1; }

/* ============================================================================
 * Tags
 * ============================================================================ */
.tag {
  display: inline-block; padding: 1px 7px;
  border-radius: 12px; font-size: 10.5px; font-weight: 500;
  background: var(--panel-3); color: var(--muted);
  border: 1px solid var(--border);
  vertical-align: middle;
}
.tag.plant   { color: var(--good); border-color: var(--good); background: var(--good-bg); }
.tag.expasy  { color: var(--warn); border-color: var(--warn); background: var(--warn-bg); }
.tag.new     { color: var(--new);  border-color: var(--new);  background: var(--new-bg); }
.tag.action { font-weight: 600; letter-spacing: .3px; }
.tag.ADD     { color: var(--good); border-color: var(--good); background: var(--good-bg); }
.tag.REMOVE  { color: var(--bad);  border-color: var(--bad);  background: var(--bad-bg); }
.tag.UPDATE  { color: var(--accent); border-color: var(--accent); background: var(--accent-bg); }
.tag.NEW     { color: var(--new);  border-color: var(--new);  background: var(--new-bg); }
.tag.REASSIGN { color: var(--accent); border-color: var(--accent); background: var(--accent-bg); }
.tag.CHANGE   { color: var(--accent); border-color: var(--accent); background: var(--accent-bg); }
.tag.ASSIGN   { color: var(--accent); border-color: var(--accent); background: var(--accent-bg); }
.tag.RELOCATE { color: var(--warn); border-color: var(--warn); background: var(--warn-bg); }

/* ============================================================================
 * Search results
 * ============================================================================ */
.results {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 5px;
  flex: 1; min-height: 0;
  overflow-y: auto;
}
.results .group-header {
  padding: 5px 10px;
  font-size: 10.5px; font-weight: 600;
  color: var(--muted);
  text-transform: uppercase; letter-spacing: .5px;
  border-bottom: 1px solid var(--border-soft);
  background: var(--panel-2);
  position: sticky; top: 0;
  z-index: 1;
}
.results .item {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 10px;
  font-size: 12.5px; cursor: pointer;
  border-bottom: 1px solid var(--border-soft);
}
.results .item:last-child { border-bottom: 0; }
.results .item:hover { background: var(--hover); }
.results .item.selected { background: var(--selected-bg); }
.results .item .name { flex: 1; word-break: break-word; min-width: 0; }
.results .item .meta { font-size: 11px; color: var(--muted); flex-shrink: 0; }
.results .item mark {
  background: var(--accent-soft); color: inherit;
  padding: 0 2px; border-radius: 2px;
}
.results .item .sub {
  display: block; font-size: 10.5px; color: var(--dim);
  font-family: ui-monospace, monospace; margin-top: 1px;
}
.results .empty { padding: 14px; text-align: center; color: var(--dim); font-style: italic; }

/* ============================================================================
 * Current-enzyme banner
 * ============================================================================ */
.current-enzyme {
  background: var(--accent-bg);
  border: 1px solid var(--accent-soft);
  border-radius: 5px;
  padding: 8px 10px;
  display: flex; align-items: center; gap: 10px;
  font-size: 12.5px;
  margin-bottom: 8px;
}
.current-enzyme .label {
  font-size: 10px; color: var(--accent);
  text-transform: uppercase; letter-spacing: .5px;
  font-weight: 700; flex-shrink: 0;
}
.current-enzyme .name {
  flex: 1; font-weight: 500; word-break: break-word; min-width: 0;
}

/* ============================================================================
 * Role card (current record + browse detail)
 * ============================================================================ */
.role-card {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 5px;
}
.role-card .field {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 4px 10px;
  padding: 5px 10px;
  border-bottom: 1px solid var(--border-soft);
  font-size: 12px;
  align-items: start;
}
.role-card .field:last-child { border-bottom: 0; }
.role-card .field .k {
  color: var(--muted);
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: .4px;
  font-weight: 600;
  padding-top: 1px;
}
.role-card .field .v {
  font-family: ui-monospace, monospace;
  word-break: break-word;
}
.role-card .field .v.empty {
  color: var(--dim);
  font-style: italic;
  font-family: inherit;
}
.role-card .field .v code {
  display: inline-block;
  background: var(--panel-3);
  color: var(--accent);
  padding: 1px 5px;
  border-radius: 3px;
  margin: 1px 3px 1px 0;
  font-size: 11px;
}
.role-card .field .v .obj-line {
  margin: 1px 0;
}

/* ============================================================================
 * Entry rows (ADD/REMOVE entries)
 * ============================================================================ */
.entry-row {
  display: flex; gap: 5px; margin-bottom: 4px; align-items: flex-start;
}
.entry-row > input, .entry-row > select { flex: 1; }
.entry-row .entry-extra-wrap {
  flex: 1; display: flex; gap: 4px;
}
.entry-row .entry-extra-wrap > * { flex: 1; }
.entry-row .rm-btn { flex: 0 0 auto; }

/* ============================================================================
 * Staging cards
 * ============================================================================ */
.staging-card {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px;
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 5px;
  margin-bottom: 4px;
  font-size: 12px;
}
.staging-card .num {
  color: var(--dim); width: 28px;
  font-family: ui-monospace, monospace; font-size: 11px;
  text-align: right; flex-shrink: 0;
}
.staging-card .body {
  flex: 1; min-width: 0;
  font-family: ui-monospace, monospace; word-break: break-all;
}
.staging-card .body .e { color: var(--accent); }
.staging-card .body .f { color: var(--accent); opacity: 0.85; }
.staging-card .body .v { color: var(--good); }
.staging-card .body .x { color: var(--warn); }
.staging-card .acts { display: flex; gap: 2px; flex-shrink: 0; }

/* ============================================================================
 * File editor table
 * ============================================================================ */
.editor-table {
  width: 100%; border-collapse: collapse; font-size: 12px;
}
.editor-table th, .editor-table td {
  text-align: left; padding: 4px 6px;
  border-bottom: 1px solid var(--border-soft);
}
.editor-table th {
  font-size: 10.5px; color: var(--muted);
  text-transform: uppercase; letter-spacing: .4px;
  font-weight: 600; background: var(--panel-2);
  position: sticky; top: 0;
}
.editor-table tr:hover td { background: var(--hover); }
.editor-table td input, .editor-table td select {
  padding: 3px 5px; font-size: 11.5px;
  background: var(--bg);
}
.editor-table .num {
  width: 32px; color: var(--dim);
  font-family: ui-monospace, monospace; font-size: 11px;
}

/* ============================================================================
 * Banners
 * ============================================================================ */
.banner {
  padding: 7px 10px;
  border-radius: 5px;
  margin-bottom: 8px;
  font-size: 12px;
  border-left: 3px solid;
  line-height: 1.45;
}
.banner.warn { background: var(--warn-bg); border-color: var(--warn); color: var(--warn); }
.banner.bad  { background: var(--bad-bg);  border-color: var(--bad);  color: var(--bad); }
.banner.good { background: var(--good-bg); border-color: var(--good); color: var(--good); }
.banner.info { background: var(--accent-bg); border-color: var(--accent); color: var(--accent); }
.banner b { color: inherit; }

/* ============================================================================
 * Lists in side panels
 * ============================================================================ */
.list-item {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 8px; border-radius: 4px; cursor: pointer;
  font-size: 12.5px;
  border: 1px solid transparent;
}
.list-item:hover { background: var(--hover); }
.list-item.selected {
  background: var(--selected-bg);
  border-color: var(--accent-soft);
}
.list-item .name { flex: 1; word-break: break-word; min-width: 0; }
.list-item .meta { font-size: 11px; color: var(--muted); flex-shrink: 0; }
.list-item .acts { display: flex; gap: 4px; flex-shrink: 0; }

/* ============================================================================
 * Browse facets — fill available height, scroll inside
 * ============================================================================ */
.facet-section { margin-bottom: 12px; }
.facet-section h4 {
  margin: 0 0 5px; font-size: 10.5px; color: var(--muted);
  text-transform: uppercase; letter-spacing: .4px; font-weight: 600;
}
.facet-options {
  display: flex; flex-wrap: wrap; gap: 3px;
  /* No max-height — the parent .panel handles scrolling */
}
.facet-chip {
  display: inline-block; padding: 2px 8px; font-size: 11px;
  background: var(--panel-2); border: 1px solid var(--border);
  border-radius: 10px; cursor: pointer;
  white-space: nowrap;
}
.facet-chip:hover { background: var(--hover); }
.facet-chip.active {
  background: var(--accent); color: var(--accent-fg);
  border-color: var(--accent); font-weight: 500;
}

/* ============================================================================
 * Compartment grid in help
 * ============================================================================ */
.compartment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 3px;
}
.compartment-chip {
  padding: 4px 8px; background: var(--panel-2);
  border: 1px solid var(--border); border-radius: 4px;
  font-size: 11.5px; font-family: ui-monospace, monospace;
}
.compartment-chip .id {
  color: var(--accent); font-weight: 700;
  display: inline-block; width: 18px;
}

/* ============================================================================
 * Diff cards (apply tab + preview)
 * ============================================================================ */
.diff-card {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 10px; margin-bottom: 8px;
}
.diff-card h4 {
  margin: 0 0 8px; font-size: 12.5px; font-weight: 500;
  word-break: break-word;
  display: flex; align-items: center; gap: 8px;
}
.diff-section { margin: 4px 0; }
.diff-section .field-name {
  font-size: 10.5px; color: var(--muted);
  margin-bottom: 2px;
  text-transform: uppercase; letter-spacing: .4px; font-weight: 600;
}
.diff-line {
  font-family: ui-monospace, monospace; font-size: 11.5px;
  padding: 2px 8px; border-left: 2px solid;
  white-space: pre-wrap; word-break: break-word;
  margin: 1px 0;
}
.diff-line.add { color: var(--diff-add-fg); background: var(--diff-add-bg); border-color: var(--good); }
.diff-line.rem { color: var(--diff-rem-fg); background: var(--diff-rem-bg); border-color: var(--bad); }

/* ============================================================================
 * Modal
 * ============================================================================ */
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.55);
  z-index: 100;
  display: flex; align-items: center; justify-content: center;
}
.modal {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  min-width: 380px; max-width: 90vw; max-height: 85vh;
  display: flex; flex-direction: column;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.modal .modal-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border-bottom: 1px solid var(--border);
}
.modal .modal-head h3 { margin: 0; font-size: 13px; font-weight: 600; }
.modal .modal-head button {
  background: none; border: 0; color: var(--muted);
  cursor: pointer; font-size: 18px; line-height: 1;
  padding: 0 4px;
}
.modal .modal-head button:hover { color: var(--text); }
.modal .modal-body { padding: 14px; overflow-y: auto; flex: 1; }
.modal .modal-foot {
  padding: 10px 14px; border-top: 1px solid var(--border);
  display: flex; gap: 6px; justify-content: flex-end;
}

/* ============================================================================
 * Toast
 * ============================================================================ */
.toast-stack {
  position: fixed; bottom: 14px; right: 14px; z-index: 200;
  display: flex; flex-direction: column-reverse; gap: 5px;
  max-width: 400px;
}
.toast {
  background: var(--panel);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  padding: 8px 12px; border-radius: 5px;
  font-size: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  transition: all .2s;
}
.toast.bad  { border-left-color: var(--bad); }
.toast.good { border-left-color: var(--good); }
.toast.warn { border-left-color: var(--warn); }

/* ============================================================================
 * Spinner & misc
 * ============================================================================ */
.spinner {
  display: inline-block; width: 10px; height: 10px;
  border: 1.5px solid var(--muted); border-top-color: transparent;
  border-radius: 50%; animation: spin .6s linear infinite;
  margin-right: 5px; vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

.empty { color: var(--dim); font-style: italic; padding: 14px; text-align: center; }
.empty-small { color: var(--dim); padding: 6px; text-align: center; font-size: 11.5px; }
hr.sep { border: 0; border-top: 1px solid var(--border-soft); margin: 10px 0; }
.flex-between { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
kbd {
  display: inline-block; background: var(--panel-3);
  border: 1px solid var(--border); border-bottom-width: 2px;
  border-radius: 3px; padding: 1px 5px;
  font-size: 10.5px; font-family: ui-monospace, monospace;
}

/* xref banner */
.xref-msg {
  font-size: 11px; color: var(--warn);
  background: var(--warn-bg); padding: 4px 7px;
  border-radius: 4px; margin-top: 3px;
  border-left: 2px solid var(--warn);
}
"""

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PlantSEED Curation</title>
<link rel="stylesheet" href="/static/app.css">
</head>
<body>

<div class="app">

  <!-- ====== SIDEBAR =================================================== -->
  <aside class="sidebar">
    <div class="brand">Plant<span class="accent">SEED</span> Curation</div>
    <nav id="sidebar-nav">
      <button data-tab="curate"  class="active">Curate</button>
      <button data-tab="staging">Staging  <span class="label-count" id="staging-count">0</span></button>
      <button data-tab="files">Files</button>
      <button data-tab="apply">Apply Updates</button>
      <button data-tab="browse">Browse DB</button>
      <button data-tab="help">Help</button>
    </nav>
    <div class="footer">
      <div class="user-block">
        <div class="row">
          <span class="dim">curator</span>
          <button class="theme-toggle" id="btn-theme" title="Toggle light/dark">dark</button>
        </div>
        <div class="username" id="user-text" title="Click to change">loading…</div>
      </div>
    </div>
  </aside>

  <!-- ====== MAIN ====================================================== -->
  <div class="main">

    <!-- Top bar -->
    <div class="topbar">
      <div class="section-title" id="section-title">Curate</div>
      <div class="status">
        <span class="item"><span class="label">file:</span>
          <span class="value muted" id="file-text">none</span></span>
        <span class="item"><span class="label">db:</span>
          <span class="value" id="db-text">0 roles</span></span>
        <span class="item"><span class="label">EC:</span>
          <span class="value muted" id="ec-text">loading…</span></span>
        <button class="reload" id="btn-reload">reload</button>
      </div>
    </div>

    <!-- Content area -->
    <div class="content">

      <!-- =========== CURATE ========================================= -->
      <section id="tab-curate" class="section active">
        <div class="grid-curate">

          <!-- Col 1: Find or current enzyme -->
          <div class="panel">
            <h2>Enzyme</h2>
            <div id="enzyme-picker" class="col-stack" style="flex:1;">
              <input type="search" id="search-input" autocomplete="off"
                     placeholder="Search by name, EC, or gene…">
              <div class="help">
                <kbd>↑↓</kbd> navigate, <kbd>Enter</kbd> select. Prefix:
                <code>ec:</code> <code>feature:</code> <code>rxn:</code>
                <code>subsystem:</code> <code>class:</code> <code>curator:</code>
              </div>
              <div id="results-list" class="results">
                <div class="empty">Type 2+ characters to search.</div>
              </div>
              <div class="toolbar">
                <button id="btn-novel" class="btn small">+ Novel enzyme</button>
                <span class="subtle" id="search-summary" style="margin-left:auto;"></span>
              </div>
            </div>
            <div id="enzyme-current" style="display:none;">
              <div class="current-enzyme">
                <span class="label">Working on</span>
                <span class="name" id="current-name"></span>
                <button class="btn small" id="btn-switch-enzyme">Switch</button>
              </div>
              <div id="current-warnings"></div>
              <div id="current-actions" class="col-stack" style="margin-top:8px;">
                <label>Action</label>
                <select id="action-select"></select>
                <div class="help" id="action-help"></div>
                <div id="action-body" style="margin-top:8px;"></div>
                <hr class="sep">
                <div class="toolbar">
                  <button id="btn-stage" class="btn primary">Stage row(s)</button>
                  <button id="btn-stage-preview" class="btn small">Refresh preview</button>
                </div>
                <span id="stage-status" class="subtle"></span>
              </div>
            </div>
          </div>

          <!-- Col 2: Role record -->
          <div class="panel">
            <h2>Current record</h2>
            <div class="panel-scroll">
              <div id="role-detail"><div class="empty">Pick an enzyme on the left.</div></div>
            </div>
          </div>

          <!-- Col 3: Live preview -->
          <div class="panel">
            <h2>Preview after staged + new rows</h2>
            <div class="panel-scroll">
              <div id="preview-area"><div class="empty">Fill the action form to see preview.</div></div>
            </div>
          </div>

        </div>
      </section>

      <!-- =========== STAGING ======================================== -->
      <section id="tab-staging" class="section">
        <div class="col-stack" style="flex:1;">
          <div class="panel" style="flex-shrink:0;">
            <h2 class="flex-between">
              <span>Staged rows <span class="dim" id="staging-count-2">(0)</span></span>
            </h2>
            <div class="toolbar">
              <button id="btn-staging-save"   class="btn primary">Append to current file</button>
              <button id="btn-staging-saveas" class="btn">Append to another file…</button>
              <button id="btn-staging-clear"  class="btn">Clear</button>
              <button id="btn-staging-copy"   class="btn">Copy TSV</button>
            </div>
          </div>
          <div class="panel" style="flex:1; min-height:0;">
            <div class="panel-scroll">
              <div id="staging-list"></div>
            </div>
          </div>
          <details style="background:var(--panel); border:1px solid var(--border); border-radius:6px; padding:8px 12px;">
            <summary class="subtle" style="cursor:pointer;">Raw TSV preview</summary>
            <pre id="staging-raw" class="mono" style="margin-top:6px; background:var(--code-bg); padding:8px; border-radius:4px; font-size:11.5px; max-height:200px; overflow:auto;"></pre>
          </details>
        </div>
      </section>

      <!-- =========== FILES ========================================== -->
      <section id="tab-files" class="section">
        <div class="grid-files">

          <!-- Left -->
          <div class="col-stack">
            <div class="panel" style="flex:1; min-height:0;">
              <h2 class="flex-between">
                <span>Your files</span>
                <button id="btn-new-file" class="btn small primary">+ New</button>
              </h2>
              <div class="panel-scroll">
                <div id="files-list"></div>
              </div>
            </div>
            <div class="panel" style="flex-shrink:0; max-height:35%;">
              <h2>Other curators</h2>
              <div class="panel-scroll">
                <div id="other-curators" class="subtle">none</div>
              </div>
            </div>
          </div>

          <!-- Right (editor) -->
          <div class="panel">
            <h2 class="flex-between">
              <span id="file-editor-title">No file open</span>
              <span class="right actions">
                <button id="btn-file-save"   class="btn small primary">Save</button>
                <button id="btn-file-apply"  class="btn small">Apply…</button>
                <button id="btn-file-delete" class="btn small danger">Delete</button>
              </span>
            </h2>
            <div class="subtle" id="file-editor-path" style="margin-bottom:8px;"></div>
            <div id="file-banner"></div>
            <div class="panel-scroll" style="flex:1;">
              <div id="file-rows"></div>
              <details style="margin-top:10px;">
                <summary class="subtle" style="cursor:pointer;">Raw editor (advanced)</summary>
                <textarea id="file-raw-editor" spellcheck="false" style="margin-top:6px; min-height:200px;"></textarea>
              </details>
            </div>
          </div>
        </div>
      </section>

      <!-- =========== APPLY ========================================== -->
      <section id="tab-apply" class="section">
        <div class="col-stack" style="flex:1;">
          <div class="panel" style="flex-shrink:0;">
            <h2>Apply TSV to PlantSEED_Roles.json</h2>
            <div class="help">
              Equivalent to <code>Update_Enzymes_in_PlantSEED.py</code>. Dry-run first to see the diff;
              the real run writes the JSON atomically.
            </div>
            <div style="display:grid; grid-template-columns: 200px 1fr; gap:8px; margin-top:10px; align-items:start;">
              <div>
                <label>Source</label>
                <select id="apply-source">
                  <option value="staging">Staged rows</option>
                  <option value="file">Saved file</option>
                  <option value="paste">Paste TSV</option>
                </select>
              </div>
              <div>
                <div id="apply-file-pick" style="display:none;">
                  <label>File</label>
                  <select id="apply-file-select"></select>
                </div>
                <div id="apply-paste" style="display:none;">
                  <label>TSV</label>
                  <textarea id="apply-paste-area" spellcheck="false" placeholder="Paste TSV rows…"></textarea>
                </div>
              </div>
            </div>
            <hr class="sep">
            <div class="toolbar">
              <button id="btn-apply-dry"  class="btn">Dry run</button>
              <button id="btn-apply-real" class="btn warn">Apply (write JSON)</button>
              <span id="apply-status" class="subtle" style="margin-left:auto;"></span>
            </div>
          </div>
          <div class="panel" style="flex:1; min-height:0;">
            <h2>Result</h2>
            <div class="panel-scroll">
              <div id="apply-result"><div class="empty">Run a dry-run or apply to see results.</div></div>
            </div>
          </div>
        </div>
      </section>

      <!-- =========== BROWSE ========================================= -->
      <section id="tab-browse" class="section">
        <div class="grid-browse">

          <!-- Facets (left, full height, scrolls) -->
          <div class="panel">
            <h2 class="flex-between">
              <span>Filters</span>
              <button id="btn-browse-clear" class="btn tiny">clear</button>
            </h2>
            <input type="search" id="browse-input" placeholder="Filter by name…" style="flex-shrink:0;">
            <div class="panel-scroll" style="margin-top:8px;">
              <div id="browse-facets"></div>
            </div>
          </div>

          <!-- Role list (middle, full height, scrolls) -->
          <div class="panel">
            <h2 class="flex-between"><span>Roles</span>
              <span class="dim" id="browse-count">0</span></h2>
            <div class="panel-scroll">
              <div id="browse-list"></div>
            </div>
          </div>

          <!-- Role detail (right) -->
          <div class="panel">
            <h2>Detail</h2>
            <div class="panel-scroll">
              <div id="browse-detail"><div class="empty">Click a role to view it.</div></div>
            </div>
          </div>

        </div>
      </section>

      <!-- =========== HELP =========================================== -->
      <section id="tab-help" class="section">
        <div class="panel scroll" style="flex:1;">
          <h2>Help &amp; reference</h2>
          <div class="panel-scroll">
            <h3 style="font-size:13px; margin-top:0;">Workflow</h3>
            <ol style="margin-top:4px;">
              <li><b>Curate</b> — search, pick an enzyme, choose an action, fill the form. Stage the row(s).</li>
              <li>After staging the form clears but the enzyme stays selected. Click <b>Switch</b> for a different one.</li>
              <li><b>Staging</b> — review/edit pending rows. <b>Append to current file</b> writes them to disk.</li>
              <li><b>Files</b> — open any of your TSV files. Edit row-by-row or in the raw editor.</li>
              <li><b>Apply Updates</b> — runs the equivalent of <code>Update_Enzymes_in_PlantSEED.py</code>. Shows per-role before/after diffs.</li>
            </ol>

            <h3 style="font-size:13px;">Search syntax</h3>
            <p>Plain text matches role names AND feature lists, so a gene id like <code>AT3G30775</code> surfaces its role(s). Prefix to scope:</p>
            <ul>
              <li><code>ec:1.1.1</code> — EC number</li>
              <li><code>feature:AT3G30775</code> — feature substring</li>
              <li><code>rxn:rxn00001</code> — reaction</li>
              <li><code>subsystem:fatty</code> — subsystem substring</li>
              <li><code>class:amino</code> — class substring</li>
              <li><code>curator:samseaver</code> — curator</li>
              <li><code>type:universal</code> — role type</li>
            </ul>

            <h3 style="font-size:13px;">Compartments (ModelSEED Plant)</h3>
            <p>When ADDing features or reactions the extra column is <b>optional</b>. Blank → compartment <code>c</code> (cytosol) with source <code>Assumed</code>.</p>
            <div id="help-compartments" class="compartment-grid"></div>

            <h3 style="font-size:13px;">Actions</h3>
            <div id="help-actions"></div>

            <h3 style="font-size:13px;">Keyboard shortcuts</h3>
            <ul>
              <li><kbd>/</kbd> focus search</li>
              <li><kbd>g</kbd> then <kbd>c/s/f/a/b/h</kbd> jump tabs</li>
              <li><kbd>Ctrl</kbd>+<kbd>Enter</kbd> stage current action</li>
              <li><kbd>Esc</kbd> close modal</li>
            </ul>
          </div>
        </div>
      </section>

    </div><!-- /.content -->
  </div><!-- /.main -->
</div><!-- /.app -->

<div id="modal-root"></div>
<div id="toast-stack" class="toast-stack"></div>

<script src="/static/app.js"></script>
</body>
</html>
"""

INDEX_JS = r"""
// PlantSEED Curation Dashboard frontend (v4).
// Vanilla JS, no build step.

const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const state = {
  user: null,
  currentFile: null,
  selection: null,
  actionMeta: null,
  staging: [],
  fileEditor: { name: null, content: "", rows: [] },
  allRoles: [],
  facets: {},
  browseFilters: { name: "", subsystems: new Set(), types: new Set(), curators: new Set(), include: null, transporter: null },
  searchSelectedIdx: -1,
  searchFlat: [],
};

const TAB_TITLES = {
  curate:  "Curate",
  staging: "Staging",
  files:   "Files",
  apply:   "Apply Updates",
  browse:  "Browse Database",
  help:    "Help",
};

// ---------- HTTP & helpers ------------------------------------------------
async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    body: opts.body ? JSON.stringify(opts.body) : null,
  });
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = { error: text || `HTTP ${res.status}` }; }
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json;
}
const esc = (s) => (s == null ? "" : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
function highlight(text, q) {
  if (!q || q.length < 2 || q.includes(":")) return esc(text);
  const safe = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return esc(text).replace(new RegExp("(" + safe + ")", "ig"), "<mark>$1</mark>");
}
const bytesFmt = (n) => n < 1024 ? n + " B" : n < 1024*1024 ? (n/1024).toFixed(1) + " KB" : (n/1024/1024).toFixed(2) + " MB";

// ---------- Theme toggle --------------------------------------------------
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("plantseed-theme", theme);
  $("#btn-theme").textContent = theme;
}
function initTheme() {
  const saved = localStorage.getItem("plantseed-theme");
  const prefersLight = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
  applyTheme(saved || (prefersLight ? "light" : "dark"));
  $("#btn-theme").addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme") || "dark";
    applyTheme(cur === "dark" ? "light" : "dark");
  });
}

// ---------- Toast & Modal -------------------------------------------------
function toast(message, kind = "") {
  const t = document.createElement("div");
  t.className = "toast " + (kind || "");
  t.textContent = message;
  $("#toast-stack").appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; t.style.transform = "translateY(8px)"; }, 3000);
  setTimeout(() => t.remove(), 3400);
}
const Modal = {
  current: null,
  show({ title, bodyHTML, actions, onMount }) {
    this.hide();
    const wrap = document.createElement("div");
    wrap.className = "modal-backdrop";
    wrap.innerHTML = `<div class="modal">
      <div class="modal-head"><h3>${esc(title)}</h3><button data-close>×</button></div>
      <div class="modal-body">${bodyHTML}</div>
      <div class="modal-foot">${(actions || []).map((a,i) => `<button class="btn ${a.kind || ""}" data-act="${i}">${esc(a.label)}</button>`).join("")}</div>
    </div>`;
    $("#modal-root").appendChild(wrap);
    this.current = wrap;
    const body = wrap.querySelector(".modal-body");
    onMount && onMount(body);
    wrap.querySelector("[data-close]").addEventListener("click", () => this.hide());
    wrap.addEventListener("click", e => { if (e.target === wrap) this.hide(); });
    (actions || []).forEach((a,i) => {
      const btn = wrap.querySelector(`[data-act="${i}"]`);
      btn?.addEventListener("click", () => a.onClick && a.onClick(body));
    });
    setTimeout(() => wrap.querySelector("input, textarea, select")?.focus(), 30);
  },
  hide() { this.current && this.current.remove(); this.current = null; },
  confirm(message) {
    return new Promise(resolve => this.show({
      title: "Confirm",
      bodyHTML: `<div>${esc(message)}</div>`,
      actions: [
        { label: "Cancel", onClick: () => { this.hide(); resolve(false); } },
        { label: "OK", kind: "warn", onClick: () => { this.hide(); resolve(true); } },
      ],
    }));
  },
  prompt(message, defaultValue = "") {
    return new Promise(resolve => this.show({
      title: "Input",
      bodyHTML: `<label>${esc(message)}</label><input type="text" id="mp-val" value="${esc(defaultValue)}">`,
      actions: [
        { label: "Cancel", onClick: () => { this.hide(); resolve(null); } },
        { label: "OK", kind: "primary", onClick: (b) => { const v = b.querySelector("#mp-val").value; this.hide(); resolve(v); } },
      ],
      onMount: (b) => b.querySelector("#mp-val").addEventListener("keydown", e => {
        if (e.key === "Enter") { const v = e.target.value; this.hide(); resolve(v); }
      }),
    }));
  }
};
document.addEventListener("keydown", e => { if (e.key === "Escape") Modal.hide(); });

// ---------- Tabs (sidebar nav) + shortcuts --------------------------------
function showTab(name) {
  $$(".section").forEach(s => s.classList.remove("active"));
  $$(".sidebar nav button").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  $(`#tab-${name}`)?.classList.add("active");
  $("#section-title").textContent = TAB_TITLES[name] || name;
  if (name === "browse")  renderBrowse();
  if (name === "staging") renderStaging();
  if (name === "files")   refreshFiles();
  if (name === "apply")   refreshApplyTab();
  if (name === "help")    renderHelp();
}
$$(".sidebar nav button").forEach(b => b.addEventListener("click", () => showTab(b.dataset.tab)));

let chord = null;
document.addEventListener("keydown", e => {
  const t = e.target.tagName;
  if (t === "INPUT" || t === "TEXTAREA" || t === "SELECT") return;
  if (e.key === "/") { e.preventDefault(); showTab("curate"); $("#search-input").focus(); return; }
  if (e.key === "g") { chord = "g"; setTimeout(() => chord = null, 1000); return; }
  if (chord === "g") {
    const map = { c:"curate", s:"staging", f:"files", a:"apply", b:"browse", h:"help" };
    if (map[e.key]) showTab(map[e.key]);
    chord = null;
  }
});

// ---------- Bootstrap -----------------------------------------------------
async function init() {
  initTheme();
  try {
    state.actionMeta = await api("/api/actions");
    const status = await api("/api/status");
    setDbCount(status.roles);
    setExpasy(status.expasy);
    pollExpasy();
    await ensureUser();
    await refreshFiles();
    renderHelp();
  } catch (e) {
    toast("Init failed: " + e.message, "bad");
  }
}

function setDbCount(n) { $("#db-text").textContent = `${n.toLocaleString()} roles`; }
function setExpasy(e) {
  const el = $("#ec-text");
  if (e.status === "loaded") { el.textContent = `${e.count.toLocaleString()}`; el.classList.remove("muted"); }
  else if (e.status === "loading") { el.innerHTML = `<span class="spinner"></span>loading`; el.classList.add("muted"); }
  else if (e.status === "error") { el.textContent = "error"; el.classList.add("muted"); el.title = e.error || ""; }
  else { el.textContent = "idle"; el.classList.add("muted"); }
}
async function pollExpasy() {
  for (let i = 0; i < 60; i++) {
    const s = await api("/api/status");
    setExpasy(s.expasy);
    if (s.expasy.status === "loaded" || s.expasy.status === "error") return;
    await new Promise(r => setTimeout(r, 2000));
  }
}

async function ensureUser() {
  const u = await api("/api/user");
  if (!sessionStorage.getItem("user_confirmed")) {
    const chosen = await showUserModal(u);
    if (chosen) {
      const r = await api("/api/user", { method: "POST", body: { username: chosen, display_name: u.display_name } });
      state.user = { ...u, ...r, dir_name: r.username };
    } else {
      state.user = u;
    }
    sessionStorage.setItem("user_confirmed", "1");
  } else {
    state.user = u;
  }
  renderUserBadge();
}
function renderUserBadge() {
  const u = state.user;
  $("#user-text").textContent = `@${u.dir_name}`;
  $("#user-text").title = `display: ${u.display_name || "?"}\nsource: ${u.source}\nemail: ${u.email || "?"}\n(click to switch)`;
}
function showUserModal(detected) {
  return new Promise(resolve => {
    const opts = detected.candidates.map((c, i) =>
      `<label style="display:flex; align-items:center; gap:8px; padding:5px 0; cursor:pointer;">
        <input type="radio" name="ghu" value="${esc(c.value)}" ${i===0?"checked":""} style="width:auto;">
        <span><code>@${esc(c.value)}</code> <span class="dim" style="font-size:11px;">(${esc(c.source)})</span></span>
      </label>`).join("");
    Modal.show({
      title: "Confirm your GitHub username",
      bodyHTML: `<div class="help" style="margin-bottom:10px;">Pick one of the detected candidates, or type your own. Your files live in <code>Curators/&lt;username&gt;/</code>.</div>
        ${opts}
        <label>Or enter manually</label>
        <input type="text" id="user-custom" placeholder="GitHub username">`,
      actions: [
        { label: "Use this", kind: "primary", onClick: (body) => {
            const custom = body.querySelector("#user-custom").value.trim();
            const radio = body.querySelector('input[name=ghu]:checked');
            Modal.hide();
            resolve(custom || (radio ? radio.value : detected.username));
        } },
      ],
    });
  });
}
$("#user-text").addEventListener("click", async () => {
  const u = await api("/api/user");
  const chosen = await showUserModal(u);
  if (!chosen) return;
  const r = await api("/api/user", { method: "POST", body: { username: chosen, display_name: u.display_name } });
  state.user = { ...u, ...r, dir_name: r.username };
  renderUserBadge();
  await refreshFiles();
  toast(`Switched to @${r.username}`, "good");
});
$("#btn-reload").addEventListener("click", async () => {
  const r = await api("/api/reload", { method: "POST" });
  setDbCount(r.roles);
  state.allRoles = [];
  toast(`Reloaded ${r.roles} roles`, "good");
});

// ---------- Search --------------------------------------------------------
let searchDebounce = null;
$("#search-input").addEventListener("input", e => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => runSearch(e.target.value), 180);
});
$("#search-input").addEventListener("keydown", e => {
  const flat = state.searchFlat;
  if (!flat.length) return;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    state.searchSelectedIdx = Math.min(flat.length - 1, state.searchSelectedIdx + 1);
    paintResultSelection();
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    state.searchSelectedIdx = Math.max(0, state.searchSelectedIdx - 1);
    paintResultSelection();
  } else if (e.key === "Enter" && state.searchSelectedIdx >= 0) {
    e.preventDefault();
    const sel = flat[state.searchSelectedIdx];
    selectEnzyme(sel.name, sel.kind === "expasy" ? "expasy" : "plantseed");
  }
});
function paintResultSelection() {
  const items = $$(".results .item");
  items.forEach((el, i) => el.classList.toggle("selected", i === state.searchSelectedIdx));
  items[state.searchSelectedIdx]?.scrollIntoView({ block: "nearest" });
}

async function runSearch(q) {
  q = (q || "").trim();
  const root = $("#results-list");
  const summary = $("#search-summary");
  state.searchSelectedIdx = -1;
  state.searchFlat = [];
  if (q.length < 2 && !q.includes(":")) {
    root.innerHTML = `<div class="empty">Type 2+ characters to search.</div>`;
    summary.textContent = "";
    return;
  }
  root.innerHTML = `<div class="empty"><span class="spinner"></span>Searching…</div>`;
  const r = await api(`/api/search?q=${encodeURIComponent(q)}`);
  const total = r.totals.name + r.totals.expasy + r.totals.by_feature;
  let summaryText = `${r.totals.name} name`;
  if (r.totals.by_feature) summaryText += ` · ${r.totals.by_feature} feat`;
  if (r.totals.expasy) summaryText += ` · ${r.totals.expasy} EC`;
  summary.textContent = summaryText;

  if (total === 0) {
    root.innerHTML = `<div class="empty">No matches. Use <b>+ Novel</b> to create a new one.</div>`;
    return;
  }
  const psNames = new Set(r.name);
  const parts = [];

  if (r.name.length) {
    parts.push(`<div class="group-header">PlantSEED — ${r.totals.name}</div>`);
    r.name.forEach(n => {
      parts.push(`<div class="item" data-name="${esc(n)}" data-source="plantseed"><span class="tag plant">PS</span><span class="name">${highlight(n, q)}</span></div>`);
      state.searchFlat.push({ kind: "plantseed", name: n });
    });
  }
  if (r.by_feature.length) {
    parts.push(`<div class="group-header">By feature — ${r.totals.by_feature}</div>`);
    r.by_feature.forEach(item => {
      parts.push(`<div class="item" data-name="${esc(item.role)}" data-source="plantseed">
        <span class="tag plant">PS</span>
        <span class="name">${esc(item.role)}<span class="sub">via ${highlight(item.feature, q)}</span></span>
      </div>`);
      state.searchFlat.push({ kind: "feature", name: item.role });
    });
  }
  if (r.expasy.length) {
    parts.push(`<div class="group-header">Expasy — ${r.totals.expasy}</div>`);
    r.expasy.forEach(n => {
      const already = psNames.has(n);
      parts.push(`<div class="item" data-name="${esc(n)}" data-source="${already ? "plantseed" : "expasy"}">
        <span class="tag ${already ? "plant" : "expasy"}">${already ? "PS" : "EC"}</span>
        <span class="name">${highlight(n, q)}</span>
        <span class="meta">${already ? "in DB" : "novel"}</span>
      </div>`);
      state.searchFlat.push({ kind: already ? "plantseed" : "expasy", name: n });
    });
  }
  root.innerHTML = parts.join("");
  $$(".item", root).forEach((it, idx) => {
    it.addEventListener("click", () => selectEnzyme(it.dataset.name, it.dataset.source));
    it.addEventListener("mouseenter", () => { state.searchSelectedIdx = idx; paintResultSelection(); });
  });
}
$("#btn-novel").addEventListener("click", async () => {
  const name = await Modal.prompt("Full name for the new enzyme (include EC, e.g. … (EC 1.2.3.4)):");
  if (!name?.trim()) return;
  selectEnzyme(name.trim(), "novel");
});

// ---------- Enzyme selection ----------------------------------------------
async function selectEnzyme(name, source) {
  const isExisting = source === "plantseed";
  let role = null, warnings = [];
  if (isExisting) {
    const r = await api(`/api/role?name=${encodeURIComponent(name)}`);
    if (r.exists) { role = r.entry; warnings = r.warnings; }
    else source = "novel";
  }
  state.selection = { name, source, isNew: !isExisting, role, warnings };
  $("#enzyme-picker").style.display = "none";
  $("#enzyme-current").style.display = "";
  $("#current-name").innerHTML = `${esc(name)} ${
    source === "plantseed" ? '<span class="tag plant">in PlantSEED</span>' :
    source === "expasy"    ? '<span class="tag expasy">Expasy → CREATE</span>' :
                             '<span class="tag new">novel → CREATE</span>'
  }`;
  $("#current-warnings").innerHTML = warnings.length
    ? `<div class="banner warn">Empty required: ${warnings.map(esc).join(", ")}. Use ADD to populate.</div>` : "";
  $("#role-detail").innerHTML = renderRoleCard(role);
  populateActionSelect();
  renderActionBody();
  await refreshPreview();
}
$("#btn-switch-enzyme").addEventListener("click", () => switchEnzyme());
function switchEnzyme() {
  state.selection = null;
  $("#enzyme-picker").style.display = "";
  $("#enzyme-current").style.display = "none";
  $("#role-detail").innerHTML = `<div class="empty">Pick an enzyme on the left.</div>`;
  $("#preview-area").innerHTML = `<div class="empty">Fill the action form to see preview.</div>`;
  $("#search-input").focus();
  $("#search-input").select();
}

function renderRoleCard(role) {
  if (!role) return `<div class="empty">No PlantSEED record yet — will be created on NEW.</div>`;
  const order = ["role", "abstract_enzyme", "include", "type", "is_transporter",
                 "subsystems", "classes", "reactions", "features", "localization",
                 "publications", "curators", "kbase_id"];
  const fields = Object.keys(role);
  const sorted = [...order.filter(k => fields.includes(k)), ...fields.filter(k => !order.includes(k))];
  return `<div class="role-card">${sorted.map(k => renderField(k, role[k])).join("")}</div>`;
}
function renderField(k, v) {
  let html;
  if (v === null || v === undefined || v === "") html = `<span class="v empty">(empty)</span>`;
  else if (Array.isArray(v)) {
    html = v.length === 0 ? `<span class="v empty">[ ]</span>`
      : `<div class="v">${v.map(it => `<code>${esc(it)}</code>`).join("")}</div>`;
  } else if (typeof v === "object") {
    const lines = Object.entries(v).map(([kk, vv]) =>
      `<div class="obj-line"><code>${esc(kk)}</code> ${esc(typeof vv === "object" ? JSON.stringify(vv) : vv)}</div>`);
    html = Object.keys(v).length === 0 ? `<span class="v empty">{ }</span>`
      : `<div class="v">${lines.join("")}</div>`;
  } else if (typeof v === "boolean") html = `<span class="v"><code>${v ? "true" : "false"}</code></span>`;
  else html = `<span class="v">${esc(v)}</span>`;
  return `<div class="field"><div class="k">${esc(k)}</div>${html}</div>`;
}

// ---------- Action form ---------------------------------------------------
function populateActionSelect() {
  const sel = $("#action-select");
  const all = state.actionMeta.actions.map(a => a.name);
  const opts = state.selection?.isNew ? ["NEW", ...all.filter(a => a !== "NEW")] : all.filter(a => a !== "NEW");
  sel.innerHTML = opts.map(a => `<option value="${a}">${a}</option>`).join("");
  sel.onchange = () => { renderActionBody(); refreshPreviewDebounced(); };
}
const actionMetaFor = (name) => state.actionMeta?.actions.find(a => a.name === name);

function renderActionBody() {
  const action = $("#action-select").value;
  const meta = actionMetaFor(action);
  $("#action-help").textContent = meta?.description || "";
  const body = $("#action-body");
  if (action === "NEW") {
    body.innerHTML = `<div class="help">A blank role will be created with schema defaults.</div>`;
    bindAutoPreview(); return;
  }
  if (action === "UPDATE") {
    body.innerHTML = `<label>New enzyme name</label>
      <input type="text" id="payload-new_name" placeholder="… (EC 1.2.3.4)">
      <div class="field-error" data-err="new_name"></div>`;
    bindAutoPreview(); return;
  }
  if (action === "REASSIGN" || action === "CHANGE" || action === "ASSIGN") {
    body.innerHTML = `<label>Field</label>
      <select id="payload-field">${meta.fields.map(f => `<option>${f}</option>`).join("")}</select>
      <div class="field-error" data-err="field"></div>
      <label>Value</label><div id="payload-value-wrap"></div>
      <div class="field-error" data-err="value"></div>`;
    function paintValue() {
      const f = $("#payload-field").value;
      const wrap = $("#payload-value-wrap");
      if (state.actionMeta.scalar_types[f] === "bool") {
        wrap.innerHTML = `<select id="payload-value"><option value="true">true</option><option value="false">false</option></select>`;
      } else {
        wrap.innerHTML = `<input type="text" id="payload-value" placeholder="value">`;
      }
      $("#payload-value").addEventListener("input", refreshPreviewDebounced);
      $("#payload-value").addEventListener("change", refreshPreviewDebounced);
    }
    paintValue();
    $("#payload-field").onchange = () => { paintValue(); refreshPreviewDebounced(); };
    return;
  }
  if (action === "RELOCATE") {
    body.innerHTML = `<label>Field</label>
      <select id="payload-field">${meta.fields.map(f => `<option>${f}</option>`).join("")}</select>
      <div class="field-error" data-err="field"></div>
      <label>Old key</label><input type="text" id="payload-old" placeholder="Existing key">
      <div class="field-error" data-err="old"></div>
      <label>New key</label><input type="text" id="payload-new" placeholder="Replacement key">
      <div class="field-error" data-err="new"></div>`;
    bindAutoPreview(); return;
  }
  body.innerHTML = `<label>Field</label>
    <select id="payload-field">${meta.fields.map(f => `<option>${f}</option>`).join("")}</select>
    <div class="field-error" data-err="field"></div>
    <div id="payload-entries" style="margin-top:8px;"></div>
    <button id="btn-add-entry" class="btn small" type="button">+ Add entry</button>
    <div id="action-extra-help" class="help"></div>`;
  $("#payload-field").onchange = () => { renderEntriesArea(); refreshPreviewDebounced(); paintExtraHelp(); };
  $("#btn-add-entry").onclick = () => { addEntryRow(); refreshPreviewDebounced(); };
  renderEntriesArea(); paintExtraHelp();
}

function bindAutoPreview() {
  $$("#action-body input, #action-body select").forEach(el => {
    el.addEventListener("input", refreshPreviewDebounced);
    el.addEventListener("change", refreshPreviewDebounced);
  });
}
function paintExtraHelp() {
  const action = $("#action-select").value;
  const field  = $("#payload-field")?.value;
  const help = $("#action-extra-help");
  if (!help) return;
  if (action === "ADD" && (field === "features" || field === "reactions")) {
    help.innerHTML = `Extra column is <b>optional</b>. Blank → compartment <code>${state.actionMeta.default_compartment}</code> (cytosol).`;
  } else { help.innerHTML = ""; }
}
function renderEntriesArea() {
  $("#payload-entries").innerHTML = "";
  addEntryRow();
}
function addEntryRow() {
  const action = $("#action-select").value;
  const field = $("#payload-field").value;
  const root = $("#payload-entries");
  const cfg = action === "ADD" ? state.actionMeta.multi_col[field] : null;
  const div = document.createElement("div");
  div.className = "entry-row";
  let extraHTML = "";
  if (cfg) {
    if (cfg.extra_kind === "compartment_only") {
      const opts = state.actionMeta.compartments.map(c => `<option value="${c.id}">${c.id} (${esc(c.name)})</option>`).join("");
      extraHTML = `<div class="entry-extra-wrap">
        <select class="entry-extra"><option value="">— (default: c)</option>${opts}</select>
      </div>`;
    } else if (cfg.extra_kind === "compartment_source") {
      const cptOpts = state.actionMeta.compartments.map(c => `<option value="${c.id}">${c.id} (${esc(c.name)})</option>`).join("");
      extraHTML = `<div class="entry-extra-wrap">
        <select class="entry-cpt"><option value="">— (default: c)</option>${cptOpts}</select>
        <input type="text" class="entry-src" placeholder="source (PPDB, SUBA…)">
      </div>`;
    } else {
      extraHTML = `<input type="text" class="entry-extra" placeholder="${esc(cfg.extra_label)}">`;
    }
  }
  div.innerHTML = `
    <input type="text" class="entry-value" placeholder="${esc(cfg ? cfg.primary_label : "value")}">
    ${extraHTML}
    <button class="btn tiny rm-btn" data-act="rm" title="Remove" type="button">×</button>`;
  root.appendChild(div);
  div.querySelector("[data-act=rm]").onclick = () => { div.remove(); refreshPreviewDebounced(); };
  div.querySelectorAll("input, select").forEach(el => el.addEventListener("input", refreshPreviewDebounced));
  const valInp = div.querySelector(".entry-value");
  valInp.addEventListener("blur", () => maybeShowXref(field, valInp));
}
async function maybeShowXref(field, inp) {
  const v = (inp.value || "").trim();
  if (!v || v.length < 3) return;
  if (!["features", "reactions", "publications"].includes(field)) return;
  const mode = field === "features" ? "substring" : "exact";
  const exclude = state.selection?.name || "";
  try {
    const r = await api(`/api/xref?field=${field}&value=${encodeURIComponent(v)}&mode=${mode}&exclude=${encodeURIComponent(exclude)}`);
    const row = inp.closest(".entry-row");
    row.querySelector(".xref-msg")?.remove();
    if (r.matches.length) {
      const div = document.createElement("div");
      div.className = "xref-msg";
      div.innerHTML = `<b>${esc(v)}</b> appears in ${r.total} other role(s): ${r.matches.slice(0, 3).map(esc).join(", ")}${r.total > 3 ? "…" : ""}`;
      row.appendChild(div);
    }
  } catch (e) {}
}
function gatherPayload() {
  const action = $("#action-select").value;
  if (action === "NEW") return {};
  if (action === "UPDATE") return { new_name: $("#payload-new_name")?.value || "" };
  const field = $("#payload-field")?.value;
  if (action === "REASSIGN" || action === "CHANGE" || action === "ASSIGN") return { field, value: $("#payload-value")?.value || "" };
  if (action === "RELOCATE") return { field, old: $("#payload-old")?.value || "", new: $("#payload-new")?.value || "" };
  if (action === "ADD" || action === "REMOVE") {
    const entries = $$("#payload-entries .entry-row").map(div => {
      const value = div.querySelector(".entry-value")?.value || "";
      let extra = "";
      const cpt = div.querySelector(".entry-cpt");
      const src = div.querySelector(".entry-src");
      if (cpt) {
        const c = cpt.value, s = src?.value?.trim() || "";
        if (c && s) extra = `${c}:${s}`;
        else if (c) extra = c;
        else if (s) extra = `:${s}`;
      } else {
        extra = div.querySelector(".entry-extra")?.value || "";
      }
      return { value, extra };
    });
    return { field, entries };
  }
  return {};
}
function showFieldErrors(errors) {
  $$("#action-body .field-error").forEach(el => el.textContent = "");
  $$("#action-body input, #action-body select").forEach(el => el.classList.remove("invalid"));
  errors.forEach(e => {
    $(`[data-err="${e.field}"]`)?.replaceChildren(document.createTextNode(e.message));
    const inpId = "payload-" + e.field.replace(/[\[\].]/g, "-");
    $("#" + inpId)?.classList.add("invalid");
  });
}

// ---------- Preview -------------------------------------------------------
let previewDebounce = null;
function refreshPreviewDebounced() { clearTimeout(previewDebounce); previewDebounce = setTimeout(refreshPreview, 250); }
async function refreshPreview() {
  if (!state.selection) return;
  const area = $("#preview-area");
  area.innerHTML = `<div class="empty"><span class="spinner"></span>Computing…</div>`;
  const pendingRows = state.staging.filter(r => r.split("\t")[0] === state.selection.name);
  let currentRows = [];
  try {
    const action = $("#action-select")?.value;
    if (action) {
      const r = await api("/api/build", { method: "POST",
        body: { action, enzyme: state.selection.name, payload: gatherPayload() } });
      if (r.errors && r.errors.length) showFieldErrors(r.errors);
      else { showFieldErrors([]); currentRows = r.rows; }
    }
  } catch (e) {}
  const rows = [...pendingRows, ...currentRows];
  if (rows.length === 0) { area.innerHTML = `<div class="empty">Fill the action form to see preview.</div>`; return; }
  try {
    const p = await api("/api/preview", { method: "POST",
      body: { enzyme: state.selection.name, rows } });
    const parts = [];
    if (p.errors?.length)   parts.push(`<div class="banner bad"><b>Errors</b><br>${p.errors.map(esc).join("<br>")}</div>`);
    if (p.warnings?.length) parts.push(`<div class="banner warn"><b>${p.warnings.length} warning(s)</b><br>${p.warnings.slice(0,5).map(esc).join("<br>")}${p.warnings.length>5?"<br>… +"+(p.warnings.length-5)+" more":""}</div>`);
    if (p.renamed_to)       parts.push(`<div class="banner info">Would rename to <code>${esc(p.renamed_to)}</code></div>`);
    if (!p.after) parts.push(`<div class="empty">Would not produce a role record.</div>`);
    else parts.push(renderDiff(p.before, p.after));
    area.innerHTML = parts.join("");
  } catch (e) {
    area.innerHTML = `<div class="banner bad">Preview error: ${esc(e.message)}</div>`;
  }
}
function renderDiff(before, after) {
  if (!after) return `<div class="empty">No after state</div>`;
  const fields = new Set([...Object.keys(before || {}), ...Object.keys(after)]);
  const order = ["role", "abstract_enzyme", "include", "type", "is_transporter",
                 "subsystems", "classes", "reactions", "features", "localization",
                 "publications", "curators", "kbase_id"];
  const sorted = [...order.filter(k => fields.has(k)), ...[...fields].filter(k => !order.includes(k))];
  const parts = [];
  for (const k of sorted) {
    const a = before?.[k], b = after?.[k];
    const aStr = a === undefined ? "(absent)" : JSON.stringify(a, null, 2);
    const bStr = b === undefined ? "(absent)" : JSON.stringify(b, null, 2);
    if (aStr === bStr) continue;
    parts.push(`<div class="diff-section">
      <div class="field-name">${esc(k)}</div>
      <div class="diff-line rem">- ${esc(aStr)}</div>
      <div class="diff-line add">+ ${esc(bStr)}</div>
    </div>`);
  }
  return parts.length ? parts.join("") : `<div class="empty">No changes (no-op).</div>`;
}

// ---------- Stage ---------------------------------------------------------
$("#btn-stage").addEventListener("click", stageCurrentAction);
$("#btn-stage-preview").addEventListener("click", refreshPreview);
async function stageCurrentAction() {
  if (!state.selection) { toast("Pick an enzyme first", "warn"); return; }
  try {
    const action = $("#action-select").value;
    const r = await api("/api/build", { method: "POST",
      body: { action, enzyme: state.selection.name, payload: gatherPayload() } });
    if (r.errors?.length) { showFieldErrors(r.errors); toast("Fix highlighted fields", "bad"); return; }
    if (r.warnings?.length) r.warnings.forEach(w => toast(w, "warn"));
    if (!r.rows.length) { toast("No rows produced", "bad"); return; }
    state.staging.push(...r.rows);
    refreshStagingBadge();
    $("#stage-status").textContent = `Staged ${r.rows.length}. ${state.staging.length} row(s) pending. Enzyme stays selected.`;
    toast(`Staged ${r.rows.length} row(s)`, "good");
    renderActionBody();
    refreshPreview();
  } catch (e) { toast(e.message, "bad"); }
}
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && $("#tab-curate").classList.contains("active")) {
    e.preventDefault();
    stageCurrentAction();
  }
});
function refreshStagingBadge() {
  const c = state.staging.length;
  const b = $("#staging-count");
  b.classList.toggle("visible", c > 0);
  b.textContent = c;
  $("#staging-count-2").textContent = `(${c})`;
}

// ---------- Staging tab ---------------------------------------------------
function renderStaging() {
  refreshStagingBadge();
  const root = $("#staging-list");
  if (state.staging.length === 0) {
    root.innerHTML = `<div class="empty">No staged rows. Use Curate to add some.</div>`;
    $("#staging-raw").textContent = "";
    return;
  }
  root.innerHTML = state.staging.map((r, i) => stagingCardHTML(r, i)).join("");
  $$(".staging-card [data-act]", root).forEach(b => {
    b.addEventListener("click", () => {
      const idx = parseInt(b.closest(".staging-card").dataset.idx);
      const act = b.dataset.act;
      if (act === "del") { state.staging.splice(idx, 1); renderStaging(); return; }
      if (act === "up" && idx > 0)   { [state.staging[idx-1], state.staging[idx]] = [state.staging[idx], state.staging[idx-1]]; renderStaging(); return; }
      if (act === "down" && idx < state.staging.length - 1) { [state.staging[idx+1], state.staging[idx]] = [state.staging[idx], state.staging[idx+1]]; renderStaging(); return; }
      if (act === "edit") stagingEditModal(idx);
    });
  });
  $("#staging-raw").textContent = state.staging.join("\n");
}
function stagingCardHTML(row, idx) {
  const c = row.split("\t");
  const enzyme = esc(c[0] || "");
  const action = esc(c[1] || "?");
  const field  = c[2] ? `<span class="f">${esc(c[2])}</span>` : "";
  const value  = c[3] ? ` <span class="v">${esc(c[3])}</span>` : "";
  const extra  = c[4] ? ` <span class="x">${esc(c[4])}</span>` : "";
  return `<div class="staging-card" data-idx="${idx}">
    <span class="num">${idx + 1}</span>
    <span class="tag action ${action}">${action}</span>
    <div class="body"><span class="e">${enzyme}</span> ${field}${value}${extra}</div>
    <div class="acts">
      <button class="btn tiny" data-act="up"   title="Up">↑</button>
      <button class="btn tiny" data-act="down" title="Down">↓</button>
      <button class="btn tiny" data-act="edit" title="Edit">edit</button>
      <button class="btn tiny danger" data-act="del" title="Delete">×</button>
    </div>
  </div>`;
}
function stagingEditModal(idx) {
  const cols = state.staging[idx].split("\t");
  const opts = state.actionMeta.actions.map(a => `<option ${a.name === cols[1] ? "selected" : ""}>${a.name}</option>`).join("");
  Modal.show({
    title: `Edit staged row #${idx + 1}`,
    bodyHTML: `
      <label>Enzyme</label><input id="e-enz" type="text" value="${esc(cols[0] || "")}">
      <label>Action</label><select id="e-act">${opts}</select>
      <label>Field</label><input id="e-fld" type="text" value="${esc(cols[2] || "")}">
      <label>Value</label><input id="e-val" type="text" value="${esc(cols[3] || "")}">
      <label>Extra (optional)</label><input id="e-ext" type="text" value="${esc(cols[4] || "")}">`,
    actions: [
      { label: "Cancel", onClick: () => Modal.hide() },
      { label: "Save", kind: "primary", onClick: (b) => {
          const nc = [b.querySelector("#e-enz").value, b.querySelector("#e-act").value];
          const f = b.querySelector("#e-fld").value;
          const v = b.querySelector("#e-val").value;
          const x = b.querySelector("#e-ext").value;
          if (f) nc.push(f); if (v) nc.push(v); if (x) nc.push(x);
          state.staging[idx] = nc.join("\t");
          Modal.hide(); renderStaging(); toast("Row updated", "good");
      } },
    ]
  });
}
$("#btn-staging-clear").addEventListener("click", async () => {
  if (!state.staging.length) return;
  if (await Modal.confirm(`Discard all ${state.staging.length} staged row(s)?`)) {
    state.staging = []; renderStaging();
  }
});
$("#btn-staging-save").addEventListener("click", async () => {
  if (!state.staging.length) { toast("Nothing to save", "warn"); return; }
  if (!state.currentFile) {
    const name = await Modal.prompt("No current file. Filename:", "Updates.tsv");
    if (!name) return;
    await api("/api/file/create", { method: "POST", body: { user: state.user.dir_name, name } });
    setCurrentFile(name.endsWith(".tsv") ? name : name + ".tsv");
  }
  const r = await api("/api/file/append", { method: "POST",
    body: { user: state.user.dir_name, name: state.currentFile.name, rows: state.staging } });
  toast(`Appended ${r.appended} row(s) to ${state.currentFile.name}`, "good");
  state.staging = []; renderStaging();
  await refreshFiles();
});
$("#btn-staging-saveas").addEventListener("click", async () => {
  if (!state.staging.length) { toast("Nothing to save", "warn"); return; }
  const name = await Modal.prompt("Filename:", "Updates.tsv");
  if (!name) return;
  const fname = name.endsWith(".tsv") ? name : name + ".tsv";
  await api("/api/file/create", { method: "POST", body: { user: state.user.dir_name, name: fname } });
  const r = await api("/api/file/append", { method: "POST",
    body: { user: state.user.dir_name, name: fname, rows: state.staging } });
  toast(`Appended ${r.appended} row(s) to ${fname}`, "good");
  setCurrentFile(fname);
  state.staging = []; renderStaging();
  await refreshFiles();
});
$("#btn-staging-copy").addEventListener("click", () => {
  if (!state.staging.length) { toast("Nothing to copy", "warn"); return; }
  navigator.clipboard.writeText(state.staging.join("\n"))
    .then(() => toast("Copied", "good"))
    .catch(e => toast("Copy failed: " + e.message, "bad"));
});

// ---------- Files tab -----------------------------------------------------
async function refreshFiles() {
  if (!state.user) return;
  const r = await api(`/api/files?user=${encodeURIComponent(state.user.dir_name)}`);
  renderFilesList(r.files, r.dir);
  renderOtherCurators(r.all_curators);
  populateApplyFileSelect(r.files);
  if (state.fileEditor.name && r.files.some(f => f.name === state.fileEditor.name)) {
    openFile(state.fileEditor.name);
  } else if (!state.currentFile && r.files.length > 0) {
    setCurrentFile(r.files[0].name);
  } else if (state.currentFile && !r.files.some(f => f.name === state.currentFile.name)) {
    setCurrentFile(r.files[0]?.name || null);
  }
}
function setCurrentFile(name) {
  state.currentFile = name ? { name } : null;
  const el = $("#file-text");
  el.textContent = name || "none";
  el.classList.toggle("muted", !name);
}
function renderFilesList(files, dir) {
  const root = $("#files-list");
  if (files.length === 0) { root.innerHTML = `<div class="empty-small">No files yet.</div>`; return; }
  root.innerHTML = `<div class="dim" style="font-size:11px; margin-bottom:6px; word-break:break-all;">${esc(dir)}</div>` +
    files.map(f => `
      <div class="list-item ${state.currentFile?.name === f.name ? "selected" : ""}" data-name="${esc(f.name)}">
        <span class="name">${esc(f.name)}</span>
        <span class="meta">${f.rows}r · ${bytesFmt(f.size)}</span>
        <div class="acts">
          <button class="btn tiny" data-act="select">${state.currentFile?.name === f.name ? "✓" : "set"}</button>
        </div>
      </div>`).join("");
  $$(".list-item", root).forEach(it => it.addEventListener("click", e => {
    if (e.target.dataset.act === "select") { setCurrentFile(it.dataset.name); refreshFiles(); return; }
    openFile(it.dataset.name);
  }));
}
function renderOtherCurators(list) {
  const root = $("#other-curators");
  if (!list?.length) { root.innerHTML = `<div class="empty-small">none</div>`; return; }
  root.innerHTML = list.map(c => `
    <div class="list-item" data-user="${esc(c.name)}">
      <span class="name">@${esc(c.name)}</span>
      <span class="meta">${c.n_files}f</span>
    </div>`).join("");
  $$(".list-item", root).forEach(it => it.addEventListener("click", async () => {
    const u = it.dataset.user;
    const r = await api(`/api/files?user=${encodeURIComponent(u)}`);
    Modal.show({
      title: `@${u} (read-only)`,
      bodyHTML: r.files.length ? r.files.map(f => `<div class="list-item"><span class="name">${esc(f.name)}</span><span class="meta">${f.rows} rows · ${bytesFmt(f.size)}</span></div>`).join("") : `<div class="empty-small">No files</div>`,
      actions: [{ label: "Close", onClick: () => Modal.hide() }],
    });
  }));
}
$("#btn-new-file").addEventListener("click", async () => {
  const name = await Modal.prompt("New filename (.tsv appended if missing):", "Updates.tsv");
  if (!name) return;
  const r = await api("/api/file/create", { method: "POST", body: { user: state.user.dir_name, name } });
  toast(`Created ${r.name}`, "good");
  setCurrentFile(r.name);
  await refreshFiles();
  openFile(r.name);
});
async function openFile(name) {
  const r = await api(`/api/file?user=${encodeURIComponent(state.user.dir_name)}&name=${encodeURIComponent(name)}`);
  state.fileEditor = { name, content: r.content, rows: r.rows };
  $("#file-editor-title").textContent = name;
  $("#file-editor-path").textContent = `Curators/${state.user.dir_name}/${name}`;
  $("#file-raw-editor").value = r.content;
  renderFileRows(r.rows);
  $("#file-banner").innerHTML = "";
}
function renderFileRows(rows) {
  const root = $("#file-rows");
  if (!rows.length) { root.innerHTML = `<div class="empty-small">File is empty.</div>`; return; }
  const acts = state.actionMeta.actions.map(a => a.name);
  root.innerHTML = `<table class="editor-table"><thead><tr>
    <th class="num">#</th><th>Enzyme</th><th>Action</th><th>Field</th><th>Value</th><th>Extra</th><th></th>
  </tr></thead><tbody>${rows.map((r, i) => `
    <tr data-idx="${i}">
      <td class="num">${r.lineno}</td>
      <td><input type="text" data-k="enzyme" value="${esc(r.enzyme || "")}"></td>
      <td><select data-k="action">${acts.map(a => `<option ${a === r.action ? "selected" : ""}>${a}</option>`).join("")}</select></td>
      <td><input type="text" data-k="field" value="${esc(r.field || "")}"></td>
      <td><input type="text" data-k="value" value="${esc(r.value || "")}"></td>
      <td><input type="text" data-k="extra" value="${esc(r.extra || "")}"></td>
      <td><button class="btn tiny danger" data-act="del">×</button></td>
    </tr>`).join("")}</tbody></table>`;
  $$("[data-act=del]", root).forEach(b => b.addEventListener("click", () => { b.closest("tr").remove(); syncRaw(); }));
  $$("input, select", root).forEach(el => el.addEventListener("input", syncRaw));
}
function syncRaw() {
  const lines = $$("#file-rows tbody tr").map(tr => {
    const enz = tr.querySelector('[data-k="enzyme"]').value;
    const act = tr.querySelector('[data-k="action"]').value;
    const f = tr.querySelector('[data-k="field"]').value;
    const v = tr.querySelector('[data-k="value"]').value;
    const x = tr.querySelector('[data-k="extra"]').value;
    const cols = [enz, act];
    if (f) cols.push(f); if (v) cols.push(v); if (x) cols.push(x);
    return cols.join("\t");
  });
  $("#file-raw-editor").value = lines.join("\n") + (lines.length ? "\n" : "");
  $("#file-banner").innerHTML = `<div class="banner warn">Unsaved changes — click Save to write to disk.</div>`;
}
$("#btn-file-save").addEventListener("click", async () => {
  if (!state.fileEditor.name) { toast("No file open", "warn"); return; }
  await api("/api/file/save", { method: "POST",
    body: { user: state.user.dir_name, name: state.fileEditor.name, content: $("#file-raw-editor").value } });
  toast("Saved", "good");
  await refreshFiles();
  await openFile(state.fileEditor.name);
});
$("#btn-file-apply").addEventListener("click", () => {
  if (!state.fileEditor.name) { toast("No file open", "warn"); return; }
  showTab("apply");
  $("#apply-source").value = "file";
  $("#apply-source").dispatchEvent(new Event("change"));
  $("#apply-file-select").value = state.fileEditor.name;
});
$("#btn-file-delete").addEventListener("click", async () => {
  if (!state.fileEditor.name) return;
  if (!(await Modal.confirm(`Delete ${state.fileEditor.name}? This cannot be undone.`))) return;
  await api("/api/file/delete", { method: "POST",
    body: { user: state.user.dir_name, name: state.fileEditor.name } });
  toast("Deleted", "good");
  state.fileEditor = { name: null, content: "", rows: [] };
  $("#file-editor-title").textContent = "No file open";
  $("#file-rows").innerHTML = "";
  $("#file-raw-editor").value = "";
  await refreshFiles();
});

// ---------- Apply tab -----------------------------------------------------
function populateApplyFileSelect(files) {
  $("#apply-file-select").innerHTML = files.map(f => `<option value="${esc(f.name)}">${esc(f.name)} (${f.rows} rows)</option>`).join("");
}
$("#apply-source").addEventListener("change", () => {
  const v = $("#apply-source").value;
  $("#apply-file-pick").style.display = v === "file" ? "" : "none";
  $("#apply-paste").style.display = v === "paste" ? "" : "none";
});
function refreshApplyTab() { refreshFiles(); $("#apply-source").dispatchEvent(new Event("change")); }
async function gatherApplyTSV() {
  const v = $("#apply-source").value;
  if (v === "staging") return state.staging.join("\n");
  if (v === "paste") return $("#apply-paste-area").value;
  if (v === "file") {
    const name = $("#apply-file-select").value;
    if (!name) throw new Error("Select a file");
    const r = await api(`/api/file?user=${encodeURIComponent(state.user.dir_name)}&name=${encodeURIComponent(name)}`);
    return r.content;
  }
  return "";
}
async function runApply(dryRun) {
  const tsv = await gatherApplyTSV();
  if (!tsv.trim()) { toast("Nothing to apply", "warn"); return; }
  if (!dryRun && !(await Modal.confirm("Apply changes to PlantSEED_Roles.json?"))) return;
  $("#apply-status").innerHTML = `<span class="spinner"></span>${dryRun ? "Dry-running" : "Applying"}…`;
  $("#apply-result").innerHTML = "";
  try {
    const r = await api("/api/apply", { method: "POST",
      body: { user: state.user.dir_name, tsv, dry_run: dryRun } });
    renderApplyResult(r, dryRun);
    $("#apply-status").textContent = `${r.errors.length} error · ${r.warnings.length} warning · ${r.summary?.touched?.length || 0} role(s) ${dryRun ? "would be" : ""} touched`;
    if (!dryRun && r.errors.length === 0 && r.summary?.touched?.length) {
      toast(`Database updated — ${r.summary.touched.length} role(s)`, "good");
      const s = await api("/api/status");
      setDbCount(s.roles);
      state.allRoles = [];
    } else if (dryRun) {
      toast("Dry-run complete", "good");
    } else if (r.errors.length) {
      toast("Apply blocked by errors", "bad");
    }
  } catch (e) {
    $("#apply-result").innerHTML = `<div class="banner bad">ERROR: ${esc(e.message)}</div>`;
    $("#apply-status").textContent = "failed";
    toast("Apply failed: " + e.message, "bad");
  }
}
function renderApplyResult(r, dryRun) {
  const root = $("#apply-result");
  const parts = [];
  if (r.errors.length)   parts.push(`<div class="banner bad"><b>${r.errors.length} error(s)</b><br>${r.errors.map(esc).join("<br>")}</div>`);
  if (r.warnings.length) parts.push(`<div class="banner warn"><b>${r.warnings.length} warning(s)</b><br>${r.warnings.slice(0,10).map(esc).join("<br>")}${r.warnings.length>10?"<br>… +"+(r.warnings.length-10)+" more":""}</div>`);
  if (r.info.length)     parts.push(`<div class="banner good">${r.info.map(esc).join("<br>")}</div>`);
  const s = r.summary || {};
  if (s.touched?.length) {
    parts.push(`<div class="subtle" style="margin-bottom:10px;"><b>${s.touched.length}</b> role(s) ${dryRun ? "would be" : "were"} touched${s.new?.length ? ` · <b>${s.new.length}</b> new` : ""}${Object.keys(s.renamed||{}).length ? ` · <b>${Object.keys(s.renamed).length}</b> rename(s)` : ""}</div>`);
  }
  if (r.role_diffs?.length) {
    r.role_diffs.forEach(d => parts.push(renderRoleDiffCard(d)));
  } else if (!r.errors.length && !r.warnings.length) {
    parts.push(`<div class="empty">No changes.</div>`);
  }
  root.innerHTML = parts.join("");
}
function renderRoleDiffCard(d) {
  const tag = d.is_new ? '<span class="tag NEW">NEW</span>'
    : d.renamed_from ? `<span class="tag UPDATE">RENAMED from ${esc(d.renamed_from)}</span>`
    : '<span class="tag CHANGE">MODIFIED</span>';
  return `<div class="diff-card">
    <h4>${tag} <span>${esc(d.role)}</span></h4>
    ${renderDiff(d.before, d.after)}
  </div>`;
}
$("#btn-apply-dry").addEventListener("click", () => runApply(true));
$("#btn-apply-real").addEventListener("click", () => runApply(false));

// ---------- Browse --------------------------------------------------------
let browseTimer = null;
async function renderBrowse() {
  if (state.allRoles.length === 0) {
    const r = await api("/api/roles/all");
    state.allRoles = r.roles;
    state.facets = r.facets;
  }
  renderBrowseFacets();
  applyBrowseFilters();
  $("#browse-input").oninput = e => {
    clearTimeout(browseTimer);
    browseTimer = setTimeout(() => { state.browseFilters.name = e.target.value; applyBrowseFilters(); }, 150);
  };
}
function renderBrowseFacets() {
  const root = $("#browse-facets");
  const f = state.browseFilters;
  function chips(field, title, values) {
    if (!values?.length) return "";
    return `<div class="facet-section">
      <h4>${title}</h4>
      <div class="facet-options">
        ${values.map(v => `<span class="facet-chip ${f[field].has(v) ? "active" : ""}" data-field="${field}" data-val="${esc(v)}">${esc(v)}</span>`).join("")}
      </div>
    </div>`;
  }
  root.innerHTML =
    `<div class="facet-section">
      <h4>Include</h4>
      <span class="facet-chip ${f.include === true ? "active" : ""}"  data-toggle="include" data-val="true">included</span>
      <span class="facet-chip ${f.include === false ? "active" : ""}" data-toggle="include" data-val="false">excluded</span>
    </div>
    <div class="facet-section">
      <h4>Transporter</h4>
      <span class="facet-chip ${f.transporter === true ? "active" : ""}"  data-toggle="transporter" data-val="true">yes</span>
      <span class="facet-chip ${f.transporter === false ? "active" : ""}" data-toggle="transporter" data-val="false">no</span>
    </div>` +
    chips("types", "Type", state.facets.types) +
    chips("subsystems", `Subsystem (${state.facets.subsystems?.length || 0})`, state.facets.subsystems) +
    chips("curators",   `Curator (${state.facets.curators?.length || 0})`,    state.facets.curators);
  $$(".facet-chip[data-field]", root).forEach(c => c.addEventListener("click", () => {
    const set = state.browseFilters[c.dataset.field];
    set.has(c.dataset.val) ? set.delete(c.dataset.val) : set.add(c.dataset.val);
    renderBrowseFacets(); applyBrowseFilters();
  }));
  $$(".facet-chip[data-toggle]", root).forEach(c => c.addEventListener("click", () => {
    const key = c.dataset.toggle, v = c.dataset.val === "true";
    state.browseFilters[key] = state.browseFilters[key] === v ? null : v;
    renderBrowseFacets(); applyBrowseFilters();
  }));
}
$("#btn-browse-clear").addEventListener("click", () => {
  state.browseFilters = { name: "", subsystems: new Set(), types: new Set(), curators: new Set(), include: null, transporter: null };
  $("#browse-input").value = "";
  renderBrowseFacets(); applyBrowseFilters();
});
function applyBrowseFilters() {
  const f = state.browseFilters;
  const q = (f.name || "").toLowerCase();
  const filtered = state.allRoles.filter(r => {
    if (q && !r.role.toLowerCase().includes(q)) return false;
    if (f.types.size > 0 && !f.types.has(r.type)) return false;
    if (f.subsystems.size > 0 && !r.subsystems.some(s => f.subsystems.has(s))) return false;
    if (f.curators.size > 0 && !r.curators.some(c => f.curators.has(c))) return false;
    if (f.include !== null && Boolean(r.include) !== f.include) return false;
    if (f.transporter !== null && Boolean(r.is_transporter) !== f.transporter) return false;
    return true;
  });
  $("#browse-count").textContent = `${filtered.length} / ${state.allRoles.length}`;
  const root = $("#browse-list");
  if (!filtered.length) { root.innerHTML = `<div class="empty">No matches</div>`; return; }
  const visible = filtered.slice(0, 500);
  root.innerHTML = visible.map(r => `
    <div class="list-item" data-name="${esc(r.role)}">
      <span class="name">${esc(r.role)}</span>
      <span class="meta">${r.n_features}f · ${r.n_reactions}r${r.is_transporter ? " · trans" : ""}${!r.include ? " · excl" : ""}</span>
    </div>`).join("") +
    (filtered.length > visible.length ? `<div class="empty-small">${filtered.length - visible.length} more — refine your filter</div>` : "");
  $$(".list-item", root).forEach(it => it.addEventListener("click", async () => {
    $$(".list-item", root).forEach(i => i.classList.remove("selected"));
    it.classList.add("selected");
    const r = await api(`/api/role?name=${encodeURIComponent(it.dataset.name)}`);
    if (r.exists) $("#browse-detail").innerHTML = renderRoleCard(r.entry);
  }));
}

// ---------- Help ----------------------------------------------------------
function renderHelp() {
  if (!state.actionMeta) return;
  $("#help-actions").innerHTML = state.actionMeta.actions.map(a => `
    <div style="display:flex; align-items:flex-start; gap:10px; padding:5px 0; border-bottom:1px solid var(--border-soft);">
      <span style="min-width:80px;"><span class="tag action ${esc(a.name)}">${esc(a.name)}</span></span>
      <div>
        <div>${esc(a.description)}</div>
        ${a.fields.length ? `<div class="dim" style="font-size:11px;">Fields: ${a.fields.map(esc).join(", ")}</div>` : ""}
      </div>
    </div>`).join("");
  $("#help-compartments").innerHTML = state.actionMeta.compartments.map(c =>
    `<div class="compartment-chip"><span class="id">${esc(c.id)}</span> ${esc(c.name)}</div>`).join("");
}

init();
"""

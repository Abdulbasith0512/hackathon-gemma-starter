"use strict";
/* Asset Intelligence Copilot front-end. No build step, no libraries. */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } } };

const state = { boot: null, userId: null, convId: null, busy: false };
const ID_RE = /\b(?:WELL|INS|MNT|REG|CTX|COR|SN|RULE)-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\b|\breport:MNT-[\w-]+|\b[A-Za-z0-9-]+#[\w.]+\b|\b(?:SR|RC|WS)-\d{2}\b/g;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined });
  let data = null;
  try { data = await res.json(); } catch { /* not JSON */ }
  if (!res.ok) throw new Error((data && (data.detail || data.error)) || `${res.status} ${res.statusText}`);
  return data;
}

/* ---------- text and chips ---------- */
function refClass(id) { return /^COR-|^RULE-|^SN-/.test(id) ? "ref cor" : /#|^report:|^(SR|RC|WS)-\d{2}$/.test(id) ? "ref doc" : "ref"; }
function chip(id) { return `<button class="${refClass(id)}" data-ref="${esc(id)}" title="Open evidence">${esc(id)}</button>`; }
function linkIds(html) { return html.replace(ID_RE, (m) => chip(m)); }
function inline(s) {
  let e = esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  e = e.replace(/\[([^\]]*)\]/g, (m, inner) => (ID_RE.test(inner) ? (ID_RE.lastIndex = 0, inner) : (ID_RE.lastIndex = 0, m)));
  return linkIds(e);
}
function renderText(t) {
  const lines = String(t || "").split("\n"); let html = "", inList = false;
  const isRow = (l) => /^\s*\|.*\|\s*$/.test(l), isSep = (l) => /^\s*\|[\s:|-]+\|\s*$/.test(l);
  const cells = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => inline(c.trim()));
  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    if (isRow(raw)) {                                   // a Markdown table
      if (inList) { html += "</ul>"; inList = false; }
      const rows = []; while (i < lines.length && isRow(lines[i])) { if (!isSep(lines[i])) rows.push(cells(lines[i])); i++; } i--;
      if (rows.length) html += `<div class="tablewrap"><table class="data"><thead><tr>${rows[0].map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${rows.slice(1).map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
      continue;
    }
    const m = raw.match(/^\s*(?:[*•-]|\d+[.)])\s+(.*)$/);
    if (m) { if (!inList) { html += "<ul>"; inList = true; } html += `<li>${inline(m[1])}</li>`; }
    else { if (inList) { html += "</ul>"; inList = false; } if (raw.trim()) html += `<p>${inline(raw)}</p>`; }
  }
  return html + (inList ? "</ul>" : "");
}
const fmtD = (iso) => { const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? `${+m[3]} ${MONTHS[+m[2] - 1]}` : iso; };

/* ---------- visuals ---------- */
function tableHTML(s) {
  if (!s.rows.length) return `<div class="empty">No rows.</div>`;
  const head = s.columns.map((c) => `<th>${esc(c)}</th>`).join("");
  const rows = s.rows.slice(0, 300).map((r) => `<tr>${r.map((c) => `<td>${typeof c === "string" ? linkIds(esc(c)) : esc(c ?? "")}</td>`).join("")}</tr>`).join("");
  return `<div class="tablewrap"><table class="data"><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>${s.rows.length > 300 ? `<div class="sub">Showing 300 of ${s.rows.length} rows.</div>` : ""}`;
}
function cardHTML(s) {
  const cls = s.status === "producing" ? "producing" : s.status === "not producing" ? "not-producing" : "unknown";
  const metrics = s.metrics.map((m) => `<div class="metric"><div class="k">${esc(m.label)}</div><div class="v">${esc(m.value)}</div><div class="n ${m.note === "out of date" ? "warn" : ""}">${esc(m.note || "")}</div></div>`).join("");
  const reasons = (s.reasons || []).map((r) => `<div class="reason">${linkIds(esc(r))}</div>`).join("");
  return `<div class="card"><div class="card-top">${chip(s.title).replace('class="ref"', 'class="ref" style="font-size:18px;padding:2px 10px"')}<span class="pill ${cls}">${esc(s.status)}</span><span class="sub">${esc(s.subtitle)}</span></div><div class="metrics">${metrics}</div>${reasons}</div>`;
}
function barHTML(s) {
  const n = s.labels.length; if (!n) return `<div class="empty">Nothing to chart.</div>`;
  const W = 720, left = 150, right = 110, rowH = 42, H = n * rowH + 12, max = Math.max(...s.values, 1);
  const bars = s.labels.map((l, i) => {
    const y = 8 + i * rowH, w = Math.max(2, (W - left - right) * (s.values[i] / max)), ref = (s.refs || [])[i];
    const fmt = Number.isInteger(s.values[i]) ? s.values[i].toLocaleString() : s.values[i];
    return `<g><text class="lab" x="${left - 12}" y="${y + 24}" text-anchor="end" ${ref ? `data-ref="${esc(ref)}"` : ""}>${esc(l)}</text>
      <rect x="${left}" y="${y + 6}" width="${w}" height="26" rx="6" fill="url(#bg)"><title>${esc(l)}: ${fmt} ${esc(s.unit || "")}</title></rect>
      <text class="val" x="${left + w + 10}" y="${y + 24}">${fmt} ${esc(s.unit || "")}</text>${s.sub ? `<text x="${left + 8}" y="${y + 24}" style="fill:#1a1203;font-size:11px;font-weight:700">${esc(s.sub[i] || "")}</text>` : ""}</g>`;
  }).join("");
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(s.title || "Bar chart")}"><defs><linearGradient id="bg" x1="0" x2="1"><stop offset="0" stop-color="#f5a524"/><stop offset="1" stop-color="#fbbf24"/></linearGradient></defs>${bars}</svg>`;
}
function lineHTML(s) {
  const n = s.x.length; if (!n) return `<div class="empty">No readings.</div>`;
  const W = 720, H = 300, m = { l: 48, r: 16, t: 18, b: 44 };
  const all = s.series.flatMap((x) => x.values).filter((v) => v != null); let lo = Math.min(...all), hi = Math.max(...all); const pad = (hi - lo || 1) * 0.12; lo -= pad; hi += pad;
  const X = (i) => m.l + (n === 1 ? 0 : (i * (W - m.l - m.r)) / (n - 1)), Y = (v) => m.t + (H - m.t - m.b) * (1 - (v - lo) / (hi - lo));
  const colors = ["#f5a524", "#60a5fa"];
  let g = "";
  for (let t = 0; t <= 4; t++) { const v = lo + ((hi - lo) * t) / 4, y = Y(v); g += `<line class="gridl" x1="${m.l}" x2="${W - m.r}" y1="${y}" y2="${y}"/><text x="${m.l - 8}" y="${y + 4}" text-anchor="end">${v.toFixed(0)}</text>`; }
  const step = Math.ceil(n / 7);
  s.x.forEach((d, i) => { if (i % step === 0 || i === n - 1) g += `<text x="${X(i)}" y="${H - 20}" text-anchor="middle">${fmtD(d)}</text>`; });
  (s.markers || []).forEach((mk) => { g += `<rect x="${X(mk.index) - 9}" y="${m.t}" width="18" height="${H - m.t - m.b}" fill="rgba(248,113,113,.13)"/>`; });
  s.series.forEach((ser, k) => {
    const pts = ser.values.map((v, i) => (v == null ? null : `${X(i)},${Y(v)}`)).filter(Boolean).join(" ");
    g += `<polyline points="${pts}" fill="none" stroke="${colors[k % 2]}" stroke-width="2.4" stroke-linejoin="round"/>`;
    ser.values.forEach((v, i) => { if (v != null) g += `<circle class="pt" cx="${X(i)}" cy="${Y(v)}" r="3.4" fill="${colors[k % 2]}" ${s.refs ? `data-ref="${esc(s.refs[i])}"` : ""}><title>${fmtD(s.x[i])} · ${esc(ser.name)}: ${v}</title></circle>`; });
  });
  (s.markers || []).forEach((mk) => { const v = s.series[0].values[mk.index]; g += `<circle class="pt" cx="${X(mk.index)}" cy="${Y(v)}" r="8" fill="none" stroke="#f87171" stroke-width="2.4" data-ref="${esc(mk.ref)}"><title>${fmtD(s.x[mk.index])} · not producing oil</title></circle>`; });
  const legend = s.series.map((x, k) => `<span><i style="background:${colors[k % 2]}"></i>${esc(x.name)}</span>`).join("") + ((s.markers || []).length ? `<span><i style="background:#f87171"></i>Not producing oil (${s.markers.length})</span>` : "");
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(s.title || "Line chart")}">${g}</svg><div class="legend">${legend}</div>`;
}
function mapHTML(s) {
  const pts = (s.points || []); if (!pts.length) return `<div class="empty">No locations to show.</div>`;
  const W = 720, H = 360, pad = 50; const lats = pts.map((p) => p.lat), lons = pts.map((p) => p.lon);
  let la0 = Math.min(...lats), la1 = Math.max(...lats), lo0 = Math.min(...lons), lo1 = Math.max(...lons);
  const k = Math.cos(((la0 + la1) / 2) * Math.PI / 180); const spanLon = Math.max((lo1 - lo0) * k, 0.004), spanLat = Math.max(la1 - la0, 0.004);
  const sc = Math.min((W - 2 * pad) / spanLon, (H - 2 * pad) / spanLat);
  const cx = (lo0 + lo1) / 2, cy = (la0 + la1) / 2;
  const X = (lon) => W / 2 + (lon - cx) * k * sc, Y = (lat) => H / 2 - (lat - cy) * sc;
  const vmax = Math.max(...pts.map((p) => p.value || 0), 1);
  let g = ""; for (let i = 1; i < 8; i++) g += `<line class="gridl" x1="${(W / 8) * i}" x2="${(W / 8) * i}" y1="0" y2="${H}"/>`; for (let i = 1; i < 5; i++) g += `<line class="gridl" x1="0" x2="${W}" y1="${(H / 5) * i}" y2="${(H / 5) * i}"/>`;
  g += pts.map((p) => { const r = 8 + 14 * Math.sqrt((p.value || 0) / vmax); return `<g class="pt" data-ref="${esc(p.ref)}"><circle cx="${X(p.lon)}" cy="${Y(p.lat)}" r="${r}" fill="rgba(245,165,36,.25)" stroke="#f5a524" stroke-width="2"/><circle cx="${X(p.lon)}" cy="${Y(p.lat)}" r="3.2" fill="#f5a524"/><text x="${X(p.lon) + r + 4}" y="${Y(p.lat) + 4}" style="fill:#e7edf4;font-size:12px">${esc(p.label)}${p.value != null ? ` · ${p.value} bbl` : ""}</text><title>${esc(p.label)} (${p.lat}, ${p.lon})</title></g>`; }).join("");
  g += `<text x="${W - 14}" y="22" text-anchor="end" style="font-size:13px;fill:#93a1b3">N ↑</text><text x="12" y="${H - 10}" style="font-size:11px">lat ${la0.toFixed(3)}–${la1.toFixed(3)} · lon ${lo0.toFixed(3)}–${lo1.toFixed(3)} (no basemap; positions to scale)</text>`;
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Map of wells" style="background:#0c121a;border-radius:10px">${g}</svg>`;
}
function heatHTML(s, host) {
  const max = Math.max(...s.values.flat(), 1);
  const cols = s.cols.length + 2;
  let h = `<div class="heat" style="grid-template-columns:minmax(120px,1.6fr) repeat(${s.cols.length}, minmax(34px,1fr)) 54px"><div></div>${s.cols.map((c) => `<div class="h">${esc(c)}</div>`).join("")}<div class="h">Total</div>`;
  s.rows.forEach((r, i) => {
    h += `<div class="rl">${esc(r)}</div>`;
    s.values[i].forEach((v, j) => { const a = v ? 0.16 + 0.84 * (v / max) : 0.04; h += `<button class="cell" data-cell="${i},${j}" style="background:rgba(245,165,36,${a.toFixed(2)});${v ? "" : "color:#64748b;"}" aria-label="${esc(r)} ${esc(s.cols[j])}: ${v}">${v}</button>`; });
    h += `<div class="tot">${s.values[i].reduce((a, b) => a + b, 0)}</div>`;
  });
  return h + `</div><div class="pop" hidden></div><div class="sub" style="margin-top:6px">Click a cell to list the inspections behind it.</div>`;
}
function renderVisual(kind, spec) {
  return { table: tableHTML, bar: barHTML, line: lineHTML, map: mapHTML, heatmap: heatHTML, status_card: cardHTML }[kind]?.(spec) || `<div class="empty">Cannot draw this visual.</div>`;
}
const LABELS = { table: "Table", bar: "Bar", line: "Line", map: "Map", heatmap: "Heatmap", status_card: "Card" };
function renderBlock(b) {
  const v = b.visual, el = document.createElement("div"); el.className = "block";
  const sw = v.available.length > 1 ? `<div class="seg" role="group" aria-label="View as">${v.available.map((k) => `<button data-k="${k}" class="${k === v.kind ? "on" : ""}">${LABELS[k]}</button>`).join("")}</div>` : "";
  el.innerHTML = `<div class="block-head"><div><h3>${esc(b.title || "Result")}</h3>${b.window ? `<div class="sub">${esc(b.window.label)}${b.window.assumption ? " · " + esc(b.window.assumption) : ""}</div>` : ""}</div>${sw}</div>${v.note ? `<div class="notice" style="margin-top:8px">${esc(v.note)}</div>` : ""}<div class="block-body"></div>`;
  const body = $(".block-body", el);
  const show = (k) => { body.innerHTML = renderVisual(k, v.specs[k]); $$(".seg button", el).forEach((x) => x.classList.toggle("on", x.dataset.k === k)); if (k === "heatmap") wireHeat(body, v.specs[k]); };
  show(v.kind);
  $$(".seg button", el).forEach((btn) => btn.addEventListener("click", () => show(btn.dataset.k)));
  return el;
}
function wireHeat(body, s) {
  $$("button.cell", body).forEach((btn) => btn.addEventListener("click", () => {
    const [i, j] = btn.dataset.cell.split(",").map(Number), ids = s.cells[i][j], pop = $(".pop", body);
    pop.hidden = false; pop.innerHTML = ids.length ? `<strong>${esc(s.rows[i])} · ${esc(s.cols[j])}</strong> — ${ids.length} spill(s): ${ids.map(chip).join(" ")}` : `No spills in ${esc(s.rows[i])} for ${esc(s.cols[j])}.`;
  }));
}

/* ---------- message rendering ---------- */
const FLAG_LABEL = { corrected: "Corrected data", conflict: "Conflict", needs_confirmation: "Needs confirmation", unconfirmed: "Unconfirmed", missing_evidence: "No evidence", stale: "Out of date", rule: "User rule" };
function signalsHTML(flags) {
  if (!flags?.length) return "";
  return `<div class="signals" aria-label="Signals">${flags.map((f) => `<div class="signal ${esc(f.type)}"><span class="tag">${esc(FLAG_LABEL[f.type] || f.type)}</span><span>${linkIds(esc(f.text))} ${(f.refs || []).slice(0, 4).map((r) => (f.text.includes(r) ? "" : chip(r))).join(" ")}</span></div>`).join("")}</div>`;
}
function scrollDown() { const m = $("#messages"); m.scrollTop = m.scrollHeight; }
function addUser(text) { const el = document.createElement("div"); el.className = "msg user"; el.innerHTML = `<div class="bubble">${esc(text)}</div>`; $("#messages").appendChild(el); scrollDown(); return el; }

function renderAssistant(p) {
  const el = document.createElement("div"); el.className = "msg assistant";
  const how = (p.tool_calls || []).length ? `<details class="how"><summary>How this was worked out</summary><ul>${p.tool_calls.map((c) => `<li><code>${esc(c.name)}(${esc(Object.entries(c.args).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", "))})</code> ${c.ok ? "✓" : "✗ " + esc(c.error || "")}</li>`).join("")}</ul><div>As-of date ${esc(p.as_of || "")}. ${p.answer_source === "model" ? "Wording by Gemma; every figure was checked against the tool results." : "Shown as verified facts straight from the records."}</div></details>` : "";
  el.innerHTML = `<div class="who"><span class="avatar">A</span> Copilot</div><div class="answer">${renderText(p.answer)}${p.answer_source === "verified facts" ? `<div class="src-note">Verified facts from the records</div>` : ""}</div>`;
  (p.blocks || []).forEach((b) => el.appendChild(renderBlock(b)));
  el.insertAdjacentHTML("beforeend", signalsHTML(p.flags));
  (p.pending || []).forEach((pa) => el.appendChild(renderPending(pa)));
  if (p.citations?.length) {
    const mk = (c) => `<button class="${refClass(c.id)}" data-ref="${esc(c.id)}" title="${esc(c.label)}">${esc(c.id)}</button>`, N = 14;
    const box = document.createElement("div"); box.className = "sources";
    const draw = (all) => { box.innerHTML = `<span class="k">Sources</span>${p.citations.slice(0, all ? 400 : N).map(mk).join("")}${p.citations.length > N ? `<button class="small" data-more>${all ? "Show fewer" : `Show all ${p.citations.length}`}</button>` : ""}`; $("[data-more]", box)?.addEventListener("click", () => draw(!all)); };
    draw(false); el.appendChild(box);
  }
  (p.warnings || []).forEach((w) => el.insertAdjacentHTML("beforeend", `<div class="warnline">⚠ ${esc(w)}</div>`));
  (p.errors || []).forEach((w) => el.insertAdjacentHTML("beforeend", `<div class="warnline">Tool note: ${esc(w)}</div>`));
  el.insertAdjacentHTML("beforeend", how);
  $("#messages").appendChild(el); return el;
}

function renderPending(pa) {
  const el = document.createElement("div"); el.className = "pending";
  const pv = pa.preview;
  el.innerHTML = `<h3>${esc(pv.title)}</h3><table>${pv.rows.map(([k, v, cls]) => `<tr><td>${esc(k)}</td><td class="${esc(cls || "")}">${linkIds(esc(v))}</td></tr>`).join("")}</table>${(pv.impact || []).map((t) => `<div class="sub" style="margin-top:6px">Effect: ${esc(t)}</div>`).join("")}${(pv.warnings || []).map((t) => `<div class="warn">⚠ ${linkIds(esc(t))}</div>`).join("")}<div class="btns"><button class="primary confirm" style="padding:8px 18px">Confirm and save</button><button class="ghost cancel">Cancel</button></div>`;
  const done = (t, cls) => { $(".btns", el).outerHTML = `<div class="${cls || "done-tag"}">${t}</div>`; };
  $(".confirm", el).addEventListener("click", async () => {
    $$("button", el).forEach((b) => (b.disabled = true));
    try {
      const out = await api(`/api/actions/${pa.action_id}/confirm`, { method: "POST", body: { user_id: state.userId } });
      done("✓ Saved. This now applies to everyone's later answers; the original value is kept.");
      renderAssistant(out); scrollDown(); loadConvs();
    } catch (e) { done("Could not save: " + esc(e.message), "warnline"); }
  });
  $(".cancel", el).addEventListener("click", async () => { try { await api(`/api/actions/${pa.action_id}/cancel`, { method: "POST", body: { user_id: state.userId } }); } catch { /* already closed */ } done("Cancelled. Nothing was saved.", "sub"); });
  return el;
}

/* ---------- chat flow ---------- */
function showHero() {
  const s = state.boot?.suggestions || [], tags = ["Status", "Ranking", "Spills", "Wells", "Heatmap"];
  $("#messages").innerHTML = `<div class="hero"><h2>Ask about your wells</h2><p>Answers come with the records and manual passages behind them. Corrections you make are kept, attributed, and applied for everyone.</p><div class="suggest">${s.map((q, i) => `<button data-q="${esc(q)}"><span class="tag">${tags[i] || "Ask"}</span>${esc(q)}</button>`).join("")}</div></div>`;
}
async function send(text) {
  text = text.trim(); if (!text || state.busy) return;
  state.busy = true; $("#send").disabled = true;
  if ($(".hero")) $("#messages").innerHTML = "";
  addUser(text); $("#input").value = ""; autosize();
  const typing = document.createElement("div"); typing.className = "msg assistant";
  typing.innerHTML = `<div class="who"><span class="avatar">A</span> Copilot</div><div class="answer"><span class="typing"><i></i><i></i><i></i> <span id="tick">Choosing tools and checking the records…</span></span></div>`;
  $("#messages").appendChild(typing); scrollDown();
  const t0 = Date.now(), timer = setInterval(() => { const s = Math.round((Date.now() - t0) / 1000); const el = $("#tick"); if (el) el.textContent = s < 8 ? "Choosing tools and checking the records…" : `Still working (${s}s)… the model may be waiting on its rate limit.`; }, 1000);
  try {
    const out = await api("/api/chat", { method: "POST", body: { user_id: state.userId, message: text, conv_id: state.convId } });
    typing.remove();
    if (out.error) { renderError(out.error, text); }
    else { state.convId = out.conv_id; renderAssistant(out); loadConvs(); }
  } catch (e) { typing.remove(); renderError(e.message, text); }
  finally { clearInterval(timer); state.busy = false; $("#send").disabled = false; scrollDown(); $("#input").focus(); }
}
function renderError(msg, text) {
  const el = document.createElement("div"); el.className = "msg assistant";
  el.innerHTML = `<div class="errbox"><strong>That did not work.</strong><div>${esc(msg)}</div><button class="ghost">Try again</button></div>`;
  $("button", el).addEventListener("click", () => { el.remove(); send(text); });
  $("#messages").appendChild(el);
}
function autosize() { const t = $("#input"); t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 160) + "px"; }

async function loadConvs() {
  const list = await api(`/api/conversations?user_id=${encodeURIComponent(state.userId)}`);
  const ul = $("#conv-list"); ul.innerHTML = list.length ? "" : `<li class="sub" style="padding:8px 10px">No chats yet.</li>`;
  list.forEach((c) => { const li = document.createElement("li"); li.innerHTML = `<button class="${c.conv_id === state.convId ? "active" : ""}" title="${esc(c.title)}">${esc(c.title || "Chat")}</button>`; $("button", li).addEventListener("click", () => openConv(c.conv_id)); ul.appendChild(li); });
}
async function openConv(id) {
  const msgs = await api(`/api/conversations/${id}?user_id=${encodeURIComponent(state.userId)}`);
  state.convId = id; $("#messages").innerHTML = "";
  msgs.forEach((m) => (m.role === "user" ? addUser(m.content) : renderAssistant(m.payload ? { ...m.payload, answer: m.content } : { answer: m.content })));
  loadConvs(); scrollDown();
}
function newChat() { state.convId = null; showHero(); loadConvs(); $("#input").focus(); }

/* ---------- evidence drawer ---------- */
async function openEvidence(ref) {
  $("#drawer").hidden = false; $("#scrim").hidden = false; $("#drawer-title").textContent = ref; $("#drawer-sub").textContent = ""; $("#drawer-body").innerHTML = `<div class="sub">Loading…</div>`;
  try {
    const d = await api(`/api/evidence?ref=${encodeURIComponent(ref)}`);
    $("#drawer-title").textContent = d.title; $("#drawer-sub").textContent = d.subtitle || "";
    let h = d.source ? `<div class="srcline">Source: ${esc(d.source)}</div>` : "";
    if (d.fields.length) h += `<dl class="fields">${d.fields.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${linkIds(esc(v === "" || v == null ? "—" : v))}</dd>`).join("")}</dl>`;
    if (d.corrections?.length) h += `<div class="eyebrow">Corrections applied</div>` + d.corrections.map((c) => `<div class="signal corrected"><span class="tag">${esc(c.correction_id)}</span><span>${esc(c.field)}: ${esc(c.original_value)} → <strong>${esc(c.new_value)}</strong>. ${esc(c.reason)}</span></div>`).join("");
    if (d.sections.length) h += d.sections.map((s) => `<div class="section-box ${s.highlight ? "hl" : ""}"><h4>${esc(s.heading)}</h4><div class="sec-text">${renderText(s.text)}</div></div>`).join("");
    if (d.related.length) h += `<div class="eyebrow" style="margin-top:12px">Related</div><div class="related">${d.related.map((r) => `<button class="${refClass(r.ref)}" data-ref="${esc(r.ref)}">${esc(r.label)}</button>`).join("")}</div>`;
    if (d.raw) h += `<details class="raw"><summary class="sub">Original record (JSON)</summary><pre>${esc(JSON.stringify(d.raw, null, 2))}</pre></details>`;
    $("#drawer-body").innerHTML = h;
    $(".section-box.hl", $("#drawer-body"))?.scrollIntoView({ block: "start", behavior: "instant" });
  } catch (e) { $("#drawer-body").innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}
function closeDrawer() { $("#drawer").hidden = true; $("#scrim").hidden = true; }

/* ---------- audit + rules pages ---------- */
async function loadAudit() {
  const a = await api("/api/audit"), u = (id) => esc(a.users[id] || id), body = $("#audit-body");
  const cor = a.corrections.length ? `<div class="tablewrap"><table class="data"><thead><tr><th>ID</th><th>Record</th><th>Field</th><th>Original (kept)</th><th>New</th><th>By</th><th>Why</th><th>When</th><th>Scope</th><th>Status</th></tr></thead><tbody>${a.corrections.map((c) => `<tr><td>${chip(c.correction_id)}</td><td>${chip(c.target_id)}</td><td>${esc(c.field)}</td><td>${esc(c.original_value)}</td><td><strong>${esc(c.new_value)}</strong></td><td>${u(c.author_user_id)}</td><td>${esc(c.reason)}</td><td>${esc(c.created_at.slice(0, 16).replace("T", " "))}</td><td>${esc(c.scope_type)}: ${esc(c.scope_value)}</td><td class="st-${esc(c.status)}">${esc(c.status)}</td></tr>`).join("")}</tbody></table></div>` : `<div class="empty">No corrections yet. When someone corrects a reading or an AI estimate, it appears here with the original value, who changed it, why, and its scope.</div>`;
  const rules = a.rules.length ? `<div class="tablewrap"><table class="data"><thead><tr><th>ID</th><th>Scope</th><th>Setting</th><th>Equipment</th><th>Value</th><th>Set by</th><th>Why</th><th>Status</th></tr></thead><tbody>${a.rules.map((r) => `<tr><td>${chip(r.rule_id)}</td><td>${esc(r.scope_type)}: ${esc(r.scope_value)}</td><td>${esc(r.key)}</td><td>${esc(r.equipment_kind || "all")}</td><td><strong>${esc(r.value)}</strong></td><td>${u(r.author_user_id)}</td><td>${esc(r.reason)}</td><td class="st-${esc(r.status)}">${esc(r.status)}</td></tr>`).join("")}</tbody></table></div>` : `<div class="empty">No type-scoped rules yet.</div>`;
  const notes = a.shared_notes.length ? `<div class="tablewrap"><table class="data"><thead><tr><th>ID</th><th>Well</th><th>Kind</th><th>Text</th><th>By</th><th>Valid</th><th>Status</th></tr></thead><tbody>${a.shared_notes.map((n) => `<tr><td>${chip(n.note_id)}</td><td>${chip(n.asset_id)}</td><td>${esc(n.kind)}</td><td>${esc(n.text)}</td><td>${u(n.author_user_id)}</td><td>${esc(n.valid_from || "")} ${n.valid_to ? "→ " + esc(n.valid_to) : ""}</td><td>${esc(n.status)}</td></tr>`).join("")}</tbody></table></div>` : `<div class="empty">No shared notes or claims yet.</div>`;
  body.innerHTML = `<h2>Shared knowledge audit trail</h2><p class="lead">Everything users have told the copilot that changes answers for everyone. Originals are never overwritten.</p><h2>Corrections</h2>${cor}<h2>Rules scoped to a well type or well</h2>${rules}<h2>Shared notes and claims</h2>${notes}`;
}
function loadRules() {
  const r = state.boot.rules;
  $("#rules-body").innerHTML = `<h2>Rules the copilot applies</h2><p class="lead">Read from the well-type manuals and SOPs in the loaded dataset. Each rule links to the passage it came from.</p><div class="tablewrap"><table class="data"><thead><tr><th>Rule</th><th>Value</th><th>Applies to</th><th>Source</th><th>Passage</th></tr></thead><tbody>${r.map((x) => `<tr><td>${esc(x.key)}</td><td><strong>${esc(x.value)}</strong> ${esc(x.unit)}</td><td>${esc(x.scope)}${x.inherited_from ? ` (from ${esc(x.inherited_from)})` : ""}</td><td>${x.fallback ? `<span class="signal missing_evidence" style="display:inline-flex"><span class="tag">fallback</span></span>` : chip(x.ref)}</td><td class="sub">${esc(x.quote || "")}</td></tr>`).join("")}</tbody></table></div>`;
}

/* ---------- wiring ---------- */
function setView(v) {
  $$(".view").forEach((x) => (x.hidden = x.id !== `view-${v}`)); $$(".rail-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === v));
  if (v === "audit") loadAudit().catch((e) => ($("#audit-body").innerHTML = `<div class="empty">${esc(e.message)}</div>`)); if (v === "rules") loadRules();
}
async function init() {
  try { state.boot = await api("/api/bootstrap"); $("#live-dot").className = "dot on"; }
  catch (e) { $("#live-dot").className = "dot off"; $("#messages").innerHTML = `<div class="errbox" style="max-width:640px;margin:8vh auto"><strong>Cannot reach the server.</strong><div>${esc(e.message)}</div></div>`; return; }
  const b = state.boot, s = b.stats;
  $("#dataset-sub").textContent = `${s.wells} wells · ${s.inspections.toLocaleString()} inspections · ${s.maintenance.toLocaleString()} repairs · ${s.reports.toLocaleString()} reports`;
  $("#asof-val").textContent = b.as_of; $("#model-chip").textContent = `${b.model} · thinking ${b.thinking}`;
  const sel = $("#user-select"); sel.innerHTML = b.users.map((u) => `<option value="${esc(u.user_id)}">${esc(u.name)} — ${esc(u.role.replace(/_/g, " "))}</option>`).join("");
  const saved = store.get("ahc_user"); state.userId = b.users.some((u) => u.user_id === saved) ? saved : (b.users.find((u) => u.role === "production_supervisor") || b.users[0]).user_id; sel.value = state.userId;
  sel.addEventListener("change", () => { state.userId = sel.value; store.set("ahc_user", state.userId); state.convId = null; showHero(); loadConvs(); const n = sel.options[sel.selectedIndex].text.split(" — ")[0]; $("#privacy").textContent = `Private to ${n}`; });
  $("#privacy").textContent = `Private to ${sel.options[sel.selectedIndex].text.split(" — ")[0]}`;
  if (b.warnings?.length) $("#view-chat").insertAdjacentHTML("beforebegin", `<div class="banner" role="alert">${b.warnings.map((w) => `<div>⚠ ${esc(w)}</div>`).join("")}</div>`);
  showHero(); loadConvs();
  const q = new URLSearchParams(location.search);  // ?user=U-201&ask=... opens a ready-to-run demo link
  if (q.get("user") && b.users.some((u) => u.user_id === q.get("user"))) { state.userId = q.get("user"); sel.value = state.userId; $("#privacy").textContent = `Private to ${sel.options[sel.selectedIndex].text.split(" — ")[0]}`; loadConvs(); }
  if (q.get("view")) setView(q.get("view"));
  if (q.get("ref")) openEvidence(q.get("ref"));
  if (q.get("ask")) send(q.get("ask"));
}
document.addEventListener("click", (e) => {
  const r = e.target.closest("[data-ref]"); if (r) { openEvidence(r.dataset.ref); return; }
  const q = e.target.closest("[data-q]"); if (q) send(q.dataset.q);
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });
$("#scrim").addEventListener("click", closeDrawer); $("#drawer-close").addEventListener("click", closeDrawer);
$("#composer").addEventListener("submit", (e) => { e.preventDefault(); send($("#input").value); });
$("#input").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send($("#input").value); } });
$("#input").addEventListener("input", autosize);
$("#new-chat").addEventListener("click", newChat);
$$(".rail-btn").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
$("#asof-btn").addEventListener("click", async () => {
  const v = window.prompt("Reference date for “today” (YYYY-MM-DD):", state.boot.as_of); if (!v) return;
  try { const out = await api("/api/settings", { method: "POST", body: { as_of: v.trim() } }); state.boot.as_of = out.as_of; $("#asof-val").textContent = out.as_of; } catch (e) { alert(e.message); }
});
init();

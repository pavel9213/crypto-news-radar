const DATA_URL = "https://raw.githubusercontent.com/pavel9213/crypto-news-radar/main/data/news.json";
const $ = (selector) => document.querySelector(selector);
const state = { events: [], query: "", project: "", topic: "", signal: "", language: "", trust: "" };
const WATCHED_PROJECTS = [
  "INK", "Soneium", "Base", "Linea", "Ethereum", "Bitcoin", "Solana",
  "Arbitrum", "Optimism", "Polygon", "Avalanche", "Canton", "Plume",
  "Stable", "Somnia", "Kite AI", "Malda", "MYID"
];

const PROJECT_RULES = [
  ["INK", /(?:\$INK|\binkonchain\b|\bink network\b)/i],
  ["Soneium", /\bsoneium\b/i],
  ["Base", /(?:\bbase chain\b|\bbase network\b|\bon base\b|\bbase blockchain\b)/i],
  ["Linea", /\blinea\b/i],
  ["Ethereum", /\bethereum\b|\beth\b/i],
  ["Bitcoin", /\bbitcoin\b|\bbtc\b/i],
  ["Solana", /\bsolana\b|\bsol\b/i],
  ["Arbitrum", /\barbitrum\b/i],
  ["Optimism", /\boptimism\b|\bop mainnet\b/i],
  ["Polygon", /\bpolygon\b|\bpol token\b/i],
  ["Avalanche", /\bavalanche\b|\bavax\b/i],
  ["Canton", /\bcanton network\b|\bcanton blockchain\b/i],
  ["Plume", /\bplume network\b|\bplume blockchain\b/i],
  ["Stable", /\bstablecoin\b|\bstable chain\b|\bstable network\b/i],
  ["Somnia", /\bsomnia\b/i],
  ["Kite AI", /\bkite ai\b/i],
  ["Malda", /\bmalda\b/i],
  ["MYID", /\bmyid\b/i]
];

function getProjects(event) {
  const sourceProjects = {
    "soneium-official-blog": "Soneium",
    "base-official-blog": "Base",
    "linea-official-blog": "Linea"
  };
  const fromSource = sourceProjects[event.source_id];
  const text = [event.title, event.summary, event.source_name].join(" ");
  const detected = PROJECT_RULES.filter(([, pattern]) => pattern.test(text)).map(([name]) => name);
  return [...new Set([...(fromSource ? [fromSource] : []), ...detected])];
}

const SIGNAL_RULES = [
  ["tge", /\b(tge|token generation event|token launch|launch(?:es|ed|ing)? (?:its )?(?:native )?token|token goes live)\b/i],
  ["airdrop", /\b(airdrop|air drop|claim tokens|claim window)\b/i],
  ["snapshot", /\b(snapshot|points snapshot|eligibility snapshot)\b/i],
  ["security", /\b(exploit|hacked?|hackers?|breach|vulnerabilit(?:y|ies)|drained|compromised|security incident|phishing attack)\b/i],
  ["regulation", /\b(regulat(?:ion|ory)|sec |cftc|lawsuit|legislation|court ruling|compliance|ban(?:ned)?|approved by the sec)\b/i],
  ["unconfirmed", /\b(rumou?rs?|unconfirmed|unverified|speculation|allegedly|not confirmed)\b/i]
];

function getSignals(event) {
  const text = [event.title, event.summary].join(" ");
  return SIGNAL_RULES.filter(([, pattern]) => pattern.test(text)).map(([name]) => name);
}

function signalLabel(signal) {
  return ({
    tge: "TGE / token launch",
    airdrop: "Airdrop",
    snapshot: "Snapshot",
    security: "Security alert",
    regulation: "Regulation",
    unconfirmed: "Unconfirmed"
  })[signal] || signal;
}

function safeDate(value) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

function fillSelect(select, values, label) {
  const current = select.value;
  select.replaceChildren(new Option(label, ""));
  [...new Set(values.filter(Boolean))].sort().forEach((value) => {
    select.add(new Option(value.replaceAll("-", " "), value));
  });
  if ([...select.options].some((option) => option.value === current)) select.value = current;
}

function getFilteredEvents() {
  return state.events.filter((event) => {
    const text = [event.title, event.summary, event.source_name, ...(event.topics || [])].join(" ").toLowerCase();
    return (!state.query || text.includes(state.query.toLowerCase()))
      && (!state.project || getProjects(event).includes(state.project))
      && (!state.topic || (event.topics || []).includes(state.topic))
      && (!state.signal || getSignals(event).includes(state.signal))
      && (!state.language || event.language === state.language)
      && (!state.trust || event.source_trust === state.trust);
  });
}

function render() {
  const events = getFilteredEvents();
  $("#result-count").textContent = `${events.length} of ${state.events.length} stories`;
  $("#news-grid").innerHTML = events.map((event) => {
    const topic = (event.topics || ["other"])[0] || "other";
    const published = safeDate(event.published_at);
    const summary = event.summary ? `<p class="story-summary">${escapeHtml(event.summary)}</p>` : "";
    const projects = getProjects(event);
    const signals = getSignals(event);
    const projectBadges = projects.slice(0, 2).map((project) =>
      `<span class="project-pill">${escapeHtml(project)}</span>`
    ).join("");
    const trustLabel = event.source_trust === "primary" ? "Primary source" : "Media report";
    const trustClass = event.source_trust === "primary" ? "trust-primary" : "trust-media";
    const signalBadges = signals.slice(0, 2).map((signal) =>
      `<span class="signal-pill signal-${escapeHtml(signal)}">${escapeHtml(signalLabel(signal))}</span>`
    ).join("");
    return `<article class="story">
      <div class="story-meta"><span class="topic-pill">${escapeHtml(topic)}</span><span>${escapeHtml(published)}</span></div>
      ${projectBadges ? `<div class="project-row">${projectBadges}</div>` : ""}
      ${signalBadges ? `<div class="signal-row">${signalBadges}</div>` : ""}
      <h3><a href="${escapeHtml(event.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(event.title)}</a></h3>
      ${summary}
      <div class="story-footer"><span>${escapeHtml(event.source_name || "Unknown source")} <span class="trust-label ${trustClass}">${trustLabel}</span></span><a href="${escapeHtml(event.url)}" target="_blank" rel="noopener noreferrer">Read source ↗</a></div>
    </article>`;
  }).join("");
  $("#empty-state").hidden = events.length !== 0;
  $("#news-grid").hidden = events.length === 0;
  if (state.events.length) $("#status").hidden = true;
}

const SOURCE_NAMES = {
  "coindesk": "CoinDesk", "cointelegraph": "Cointelegraph",
  "ethereum-blog": "Ethereum Foundation", "bitcoin-magazine": "Bitcoin Magazine",
  "decrypt": "Decrypt", "nasa-technology": "NASA Technology",
  "soneium-official-blog": "Soneium", "base-official-blog": "Base",
  "linea-official-blog": "Linea"
};

function renderSourceHealth(sources, generatedAt) {
  const grid = $("#source-health-grid");
  if (!Array.isArray(sources) || !sources.length) {
    grid.innerHTML = '<p class="source-health-empty">No source health data is available in this collection.</p>';
    $("#source-health-summary").textContent = "No checks available";
    $("#source-health-updated").textContent = "";
    return;
  }
  const healthy = sources.filter(source => source.ok && Number(source.items) > 0).length;
  const warnings = sources.filter(source => !source.ok && !source.error).length;
  const errors = sources.filter(source => Boolean(source.error)).length;
  $("#source-health-summary").textContent = `${healthy}/${sources.length} sources healthy · ${warnings} warnings · ${errors} errors`;
  grid.innerHTML = sources.map(source => {
    const isHealthy = Boolean(source.ok && Number(source.items) > 0);
    const hasError = Boolean(source.error);
    const status = isHealthy ? "Operational" : hasError ? "Connection error" : "No stories found";
    const statusClass = isHealthy ? "healthy" : hasError ? "failed" : "warning";
    const name = SOURCE_NAMES[source.source_id] || source.source_id.replaceAll("-", " ");
    const detail = isHealthy ? `${Number(source.items)} stories collected`
      : hasError ? escapeHtml(source.error) : "Feed responded, but no article links were collected";
    return `<article class="source-health-card">
      <div class="source-health-card-top"><strong>${escapeHtml(name)}</strong><span class="health-dot ${statusClass}" aria-label="${status}"></span></div>
      <span class="source-health-status ${statusClass}">${status}</span><p>${detail}</p>
    </article>`;
  }).join("");
  $("#source-health-updated").textContent = generatedAt ? `Last checked: ${safeDate(generatedAt)}` : "Check time unavailable";
}

const PROJECT_MONITOR = [
  { name: "INK", sourceId: null, url: "https://inkonchain.com/", note: "Official hub only · automated feed not connected" },
  { name: "Soneium", sourceId: "soneium-official-blog", url: "https://soneium.org/en/blog" },
  { name: "Base", sourceId: "base-official-blog", url: "https://www.base.org/blog" },
  { name: "Linea", sourceId: "linea-official-blog", url: "https://linea.build/blog" }
];

function renderProjectMonitor(sources) {
  const sourceMap = new Map((Array.isArray(sources) ? sources : []).map(source => [source.source_id, source]));
  $("#project-monitor-grid").innerHTML = PROJECT_MONITOR.map(project => {
    const source = project.sourceId ? sourceMap.get(project.sourceId) : null;
    const stories = state.events.filter(event => getProjects(event).includes(project.name))
      .sort((a, b) => new Date(b.published_at || b.collected_at || 0) - new Date(a.published_at || a.collected_at || 0));
    const connected = Boolean(project.sourceId);
    const healthy = Boolean(source && source.ok && Number(source.items) > 0);
    const status = !connected ? "Official feed not connected" : healthy ? "Official feed operational" : source?.error ? "Source error" : "No recent stories";
    const statusClass = !connected ? "not-connected" : healthy ? "healthy" : source?.error ? "failed" : "warning";
    const latest = stories.slice(0, 2).map(event =>
      `<li><a href="${escapeHtml(event.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(event.title)}</a><span>${escapeHtml(event.source_name || "Source")} · ${escapeHtml(safeDate(event.published_at || event.collected_at))}</span></li>`
    ).join("");
    const feedNote = connected
      ? (source ? `${Number(source.items || 0)} items in latest collection` : "Waiting for collector data")
      : "Only the official project hub is linked; no automated INK feed is configured yet.";
    return `<article class="project-monitor-card project-${project.name.toLowerCase()}">
      <div class="project-monitor-top"><h3>${escapeHtml(project.name)}</h3><span class="project-monitor-count">${stories.length} stories</span></div>
      <span class="project-monitor-status ${statusClass}"><i></i>${status}</span>
      <p class="project-monitor-note">${escapeHtml(feedNote)}</p>
      ${latest ? `<ul class="project-monitor-latest">${latest}</ul>` : '<p class="project-monitor-empty">No matching stories in the current collection.</p>'}
      <div class="project-monitor-actions"><button type="button" data-project-filter="${escapeHtml(project.name)}">View in news feed</button><a href="${escapeHtml(project.url)}" target="_blank" rel="noopener noreferrer">Official site ↗</a></div>
    </article>`;
  }).join("");
}

function updateStats(payload) {
  renderProjectMonitor(payload.sources);
  $("#total-count").textContent = String(payload.event_count ?? state.events.length);
  $("#source-count").textContent = String(payload.source_count ?? "—");
  $("#updated-at").textContent = payload.generated_at ? safeDate(payload.generated_at) : "Unknown";
  renderSourceHealth(payload.sources, payload.generated_at);
}

async function loadNews() {
  const button = $("#refresh");
  button.disabled = true;
  button.textContent = "Loading…";
  $("#status").hidden = false;
  $("#status").textContent = "Loading collected news…";
  try {
    const response = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`News data is not available yet (HTTP ${response.status}).`);
    const payload = await response.json();
    if (!Array.isArray(payload.events)) throw new Error("The news data has an unexpected format.");
    state.events = payload.events;
    fillSelect($("#project"), [...WATCHED_PROJECTS, ...state.events.flatMap((event) => getProjects(event))], "All projects");
    fillSelect($("#topic"), state.events.flatMap((event) => event.topics || []), "All topics");
    fillSelect($("#language"), state.events.map((event) => event.language), "All languages");
    updateStats(payload);
    $("#status").hidden = state.events.length > 0;
    if (!state.events.length) $("#status").textContent = "The collector ran, but no stories are available yet. Check the source status in the generated data.";
    render();
  } catch (error) {
    state.events = [];
    $("#status").hidden = false;
    $("#status").textContent = `${error.message} Run the “Collect crypto news” workflow in GitHub Actions, then refresh this page.`;
    $("#news-grid").innerHTML = "";
    $("#result-count").textContent = "Feed not loaded";
    $("#total-count").textContent = "0";
    $("#source-count").textContent = "—";
    $("#updated-at").textContent = "Waiting";
  } finally {
    button.disabled = false;
    button.textContent = "↻ Refresh";
  }
}

$("#search").addEventListener("input", (event) => { state.query = event.target.value.trim(); render(); });
$("#project").addEventListener("change", (event) => { state.project = event.target.value; render(); });
$("#topic").addEventListener("change", (event) => { state.topic = event.target.value; render(); });
$("#signal").addEventListener("change", (event) => { state.signal = event.target.value; render(); });
$("#language").addEventListener("change", (event) => { state.language = event.target.value; render(); });
$("#trust").addEventListener("change", (event) => { state.trust = event.target.value; render(); });
$("#refresh").addEventListener("click", loadNews);
$("#project-monitor-grid").addEventListener("click", (event) => {
  const button = event.target.closest("[data-project-filter]");
  if (!button) return;
  state.project = button.dataset.projectFilter;
  $("#project").value = state.project;
  render();
  document.querySelector(".toolbar").scrollIntoView({ behavior: "smooth", block: "center" });
});
$("#clear-filters").addEventListener("click", () => {
  state.query = ""; state.project = ""; state.topic = ""; state.signal = ""; state.language = ""; state.trust = "";
  $("#search").value = ""; $("#project").value = ""; $("#topic").value = ""; $("#signal").value = ""; $("#language").value = ""; $("#trust").value = "";
  render();
});

loadNews();

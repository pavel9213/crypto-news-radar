const DATA_URL = "./data/news.json";
const $ = (selector) => document.querySelector(selector);
const state = { events: [], query: "", topic: "", language: "" };

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
      && (!state.topic || (event.topics || []).includes(state.topic))
      && (!state.language || event.language === state.language);
  });
}

function render() {
  const events = getFilteredEvents();
  $("#result-count").textContent = `${events.length} of ${state.events.length} stories`;
  $("#news-grid").innerHTML = events.map((event) => {
    const topic = (event.topics || ["other"])[0] || "other";
    const published = safeDate(event.published_at);
    const summary = event.summary ? `<p class="story-summary">${escapeHtml(event.summary)}</p>` : "";
    return `<article class="story">
      <div class="story-meta"><span class="topic-pill">${escapeHtml(topic)}</span><span>${escapeHtml(published)}</span></div>
      <h3><a href="${escapeHtml(event.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(event.title)}</a></h3>
      ${summary}
      <div class="story-footer"><span>${escapeHtml(event.source_name || "Unknown source")}</span><a href="${escapeHtml(event.url)}" target="_blank" rel="noopener noreferrer">Read source ↗</a></div>
    </article>`;
  }).join("");
  $("#empty-state").hidden = events.length !== 0;
  $("#news-grid").hidden = events.length === 0;
  if (state.events.length) $("#status").hidden = true;
}

function updateStats(payload) {
  $("#total-count").textContent = String(payload.event_count ?? state.events.length);
  $("#source-count").textContent = String(payload.source_count ?? "—");
  $("#updated-at").textContent = payload.generated_at ? safeDate(payload.generated_at) : "Unknown";
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
    fillSelect($("#topic"), state.events.flatMap((event) => event.topics || []), "All topics");
    fillSelect($("#language"), state.events.map((event) => event.language), "All languages");
    updateStats(payload);
    $("#status").hidden = state.events.length > 0;
    if (!state.events.length) $("#status").textContent = "The collector ran, but no stories are available yet. Check the source status in the generated data.";
    render();
  } catch (error) {
    state.events = [];
    $("#status").hidden = false;
    $("#status").textContent = `${error.message} The first scheduled collection will create data/news.json; run the “Collect crypto news” workflow in GitHub Actions to try it now.`;
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
$("#topic").addEventListener("change", (event) => { state.topic = event.target.value; render(); });
$("#language").addEventListener("change", (event) => { state.language = event.target.value; render(); });
$("#refresh").addEventListener("click", loadNews);
$("#clear-filters").addEventListener("click", () => {
  state.query = ""; state.topic = ""; state.language = "";
  $("#search").value = ""; $("#topic").value = ""; $("#language").value = "";
  render();
});

loadNews();

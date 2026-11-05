const DATA_URL = "https://raw.githubusercontent.com/pavel9213/crypto-news-radar/main/data/news.json";
const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

function safeDate(value) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "full", timeStyle: "short" }).format(date);
}

const PROJECT_RULES = [
  ["INK", /(?:\$INK|\binkonchain\b|\bink network\b)/i],
  ["Soneium", /\bsoneium\b/i], ["Base", /(?:\bbase chain\b|\bbase network\b|\bon base\b|\bbase blockchain\b)/i],
  ["Linea", /\blinea\b/i], ["Ethereum", /\bethereum\b|\beth\b/i], ["Bitcoin", /\bbitcoin\b|\bbtc\b/i],
  ["Solana", /\bsolana\b|\bsol\b/i], ["Arbitrum", /\barbitrum\b/i], ["Optimism", /\boptimism\b|\bop mainnet\b/i],
  ["Polygon", /\bpolygon\b|\bpol token\b/i], ["Avalanche", /\bavalanche\b|\bavax\b/i],
  ["Canton", /\bcanton network\b|\bcanton blockchain\b/i], ["Plume", /\bplume network\b|\bplume blockchain\b/i],
  ["Somnia", /\bsomnia\b/i], ["Kite AI", /\bkite ai\b/i], ["Malda", /\bmalda\b/i], ["MYID", /\bmyid\b/i]
];
const SOURCE_PROJECTS = {
  "ink-kraken-blog": "INK", "soneium-official-blog": "Soneium",
  "base-official-blog": "Base", "linea-official-blog": "Linea"
};
const SIGNAL_RULES = [
  ["tge", /\b(tge|token generation event|token launch|launch(?:es|ed|ing)? (?:its )?(?:native )?token|token goes live)\b/i],
  ["airdrop", /\b(airdrop|air drop|claim tokens|claim window)\b/i],
  ["snapshot", /\b(snapshot|points snapshot|eligibility snapshot)\b/i],
  ["security", /\b(exploit|hacked?|hackers?|breach|vulnerabilit(?:y|ies)|drained|compromised|security incident|phishing attack)\b/i],
  ["regulation", /\b(regulat(?:ion|ory)|sec |cftc|lawsuit|legislation|court ruling|compliance|ban(?:ned)?|approved by the sec)\b/i],
  ["unconfirmed", /\b(rumou?rs?|unconfirmed|unverified|speculation|allegedly|not confirmed)\b/i]
];
const SIGNAL_LABELS = {
  tge: "TGE / token launch", airdrop: "Airdrop", snapshot: "Snapshot",
  security: "Security alert", regulation: "Regulation", unconfirmed: "Unconfirmed"
};

function getProjects(event) {
  const text = [event.title, event.summary, event.source_name].join(" ");
  const detected = PROJECT_RULES.filter(([, pattern]) => pattern.test(text)).map(([name]) => name);
  return [...new Set([...(SOURCE_PROJECTS[event.source_id] ? [SOURCE_PROJECTS[event.source_id]] : []), ...detected])];
}
function getSignals(event) {
  const text = [event.title, event.summary].join(" ");
  return SIGNAL_RULES.filter(([, pattern]) => pattern.test(text)).map(([name]) => name);
}
function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch { return ""; }
}
function storyImage(event) {
  const imageUrl = safeExternalUrl(event.image_url);
  return imageUrl
    ? `<figure class="article-hero-image"><img src="${escapeHtml(imageUrl)}" alt="" referrerpolicy="no-referrer"><figcaption>Image provided by the original publisher</figcaption></figure>`
    : '<div class="article-image-fallback"><span>CRYPTO NEWS RADAR</span></div>';
}
function renderRelated(event, events) {
  const projects = getProjects(event);
  const topics = event.topics || [];
  return events.filter(item => item.id !== event.id).map(item => {
    const sharedProjects = getProjects(item).filter(name => projects.includes(name)).length;
    const sharedTopics = (item.topics || []).filter(name => topics.includes(name)).length;
    return { item, score: sharedProjects * 3 + sharedTopics };
  }).filter(entry => entry.score > 0).sort((a, b) => b.score - a.score)
    .slice(0, 3).map(({ item }) => `<article class="related-card">
      <span>${escapeHtml((item.topics || ["Latest"])[0])}</span>
      <h3><a href="stories/${encodeURIComponent(item.id || "")}.html">${escapeHtml(item.title)}</a></h3>
      <p>${escapeHtml(item.source_name || "News source")} · ${escapeHtml(safeDate(item.published_at || item.collected_at))}</p>
    </article>`).join("");
}

async function loadArticle() {
  const status = $("#article-status");
  const content = $("#article-content");
  const id = new URLSearchParams(window.location.search).get("id");
  if (!id) {
    status.textContent = "No story was selected. Return to the news desk and choose a headline.";
    return;
  }
  try {
    const response = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`News data is temporarily unavailable (HTTP ${response.status}).`);
    const payload = await response.json();
    const event = (payload.events || []).find(item => item.id === id);
    if (!event) throw new Error("This story is no longer in the latest collection. It may have expired from the feed.");
    const originalUrl = safeExternalUrl(event.url);
    const projects = getProjects(event);
    const signals = getSignals(event);
    const topics = (event.topics || []).map(topic => `<span class="article-tag">${escapeHtml(topic)}</span>`).join("");
    const projectTags = projects.map(name => `<span class="article-tag article-project-tag">${escapeHtml(name)}</span>`).join("");
    const signalTags = signals.map(name => `<span class="signal-pill signal-${escapeHtml(name)}">${escapeHtml(SIGNAL_LABELS[name] || name)}</span>`).join("");
    const trust = event.source_trust === "primary" ? "Primary source" : "Media report";
    content.innerHTML = `
      <div class="article-kicker"><span>CRYPTO NEWS RADAR / STORY</span><span>${escapeHtml(trust)}</span></div>
      <div class="article-tags">${topics}${projectTags}</div>
      <h1>${escapeHtml(event.title)}</h1>
      <div class="article-byline"><strong>${escapeHtml(event.source_name || "News source")}</strong><span>${escapeHtml(safeDate(event.published_at || event.collected_at))}</span></div>
      ${storyImage(event)}
      ${event.summary ? `<div class="article-summary"><span>THE STORY</span><p>${escapeHtml(event.summary)}</p></div>` : '<div class="article-summary"><span>THE STORY</span><p>The collector has captured this headline, but the publisher did not provide a summary. Visit the original report for the full article.</p></div>'}
      ${signalTags ? `<section class="article-signals"><h2>Detected signals</h2><div>${signalTags}</div><p>Signals are automated keyword hints. They are not editorial verification or confirmation of the underlying claim.</p></section>` : ""}
      <div class="article-source-box"><div><span>ORIGINAL PUBLICATION</span><strong>${escapeHtml(event.source_name || "Original source")}</strong></div>${originalUrl ? `<a href="${escapeHtml(originalUrl)}" target="_blank" rel="noopener noreferrer">Read original report ↗</a>` : '<span>Original link unavailable</span>'}</div>
      <p class="article-disclaimer">Crypto News Radar aggregates headlines and available publisher summaries. This page does not reproduce the full original article. Verify important claims with the publisher and primary sources. Not financial advice.</p>`;
    content.hidden = false;
    status.hidden = true;
    document.title = `${event.title} — Crypto News Radar`;
    const related = renderRelated(event, payload.events || []);
    if (related) {
      $("#related-stories").innerHTML = related;
      $("#related-section").hidden = false;
    }
  } catch (error) {
    status.textContent = `${error.message} Return to the news desk to browse the latest stories.`;
  }
}
loadArticle();

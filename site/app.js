/* Progressive enhancement. The built HTML contains the complete public list. */
"use strict";

const shortMonths = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function normalize(value) {
  return String(value).normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function matchesEvent(event, filters, today) {
  if (!event.published) return false;
  if (filters.view === "upcoming" && event.end_date < today) return false;
  if (filters.view === "past" && event.end_date >= today) return false;
  if (filters.region && event.location.region !== filters.region) return false;
  if (filters.topic && !event.topics.includes(filters.topic)) return false;
  if (filters.format && !event.formats.includes(filters.format)) return false;
  const haystack = normalize([event.id, event.title, event.summary, ...Object.values(event.location),
    ...event.topics, ...event.formats, event.notes].join(" "));
  return normalize(filters.q || "").trim().split(/\s+/).every(word => haystack.includes(word));
}

function summaryFor(event, now = new Date()) {
  const instant = new Date(now);
  const today = instant.toISOString().slice(0, 10);
  const future = event.deadlines.filter(item => item.cutoff_utc
    ? Date.parse(item.cutoff_utc) >= instant.getTime()
    : item.date >= today).sort((a, b) =>
      Date.parse(a.cutoff_utc || a.date + "T00:00:00Z") - Date.parse(b.cutoff_utc || b.date + "T00:00:00Z"));
  if (!future.length) return event.deadlines.length ? "Recorded deadlines have passed" : "Deadlines not recorded";
  const item = future[0];
  const [year, month, day] = item.date.split("-").map(Number);
  const date = `${day} ${shortMonths[month - 1]} ${year}`;
  return item.kind + " · " + date + (item.time ? " · " + item.time + " " + item.timezone : "");
}

if (typeof module !== "undefined" && module.exports) module.exports = {normalize, matchesEvent, summaryFor};

if (typeof document !== "undefined") {
  const root = document.documentElement;
  const themeField = document.getElementById("theme");
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
  const themeKey = "conferences-color-theme";

  function applyTheme(value) {
    const theme = ["light", "dark"].includes(value) ? value : "system";
    if (theme === "system") delete root.dataset.theme;
    else root.dataset.theme = theme;
    themeField.value = theme;
    const dark = theme === "dark" || (theme === "system" && systemTheme.matches);
    for (const meta of document.querySelectorAll('meta[name="theme-color"]')) {
      meta.content = dark ? "#121c19" : "#f7f7f2";
    }
  }

  applyTheme(root.dataset.theme);
  document.getElementById("theme-control").hidden = false;
  themeField.addEventListener("change", () => {
    applyTheme(themeField.value);
    try {
      if (themeField.value === "system") localStorage.removeItem(themeKey);
      else localStorage.setItem(themeKey, themeField.value);
    } catch (_) { /* The selected theme still works for this visit. */ }
  });
  systemTheme.addEventListener("change", () => applyTheme(themeField.value));
  window.addEventListener("storage", event => {
    if (event.key === themeKey || event.key === null) applyTheme(event.newValue);
  });

}

if (typeof document !== "undefined" && document.getElementById("event-data")) {
  const events = JSON.parse(document.getElementById("event-data").textContent);
  const cards = new Map([...document.querySelectorAll("[data-event-id]")].map(card => [card.dataset.eventId, card]));
  const fields = Object.fromEntries(["search", "region", "topic", "format"].map(key => [key, document.getElementById(key)]));
  const defaults = {q: "", region: "", topic: "", format: "", view: "upcoming"};
  let filters = {...defaults};

  function readURL() {
    const params = new URLSearchParams(location.search);
    filters = {...defaults};
    filters.q = params.get("q") || "";
    for (const name of ["region", "topic", "format"]) {
      const value = params.get(name) || "";
      filters[name] = [...fields[name].options].some(option => option.value === value) ? value : "";
    }
    if (["upcoming", "past", "all"].includes(params.get("view"))) filters.view = params.get("view");
    fields.search.value = filters.q;
    for (const name of ["region", "topic", "format"]) fields[name].value = filters[name];
  }

  function updateURL() {
    const url = new URL(location.href);
    for (const [key, value] of Object.entries(filters)) {
      if (value && value !== defaults[key]) url.searchParams.set(key, value);
      else url.searchParams.delete(key);
    }
    try { history.replaceState(null, "", url); } catch (_) { /* Local file previews still work. */ }
  }

  function apply(writeURL = true) {
    const now = new Date();
    const currentDate = now.toISOString().slice(0, 10);
    let visible = 0;
    for (const event of events) {
      const card = cards.get(event.id);
      card.hidden = !matchesEvent(event, filters, currentDate);
      if (!card.hidden) visible += 1;
      const summary = card.querySelector(".deadline-summary");
      const summaryText = summaryFor(event, now);
      if (summary.textContent !== summaryText) summary.textContent = summaryText;
    }
    for (const group of document.querySelectorAll(".month-group")) {
      const count = [...group.querySelectorAll(".event")].filter(card => !card.hidden).length;
      group.hidden = count === 0;
      group.querySelector(".month-count").textContent = String(count).padStart(2, "0");
    }
    const count = document.querySelector(".result-count");
    const countText = visible + " of " + events.length + " meetings";
    if (count.textContent !== countText) count.textContent = countText;
    document.getElementById("directory-title").textContent = {
      upcoming: "Upcoming & ongoing", past: "Past meetings", all: "All listed meetings"
    }[filters.view];
    document.getElementById("empty-state").hidden = visible !== 0;
    for (const button of document.querySelectorAll("[data-view]")) button.setAttribute("aria-pressed", String(button.dataset.view === filters.view));
    if (writeURL) updateURL();
  }

  function clear(view = "upcoming") {
    filters = {...defaults, view};
    for (const field of Object.values(fields)) field.value = "";
    apply();
  }

  function revealHash() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    const card = cards.get(id);
    if (!card) return;
    if (card.hidden) clear("all");
    card.querySelector("details").open = true;
    card.scrollIntoView({block: "start"});
  }

  readURL();
  document.documentElement.classList.add("js");
  apply(false);
  revealHash();
  document.getElementById("filters").addEventListener("submit", event => event.preventDefault());
  fields.search.addEventListener("input", () => { filters.q = fields.search.value; apply(); });
  for (const name of ["region", "topic", "format"]) fields[name].addEventListener("change", () => { filters[name] = fields[name].value; apply(); });
  for (const button of document.querySelectorAll("[data-view]")) button.addEventListener("click", () => { filters.view = button.dataset.view; apply(); });
  document.getElementById("clear-filters").addEventListener("click", () => clear());
  document.getElementById("empty-reset").addEventListener("click", () => clear("all"));
  window.addEventListener("popstate", () => { readURL(); apply(false); revealHash(); });
  window.addEventListener("hashchange", revealHash);
  window.addEventListener("pageshow", () => apply(false));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) apply(false); });
  window.setInterval(() => { if (!document.hidden) apply(false); }, 60_000);
}

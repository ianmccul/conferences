/* Progressive enhancement. The built HTML contains the complete public list. */
"use strict";

function normalize(value) {
  return String(value).normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function matchesEvent(event, filters, today) {
  if (!event.published) return false;
  if (filters.view === "upcoming" && event.end_date < today) return false;
  if (filters.view === "past" && event.end_date >= today) return false;
  if (filters.region && event.location.region !== filters.region) return false;
  if (filters.topic && !event.topics.includes(filters.topic)) return false;
  if (filters.format && event.format !== filters.format) return false;
  const haystack = normalize([event.id, event.title, event.summary, ...Object.values(event.location),
    ...event.topics, event.format, event.notes].join(" "));
  return normalize(filters.q || "").trim().split(/\s+/).every(word => haystack.includes(word));
}

function summaryFor(event, today) {
  const future = event.deadlines.filter(item => item.date >= today).sort((a, b) => a.date.localeCompare(b.date));
  if (!future.length) return event.deadlines.length ? "Recorded deadline dates have passed" : "Deadlines not recorded";
  const date = new Intl.DateTimeFormat("en-GB", {day: "numeric", month: "short", year: "numeric", timeZone: "UTC"})
    .format(new Date(future[0].date + "T12:00:00Z"));
  return future[0].kind + " · " + date;
}

if (typeof module !== "undefined" && module.exports) module.exports = {normalize, matchesEvent, summaryFor};

if (typeof document !== "undefined") {
  const events = JSON.parse(document.getElementById("event-data").textContent);
  const today = () => new Date().toISOString().slice(0, 10);
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
    const currentDate = today();
    let visible = 0;
    for (const event of events) {
      const card = cards.get(event.id);
      card.hidden = !matchesEvent(event, filters, currentDate);
      if (!card.hidden) visible += 1;
      card.querySelector(".deadline-summary").textContent = summaryFor(event, currentDate);
    }
    for (const group of document.querySelectorAll(".month-group")) {
      const count = [...group.querySelectorAll(".event")].filter(card => !card.hidden).length;
      group.hidden = count === 0;
      group.querySelector(".month-count").textContent = String(count).padStart(2, "0");
    }
    document.querySelector(".result-count").textContent = visible + " of " + events.length + " meetings";
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
}

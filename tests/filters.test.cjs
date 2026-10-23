const test = require("node:test");
const assert = require("node:assert/strict");
const {execFileSync} = require("node:child_process");
const path = require("node:path");
const {matchesEvent, summaryFor} = require("../site/app.js");

const event = {
  id: "tnsaa-2026", title: "Tensor Network States: Algorithms and Applications",
  summary: "A meeting on tensor-network algorithms", start_date: "2026-12-29", end_date: "2027-01-05",
  location: {city: "Zürich", country: "Switzerland", region: "Europe", venue: "Example Institute"},
  formats: ["Workshop"], topics: ["Tensor networks", "Numerical methods"], notes: "", published: true,
  deadlines: []
};
const defaults = {q: "", region: "", topic: "", format: "", view: "upcoming"};

test("ongoing meetings remain upcoming through the final date, including across a year", () => {
  assert.ok(matchesEvent(event, defaults, "2027-01-01"));
  assert.ok(matchesEvent(event, defaults, "2027-01-05"));
  assert.ok(!matchesEvent(event, defaults, "2027-01-06"));
  assert.ok(matchesEvent(event, {...defaults, view: "past"}, "2027-01-06"));
  assert.ok(!matchesEvent(event, {...defaults, view: "past"}, "2027-01-05"));
  assert.ok(matchesEvent(event, {...defaults, view: "all"}, "2028-01-01"));
});

test("search combines words, ignores accents and case, and includes short event IDs", () => {
  assert.ok(matchesEvent(event, {...defaults, q: "ZURICH network"}, "2026-10-23"));
  assert.ok(matchesEvent(event, {...defaults, q: " TNSAA "}, "2026-10-23"));
  assert.ok(!matchesEvent(event, {...defaults, q: "Zurich superconductivity"}, "2026-10-23"));
});

test("region, topic and meeting-type filters combine with search", () => {
  const filter = {...defaults, q: "algorithms", region: "Europe", topic: "Tensor networks", format: "Workshop"};
  assert.ok(matchesEvent(event, filter, "2026-10-23"));
  for (const mismatch of [{region: "Asia"}, {topic: "Gauge theories"}, {format: "School"}]) {
    assert.ok(!matchesEvent(event, {...filter, ...mismatch}, "2026-10-23"));
  }
});

test("combined schools and conferences match either type and both types are searchable", () => {
  const combined = {...event, formats: ["School", "Conference"]};
  for (const format of ["School", "Conference"]) {
    assert.ok(matchesEvent(combined, {...defaults, format}, "2026-10-23"), format);
    assert.ok(matchesEvent(combined, {...defaults, q: format.toLowerCase()}, "2026-10-23"), format);
    assert.ok(matchesEvent(combined, {...defaults, format, region: "Europe", topic: "Tensor networks", q: "Zurich"}, "2026-10-23"));
    assert.ok(!matchesEvent(combined, {...defaults, format, region: "Asia"}, "2026-10-23"));
  }
  assert.ok(matchesEvent(combined, defaults, "2026-10-23"));
  assert.ok(!matchesEvent(combined, {...defaults, format: "Workshop"}, "2026-10-23"));
  assert.ok(!matchesEvent(combined, {...defaults, format: "Programme"}, "2026-10-23"));
  assert.ok(!matchesEvent({...event, formats: ["School"]}, {...defaults, format: "Conference"}, "2026-10-23"));
});

test("unpublished records are excluded from every view", () => {
  for (const view of ["upcoming", "past", "all"]) {
    assert.ok(!matchesEvent({...event, published: false}, {...defaults, view}, "2026-10-23"));
  }
});

test("next deadline date is selected in order and the deadline day is included", () => {
  const withDeadlines = {...event, deadlines: [
    {kind: "Registration", date: "2026-12-01"},
    {kind: "Abstracts", date: "2026-11-01"},
    {kind: "Funding", date: "2026-10-01"},
  ]};
  assert.equal(summaryFor(withDeadlines, "2026-11-01"), "Abstracts · 1 Nov 2026");
  assert.equal(summaryFor(withDeadlines, "2026-11-02"), "Registration · 1 Dec 2026");
  assert.equal(withDeadlines.deadlines[0].kind, "Registration", "summary must not reorder source data");
});

test("absent or expired dates do not imply registration is open or closed", () => {
  assert.equal(summaryFor(event, "2026-10-23"), "Deadlines not recorded");
  assert.equal(summaryFor({...event, deadlines: [{date: "2026-10-01", kind: "Abstracts"}]}, "2026-10-23"),
    "Recorded deadlines have passed");
});

test("timed deadlines expire at their UTC cutoff, not at a calendar-date boundary", () => {
  const withDeadlines = {...event, deadlines: [{kind: "Poster", date: "2026-12-04", time: "23:59",
    timezone: "AoE", cutoff_utc: "2026-12-05T11:59:00Z"}]};
  for (const now of ["2026-12-05T00:00:00Z", "2026-12-05T11:58:59Z", "2026-12-05T11:59:00Z"]) {
    assert.equal(summaryFor(withDeadlines, now), "Poster · 4 Dec 2026 · 23:59 AoE");
  }
  assert.equal(summaryFor(withDeadlines, "2026-12-05T11:59:01Z"), "Recorded deadlines have passed");
});

test("deadline ordering uses cutoff instants across different timezones", () => {
  const withDeadlines = {...event, deadlines: [
    {kind: "Poster", date: "2026-12-04", time: "23:59", timezone: "AoE", cutoff_utc: "2026-12-05T11:59:00Z"},
    {kind: "Abstract", date: "2026-12-05", time: "09:00", timezone: "Asia/Tokyo", cutoff_utc: "2026-12-05T00:00:00Z"},
  ]};
  assert.equal(summaryFor(withDeadlines, "2026-12-04T22:00:00Z"), "Abstract · 5 Dec 2026 · 09:00 Asia/Tokyo");
  assert.equal(summaryFor(withDeadlines, "2026-12-05T00:00:01Z"), "Poster · 4 Dec 2026 · 23:59 AoE");
});

test("date-only deadlines retain calendar-date behavior without an invented cutoff", () => {
  const withDeadlines = {...event, deadlines: [{kind: "Registration", date: "2026-12-04", time: null, timezone: null, cutoff_utc: null}]};
  assert.equal(summaryFor(withDeadlines, "2026-12-04T23:59:59Z"), "Registration · 4 Dec 2026");
  assert.equal(summaryFor(withDeadlines, "2026-12-05T00:00:00Z"), "Recorded deadlines have passed");
});

test("built HTML and browser summaries agree before and after every recorded timed cutoff", () => {
  const script = `
import json, sys
from datetime import timedelta
from html import escape
from pathlib import Path
sys.path.insert(0, 'scripts')
import build
data = build.validate(json.loads(Path('data/events.json').read_text()))
by_id = {e['id']: e for e in data['events']}
cases = []
for event in data['events']:
    for deadline in event['deadlines']:
        cutoff = build.deadline_cutoff(deadline)
        if cutoff is None:
            continue
        for offset in [-1, 0, 1]:
            now = cutoff + timedelta(seconds=offset)
            summary = build.deadline_summary(event, now)
            html = build.render_event(event, now, by_id)
            assert '<span class="deadline-summary">' + escape(summary) + '</span>' in html
            cases.append({'event': build.browser_event(event), 'now': now.isoformat(), 'summary': summary})
print(json.dumps(cases))
`;
  const cases = JSON.parse(execFileSync("python3", ["-c", script], {cwd: path.resolve(__dirname, ".."), encoding: "utf8"}));
  assert.ok(cases.length >= 15, "exercise the recorded AoE deadlines and every additional timed deadline");
  for (const item of cases) {
    assert.equal(summaryFor(item.event, item.now), item.summary, `${item.event.id} at ${item.now}`);
  }
});

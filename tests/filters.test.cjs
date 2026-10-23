const test = require("node:test");
const assert = require("node:assert/strict");
const {matchesEvent, summaryFor} = require("../site/app.js");

const event = {
  id: "tnsaa-2026", title: "Tensor Network States: Algorithms and Applications",
  summary: "A meeting on tensor-network algorithms", start_date: "2026-12-29", end_date: "2027-01-05",
  location: {city: "Zürich", country: "Switzerland", region: "Europe", venue: "Example Institute"},
  format: "Workshop", topics: ["Tensor networks", "Numerical methods"], notes: "", published: true,
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
    "Recorded deadline dates have passed");
});
